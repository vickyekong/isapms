import { test, expect } from "@playwright/test";

const password = "Sample@12345";

async function signIn(page, identifier) {
  await page.goto("/login");
  await page.getByLabel("Email, staff ID, or matriculation number").fill(identifier);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
}

test("administrator can sign in and open the student register", async ({ page }) => {
  await signIn(page, "sample.admin@nexusstate.edu.ng");
  await page.getByRole("link", { name: "Students" }).click();
  await expect(page.getByRole("heading", { name: "Students" })).toBeVisible();
});

test("lecturer can open attendance and a student is blocked from user management", async ({ page }) => {
  await signIn(page, "sample.lecturer01@nexusstate.edu.ng");
  await page.getByRole("link", { name: "Attendance" }).click();
  await expect(page.getByRole("heading", { name: "Attendance" })).toBeVisible();
  await page.goto("/users");
  await expect(page.getByRole("heading", { name: "You do not have access to that page" })).toBeVisible();
});

test("student can view personal results", async ({ page }) => {
  await signIn(page, "sample.student001@nexusstate.edu.ng");
  await page.getByRole("link", { name: "Results" }).click();
  await expect(page.getByRole("heading", { name: "Results" })).toBeVisible();
});
