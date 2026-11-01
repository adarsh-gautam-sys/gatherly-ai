import { test, expect, chromium } from "@playwright/test";
import axe from "axe-core";
import lighthouse from "lighthouse";
import { launch } from "chrome-launcher";
import { mkdir, writeFile } from "node:fs/promises";

const review = ".impeccable/review";
async function accessible(page) {
  await page.evaluate(axe.source);
  const failures = await page.evaluate(async () =>
    (
      await axe.run(document, {
        runOnly: [
          "wcag2a",
          "wcag2aa",
          "wcag21a",
          "wcag21aa",
          "wcag22aa",
          "best-practice",
        ],
      })
    ).violations.map((item) => ({
      id: item.id,
      nodes: item.nodes.map((node) => node.target),
    })),
  );
  expect(failures).toEqual([]);
}

async function tabTo(page, target) {
  for (let count = 0; count < 30; count++) {
    if (await target.evaluate((element) => element === document.activeElement))
      return;
    await page.keyboard.press("Tab");
  }
  await expect(target).toBeFocused();
}
async function fillEvent(
  page,
  type = "birthday",
  name = "The neighbourhood celebration",
) {
  await page
    .getByRole("radio", {
      name: {
        wedding: "Wedding",
        birthday: "Birthday",
        community: "Community",
      }[type],
      exact: true,
    })
    .check();
  await page.getByLabel("Event name", { exact: true }).fill(name);
  await page.getByLabel("Event date", { exact: true }).fill("2099-06-01");
  await page.getByLabel("Number of guests").fill("25");
  await page.getByLabel("Total budget", { exact: true }).fill("25000");
}
async function generate(page, type = "birthday", name) {
  await fillEvent(page, type, name);
  await page.getByRole("button", { name: "Create my plan" }).click();
  await expect(page.locator("#results")).toBeVisible();
  await expect(page.locator("#event-form")).toHaveAttribute(
    "aria-busy",
    "false",
  );
}
test.use({ bypassCSP: true }); // axe is injected only into the isolated test browser.

test("intake, validation, mobile and dark mode are accessible", async ({
  page,
}) => {
  await mkdir(review, { recursive: true });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/");
  await accessible(page);
  await page.screenshot({
    path: `${review}/intake-desktop.png`,
    fullPage: true,
  });
  await page.getByRole("button", { name: "Create my plan" }).click();
  await expect(page.locator("#errors")).toBeFocused();
  await accessible(page);
  await page.locator("#name").fill("<img src=x onerror=alert(1)>");
  await page.setViewportSize({ width: 320, height: 800 });
  await accessible(page);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.reload();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: `${review}/intake-mobile.png`,
    fullPage: true,
  });
  await page.emulateMedia({ colorScheme: "dark", reducedMotion: "reduce" });
  await accessible(page);
});

for (const type of ["wedding", "birthday", "community"])
  test(`${type}: complete planning, progress, updates and JSON round trip`, async ({
    page,
  }) => {
    await page.goto("/");
    await generate(page, type, "A <script> celebration");
    await expect(page.locator("#plan-title")).toHaveText(
      "A <script> celebration",
    );
    await expect(page.locator("#ai-notice")).toContainText("template");
    await accessible(page);
    await page.locator("#next-tasks input").first().check();
    await expect(page.locator("#completion")).toContainText("1 of");
    await page.getByRole("tab", { name: "Vendors", exact: true }).click();
    await page.locator("#vendors select").first().selectOption("contacted");
    await page.getByRole("tab", { name: "Budget", exact: true }).click();
    await page.getByLabel("Try a new total").fill("20000.01");
    await page
      .getByRole("button", { name: "Update budget", exact: true })
      .click();
    await expect(page.locator("#total")).toHaveText("INR 20,000.01");
    await expect(page.locator("#ai-notice")).toContainText("previous budget");
    await page.getByRole("tab", { name: "Vendors", exact: true }).click();
    await expect(page.locator("#vendors select").first()).toHaveValue(
      "contacted",
    );
    await accessible(page);
    await page.getByRole("tab", { name: "Ideas", exact: true }).click();
    await page
      .getByLabel("What would you like to change?")
      .fill("Make it vegetarian");
    await page.getByRole("button", { name: "Refine my ideas" }).click();
    await expect(page.locator("#status")).toContainText("Ideas refined");
    await expect(page.locator("#completion")).toContainText("1 of");
    await accessible(page);
    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("button", { name: "JSON", exact: true }).click();
    const download = await downloadPromise;
    const path = await download.path();
    await page.reload();
    await page.locator("#import").setInputFiles(path);
    await expect(page.locator("#results")).toBeVisible();
    await expect(page.locator("#completion")).toContainText("1 of");
    for (const format of ["Markdown", "Calendar"]) {
      const event = page.waitForEvent("download");
      await page.getByRole("button", { name: format, exact: true }).click();
      expect((await event).suggestedFilename()).toMatch(
        /^gatherly-plan\.(md|ics)$/,
      );
      await expect(page.locator("#status")).toContainText("Export ready");
    }
  });

test("keyboard walkthrough, failure recovery and print preserve the working plan", async ({
  page,
}) => {
  await page.goto("/");
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Skip to planner" }),
  ).toBeFocused();
  await page.keyboard.press("Enter");
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("radio", { name: "Wedding", exact: true }),
  ).toBeFocused();
  await page.keyboard.press("Space");
  await page.keyboard.press("Tab");
  await page.keyboard.type("Keyboard celebration");
  await page.keyboard.press("Tab");
  await page.getByLabel("Event date", { exact: true }).fill("2099-06-01");
  await tabTo(page, page.getByLabel("Number of guests"));
  await page.keyboard.type("25");
  await tabTo(page, page.getByLabel("Total budget", { exact: true }));
  await page.keyboard.type("25000");
  await tabTo(page, page.locator(".preferences summary"));
  await page.keyboard.press("Enter");
  await tabTo(page, page.getByRole("button", { name: "Create my plan" }));
  await page.keyboard.press("Enter");
  await expect(page.locator("#results")).toBeVisible();
  await page.getByRole("tab", { name: "Budget", exact: true }).focus();
  await page.keyboard.press("ArrowRight");
  await expect(
    page.getByRole("tab", { name: "Timeline", exact: true }),
  ).toBeFocused();
  await page.keyboard.press("Tab");
  await page.keyboard.press("Tab");
  await page.keyboard.press("Space");
  await expect(page.locator("#completion")).toContainText("1 of");
  await accessible(page);
  await page.getByRole("tab", { name: "Budget", exact: true }).click();
  await page.route("**/api/v1/plans/budget", (route) => route.abort());
  await page
    .getByRole("button", { name: "Update budget", exact: true })
    .click();
  await expect(page.locator("#feedback")).toBeFocused();
  await expect(page.locator("#total")).toHaveText("INR 25,000.00");
  await page.unroute("**/api/v1/plans/budget");
  await page.getByRole("button", { name: "Edit event details" }).click();
  await page.getByRole("button", { name: "Return to current plan" }).click();
  await expect(page.locator("#completion")).toContainText("1 of");
  await page.getByRole("tab", { name: "Ideas", exact: true }).click();
  await page
    .getByRole("button", { name: "Refresh ideas", exact: true })
    .click();
  await expect(page.locator("#status")).toHaveText("Ideas refreshed.");
  await page.evaluate(() => (window.print = () => {}));
  await page.getByRole("button", { name: "Print / PDF" }).click();
  await page.emulateMedia({ media: "print" });
  await expect(page.locator("#timeline")).toBeVisible();
  await expect(page.locator("#vendors")).toBeVisible();
});

test("invalid imports keep the intake usable", async ({ page }) => {
  await page.goto("/");
  await page.locator("#import").setInputFiles({
    name: "bad.json",
    mimeType: "application/json",
    buffer: Buffer.from("{bad"),
  });
  await expect(page.locator("#feedback")).toContainText("not valid JSON");
  await page.locator("#import").setInputFiles({
    name: "bad.json",
    mimeType: "application/json",
    buffer: Buffer.from('{"name":"fake"}'),
  });
  await expect(page.locator("#feedback")).toContainText("invalid");
  await expect(page.locator("#intake")).toBeVisible();
});

test("responsive result evidence and zero accessibility violations across every section", async ({
  page,
}) => {
  await page.goto("/");
  await generate(page, "community");
  for (const width of [1440, 390, 320, 640]) {
    await page.setViewportSize({ width, height: width === 1440 ? 1000 : 844 });
    for (const section of ["Budget", "Timeline", "Vendors", "Ideas"]) {
      await page.getByRole("tab", { name: section, exact: true }).click();
      await accessible(page);
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
    }
    await page.getByRole("tab", { name: "Budget", exact: true }).click();
    if ([1440, 390].includes(width)) {
      await page.locator("#plan-title").focus();
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.screenshot({
        path: `${review}/${width === 1440 ? "desktop" : "mobile"}.png`,
        fullPage: true,
      });
    }
  }
});

test("Lighthouse accessibility is 100 and best practices at least 95", async () => {
  const chrome = await launch({
    chromePath: chromium.executablePath(),
    chromeFlags: ["--headless", "--no-sandbox"],
  });
  try {
    const result = await lighthouse("http://127.0.0.1:8123/", {
      port: chrome.port,
      onlyCategories: ["accessibility", "best-practices"],
      logLevel: "error",
      output: "json",
    });
    await mkdir(".cache/browser", { recursive: true });
    await writeFile(".cache/browser/lighthouse.json", result.report);
    console.log(
      "Lighthouse",
      Object.fromEntries(
        Object.entries(result.lhr.categories).map(([name, data]) => [
          name,
          data.score * 100,
        ]),
      ),
    );
    expect(result.lhr.categories.accessibility.score).toBe(1);
    expect(
      result.lhr.categories["best-practices"].score,
    ).toBeGreaterThanOrEqual(0.95);
  } finally {
    await chrome.kill();
  }
});
