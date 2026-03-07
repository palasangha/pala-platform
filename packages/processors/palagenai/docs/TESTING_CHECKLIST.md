# System Settings Testing Checklist

## Pre-Testing Setup

- [ ] Docker and docker-compose are installed
- [ ] Application is running (`docker-compose up`)
- [ ] Frontend is accessible (http://localhost:3000)
- [ ] Backend API is accessible (http://localhost:5000)
- [ ] User is logged in

---

## Navigation Testing

### Access System Settings Page
- [ ] From any page, locate the Settings button (gear icon) in top navigation
- [ ] Settings button is positioned on the right side of navigation bar
- [ ] Click Settings button
- [ ] Page loads successfully (/system-settings)
- [ ] No console errors appear

### Navigation Bar Display
- [ ] Navigation bar shows: Projects | Bulk OCR | Archipelago | Workers | Supervisor | [Settings]
- [ ] Settings button has purple background when active
- [ ] Settings button text is "Settings" with gear icon
- [ ] All other navigation buttons work

---

## Service URLs Section

### Backend URL
- [ ] Backend URL displays (should be http://localhost:5000)
- [ ] Copy button next to Backend URL works
- [ ] Clicking copy shows "Copied" confirmation
- [ ] Backend port displays correctly (5000)
- [ ] Environment shows (Development/Production)

### Frontend URL
- [ ] Frontend URL displays (should be http://localhost:3000)
- [ ] Copy button next to Frontend URL works
- [ ] Clicking copy shows "Copied" confirmation
- [ ] Frontend port displays correctly (3000)
- [ ] Environment shows (development/production)

---

## Running Docker Services Section

### Section Display
- [ ] Title shows "Running Docker Services (XX)" where XX is count
- [ ] Services are displayed in a list/card format
- [ ] Each service card shows:
  - [ ] Service name (e.g., gvpocr-backend)
  - [ ] Image name (e.g., gvpocr-backend:latest)
  - [ ] Status (e.g., "Up 3 hours") in green text
  - [ ] Container ID (short 12-char version)
  - [ ] Port mappings (if any)

### Service Actions
- [ ] Each service has a "Download Logs" button
- [ ] Each service has a "Restart" button
- [ ] Clicking Download Logs downloads a .txt file
- [ ] File contains service logs
- [ ] Clicking Restart shows "Restarting..." state
- [ ] After restart, page auto-refreshes

### Service Count
- [ ] Count matches `docker ps` output
- [ ] Should show 15-20 services typically
- [ ] New services appear after restart

---

## Configured Services Section

### Section Display
- [ ] Title shows "Configured Services in docker-compose.yml (XX)" where XX is count
- [ ] Services displayed in 3-column grid layout (on desktop)
- [ ] Services from docker-compose.yml are listed
- [ ] Service count should be 20+

### Service Status Badges
- [ ] Running services show 🟢 with "Running" label in green
- [ ] Stopped services show ⚪ with "Stopped" label in yellow
- [ ] Colors are accurate (green for running, yellow for stopped)
- [ ] Status matches running services list

### Service Information
- [ ] Each card shows service name
- [ ] Service image is displayed
- [ ] Status badge is visible and correct

### Examples of Services
- [ ] mongodb shows status
- [ ] backend shows status (should be running)
- [ ] frontend shows status (should be running)
- [ ] Recognizes all services from docker-compose.yml

---

## Configuration Section

### Configuration Display
- [ ] "Configuration" section displays
- [ ] "Edit Settings" button is visible

### Archipelago Commons
- [ ] Base URL field shows the configured URL
- [ ] SSL Verify toggle shows current setting (Enabled/Disabled)
- [ ] Color coding: Green for enabled, yellow for disabled

### Database
- [ ] MongoDB status shows (Connected/Disconnected)
- [ ] Status color is correct (green/red)
- [ ] Database name displays (gvpocr)

### Message Queue (NSQ)
- [ ] NSQ status shows (Enabled/Disabled)
- [ ] NSQ address displays
- [ ] Status color is correct

### Docker
- [ ] Swarm Mode status shows (Enabled/Disabled)
- [ ] Worker image name displays

---

## Edit Settings Mode

### Entering Edit Mode
- [ ] Click "Edit Settings" button
- [ ] Button changes to "Save" and "Cancel"
- [ ] Archipelago URL field becomes editable (text input)
- [ ] SSL Verify becomes a checkbox (interactive)

### Editing Values
- [ ] Modify Archipelago URL to a test value
- [ ] Check SSL Verify checkbox/uncheck it
- [ ] Changes are reflected in the form

### Saving Changes
- [ ] Click "Save" button
- [ ] Shows loading state or confirmation message
- [ ] Settings are saved to .env file
- [ ] Values persist after page refresh
- [ ] Returns to view-only mode

### Canceling Changes
- [ ] Make changes to a field
- [ ] Click "Cancel" button
- [ ] Changes are discarded
- [ ] Returns to view-only mode

---

## Auto-Refresh Functionality

### Refresh Indicator
- [ ] Page shows "Last updated: HH:MM:SS" at bottom
- [ ] Timestamp updates every 30 seconds
- [ ] Service status updates automatically

### Refresh Behavior
- [ ] Service statuses refresh without manual action
- [ ] New services appear in list
- [ ] Removed services disappear from list
- [ ] Configuration changes appear after save

---

## Error Handling

### Network Errors
- [ ] Intentionally disconnect internet
- [ ] Page shows error message
- [ ] Reconnect internet
- [ ] Page recovers and loads data

### API Errors
- [ ] Backend returns error (simulate by stopping backend)
- [ ] Error message displays in red box
- [ ] Error text is helpful and descriptive
- [ ] Frontend doesn't crash

### Timeout Handling
- [ ] Wait for request timeout (>10 seconds)
- [ ] Error message appears
- [ ] System handles gracefully

---

## Console Checks

Open Developer Tools (F12) and go to Console tab:

- [ ] No red error messages
- [ ] No "TypeError" messages
- [ ] No "Cannot find..." messages
- [ ] No CORS errors
- [ ] No 404 errors
- [ ] Network tab shows all requests returning 200 status

### Specific Checks
- [ ] GET /api/system/status → 200 OK
- [ ] GET /api/system/config → 200 OK
- [ ] Requests contain Authorization header with valid token
- [ ] Response JSON is well-formed

---

## Responsive Design

### Desktop (1200px+)
- [ ] 3-column grid for configured services
- [ ] All content visible without scrolling
- [ ] Buttons are properly spaced

### Tablet (768px-1199px)
- [ ] 2-column grid for configured services
- [ ] Content is readable
- [ ] Navigation doesn't overflow

### Mobile (< 768px)
- [ ] 1-column grid for configured services
- [ ] Navigation wraps properly
- [ ] Buttons are touch-friendly (≥44px)
- [ ] Content is readable

---

## Performance Tests

- [ ] Page loads in < 3 seconds
- [ ] List of services renders smoothly
- [ ] No lag when scrolling
- [ ] Restart button responds immediately
- [ ] Download logs completes quickly

---

## Security Tests

### Authentication
- [ ] Logout and access /system-settings directly
- [ ] Redirected to login page
- [ ] Cannot access without token
- [ ] Invalid token shows error

### Token Refresh
- [ ] Token expires during session
- [ ] System automatically refreshes token
- [ ] Request succeeds with new token
- [ ] No user disruption

---

## Cross-Browser Testing

Test in each browser:

### Chrome/Edge
- [ ] Page loads correctly
- [ ] All features work
- [ ] No console errors

### Firefox
- [ ] Page loads correctly
- [ ] All features work
- [ ] No console errors

### Safari
- [ ] Page loads correctly
- [ ] All features work
- [ ] No console errors

---

## Logout Testing

- [ ] Click Logout button in top right
- [ ] Redirected to login page
- [ ] Session is cleared
- [ ] Token is removed from localStorage
- [ ] Cannot navigate back to System Settings

---

## Final Verification

- [ ] All services from docker-compose.yml are visible
- [ ] All running services from docker ps are listed
- [ ] Configuration is accurate
- [ ] No data is missing or incorrect
- [ ] UI is clean and professional
- [ ] Navigation is intuitive
- [ ] Error handling is robust
- [ ] Performance is acceptable

---

## Sign-Off

- [ ] All tests passed
- [ ] No critical issues found
- [ ] Ready for production deployment

**Tested by:** ___________________
**Date:** ___________________
**Notes:** 
```
[Add any issues or observations here]
```

