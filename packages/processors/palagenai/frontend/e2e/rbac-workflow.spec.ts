import { test, expect, Page } from '@playwright/test';

// Helper functions
async function login(page: Page, email: string, password: string) {
  await page.goto('/');
  
  // Check if already logged in
  const isLoggedIn = await page.locator('text=Logout').isVisible().catch(() => false);
  if (isLoggedIn) {
    await page.locator('text=Logout').click();
    await page.waitForTimeout(1000);
  }
  
  // Fill login form
  await page.fill('input[type="email"], input[name="email"]', email);
  await page.fill('input[type="password"], input[name="password"]', password);
  await page.click('button[type="submit"], button:has-text("Login")');
  
  // Wait for successful login
  await page.waitForURL(/dashboard|bulk|home/, { timeout: 10000 });
  await page.waitForTimeout(1000); // Give time for auth to settle
}

async function logout(page: Page) {
  const logoutBtn = page.locator('text=Logout, button:has-text("Logout")').first();
  if (await logoutBtn.isVisible()) {
    await logoutBtn.click();
    await page.waitForTimeout(1000);
  }
}

// Test Suite 1: Authentication & Login
test.describe('RBAC Authentication Tests', () => {
  test('Admin can login successfully', async ({ page }) => {
    await login(page, 'admin@example.com', 'admin123');
    
    // Verify admin dashboard elements visible
    await expect(page.locator('text=Admin, text=Dashboard')).toBeVisible({ timeout: 5000 });
  });

  test('Reviewer can login successfully', async ({ page }) => {
    await login(page, 'reviewer1@example.com', 'reviewer123');
    
    // Verify reviewer interface visible
    await expect(page.locator('text=Review Queue, text=Assigned Documents')).toBeVisible({ timeout: 5000 });
  });

  test('Teacher can login successfully', async ({ page }) => {
    await login(page, 'teacher1@example.com', 'teacher123');
    
    // Verify teacher interface visible
    await expect(page.locator('text=Document Queue, text=Assign')).toBeVisible({ timeout: 5000 });
  });

  test('Invalid credentials rejected', async ({ page }) => {
    await page.goto('/');
    await page.fill('input[type="email"]', 'wrong@example.com');
    await page.fill('input[type="password"]', 'wrongpass');
    await page.click('button[type="submit"]');
    
    // Should show error message
    await expect(page.locator('text=Invalid credentials, text=Login failed')).toBeVisible({ timeout: 5000 });
  });
});

// Test Suite 2: Teacher - Document Assignment
test.describe('Teacher - Document Assignment Workflow', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, 'teacher1@example.com', 'teacher123');
  });

  test('Teacher can view pending documents', async ({ page }) => {
    // Navigate to document queue
    await page.goto('/documents');
    
    // Filter pending documents
    await page.click('select[name="status"], button:has-text("Pending")');
    
    // Should see pending documents
    await expect(page.locator('text=Letter_Gandhi_to_Nehru_1947.pdf')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=Pending')).toBeVisible();
  });

  test('Teacher can view private documents', async ({ page }) => {
    await page.goto('/documents');
    
    // Filter by private classification
    await page.click('button:has-text("Classification")');
    await page.click('text=Private');
    
    // Should see private documents
    await expect(page.locator('text=Letter_Gandhi_to_Nehru_1947.pdf')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=🔒, text=Private')).toBeVisible();
  });

  test('Teacher can assign document to reviewer', async ({ page }) => {
    await page.goto('/documents');
    
    // Find pending document
    const docRow = page.locator('tr:has-text("Letter_Gandhi_to_Nehru_1947")').first();
    await docRow.click();
    
    // Click assign button
    await page.click('button:has-text("Assign")');
    
    // Select reviewer from dropdown
    await page.click('select[name="reviewer"]');
    await page.click('option:has-text("reviewer1@example.com")');
    
    // Confirm assignment
    await page.click('button:has-text("Confirm")');
    
    // Should show success message
    await expect(page.locator('text=Document assigned successfully')).toBeVisible({ timeout: 5000 });
    
    // Status should change to In Review
    await expect(page.locator('text=In Review')).toBeVisible();
  });

  test('Teacher can bulk assign multiple documents', async ({ page }) => {
    await page.goto('/documents');
    
    // Select multiple pending documents
    await page.click('input[type="checkbox"][value*="Thank_You_Letter"]');
    await page.click('input[type="checkbox"][value*="Personal_Letter"]');
    
    // Click bulk assign
    await page.click('button:has-text("Bulk Assign")');
    
    // Select reviewer
    await page.selectOption('select[name="reviewer"]', 'reviewer2@example.com');
    await page.click('button:has-text("Assign Selected")');
    
    // Should show success
    await expect(page.locator('text=2 documents assigned')).toBeVisible({ timeout: 5000 });
  });

  test('Teacher cannot approve/reject documents', async ({ page }) => {
    await page.goto('/documents');
    
    // Find a document in review
    await page.click('text=Discourse_Vipassana_Course');
    
    // Approve/Reject buttons should not be visible for teachers
    await expect(page.locator('button:has-text("Approve")')).not.toBeVisible();
    await expect(page.locator('button:has-text("Reject")')).not.toBeVisible();
  });
});

// Test Suite 3: Reviewer - Review & Approval
test.describe('Reviewer - Document Review Workflow', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, 'reviewer1@example.com', 'reviewer123');
  });

  test('Reviewer can view assigned documents', async ({ page }) => {
    await page.goto('/my-documents');
    
    // Should see assigned documents
    await expect(page.locator('text=My Assigned Documents')).toBeVisible();
    await expect(page.locator('tr[data-status="in_review"]')).toBeVisible({ timeout: 5000 });
  });

  test('Reviewer cannot see unassigned private documents', async ({ page }) => {
    await page.goto('/documents');
    
    // Try to filter private documents
    await page.click('button:has-text("Private")');
    
    // Should only see assigned private docs, not all private docs
    const privateDocsCount = await page.locator('tr:has-text("🔒")').count();
    
    // Reviewer should see fewer private docs than teacher (only assigned ones)
    expect(privateDocsCount).toBeLessThan(4); // Total private docs = 4
  });

  test('Reviewer can approve document', async ({ page }) => {
    await page.goto('/my-documents');
    
    // Click on assigned document
    await page.click('text=Discourse_Vipassana_Course');
    
    // Review the document
    await expect(page.locator('text=OCR Text:')).toBeVisible();
    
    // Click approve button
    await page.click('button:has-text("Approve")');
    
    // Add review notes
    await page.fill('textarea[name="notes"]', 'Text quality excellent, metadata complete');
    
    // Confirm approval
    await page.click('button:has-text("Confirm Approval")');
    
    // Should show success
    await expect(page.locator('text=Document approved successfully')).toBeVisible({ timeout: 5000 });
    
    // Document should be removed from active queue
    await page.goto('/my-documents');
    await expect(page.locator('text=Discourse_Vipassana_Course')).not.toBeVisible();
  });

  test('Reviewer can reject document with reason', async ({ page }) => {
    await page.goto('/my-documents');
    
    // Click on assigned document
    await page.click('text=Course_Schedule_Mumbai');
    
    // Click reject button
    await page.click('button:has-text("Reject")');
    
    // Select rejection reason
    await page.selectOption('select[name="reason"]', 'poor_ocr_quality');
    
    // Add notes
    await page.fill('textarea[name="notes"]', 'Multiple words unreadable, needs re-processing');
    
    // Confirm rejection
    await page.click('button:has-text("Confirm Rejection")');
    
    // Should show success
    await expect(page.locator('text=Document rejected')).toBeVisible({ timeout: 5000 });
  });

  test('Reviewer can view review statistics', async ({ page }) => {
    await page.goto('/my-stats');
    
    // Should see statistics
    await expect(page.locator('text=My Review Statistics')).toBeVisible();
    await expect(page.locator('text=Total Reviewed:')).toBeVisible();
    await expect(page.locator('text=Approved:')).toBeVisible();
    await expect(page.locator('text=Rejected:')).toBeVisible();
  });

  test('Reviewer cannot assign documents', async ({ page }) => {
    await page.goto('/documents');
    
    // Assign button should not be available
    await expect(page.locator('button:has-text("Assign to Reviewer")')).not.toBeVisible();
  });

  test('Reviewer cannot access admin panel', async ({ page }) => {
    await page.goto('/admin');
    
    // Should be redirected or show access denied
    await expect(page.locator('text=Access Denied, text=Unauthorized')).toBeVisible({ timeout: 5000 });
  });
});

// Test Suite 4: Admin - Full Access
test.describe('Admin - Full System Access', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, 'admin@example.com', 'admin123');
  });

  test('Admin can view all documents', async ({ page }) => {
    await page.goto('/documents');
    
    // Should see all documents regardless of status/classification
    const allDocs = await page.locator('tr[data-document]').count();
    expect(allDocs).toBeGreaterThanOrEqual(10);
  });

  test('Admin can view audit logs', async ({ page }) => {
    await page.goto('/admin/audit-logs');
    
    // Should see audit log entries
    await expect(page.locator('text=Audit Logs')).toBeVisible();
    await expect(page.locator('tr:has-text("document_assigned")')).toBeVisible({ timeout: 5000 });
  });

  test('Admin can filter audit logs by action', async ({ page }) => {
    await page.goto('/admin/audit-logs');
    
    // Filter by action type
    await page.selectOption('select[name="action"]', 'document_assigned');
    await page.click('button:has-text("Filter")');
    
    // Should only show assignment actions
    await expect(page.locator('tr:has-text("document_assigned")')).toBeVisible();
    await expect(page.locator('tr:has-text("document_approved")')).not.toBeVisible();
  });

  test('Admin can view user management', async ({ page }) => {
    await page.goto('/admin/users');
    
    // Should see all users
    await expect(page.locator('text=User Management')).toBeVisible();
    await expect(page.locator('tr:has-text("reviewer1@example.com")')).toBeVisible();
    await expect(page.locator('tr:has-text("teacher1@example.com")')).toBeVisible();
  });

  test('Admin can change user roles', async ({ page }) => {
    await page.goto('/admin/users');
    
    // Find user
    const userRow = page.locator('tr:has-text("reviewer1@example.com")');
    await userRow.click();
    
    // Click edit roles
    await page.click('button:has-text("Edit Roles")');
    
    // Add teacher role
    await page.check('input[value="teacher"]');
    
    // Save changes
    await page.click('button:has-text("Save")');
    
    // Should show success
    await expect(page.locator('text=Roles updated successfully')).toBeVisible({ timeout: 5000 });
  });

  test('Admin can export documents', async ({ page }) => {
    await page.goto('/documents');
    
    // Click export button
    const downloadPromise = page.waitForEvent('download');
    await page.click('button:has-text("Export")');
    const download = await downloadPromise;
    
    // Verify download
    expect(download.suggestedFilename()).toContain('.csv');
  });
});

// Test Suite 5: Document Status Workflow
test.describe('Document Status Transitions', () => {
  test('Full workflow: Pending → Assigned → Approved', async ({ page }) => {
    // Step 1: Teacher assigns document
    await login(page, 'teacher2@example.com', 'teacher123');
    await page.goto('/documents');
    
    const pendingDoc = page.locator('tr:has-text("Thank_You_Letter")').first();
    await pendingDoc.click();
    await page.click('button:has-text("Assign")');
    await page.selectOption('select[name="reviewer"]', 'reviewer3@example.com');
    await page.click('button:has-text("Confirm")');
    
    await expect(page.locator('text=In Review')).toBeVisible();
    await logout(page);
    
    // Step 2: Reviewer approves
    await login(page, 'reviewer3@example.com', 'reviewer123');
    await page.goto('/my-documents');
    await page.click('text=Thank_You_Letter');
    await page.click('button:has-text("Approve")');
    await page.fill('textarea[name="notes"]', 'Approved by E2E test');
    await page.click('button:has-text("Confirm")');
    
    await expect(page.locator('text=Document approved')).toBeVisible();
    await logout(page);
    
    // Step 3: Verify as admin
    await login(page, 'admin@example.com', 'admin123');
    await page.goto('/documents');
    await page.click('text=Thank_You_Letter');
    
    await expect(page.locator('text=Approved')).toBeVisible();
    await expect(page.locator('text=reviewer3@example.com')).toBeVisible();
  });

  test('Rejection workflow with reassignment', async ({ page }) => {
    // Reviewer rejects
    await login(page, 'reviewer2@example.com', 'reviewer123');
    await page.goto('/my-documents');
    
    const doc = page.locator('tr[data-status="in_review"]').first();
    await doc.click();
    await page.click('button:has-text("Reject")');
    await page.selectOption('select[name="reason"]', 'poor_ocr_quality');
    await page.fill('textarea[name="notes"]', 'Needs reprocessing');
    await page.click('button:has-text("Confirm")');
    
    await expect(page.locator('text=Document rejected')).toBeVisible();
    await logout(page);
    
    // Teacher can reassign
    await login(page, 'teacher3@example.com', 'teacher123');
    await page.goto('/documents');
    await page.click('select[name="status"]');
    await page.click('option:has-text("Rejected")');
    
    // Should see rejected document available for reassignment
    await expect(page.locator('tr[data-status="rejected"]')).toBeVisible();
  });
});

// Test Suite 6: Error Handling & Edge Cases
test.describe('Error Handling & Edge Cases', () => {
  test('Cannot assign already assigned document', async ({ page }) => {
    await login(page, 'teacher1@example.com', 'teacher123');
    await page.goto('/documents');
    
    // Try to assign document that's already in review
    const inReviewDoc = page.locator('tr[data-status="in_review"]').first();
    await inReviewDoc.click();
    
    // Assign button should be disabled or show "Already Assigned"
    const assignBtn = page.locator('button:has-text("Assign")');
    await expect(assignBtn).toBeDisabled().or(expect(page.locator('text=Already Assigned')).toBeVisible());
  });

  test('Empty review notes shows validation error', async ({ page }) => {
    await login(page, 'reviewer1@example.com', 'reviewer123');
    await page.goto('/my-documents');
    
    const doc = page.locator('tr[data-status="in_review"]').first();
    await doc.click();
    await page.click('button:has-text("Approve")');
    
    // Try to submit without notes
    await page.click('button:has-text("Confirm")');
    
    // Should show validation error
    await expect(page.locator('text=Please provide review notes')).toBeVisible({ timeout: 5000 });
  });

  test('Session timeout redirects to login', async ({ page }) => {
    await login(page, 'reviewer1@example.com', 'reviewer123');
    
    // Clear cookies to simulate session expiry
    await page.context().clearCookies();
    
    // Try to navigate
    await page.goto('/my-documents');
    
    // Should redirect to login
    await expect(page).toHaveURL(/login/);
  });

  test('Concurrent assignment prevention', async ({ browser }) => {
    // Open two browser contexts
    const context1 = await browser.newContext();
    const context2 = await browser.newContext();
    
    const page1 = await context1.newPage();
    const page2 = await context2.newPage();
    
    // Both teachers try to assign same document
    await login(page1, 'teacher1@example.com', 'teacher123');
    await login(page2, 'teacher2@example.com', 'teacher123');
    
    await page1.goto('/documents');
    await page2.goto('/documents');
    
    const docName = 'Personal_Letter_Family';
    
    // Both click assign simultaneously
    await Promise.all([
      page1.click(`tr:has-text("${docName}") button:has-text("Assign")`),
      page2.click(`tr:has-text("${docName}") button:has-text("Assign")`)
    ]);
    
    // One should succeed, one should fail
    const errorVisible = await page2.locator('text=Already assigned, text=Conflict').isVisible().catch(() => false);
    expect(errorVisible).toBeTruthy();
    
    await context1.close();
    await context2.close();
  });
});

// Test Suite 7: Performance & Load
test.describe('Performance Tests', () => {
  test('Document list loads within acceptable time', async ({ page }) => {
    await login(page, 'admin@example.com', 'admin123');
    
    const startTime = Date.now();
    await page.goto('/documents');
    await page.waitForSelector('tr[data-document]', { timeout: 5000 });
    const loadTime = Date.now() - startTime;
    
    // Should load within 3 seconds
    expect(loadTime).toBeLessThan(3000);
  });

  test('Audit logs pagination works correctly', async ({ page }) => {
    await login(page, 'admin@example.com', 'admin123');
    await page.goto('/admin/audit-logs');
    
    // Should have pagination controls
    await expect(page.locator('button:has-text("Next")')).toBeVisible();
    
    // Click next page
    await page.click('button:has-text("Next")');
    
    // Should load next page
    await expect(page.locator('text=Page 2')).toBeVisible({ timeout: 3000 });
  });
});
