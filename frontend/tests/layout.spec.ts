import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { makeSnapshot, mockApi, openView } from "./fixtures";

const views = [
  ["Overview", "Overview"],
  ["Transactions", "Transactions"],
  ["Credit Center", "Credit Center"],
  ["Simulator", "Payment simulator"],
  ["Insights", "Spending insights"],
] as const;

for (const width of [360, 390, 768, 1440]) {
  for (const [nav, title] of views) {
    test(`${nav} fits ${width}px and produces a browser screenshot`, async ({ page }, testInfo) => {
      await page.setViewportSize({ width, height: 1000 });
      await mockApi(page);
      await page.goto("/");
      await expect(page.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();
      if (nav !== "Overview") await openView(page, nav);
      await expect(page.getByRole("heading", { name: title, exact: true })).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      await expect(page).toHaveTitle("Iron Bank · Banking Lab");
      const path = testInfo.outputPath(`${nav.replaceAll(" ", "-")}-${width}.png`);
      await page.screenshot({ path, fullPage: true, animations: "disabled" });
      await testInfo.attach("Rendered workspace", { path, contentType: "image/png" });
    });
  }
}

for (const [nav] of views) {
  test(`${nav} passes automated accessibility scan`, async ({ page }, testInfo) => {
    await mockApi(page);
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();
    if (nav !== "Overview") await openView(page, nav);
    const result = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
    await testInfo.attach("Accessibility findings", { body: JSON.stringify(result.violations), contentType: "application/json" });
    expect(result.violations).toEqual([]);
  });
}

test("sign-in screen passes automated accessibility scan", async ({ page }) => {
  await mockApi(page, makeSnapshot(), false);
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
  const result = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  expect(result.violations).toEqual([]);
});

test("receipt opens by keyboard, traps focus, closes with Escape and restores focus", async ({ page }, testInfo) => {
  await mockApi(page);
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();
  await openView(page, "Transactions");
  const trigger = page.getByRole("button", { name: /^View transaction 27:/ });
  await trigger.focus();
  await page.keyboard.press("Enter");
  const dialog = page.getByRole("dialog", { name: "REWE München", exact: true });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("button", { name: "Close transaction details" })).toBeFocused();
  await expect(dialog).toContainText("2026-09-24 11:15:00");
  await expect(dialog).toContainText("Not recorded");
  expect(await page.evaluate(() => document.body.style.overflow)).toBe("hidden");
  await page.keyboard.press("Tab");
  expect(await page.evaluate(() => !!document.activeElement?.closest("dialog"))).toBe(true);
  const scan = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  expect(scan.violations).toEqual([]);
  const path = testInfo.outputPath("transaction-receipt.png");
  await page.screenshot({ path, animations: "disabled" });
  await testInfo.attach("Receipt", { path, contentType: "image/png" });
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(trigger).toBeFocused();
  expect(await page.evaluate(() => document.body.style.overflow)).not.toBe("hidden");
  await page.getByRole("button", { name: /^View transaction 24:/ }).click();
  await expect(page.getByRole("dialog")).toContainText("Between your accounts");
  await expect(page.getByRole("dialog")).toContainText("Not applicable to bank transfers");
  await expect(page.locator(".transaction-dialog-summary strong")).toHaveText(/^[^−+]*200,00/);
  await page.getByRole("button", { name: "Close transaction details" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("long descriptions, account identifiers and large balances fit a phone", async ({ page }) => {
  const state = makeSnapshot();
  state.transactions[0].description = "Long synthetic merchant name ".repeat(8);
  state.transactions[0].sender_iban = "DE" + "1".repeat(32);
  state.accounts[0].balance = "999999999.99";
  await page.setViewportSize({ width: 360, height: 740 });
  await mockApi(page, state);
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await openView(page, "Transactions");
  await page.getByRole("button", { name: /^View transaction 27:/ }).click();
  const dialog = page.getByRole("dialog");
  expect(await dialog.evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true);
  expect(await dialog.evaluate((element) => element.getBoundingClientRect().height < innerHeight)).toBe(true);
});

test("empty account and analytics states remain reachable", async ({ page }) => {
  const state = makeSnapshot();
  state.accounts = []; state.cards = []; state.transactions = []; state.creditDashboard = null; state.statements = [];
  state.spending.categories = []; state.spending.total_spend = "0"; state.spending.transaction_count = 0;
  state.insights.spending_summary.categories = []; state.insights.spending_summary.top_merchants = [];
  state.insights.signals = []; state.insights.suggested_offers = [];
  await mockApi(page, state);
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "No accounts yet" })).toBeVisible();
  await openView(page, "Transactions"); await expect(page.getByRole("heading", { name: "No transactions yet" })).toBeVisible();
  await openView(page, "Credit Center"); await expect(page.getByRole("heading", { name: "No credit account yet" })).toBeVisible();
  await openView(page, "Simulator"); await expect(page.getByRole("heading", { name: "Issue a card first" })).toBeVisible();
  await openView(page, "Insights"); await expect(page.getByRole("heading", { name: "No offer suggested" })).toBeVisible();
});
