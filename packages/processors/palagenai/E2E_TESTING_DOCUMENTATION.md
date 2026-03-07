# E2E Testing Documentation - RBAC Workflows

## Overview
Comprehensive Playwright end-to-end tests for Role-Based Access Control (RBAC) workflows covering all user roles, document statuses, and approval processes.

---

## 📋 Test Coverage

### Test Suites (7 Total)

#### 1. Authentication Tests (4 tests)
- ✅ Admin login
- ✅ Reviewer login  
- ✅ Teacher login
- ✅ Invalid credentials rejection

#### 2. Teacher Workflow Tests (6 tests)
- ✅ View pending documents
- ✅ View private documents
- ✅ Assign document to reviewer
- ✅ Bulk assign multiple documents
- ✅ Cannot approve/reject (permission check)
- ✅ Access control validation

#### 3. Reviewer Workflow Tests (7 tests)
- ✅ View assigned documents
- ✅ Cannot see unassigned private documents
- ✅ Approve document with notes
- ✅ Reject document with reason
- ✅ View review statistics
- ✅ Cannot assign documents (permission check)
- ✅ Cannot access admin panel

#### 4. Admin Tests (6 tests)
- ✅ View all documents (public + private)
- ✅ View audit logs
- ✅ Filter audit logs by action
- ✅ User management access
- ✅ Change user roles
- ✅ Export documents

#### 5. Document Status Workflow Tests (2 tests)
- ✅ Full workflow: Pending → Assigned → Approved
- ✅ Rejection workflow with reassignment

#### 6. Error Handling Tests (4 tests)
- ✅ Cannot assign already assigned document
- ✅ Empty review notes validation
- ✅ Session timeout handling
- ✅ Concurrent assignment prevention

#### 7. Performance Tests (2 tests)
- ✅ Document list load time (<3s)
- ✅ Audit log pagination

**Total Tests: 31**

---

## 🚀 Running Tests

### Quick Start
```bash
# Run all tests
./run-e2e-tests.sh

# Run with UI (interactive mode)
./run-e2e-tests.sh --ui

# Run in debug mode
./run-e2e-tests.sh --debug

# Run in headed mode (see browser)
./run-e2e-tests.sh --headed
```

### From Frontend Directory
```bash
cd frontend

# Run all tests
npm run test:e2e

# Open Playwright UI
npm run test:e2e:ui

# View HTML report
npm run test:e2e:report
```

### Run Specific Test Suite
```bash
cd frontend
npx playwright test rbac-workflow.spec.ts --grep "Teacher"
npx playwright test rbac-workflow.spec.ts --grep "Reviewer"
npx playwright test rbac-workflow.spec.ts --grep "Admin"
```

### Run Single Test
```bash
npx playwright test -g "Admin can view all documents"
```

---

## 📊 Test Data Requirements

### Users (must exist in MongoDB)
- admin@example.com / admin123
- teacher1@example.com / teacher123
- teacher2@example.com / teacher123
- teacher3@example.com / teacher123
- reviewer1@example.com / reviewer123
- reviewer2@example.com / reviewer123
- reviewer3@example.com / reviewer123

### Documents (10 sample documents)
- 3 Pending status
- 3 In Review status
- 3 Approved status
- 1 Rejected status
- 6 Public classification
- 4 Private classification

**Note:** Sample data is already created by the `create_sample_data.py` script.

---

## 🎯 What Each Test Validates

### Authentication Tests
- **Purpose:** Ensure users can login with correct credentials and are rejected with wrong ones
- **Validates:** JWT token generation, session management, role-based redirects

### Teacher Workflow Tests
- **Purpose:** Verify teachers can assign documents and view all documents
- **Validates:** 
  - Document visibility (public + private)
  - Assignment functionality
  - Bulk operations
  - Permission boundaries (cannot approve/reject)

### Reviewer Workflow Tests
- **Purpose:** Ensure reviewers can only see assigned documents and perform reviews
- **Validates:**
  - Document visibility restrictions (no unassigned private docs)
  - Approval workflow
  - Rejection workflow with reasons
  - Statistics viewing
  - Permission boundaries (cannot assign, cannot access admin)

### Admin Tests
- **Purpose:** Verify admin has full system access
- **Validates:**
  - View all documents regardless of status/classification
  - Access audit logs
  - Filter and search capabilities
  - User management
  - Role modification
  - Data export

### Document Status Workflow Tests
- **Purpose:** Test complete document lifecycle
- **Validates:**
  - Status transitions (Pending → In Review → Approved/Rejected)
  - Assignment tracking
  - Approval/rejection recording
  - Reassignment capability

### Error Handling Tests
- **Purpose:** Ensure system handles edge cases gracefully
- **Validates:**
  - Duplicate assignment prevention
  - Form validation
  - Session expiry handling
  - Concurrent access control

### Performance Tests
- **Purpose:** Ensure acceptable response times
- **Validates:**
  - Page load times
  - Pagination functionality
  - Large dataset handling

---

## 🔍 Test Scenarios in Detail

### Scenario 1: Teacher Assigns Document
```
1. Login as teacher1@example.com
2. Navigate to documents page
3. Find pending document "Letter_Gandhi_to_Nehru_1947.pdf"
4. Click Assign button
5. Select reviewer1@example.com from dropdown
6. Confirm assignment
7. Verify status changes to "In Review"
8. Verify success message displayed
9. Verify audit log created
```

### Scenario 2: Reviewer Approves Document
```
1. Login as reviewer1@example.com
2. Navigate to "My Documents"
3. Open assigned document "Discourse_Vipassana_Course_1970.pdf"
4. Review OCR text and metadata
5. Click Approve button
6. Enter review notes: "Text quality excellent"
7. Click Confirm
8. Verify status changes to "Approved"
9. Verify document removed from active queue
10. Verify audit log created
```

### Scenario 3: Reviewer Rejects Document
```
1. Login as reviewer2@example.com
2. Navigate to assigned documents
3. Open "Course_Schedule_Mumbai_1971.pdf"
4. Click Reject button
5. Select reason: "Poor OCR Quality"
6. Enter notes: "Multiple words unreadable"
7. Click Confirm
8. Verify status changes to "Rejected"
9. Verify rejection reason saved
10. Verify document available for reassignment
```

### Scenario 4: Admin Views Audit Logs
```
1. Login as admin@example.com
2. Navigate to Admin → Audit Logs
3. Filter by action: "document_assigned"
4. Filter by user: reviewer1@example.com
5. Verify all assignment actions visible
6. Verify timestamps, IP addresses shown
7. Verify can export logs
```

---

## 📈 Expected Test Results

### Success Criteria
- ✅ All 31 tests pass
- ✅ No authentication errors
- ✅ All role permissions correctly enforced
- ✅ Document status transitions work correctly
- ✅ Audit logs created for all actions
- ✅ Error handling works as expected
- ✅ Performance metrics met (<3s load times)

### Generated Reports
After test run, the following reports are generated:

1. **HTML Report**: `frontend/playwright-report/index.html`
   - Visual test results
   - Screenshots of failures
   - Trace files for debugging

2. **JSON Report**: `frontend/test-results/results.json`
   - Structured test data
   - Can be parsed for CI/CD

3. **Console Output**: Terminal output with pass/fail status

---

## 🐛 Debugging Failed Tests

### View Test Report
```bash
cd frontend
npm run test:e2e:report
```

### Run Single Failed Test with Trace
```bash
npx playwright test --grep "Test name" --trace on
```

### Debug with Playwright Inspector
```bash
npx playwright test --debug --grep "Test name"
```

### View Screenshots
Failed tests automatically capture screenshots in:
```
frontend/test-results/
```

### View Trace Files
```bash
npx playwright show-trace frontend/test-results/trace.zip
```

---

## 🔧 Configuration

### Playwright Config (`playwright.config.ts`)
```typescript
- Base URL: https://localhost:3000
- Browser: Chromium (Desktop Chrome)
- Workers: 1 (sequential execution)
- Retries: 2 (in CI), 0 (local)
- Screenshots: On failure
- Trace: On first retry
- Ignore HTTPS errors: true
```

### Timeouts
- Default timeout: 30s
- Navigation timeout: 10s
- Assertion timeout: 5s

---

## 📝 Adding New Tests

### Template for New Test
```typescript
test('Description of what test validates', async ({ page }) => {
  // 1. Setup (login, navigate)
  await login(page, 'user@example.com', 'password');
  await page.goto('/page-url');
  
  // 2. Action (click, fill, etc.)
  await page.click('button:has-text("Action")');
  
  // 3. Assertion (verify expected outcome)
  await expect(page.locator('text=Success')).toBeVisible();
});
```

### Best Practices
1. Use descriptive test names
2. Include setup and teardown
3. Use data-testid attributes for stable selectors
4. Avoid hardcoded waits, use waitForSelector
5. Take screenshots on failure
6. Clean up test data after suite

---

## 🚨 Common Issues & Solutions

### Issue: Tests failing with "Element not visible"
**Solution:** Add explicit wait
```typescript
await page.waitForSelector('selector', { timeout: 5000 });
```

### Issue: Authentication fails
**Solution:** Verify test users exist in MongoDB
```bash
docker exec gvpocr-mongodb mongosh ... --eval "db.users.find({email: 'admin@example.com'})"
```

### Issue: Concurrent test failures
**Solution:** Ensure workers: 1 in config for sequential execution

### Issue: Timeout errors
**Solution:** Increase timeout in test or config
```typescript
test.setTimeout(60000); // 60 seconds
```

---

## 📊 CI/CD Integration

### GitHub Actions Example
```yaml
- name: Run E2E Tests
  run: |
    ./run-e2e-tests.sh
    
- name: Upload Test Results
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: playwright-report
    path: frontend/playwright-report
```

### Docker-based CI
```bash
docker-compose up -d
sleep 10  # Wait for services
./run-e2e-tests.sh
docker-compose down
```

---

## 📚 Resources

- [Playwright Documentation](https://playwright.dev)
- [Best Practices](https://playwright.dev/docs/best-practices)
- [Selectors Guide](https://playwright.dev/docs/selectors)
- [Debugging Guide](https://playwright.dev/docs/debug)

---

**Created:** 2026-01-26  
**Last Updated:** 2026-01-26  
**Version:** 1.0
**Total Test Coverage:** 31 tests across 7 suites
