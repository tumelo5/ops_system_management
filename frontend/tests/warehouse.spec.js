// @ts-check
import { test, expect } from '@playwright/test';

// --- Helpers ---

async function login(page) {
  await page.goto('/');
  await page.getByPlaceholder('Username').fill('tumemabs');
  await page.getByPlaceholder('Password').fill('admin');
  await page.getByRole('button', { name: /Sign In/i }).click();
  await page.waitForURL('**/warehouse**');
}

async function selectMode(page, mode) {
  await page.selectOption('.bulk-workflow__mode-select', mode);
}

// --- Tests ---

test.describe('Warehouse Client Workflow', () => {

  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/warehouse');
  });


  // ─── Login ───────────────────────────────────────────

  test('should login successfully', async ({ page }) => {
    await expect(page).toHaveURL(/warehouse/);
    await expect(page.getByText('Client Workflow')).toBeVisible();
  });


  // ─── Single Client — Base ────────────────────────────

  test('should create a single client and model successfully', async ({ page }) => {
    await selectMode(page, 'single_client');

    await page.getByPlaceholder('Client Name').fill('Test Bank');
    await page.getByPlaceholder('Client Status').fill('Active');
    await page.getByPlaceholder('Model Name').fill('TestModel X1');
    await page.getByPlaceholder('Model Status').fill('Active');

    await page.getByRole('button', { name: /add client & model/i }).click();

    await expect(page.getByText(/created successfully/i)).toBeVisible();
  });

  test('should show error when submitting duplicate client name', async ({ page }) => {
    await selectMode(page, 'single_client');

    // Submit the same client twice
    await page.getByPlaceholder('Client Name').fill('first national bank');
    await page.getByPlaceholder('Client Status').fill('Active');
    await page.getByPlaceholder('Model Name').fill('SomeModel');
    await page.getByPlaceholder('Model Status').fill('Active');

    await page.getByRole('button', { name: /add client & model/i }).click();

    await expect(page.getByText(/already exists/i)).toBeVisible();
  });

  test('should disable Add Client & Model button after successful submission', async ({ page }) => {
    await selectMode(page, 'single_client');

    await page.getByPlaceholder('Client Name').fill('New Bank');
    await page.getByPlaceholder('Client Status').fill('Active');
    await page.getByPlaceholder('Model Name').fill('New Model');
    await page.getByPlaceholder('Model Status').fill('Active');

    await page.getByRole('button', { name: /add client & model/i }).click();
    await expect(page.getByText(/created successfully/i)).toBeVisible();

    await expect(page.getByRole('button', { name: /add client & model/i })).toBeDisabled();
  });


  // ─── Single Client — Linking ─────────────────────────

  test('should unlock linking form after base step', async ({ page }) => {
    await selectMode(page, 'single_client');

    await page.getByPlaceholder('Client Name').fill('Link Test Bank');
    await page.getByPlaceholder('Client Status').fill('Active');
    await page.getByPlaceholder('Model Name').fill('Link Test Model');
    await page.getByPlaceholder('Model Status').fill('Active');

    await page.getByRole('button', { name: /add client & model/i }).click();
    await expect(page.getByText(/created successfully/i)).toBeVisible();

    await expect(page.getByPlaceholder('Batch Code')).toBeEnabled();
    await expect(page.getByPlaceholder('Version')).toBeEnabled();
  });

  test('should create batch code and version successfully', async ({ page }) => {
    await selectMode(page, 'single_client');

    await page.getByPlaceholder('Client Name').fill('Batch Test Bank');
    await page.getByPlaceholder('Client Status').fill('Active');
    await page.getByPlaceholder('Model Name').fill('Batch Test Model');
    await page.getByPlaceholder('Model Status').fill('Active');

    await page.getByRole('button', { name: /add client & model/i }).click();
    await expect(page.getByText(/created successfully/i)).toBeVisible();

    await page.getByPlaceholder('Batch Code').fill('BATCH001');
    await page.getByPlaceholder('Version').fill('v1');

    // Select client and model from dropdowns
    await page.locator('select').nth(1).selectOption({ index: 1 });
    await page.locator('select').nth(2).selectOption({ index: 1 });

    await page.getByRole('button', { name: /create batch code & version/i }).click();

    await expect(page.getByText(/created successfully/i)).toBeVisible();
  });

  test('should show error for duplicate batch code', async ({ page }) => {
    await selectMode(page, 'single_client');

    await page.getByPlaceholder('Client Name').fill('Dup Batch Bank');
    await page.getByPlaceholder('Client Status').fill('Active');
    await page.getByPlaceholder('Model Name').fill('Dup Batch Model');
    await page.getByPlaceholder('Model Status').fill('Active');

    await page.getByRole('button', { name: /add client & model/i }).click();
    await expect(page.getByText(/created successfully/i)).toBeVisible();

    await page.getByPlaceholder('Batch Code').fill('56789');
    await page.getByPlaceholder('Version').fill('v1');

    await page.locator('select').nth(1).selectOption({ index: 1 });
    await page.locator('select').nth(2).selectOption({ index: 1 });

    await page.getByRole('button', { name: /create batch code & version/i }).click();

    await expect(page.getByText(/already exists/i)).toBeVisible();
  });


  // ─── Scan Device ─────────────────────────────────────

  test('should scan a valid serial number and show device details', async ({ page }) => {
    await selectMode(page, 'single_client');

    // Complete base and linking first to unlock scan
    await page.getByPlaceholder('Client Name').fill('Scan Test Bank');
    await page.getByPlaceholder('Client Status').fill('Active');
    await page.getByPlaceholder('Model Name').fill('Scan Test Model');
    await page.getByPlaceholder('Model Status').fill('Active');
    await page.getByRole('button', { name: /add client & model/i }).click();
    await expect(page.getByText(/created successfully/i)).toBeVisible();

    await page.getByPlaceholder('Batch Code').fill('SCAN001');
    await page.getByPlaceholder('Version').fill('v1');
    await page.locator('select').nth(1).selectOption({ index: 1 });
    await page.locator('select').nth(2).selectOption({ index: 1 });
    await page.getByRole('button', { name: /create batch code & version/i }).click();
    await expect(page.getByText(/created successfully/i)).toBeVisible();

    // Scan a device
    await page.getByPlaceholder('Scan or type serial number and press Enter').fill('SCAN001-test001');
    await page.keyboard.press('Enter');

    await expect(page.getByText('SCAN001-test001')).toBeVisible();
  });

  test('should show error for invalid batch code in serial number', async ({ page }) => {
    await selectMode(page, 'existing_client');

    // Select existing client to unlock scan
    await page.locator('select').nth(1).selectOption({ index: 1 });
    await page.locator('select').nth(2).selectOption({ index: 1 });

    await page.getByPlaceholder('Scan or type serial number and press Enter').fill('INVALID999-test001');
    await page.keyboard.press('Enter');

    await expect(page.getByText(/no batch found/i)).toBeVisible();
  });

  test('should show error when scanning duplicate serial number', async ({ page }) => {
    await selectMode(page, 'existing_client');

    await page.locator('select').nth(1).selectOption({ index: 1 });

    const sn = '56789-ddngbsdn';
    await page.getByPlaceholder('Scan or type serial number and press Enter').fill(sn);
    await page.keyboard.press('Enter');

    // Try scanning the same SN again
    await page.getByPlaceholder('Scan or type serial number and press Enter').fill(sn);
    await page.keyboard.press('Enter');

    await expect(page.getByText(/already been scanned/i)).toBeVisible();
  });


  // ─── Scan table — Remove ─────────────────────────────

  test('should remove a scanned device from the table', async ({ page }) => {
    await selectMode(page, 'existing_client');

    await page.locator('select').nth(1).selectOption({ index: 1 });

    await page.getByPlaceholder('Scan or type serial number and press Enter').fill('56789-removetest');
    await page.keyboard.press('Enter');
    await expect(page.getByText('56789-removetest')).toBeVisible();

    await page.getByTitle('Remove').first().click();

    await expect(page.getByText('56789-removetest')).not.toBeVisible();
  });


  // ─── Mode reset ──────────────────────────────────────

  test('should reset form when mode changes', async ({ page }) => {
    await selectMode(page, 'single_client');
    await page.getByPlaceholder('Client Name').fill('Some Bank');

    await selectMode(page, 'bulk_clients');

    await expect(page.getByPlaceholder('Client Name').first()).toHaveValue('');
  });

});

