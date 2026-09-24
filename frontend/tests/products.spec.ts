import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { makeSnapshot, mockApi, openView } from "./fixtures";

for (const [id, type, count] of [[1, "Checking", 3], [2, "Savings", 1], [3, "Credit", 1]] as const) {
  test(`Overview opens ${type} account with only its recorded activity`, async ({ page }) => {
    const { calls } = await mockApi(page);
    await page.goto("/");
    const trigger = page.getByRole("button", { name: `Open ${type} account #${id}`, exact: true });
    await trigger.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByRole("heading", { name: `${type} account`, exact: true })).toBeFocused();
    const activity = page.getByRole("region", { name: "Account activity", exact: true });
    await expect(activity.locator(".transaction-row-button")).toHaveCount(count);
    const details = page.getByRole("region", { name: "Account details", exact: true });
    await expect(details).toContainText(`#${id}`);
    await expect(details).toContainText(makeSnapshot().accounts[id - 1].iban);
    if (id === 3) {
      await expect(page.getByRole("region", { name: "Selected credit account" })).toContainText("312,50");
      await expect(page.getByRole("heading", { name: "Statements for this account" })).toBeVisible();
      await page.getByRole("button", { name: "Open Credit Center for repayments & score →" }).click();
      await expect(page.getByRole("heading", { name: "Credit Center", exact: true })).toBeVisible();
    } else {
      await expect(activity.getByRole("button", { name: /^View transaction 27:/ })).toHaveCount(0);
      await page.getByRole("button", { name: "← All accounts & cards" }).click();
      await expect(page.getByRole("heading", { name: "Accounts", exact: true })).toBeVisible();
    }
    expect(calls.filter((call) => call.method !== "GET")).toHaveLength(0);
  });
}

test("account filters include both sides of internal transfers and receipts preserve perspective", async ({ page }) => {
  const { calls } = await mockApi(page);
  await page.goto("/");
  await openView(page, "Transactions");
  const filter = page.getByLabel("Filter by account", { exact: true });
  const row = page.getByRole("button", { name: /^View transaction 24:/ });
  await expect(page.getByRole("status")).toHaveText("4 matching transactions");
  await expect(row.locator(".transaction-side > strong")).toHaveText(/^[^−+]*200,00/);
  await filter.selectOption("2");
  await expect(page.getByRole("status")).toHaveText("1 matching transaction");
  await expect(row.locator(".transaction-side > strong")).toHaveText(/^\+200,00/);
  await expect(page.getByText("30-day spending · all accounts", { exact: true })).toHaveCount(0);
  await row.click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toContainText("Incoming · internal transfer");
  await expect(dialog).toContainText("Not applicable to bank transfers");
  await page.keyboard.press("Escape");
  await expect(row).toBeFocused();
  await filter.selectOption("1");
  await expect(page.getByRole("status")).toHaveText("3 matching transactions");
  await expect(row.locator(".transaction-side > strong")).toHaveText(/^−200,00/);
  await expect(page.getByRole("button", { name: /^View transaction 25:/ }).locator(".transaction-side > strong")).toHaveText(/^\+3\.650,00/);
  await filter.selectOption("");
  await expect(page.getByRole("status")).toHaveText("4 matching transactions");
  await expect(row.locator(".transaction-side > strong")).toHaveText(/^[^−+]*200,00/);
  expect(calls.filter((call) => call.method !== "GET")).toHaveLength(0);
});

test("card tiles open masked details and the correct linked account without CVV requests", async ({ page }) => {
  const state = makeSnapshot();
  state.cards.push({ ...state.cards[0], id: 2, number: "5100000000001122", linked_acc_id: 2 });
  const { calls } = await mockApi(page, state);
  await page.goto("/");
  await page.getByRole("button", { name: "Open synthetic card ending 1122, card #2", exact: true }).click();
  const details = page.getByRole("region", { name: "Card details", exact: true });
  await expect(details).toContainText("Savings account #2");
  await expect(details).toContainText("Activity is recorded by account, not by individual card.");
  await expect(details).not.toContainText(state.cards[1].number);
  await page.getByRole("button", { name: "Open linked account & activity" }).click();
  await expect(page.getByRole("heading", { name: "Savings account", exact: true })).toBeFocused();
  await expect(page.getByRole("region", { name: "Account activity", exact: true }).locator(".transaction-row-button")).toHaveCount(1);
  expect(calls.some((call) => call.path.includes("/cvv"))).toBe(false);
  expect(calls.filter((call) => call.method !== "GET")).toHaveLength(0);
});

test("summary tiles lead to accounts, credit details, score and transaction history", async ({ page }) => {
  await mockApi(page);
  await page.goto("/");
  await page.getByRole("button", { name: "View available cash", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Accounts", exact: true })).toBeVisible();
  await openView(page, "Overview");
  await page.getByRole("button", { name: "View available credit", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Credit account", exact: true })).toBeVisible();
  await openView(page, "Overview");
  await page.getByRole("button", { name: "View synthetic score", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Credit Center", exact: true })).toBeVisible();
  await openView(page, "Overview");
  await page.getByRole("button", { name: "View 30-day spending", exact: true }).click();
  await expect(page.getByLabel("Filter by account")).toBeVisible();
});

test("selected account survives refresh, updates from API data and handles removal", async ({ page }) => {
  const state = makeSnapshot();
  await mockApi(page, state);
  await page.goto("/");
  await page.getByRole("button", { name: "Open Savings account #2", exact: true }).click();
  state.accounts[1].balance = "9000.00";
  await page.getByRole("button", { name: "Refresh data", exact: true }).click();
  await expect(page.locator(".product-detail-balance")).toHaveText(/9\.000,00/);
  await expect(page.getByRole("heading", { name: "Savings account", exact: true })).toBeVisible();
  state.accounts = state.accounts.filter((item) => item.id !== 2);
  await page.getByRole("button", { name: "Refresh data", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Product unavailable", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "← All accounts & cards" }).click();
  await expect(page.getByRole("button", { name: "Open Savings account #2", exact: true })).toHaveCount(0);
});

test("empty savings history preserves seeded balance and does not invent activity", async ({ page }) => {
  const state = makeSnapshot();
  state.transactions = state.transactions.filter((item) => item.id !== 24);
  await mockApi(page, state);
  await page.goto("/");
  await page.getByRole("button", { name: "Open Savings account #2", exact: true }).click();
  await expect(page.locator(".product-detail-balance")).toHaveText(/8\.650,00/);
  await expect(page.getByRole("heading", { name: "No transactions for this account" })).toBeVisible();
  await expect(page.getByText("No synthetic cards are linked to this account.", { exact: true })).toBeVisible();
});

test("missing linked account is explained without a bogus navigation control", async ({ page }) => {
  const state = makeSnapshot();
  state.cards[0].linked_acc_id = 999;
  await mockApi(page, state);
  await page.goto("/");
  await page.getByRole("button", { name: "Open synthetic card ending 9948, card #1", exact: true }).click();
  await expect(page.getByRole("region", { name: "Card details", exact: true })).toContainText("Account #999 is not available");
  await expect(page.getByRole("button", { name: "Open linked account & activity" })).toHaveCount(0);
});

test("duplicate account types stay distinct and credit reads use selected ID", async ({ page }) => {
  const state = makeSnapshot();
  state.accounts.push({ ...state.accounts[2], id: 4, iban: "DE00111122223333444455", balance: "-20.00" });
  await mockApi(page, state);
  await page.route("**/credit-accounts/4", (route) => route.fulfill({ json: { ...state.creditDashboard, account_id: 4, outstanding_debt: "20.00", credit_limit: "200.00", available_credit: "180.00" } }));
  await page.route("**/credit-accounts/4/statements", (route) => route.fulfill({ json: [] }));
  await page.goto("/");
  await page.getByRole("button", { name: "Open Credit account #4", exact: true }).click();
  const details = page.getByRole("region", { name: "Selected credit account" });
  await expect(details).toContainText("180,00");
  await expect(details).not.toContainText("312,50");
  await expect(page.getByText("No statements recorded for this account yet.", { exact: true })).toBeVisible();
});

test("a mismatched credit response is rejected rather than showing another account", async ({ page }) => {
  const state = makeSnapshot();
  state.accounts.push({ ...state.accounts[2], id: 4 });
  await mockApi(page, state);
  await page.route("**/credit-accounts/4", (route) => route.fulfill({ json: state.creditDashboard }));
  await page.route("**/credit-accounts/4/statements", (route) => route.fulfill({ json: [] }));
  await page.goto("/");
  await page.getByRole("button", { name: "Open Credit account #4", exact: true }).click();
  await expect(page.getByRole("alert")).toHaveText("The returned credit details do not match this account.");
  await expect(page.getByRole("region", { name: "Selected credit account" })).not.toContainText("312,50");
});

for (const width of [360, 390, 768, 1440]) {
  test(`account and card journeys fit ${width}px with accessible controls`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 1000 });
    await mockApi(page);
    await page.goto("/");
    await openView(page, "Accounts");
    const check = async (name: string) => {
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      const scan = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
      expect(scan.violations).toEqual([]);
      const path = testInfo.outputPath(`${name}-${width}.png`);
      await page.screenshot({ path, fullPage: true, animations: "disabled" });
      await testInfo.attach(name, { path, contentType: "image/png" });
    };
    await check("accounts");
    await page.getByRole("button", { name: "Open Savings account #2", exact: true }).click();
    await check("savings-account");
    await page.getByRole("button", { name: "← All accounts & cards" }).click();
    await page.getByRole("button", { name: "Open Credit account #3", exact: true }).click();
    await check("credit-account");
    await page.getByRole("button", { name: "Open synthetic card ending 9948, card #1", exact: true }).click();
    await check("card-details");
    await openView(page, "Transactions");
    await page.getByLabel("Filter by account").selectOption("2");
    await check("filtered-transactions");
  });
}
