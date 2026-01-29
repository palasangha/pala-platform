# Email Testing and PDF Report Location

**Date:** January 25, 2026  
**Status:** ⚠️ Email credentials need update

## PDF Report Storage Location

### Host System Path:
```
/mnt/sda1/mango1_home/pala-platform/apps/feedback-system/volumes/reports/
```

### Docker Container Path:
```
/app/reports/
```

### Current Reports Available:

```bash
# List all reports
ls -lh /mnt/sda1/mango1_home/pala-platform/apps/feedback-system/volumes/reports/

# Current files:
- shop_weekly_20260118_to_20260125.pdf (4.9K)
- dpvc_weekly_20260118_to_20260125.pdf (5.3K)
- food_court_weekly_20260118_to_20260125.pdf (5.1K)
- global_pagoda_weekly_20260118_to_20260125.pdf (5.1K)
- dhammalaya_weekly_20260117_to_20260124.pdf (4.6K)
```

## Test Email Status

**Target Email:** tod@vridhamma.org  
**Status:** ❌ Failed - Gmail credentials invalid

### Error:
```
Invalid login: 535-5.7.8 Username and Password not accepted
```

### Required Actions:

1. **Update Gmail App Password**
   - Current: Expired or incorrect
   - Location: Environment variable `GMAIL_APP_PASSWORD`
   - Update in: `.env` file or docker-compose environment

2. **Or Use Alternative SMTP**
   - Configure SMTP_HOST, SMTP_USER, SMTP_PASS
   - Can use any SMTP service (Gmail, SendGrid, etc.)

## How to Send Test Email (Once Credentials Fixed)

### Method 1: Using Test Script
```bash
# Copy script to container
docker cp send_test_email.js feedback-backend:/app/

# Send test email
docker exec feedback-backend node /app/send_test_email.js \
  "tod@vridhamma.org" \
  "/app/reports/shop_weekly_20260118_to_20260125.pdf"
```

### Method 2: Using API
```bash
# Login as admin
TOKEN=$(curl -s -X POST http://localhost:3001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"superadmin@globalpagoda.org","password":"SuperAdmin@2026!"}' \
  | jq -r '.data.token')

# Trigger report (will auto-email to configured recipients)
curl -X POST http://localhost:3001/api/reports/trigger \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"department_code": "shop"}'
```

### Method 3: Manual Download and Email
```bash
# Download PDF from host
cp /mnt/sda1/mango1_home/pala-platform/apps/feedback-system/volumes/reports/shop_weekly_20260118_to_20260125.pdf ~/

# Manually attach and email to tod@vridhamma.org
```

## Fixing Gmail Credentials

### Step 1: Generate Gmail App Password
1. Go to Google Account → Security
2. Enable 2-Step Verification
3. Create App Password for "Mail"
4. Copy the 16-character password

### Step 2: Update Environment
Edit `/mnt/sda1/mango1_home/pala-platform/apps/feedback-system/.env`:
```bash
GMAIL_FROM_EMAIL=noreply@globalpagoda.org
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx  # Your new app password
```

### Step 3: Restart Backend
```bash
cd /mnt/sda1/mango1_home/pala-platform/apps/feedback-system
docker-compose restart backend
```

## Weekly Report Schedule

Reports are automatically generated and emailed weekly:
- **Frequency:** Every Monday at 9:00 AM
- **Period:** Previous 7 days
- **Recipients:** Configured per department in database
- **Location:** Saved to `/app/reports/`

### Current Recipients:

**Shop:**
- shop@globalpagoda.org

**Dhammalaya:**  
- dhammalane@globalpagoda.org

**Food Court:**
- foodcourt@globalpagoda.org

**DPVC:**
- dpvc@globalpagoda.org

**Global Pagoda:**
- head@globalpagoda.org

## To Add tod@vridhamma.org to Weekly Reports

### Option 1: Add to Department Recipients
```bash
# Update department email recipients in database
docker exec feedback-backend node -e "
const mongoose = require('mongoose');
const Department = require('./src/models/Department');

mongoose.connect(process.env.MONGODB_URI).then(async () => {
  await Department.findOneAndUpdate(
    { code: 'shop' },
    { \$addToSet: { email_recipients: 'tod@vridhamma.org' } }
  );
  console.log('Added tod@vridhamma.org to shop recipients');
  process.exit(0);
});
"
```

### Option 2: Add as Super Admin (Gets All Reports)
Update super admin email in database to receive all department reports.

## Next Steps

1. ✅ PDF reports are being generated correctly
2. ✅ Reports stored at `/volumes/reports/`
3. ⚠️ Need to fix Gmail credentials to enable email
4. 📧 Once fixed, test email will be sent to tod@vridhamma.org

---

**Test Script Location:** `/mnt/sda1/mango1_home/pala-platform/apps/feedback-system/send_test_email.js`

**Report Location (Host):** `/mnt/sda1/mango1_home/pala-platform/apps/feedback-system/volumes/reports/`

**Report Location (Container):** `/app/reports/`
