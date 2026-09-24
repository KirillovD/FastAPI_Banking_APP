import { expect, test, type Page } from "@playwright/test";
import { mockApi, openView } from "./fixtures";

async function ready(page: Page) {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();
}
async function paymentForm(page: Page) {
  await openView(page, "Simulator");
  return page.getByRole("form", { name: "Card payment", exact: true });
}

test("synthetic card payment submits once and reads updated data", async ({ page }) => {
  const mock = await mockApi(page);
  await ready(page);
  const form = await paymentForm(page);
  await form.getByRole("button", { name: "Approve synthetic payment" }).click();
  await expect(form.getByRole("status")).toHaveText("Payment approved. Displayed data updated.");
  const writes = mock.calls.filter((call) => call.path === "/payments/" && call.method === "POST");
  expect(writes).toHaveLength(1);
  expect(writes[0].body).toMatchObject({ amount: "42.50", terminal_data: { payment_type: "pos", mcc_code: "5411", merchant_name: "REWE München" } });
  expect(writes[0].body).not.toHaveProperty("cvv");
  await openView(page, "Transactions");
  await expect(page.getByRole("button", { name: /^View transaction 28:/ })).toBeVisible();
  await openView(page, "Credit Center");
  await expect(page.locator(".utilization-meta")).toContainText("230,00");
});

test("invalid PIN pattern is blocked before any request", async ({ page }) => {
  const mock = await mockApi(page);
  await ready(page);
  const form = await paymentForm(page);
  for (const value of ["12", "12ab", "12345"]) {
    await form.getByLabel("PIN", { exact: true }).fill(value);
    await form.getByRole("button", { name: "Approve synthetic payment" }).click();
    expect(await form.getByLabel("PIN", { exact: true }).evaluate((element: HTMLInputElement) => element.validity.patternMismatch)).toBe(true);
  }
  expect(mock.calls.filter((call) => call.method === "POST")).toHaveLength(0);
});

test("online payment uses the synthetic CVV returned by the fixture", async ({ page }) => {
  const mock = await mockApi(page);
  await ready(page);
  const form = await paymentForm(page);
  await form.getByRole("button", { name: "Reveal demo CVV" }).click();
  await expect(form.getByLabel("Payment type")).toHaveValue("online");
  await expect(form.getByLabel("CVV", { exact: true })).toHaveValue("321");
  await form.getByRole("button", { name: "Approve synthetic payment" }).click();
  await expect(form.getByRole("status")).toContainText("Payment approved.");
  const write = mock.calls.find((call) => call.path === "/payments/" && call.method === "POST");
  expect(write?.body).toMatchObject({ cvv: "321", terminal_data: { payment_type: "online" } });
  expect(write?.body).not.toHaveProperty("pin_block");
});

test("money input rejects zero, negative values and excess precision", async ({ page }) => {
  const mock = await mockApi(page);
  await ready(page);
  const form = await paymentForm(page);
  const input = form.getByLabel(/^Amount/);
  await input.fill("0");
  await form.getByRole("button", { name: "Approve synthetic payment" }).click();
  await expect(form.getByRole("alert")).toContainText("greater than zero");
  for (const value of ["-2", "1.234"]) {
    await input.fill(value);
    await form.getByRole("button", { name: "Approve synthetic payment" }).click();
    expect(await input.evaluate((element: HTMLInputElement) => element.validity.patternMismatch)).toBe(true);
  }
  expect(mock.calls.filter((call) => call.method === "POST")).toHaveLength(0);
  await input.fill("42,50");
  await form.getByRole("button", { name: "Approve synthetic payment" }).click();
  await expect(form.getByRole("status")).toContainText("Payment approved.");
  expect(mock.calls.find((call) => call.path === "/payments/")?.body?.amount).toBe("42.50");
});

test("bank transfer normalizes IBAN without adding an MCC", async ({ page }) => {
  const mock = await mockApi(page);
  await ready(page);
  await openView(page, "Simulator");
  const form = page.getByRole("form", { name: "Bank transfer", exact: true });
  await form.getByLabel("Recipient IBAN").fill("de39 100000000000000102");
  await form.getByLabel("Recipient name").fill("Demo User");
  await form.getByRole("button", { name: "Send transfer" }).click();
  await expect(form.getByRole("status")).toContainText("Transfer completed.");
  const write = mock.calls.find((call) => call.path === "/transactions/1" && call.method === "POST");
  expect(write?.body).toEqual({ recipient_iban: "DE39100000000000000102", recipient_name: "Demo User", amount: "25.00", description: "Dinner split" });
});

test("repayment renders the refreshed score response", async ({ page }) => {
  const mock = await mockApi(page);
  await ready(page);
  await openView(page, "Credit Center");
  await page.getByRole("form", { name: "Credit repayment" }).getByRole("button", { name: "Post repayment" }).click();
  await expect(page.getByRole("status")).toContainText("Repayment posted.");
  await expect(page.locator(".score-head h3")).toHaveText("606");
  expect(mock.calls.find((call) => call.path === "/credit-accounts/3/payments")?.body).toEqual({ amount: "50.00" });
});

test("account setup permits zero opening balance and issues synthetic credit", async ({ page }) => {
  const mock = await mockApi(page);
  await ready(page);
  await page.getByRole("button", { name: /Add product/ }).click();
  const form = page.getByRole("form", { name: "Open an account", exact: true });
  await form.getByLabel(/^Starting balance/).fill("0");
  await form.getByRole("button", { name: "Create account", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Account created.");
  expect(mock.calls.find((call) => call.path === "/accounts/" && call.method === "POST")?.body).toEqual({ type: "checking", balance: "0" });
  await page.getByRole("form", { name: "Issue a credit card", exact: true }).getByRole("button", { name: "Issue €500 credit card" }).click();
  await expect(page.getByRole("status")).toContainText("Synthetic credit card issued");
  expect(mock.calls.find((call) => call.path === "/cards/credit")?.body).toMatchObject({ type: "mastercard" });
});

for (const failure of ["422", "html", "network"] as const) {
  test(`readable ${failure} error without automatic write retries`, async ({ page }) => {
    await mockApi(page);
    await ready(page);
    const form = await paymentForm(page);
    let count = 0;
    await page.route("**/payments/", async (route) => {
      count++;
      if (failure === "network") return route.abort("failed");
      if (failure === "html") return route.fulfill({ status: 502, contentType: "text/html", body: "<h1>Upstream server error</h1>" });
      return route.fulfill({ status: 422, json: { detail: [{ loc: ["body", "amount"], msg: "Amount outside permitted bounds", input: "123.456" }] } });
    });
    await form.getByRole("button", { name: "Approve synthetic payment" }).click();
    await expect(form.getByRole("alert")).toContainText(failure === "422" ? "amount: Amount outside permitted bounds" : failure === "html" ? "temporarily unavailable" : "Could not reach");
    await expect(page.locator("body")).not.toContainText("Upstream server error");
    expect(count).toBe(1);
  });
}

test("successful write with failed read-back warns against repeating the payment", async ({ page }) => {
  const mock = await mockApi(page);
  await ready(page);
  const form = await paymentForm(page);
  await page.route("**/analytics/customer-insights?*", (route) => route.fulfill({ status: 503, json: { detail: "Insights unavailable" } }));
  await form.getByRole("button", { name: "Approve synthetic payment" }).click();
  await expect(form.getByRole("status")).toContainText("Payment approved. The displayed data could not be refreshed.");
  await expect(form.getByRole("status")).toContainText("Do not submit again");
  expect(mock.calls.filter((call) => call.path === "/payments/" && call.method === "POST")).toHaveLength(1);
  await page.unroute("**/analytics/customer-insights?*");
  await page.getByRole("button", { name: "Retry refresh" }).click();
  await expect(page.locator(".toast")).toHaveCount(0);
  expect(mock.calls.filter((call) => call.path === "/payments/" && call.method === "POST")).toHaveLength(1);
});

test("pending payment disables controls and prevents a duplicate submit", async ({ page }) => {
  await mockApi(page);
  await ready(page);
  const form = await paymentForm(page);
  let release!: () => void;
  const held = new Promise<void>((resolve) => { release = resolve; });
  let count = 0;
  await page.route("**/payments/", async (route) => { count++; await held; await route.fulfill({ json: { transaction_id: 28, status: "successful" } }); });
  await form.getByRole("button", { name: "Approve synthetic payment" }).click();
  await expect(form.getByRole("button", { name: "Processing…" })).toBeDisabled();
  await expect(form.getByLabel("PIN", { exact: true })).toBeDisabled();
  await form.dispatchEvent("submit");
  expect(count).toBe(1);
  release();
  await expect(form.getByRole("status")).toContainText("Payment approved.");
  expect(count).toBe(1);
});
