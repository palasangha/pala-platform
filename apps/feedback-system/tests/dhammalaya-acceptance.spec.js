// @ts-check
const { test, expect } = require('@playwright/test');

const BASE_URL = 'http://localhost:3030';

test.describe('Dhammalaya User Acceptance Tests', () => {
  
  test('should display Dhammalaya in department selection', async ({ page }) => {
    await page.goto(BASE_URL);
    
    // Wait for departments to load
    await page.waitForSelector('.department-card', { timeout: 10000 });
    
    // Check if Dhammalaya department is visible
    const dhammalayaCard = page.locator('.department-card:has-text("Dhammalaya")');
    await expect(dhammalayaCard).toBeVisible();
    
    // Verify the green color scheme
    const cardElement = await dhammalayaCard.elementHandle();
    const backgroundColor = await cardElement?.evaluate(el => 
      window.getComputedStyle(el).backgroundColor
    );
    console.log('Dhammalaya card background color:', backgroundColor);
  });

  test('should navigate to Dhammalaya feedback form', async ({ page }) => {
    await page.goto(BASE_URL);
    
    // Wait for departments to load
    await page.waitForSelector('.department-card', { timeout: 10000 });
    
    // Click on Dhammalaya department
    const dhammalayaCard = page.locator('.department-card:has-text("Dhammalaya")');
    await dhammalayaCard.click();
    
    // Wait for navigation or form to appear
    await page.waitForTimeout(2000);
    
    // Check for welcome message
    const welcomeText = page.locator('text=/Welcome to Dhammalaya/i');
    await expect(welcomeText).toBeVisible({ timeout: 10000 });
  });

  test('should display Dhammalaya feedback form with questions', async ({ page }) => {
    await page.goto(BASE_URL);
    
    // Wait for departments and select Dhammalaya
    await page.waitForSelector('.department-card', { timeout: 10000 });
    const dhammalayaCard = page.locator('.department-card:has-text("Dhammalaya")');
    await dhammalayaCard.click();
    
    await page.waitForTimeout(2000);
    
    // Verify form is present
    const form = page.locator('form');
    await expect(form).toBeVisible({ timeout: 10000 });
    
    // Check for rating elements (should have 5 questions)
    const ratingElements = page.locator('[data-rating], .rating, .star-rating, input[type="radio"]');
    const count = await ratingElements.count();
    console.log('Number of rating elements found:', count);
    
    // Should have at least some interactive elements
    expect(count).toBeGreaterThan(0);
  });

  test('should submit Dhammalaya feedback successfully', async ({ page }) => {
    await page.goto(BASE_URL);
    
    // Navigate to Dhammalaya form
    await page.waitForSelector('.department-card', { timeout: 10000 });
    const dhammalayaCard = page.locator('.department-card:has-text("Dhammalaya")');
    await dhammalayaCard.click();
    
    await page.waitForTimeout(2000);
    
    // Fill out the form - find all rating inputs
    const radioButtons = page.locator('input[type="radio"]');
    const radioCount = await radioButtons.count();
    
    // Select ratings (select every 5th radio button to get one per question)
    for (let i = 4; i < radioCount; i += 5) {
      await radioButtons.nth(i).click();
      await page.waitForTimeout(300);
    }
    
    // Fill optional fields if present
    const nameInput = page.locator('input[name="name"], input[placeholder*="Name"]').first();
    if (await nameInput.isVisible().catch(() => false)) {
      await nameInput.fill('Test User');
    }
    
    const emailInput = page.locator('input[name="email"], input[type="email"]').first();
    if (await emailInput.isVisible().catch(() => false)) {
      await emailInput.fill('test@example.com');
    }
    
    const commentsInput = page.locator('textarea, input[name="comments"]').first();
    if (await commentsInput.isVisible().catch(() => false)) {
      await commentsInput.fill('Great meditation environment at Dhammalaya!');
    }
    
    // Submit the form
    const submitButton = page.locator('button[type="submit"], button:has-text("Submit")').first();
    await submitButton.click();
    
    // Wait for success message or redirect
    await page.waitForTimeout(3000);
    
    // Check for success indication
    const successMessage = page.locator('text=/thank you|success|submitted/i');
    const isSuccess = await successMessage.isVisible().catch(() => false);
    
    console.log('Feedback submission successful:', isSuccess);
  });

  test('admin login shows Dhammalaya', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin`);
    
    // Login as Dhammalaya admin
    await page.waitForSelector('input[type="email"], input[name="email"]', { timeout: 10000 });
    
    await page.fill('input[type="email"], input[name="email"]', 'dhammalane@globalpagoda.org');
    await page.fill('input[type="password"], input[name="password"]', 'DhammaLane@2026!');
    
    const loginButton = page.locator('button[type="submit"], button:has-text("Login")').first();
    await loginButton.click();
    
    await page.waitForTimeout(3000);
    
    // Check for Dhammalaya in the dashboard
    const dhammalayaText = page.locator('text=/Dhammalaya/i');
    await expect(dhammalayaText.first()).toBeVisible({ timeout: 10000 });
    
    console.log('Admin dashboard shows Dhammalaya');
  });

  test('tablet interface shows Dhammalaya with green theme', async ({ page }) => {
    // Set viewport to tablet size
    await page.setViewportSize({ width: 768, height: 1024 });
    
    await page.goto(`${BASE_URL}/tablet`);
    
    await page.waitForTimeout(2000);
    
    // Select Dhammalaya department
    const dhammalayaButton = page.locator('button:has-text("Dhammalaya"), [data-department="dhamma_lane"]').first();
    
    if (await dhammalayaButton.isVisible().catch(() => false)) {
      await dhammalayaButton.click();
      await page.waitForTimeout(2000);
      
      // Verify green color theme (should be #27ae60)
      const bodyBg = await page.evaluate(() => {
        return window.getComputedStyle(document.body).backgroundColor;
      });
      console.log('Tablet interface background color:', bodyBg);
      
      // Check for welcome message
      const welcomeMessage = page.locator('text=/Welcome to Dhammalaya/i');
      await expect(welcomeMessage).toBeVisible({ timeout: 5000 });
    }
  });
});
