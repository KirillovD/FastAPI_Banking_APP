import { expect, test } from "@playwright/test";
import { makeSnapshot, mockApi, openView } from "./fixtures";

test("registration and sign-in retain the existing API flow", async ({ page }) => {
  const mock = await mockApi(page, makeSnapshot(), false);
  await page.goto("/");
  await expect(page.getByLabel("Password", { exact: true })).toHaveValue("");
  await page.getByRole("button", { name: "Create a demo account", exact: true }).click();
  // This value belongs only to the intercepted browser-test API; no account exists.
  await page.getByLabel("Password", { exact: true }).fill("Synthetic test account");
  await page.getByRole("button", { name: "Create account & sign in" }).click();
  await expect(page.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();
  expect(mock.calls.filter((call) => call.method === "POST").map((call) => call.path)).toEqual(["/users/", "/auth/"]);
  expect(mock.calls.find((call) => call.path === "/auth/")?.body?.username).toBe("demo@example.com");
});

test("authenticated action rejection returns to sign-in with an explanation", async ({ page }) => {
  await mockApi(page);
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();
  await openView(page, "Simulator");
  await page.route("**/payments/", (route) => route.fulfill({ status: 401, json: { detail: "Session expired" } }));
  await page.getByRole("form", { name: "Card payment", exact: true }).getByRole("button", { name: "Approve synthetic payment" }).click();
  await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
  await expect(page.getByRole("status")).toContainText("session has expired");
  expect(await page.evaluate(() => localStorage.getItem("aurelia_access_token"))).toBeNull();
});

test("a delayed read cannot bring back the dashboard after sign-out", async ({ page }) => {
  const mock = await mockApi(page);
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();
  let release!: () => void;
  const held = new Promise<void>((resolve) => { release = resolve; });
  let started = false;
  let finished = false;
  await page.route("**/users/", async (route) => {
    started = true;
    await held;
    await route.fulfill({ json: mock.state.user });
    finished = true;
  });
  await page.getByRole("button", { name: "Refresh data", exact: true }).click();
  await expect.poll(() => started).toBe(true);
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  release();
  await expect.poll(() => finished).toBe(true);
  await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Overview", exact: true })).toHaveCount(0);
  expect(await page.evaluate(() => localStorage.getItem("aurelia_access_token"))).toBeNull();
});
