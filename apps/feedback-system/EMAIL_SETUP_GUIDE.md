# Gmail Email Setup Guide

## Quick Setup (3 Steps)

### Step 1: Get Gmail App Password

1. Go to your Google Account: https://myaccount.google.com/security
2. Enable "2-Step Verification" (if not enabled)
3. Go to: https://myaccount.google.com/apppasswords
4. Create app password:
   - App: Mail
   - Device: Other (enter "Feedback System")
5. Copy the 16-character password (no spaces)

### Step 2: Configure System

Run the setup script:

```bash
cd /mnt/sda1/mango1_home/pala-platform/apps/feedback-system
./setup-gmail.sh
```

Or manually edit `.env`:

```bash
GMAIL_USER=your-email@gmail.com
GMAIL_APP_PASSWORD=abcd efgh ijkl mnop    # Remove spaces: abcdefghijklmnop
```

### Step 3: Test Email

```bash
# Test with your email address
docker-compose exec backend node test-email.js your-email@gmail.com food_court

# Or test with admin email
docker-compose exec backend node test-email.js admin@globalpagoda.org dpvc
```

---

## Manual Configuration

Edit the `.env` file:

```env
# Gmail SMTP (Simple - Recommended)
GMAIL_USER=feedback@globalpagoda.org
GMAIL_APP_PASSWORD=your-16-char-app-password

# Alternative: Generic SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_SECURE=false
SMTP_USER=feedback@globalpagoda.org
SMTP_PASS=your-16-char-app-password
SMTP_FROM=feedback@globalpagoda.org
```

After editing, restart backend:

```bash
docker-compose restart backend
```

---

## Test Email Script

The test script sends a PDF report to verify email is working:

```bash
docker-compose exec backend node test-email.js <recipient> <department>
```

**Parameters:**
- `<recipient>`: Email address to send to
- `<department>`: Department code (food_court, dpvc, shop, dhamma_lane, global_pagoda)

**Examples:**

```bash
# Send food court report to admin
docker-compose exec backend node test-email.js admin@example.com food_court

# Send DPVC report to yourself
docker-compose exec backend node test-email.js your@email.com dpvc

# Send shop report to multiple (comma-separated in quotes)
docker-compose exec backend node test-email.js "admin1@test.com,admin2@test.com" shop
```

---

## What Gets Sent

The email includes:
- ✉️ Professional HTML email template
- 📊 Summary statistics (total responses, average rating, comments)
- 📈 Trend indicators
- 📎 PDF attachment with full report:
  - Question-wise analysis
  - Charts and distributions
  - All user comments
  - Recommendations

---

## Scheduled Reports

Once configured, weekly reports are automatically sent:

- **Schedule**: Every Sunday at 9:00 AM (configured per department)
- **Recipients**: Department email_recipients list
- **Content**: Past week's feedback data

Check scheduled reports:

```bash
docker-compose logs backend | grep "Scheduling"
```

---

## Troubleshooting

### Email not sending?

1. **Check credentials**:
   ```bash
   docker-compose exec backend env | grep GMAIL
   ```

2. **Check email service status**:
   ```bash
   docker-compose logs backend | grep "Email service"
   ```

3. **Test connection**:
   ```bash
   docker-compose exec backend node -e "
   const nodemailer = require('nodemailer');
   const transporter = nodemailer.createTransporter({
     service: 'gmail',
     auth: {
       user: process.env.GMAIL_USER,
       pass: process.env.GMAIL_APP_PASSWORD
     }
   });
   transporter.verify()
     .then(() => console.log('✓ Gmail SMTP connection OK'))
     .catch(err => console.error('✗ Error:', err.message));
   "
   ```

### Common Issues

**"Invalid login"**
- Check app password is correct (16 characters, no spaces)
- Ensure 2-Step Verification is enabled

**"Email service not configured"**
- Restart backend after updating .env
- Check .env file has correct variable names

**"No such file"**
- Ensure there is feedback data for the department
- PDF generation requires at least 1 feedback entry

---

## Production Checklist

- [ ] Gmail App Password generated
- [ ] `.env` updated with credentials
- [ ] Backend restarted
- [ ] Test email sent successfully
- [ ] Recipients list configured for each department
- [ ] Scheduler verified in logs

---

## Support

For issues, check:
1. Backend logs: `docker-compose logs backend --tail=100`
2. Email service status: `docker-compose logs backend | grep "Email"`
3. Test script output for detailed error messages
