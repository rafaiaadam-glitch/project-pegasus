import { expect, test } from '@playwright/test';

test('home record button navigates to lecture mode and into record screen', async ({ page }) => {
  await page.goto('/');

  await expect(page.getByText('Tap to record')).toBeVisible();
  await page.getByTestId('home-record-button').click();

  await expect(page.getByRole('heading', { name: 'Select Lecture Type' })).toBeVisible();
  await page.getByLabel('Select Mathematics / Formal').click();
  await page.getByText('Continue to Record').click();

  await expect(page.getByText('Lecture Type: Mathematics / Formal')).toBeVisible();
});

test('explicit record CTA navigates to lecture mode', async ({ page }) => {
  await page.goto('/');

  await page.getByTestId('home-record-cta').click();

  await expect(page.getByRole('heading', { name: 'Select Lecture Type' })).toBeVisible();
  await expect(page.getByText('Different lecture types activate different reasoning dimensions.')).toHaveCount(1);
});
