# 📚 Complete Tutorial - Feedback System for Global Vipassana Pagoda

**Version**: 1.0.0
**Last Updated**: January 23, 2026
**System URL**: http://localhost:3030

---

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [Getting Started](#getting-started)
3. [For Regular Users/Visitors](#for-regular-usersvisitors)
4. [For Department Administrators](#for-department-administrators)
5. [For Super Administrators](#for-super-administrators)
6. [Understanding Reports](#understanding-reports)
7. [Automated Features](#automated-features)
8. [Troubleshooting](#troubleshooting)
9. [FAQ](#faq)

---

## 🎯 System Overview

### What is This System?

The Feedback System is a web-based application designed to collect, manage, and analyze feedback from visitors and users of Global Vipassana Pagoda facilities including:

- **Global Pagoda** - Main meditation and spiritual center
- **DPVC** (Dhamma Pattana Vipassana Centre) - 10-day meditation courses
- **Dhammalaya** - Meditation and study facility
- **Food Court** - Dining and refreshments
- **Souvenir Store** - Spiritual books and merchandise

### Key Features

✅ **Public Feedback Collection** - No login required for submitting feedback
✅ **Multiple Rating Types** - Star ratings, emoji ratings, and numeric sliders
✅ **Anonymous Option** - Users can submit feedback anonymously
✅ **Real-time Dashboard** - Live statistics and insights
✅ **Automated PDF Reports** - Generated weekly and on-demand
✅ **Email Delivery** - Reports sent automatically to administrators
✅ **Role-Based Access** - Different permissions for department and super admins
✅ **Rate Limiting** - Prevents spam and abuse

### User Roles

| Role | Description | Access Level |
|------|-------------|--------------|
| **Public User** | Any visitor | Submit feedback only |
| **Department Admin** | Manages specific department | View own department data + generate reports |
| **Super Admin** | System administrator | Full access to all departments + system settings |

---

## 🚀 Getting Started

### Accessing the System

1. **Open your web browser** (Chrome, Firefox, Safari, or Edge)
2. **Navigate to**: http://localhost:3030
3. You will see the **Landing Page** with 5 department cards

### System Requirements

- **Browser**: Any modern web browser (updated within last 2 years)
- **Internet**: Required for accessing the system
- **JavaScript**: Must be enabled in browser
- **Screen**: Works on desktop, tablet, and mobile devices

---

## 👤 For Regular Users/Visitors

### How to Submit Feedback

#### Step 1: Select Department

On the landing page, you'll see 5 department cards:

```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ Global Pagoda   │  │      DPVC       │  │  Dhammalaya     │
│                 │  │                 │  │                 │
│  [Give Feedback]│  │  [Give Feedback]│  │  [Give Feedback]│
└─────────────────┘  └─────────────────┘  └─────────────────┘

┌─────────────────┐  ┌─────────────────┐
│   Food Court    │  │ Souvenir Store  │
│                 │  │                 │
│  [Give Feedback]│  │  [Give Feedback]│
└─────────────────┘  └─────────────────┘
```

**Click on any department card** you want to provide feedback for.

#### Step 2: Fill Your Information

You'll see a feedback form with the following fields:

**Personal Information** (Optional if you choose Anonymous):
- **Name**: Your full name
- **Email**: Your email address
- **☐ Submit Anonymously**: Check this box if you want to remain anonymous

> **Note**: If you check "Submit Anonymously", your name and email won't be recorded.

#### Step 3: Answer Rating Questions

Each department has **6-7 questions** with different rating types:

##### ⭐ Star Ratings (1-5 stars)
Example: "Rate your experience in the meditation hall"

Click on stars to rate:
```
☆ ☆ ☆ ☆ ☆  (0 - Not rated)
★ ☆ ☆ ☆ ☆  (1 - Poor)
★ ★ ☆ ☆ ☆  (2 - Fair)
★ ★ ★ ☆ ☆  (3 - Good)
★ ★ ★ ★ ☆  (4 - Very Good)
★ ★ ★ ★ ★  (5 - Excellent)
```

##### 😊 Emoji Ratings (1-5 emojis)
Example: "How would you rate the cleanliness?"

Click on emoji to rate:
```
😢 😟 😐 🙂 😊
1  2  3  4  5
```

##### 🎚️ Numeric Slider (0-10)
Example: "How likely are you to recommend?"

Drag the slider or click on the scale:
```
0 ─────●─────────── 10
(Not likely)    (Highly likely)
```

#### Step 4: Add Comments (Optional)

At the bottom of the form, you'll find a text area for comments:

```
┌─────────────────────────────────────────────────────┐
│ Additional Comments (Optional)                      │
│                                                     │
│ Share your detailed feedback, suggestions, or       │
│ concerns here...                                     │
│                                                     │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**Best Practices for Comments**:
- ✅ Be specific and constructive
- ✅ Mention what you liked
- ✅ Suggest improvements
- ❌ Avoid offensive language
- ❌ Don't include personal sensitive information

#### Step 5: Submit Feedback

1. **Review your ratings** - Make sure all required questions are answered
2. **Click "Submit Feedback"** button at the bottom
3. **Wait for confirmation** - You'll see a success message:

```
┌─────────────────────────────────────────────────────┐
│  ✅ Thank You for Your Feedback!                    │
│                                                     │
│  Your feedback has been submitted successfully.      │
│  Reference ID: FB-20260123-XXXX                      │
│                                                     │
│  [Submit Another Feedback]  [Back to Home]           │
└─────────────────────────────────────────────────────┘
```

### Rate Limiting

**Important**: The system limits feedback submissions to **10 per 15 minutes per IP address** to prevent spam.

If you see this error:
```
❌ Too many requests. Please try again in 15 minutes.
```

**Solution**: Wait for 15 minutes before submitting another feedback.

### Example Feedback Submission

Let's say you visited the **DPVC** for a 10-day course. Here's how to submit feedback:

1. **Click on "DPVC" card** on the landing page
2. **Fill your information**:
   - Name: "Rajesh Kumar"
   - Email: "rajesh@example.com"
   - ☐ Submit Anonymously (unchecked)
3. **Answer questions**:
   - Course Quality: ★★★★★ (5 stars)
   - Teacher Guidance: ★★★★★ (5 stars)
   - Accommodation: 😊😊😊😊 (4 emojis)
   - Food Quality: ★★★★★ (5 stars)
   - Meditation Hall: ★★★★★ (5 stars)
   - Noble Silence: 😊😊😊😊😊 (5 emojis)
   - Would Recommend: 10/10 (slider)
4. **Add comment**: "Excellent 10-day course! The teachers were compassionate and the environment was perfect for deep meditation."
5. **Click "Submit Feedback"**
6. **Done!** ✅

---

## 👔 For Department Administrators

Department Administrators can view feedback data for **their assigned department only** and generate reports.

### How to Login

1. **Navigate to Admin Login**:
   - Go to http://localhost:3030/admin
   - OR click "Admin Login" link (if available on landing page)

2. **Enter Your Credentials**:
   ```
   ┌─────────────────────────────────────────────────────┐
   │           Department Admin Login                    │
   │                                                     │
   │  Email:    ┌──────────────────────────────────┐   │
   │            │ your-email@department.org         │   │
   │            └──────────────────────────────────┘   │
   │                                                     │
   │  Password: ┌──────────────────────────────────┐   │
   │            │ ••••••••••••••••                  │   │
   │            └──────────────────────────────────┘   │
   │                                                     │
   │            [  Login  ]                              │
   └─────────────────────────────────────────────────────┘
   ```

3. **Default Department Admin Accounts**:

   | Department | Email | Password |
   |------------|-------|----------|
   | DPVC | dpvc-admin@globalpagoda.org | DPVC@2026 |
   | Global Pagoda | pagoda-admin@globalpagoda.org | Pagoda@2026 |
   | Dhammalaya | dhammalaya-admin@globalpagoda.org | Dhammalaya@2026 |
   | Food Court | food-admin@globalpagoda.org | Food@2026 |
   | Souvenir Store | store-admin@globalpagoda.org | Store@2026 |

### Dashboard Overview

After login, you'll see your **Department Dashboard**:

```
╔════════════════════════════════════════════════════════════╗
║              DPVC - Admin Dashboard                        ║
╠════════════════════════════════════════════════════════════╣
║                                                            ║
║  📊 Overview (Last 30 Days)                                ║
║  ┌──────────────┬──────────────┬──────────────┐           ║
║  │ Total        │ Average      │ With         │           ║
║  │ Feedback     │ Rating       │ Comments     │           ║
║  │   42         │   4.8 / 5    │   38 (90%)   │           ║
║  └──────────────┴──────────────┴──────────────┘           ║
║                                                            ║
║  📈 Recent Feedback                                        ║
║  ┌─────────────────────────────────────────────────┐      ║
║  │ Jan 23 | Rajesh K. | Rating: 5.0 | ★★★★★      │      ║
║  │ Jan 22 | Anonymous | Rating: 4.5 | ★★★★☆      │      ║
║  │ Jan 22 | Priya S.  | Rating: 4.8 | ★★★★★      │      ║
║  └─────────────────────────────────────────────────┘      ║
║                                                            ║
║  [View All Feedback]  [Generate Report]  [Logout]          ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
```

### Viewing Feedback

**Option 1: View Summary on Dashboard**
- Dashboard shows overview statistics
- Recent feedback entries with ratings
- Average ratings for each question

**Option 2: View Detailed Feedback List**

1. Click **"View All Feedback"** button
2. You'll see a paginated list with filters:

```
Filters: [All Time ▼] [All Ratings ▼] [Has Comments ▼] [Search...]

┌─────────────────────────────────────────────────────────────┐
│ Date       │ User/Email      │ Avg Rating │ Comment          │
├─────────────────────────────────────────────────────────────┤
│ 2026-01-23 │ Rajesh Kumar    │   5.0/5    │ Excellent cours...│
│ 2026-01-22 │ Anonymous       │   4.5/5    │ Very peaceful...  │
│ 2026-01-22 │ Priya Sharma    │   4.8/5    │ Good overall...   │
└─────────────────────────────────────────────────────────────┘

Showing 1-20 of 42 | [← Previous] [Next →]
```

3. **Click on any row** to see full details including all question responses

### Generating Reports

#### Manual Report Generation

1. From your dashboard, click **"Generate Report"** button
2. Select report parameters:

```
┌─────────────────────────────────────────────────────────────┐
│            Generate Department Report                       │
│                                                             │
│  Report Period:  ┌──────────────────┐                      │
│                  │ Last 7 Days    ▼ │                      │
│                  └──────────────────┘                      │
│                  (Options: Last 7/14/30/90 days, Custom)   │
│                                                             │
│  Include:        ☑ Summary Statistics                      │
│                  ☑ Individual Feedback                     │
│                  ☑ Charts and Graphs                       │
│                  ☑ Comments                                │
│                                                             │
│              [Cancel]  [Generate PDF]                       │
└─────────────────────────────────────────────────────────────┘
```

3. Click **"Generate PDF"**
4. Report will be generated and:
   - Downloaded to your computer
   - Emailed to your registered email address
   - Saved in system for future reference

#### Report Contents

Each PDF report includes:

**Page 1: Cover Page**
- Department name
- Report period (e.g., Jan 16 - Jan 23, 2026)
- Generation date and time
- Total feedback count

**Page 2: Executive Summary**
```
📊 Summary Statistics
- Total Feedback Received: 42
- Average Overall Rating: 4.8 / 5.0
- Feedback with Comments: 38 (90.5%)
- Anonymous Submissions: 12 (28.6%)
- Access Modes: Web: 40, Kiosk: 2
```

**Page 3-4: Question-wise Analysis**
```
Question 1: Course Quality
★★★★★ (5 stars): 28 responses (66.7%)
★★★★☆ (4 stars): 10 responses (23.8%)
★★★☆☆ (3 stars): 4 responses (9.5%)
Average: 4.6 / 5.0
```

**Page 5: Charts and Graphs**
- Rating distribution bar charts
- Trend line graphs
- Satisfaction score visualization

**Page 6-N: Individual Feedback Comments**
```
Feedback #1 (Jan 23, 2026)
From: Rajesh Kumar (rajesh@example.com)
Rating: 5.0 / 5.0

"Excellent 10-day course! The teachers were very compassionate..."
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Feedback #2 (Jan 22, 2026)
From: Anonymous
Rating: 4.5 / 5.0

"Very peaceful environment. Could improve accommodation..."
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Automated Weekly Reports

**Important**: Your department is configured to receive **automated weekly reports** every **Sunday at 9:00 AM (IST)**.

You will receive an email with:
- Subject: "Weekly Feedback Report - [Your Department] - [Date Range]"
- PDF report attached
- Summary in email body

**If you don't receive reports**:
1. Check your spam/junk folder
2. Verify your email is correct in system settings
3. Contact Super Admin for assistance

---

## 👨‍💼 For Super Administrators

Super Administrators have **full system access** including:
- View all departments' feedback
- Manage department administrators
- Configure system settings
- Generate cross-department reports
- Access audit logs

### Super Admin Login

**Default Super Admin Credentials**:
- **Email**: admin@globalpagoda.org
- **Password**: Admin@2026

**Login URL**: http://localhost:3030/admin

### Super Admin Dashboard

After login, you'll see the **comprehensive dashboard**:

```
╔════════════════════════════════════════════════════════════╗
║          Global Feedback System - Super Admin              ║
╠════════════════════════════════════════════════════════════╣
║                                                            ║
║  🌍 System-Wide Statistics (Last 30 Days)                  ║
║  ┌──────────┬──────────┬──────────┬────────────┐          ║
║  │ Total    │ Avg      │ With     │ Response   │          ║
║  │ Feedback │ Rating   │ Comments │ Rate       │          ║
║  │   247    │ 4.7/5    │ 221 (89%)│ High       │          ║
║  └──────────┴──────────┴──────────┴────────────┘          ║
║                                                            ║
║  📊 By Department                                          ║
║  ┌─────────────────────┬────────┬────────┬────────┐       ║
║  │ Department          │ Count  │ Avg    │ Action │       ║
║  ├─────────────────────┼────────┼────────┼────────┤       ║
║  │ DPVC                │  78    │ 4.8    │[Report]│       ║
║  │ Global Pagoda       │  95    │ 4.7    │[Report]│       ║
║  │ Dhammalaya          │  32    │ 4.6    │[Report]│       ║
║  │ Food Court          │  28    │ 4.5    │[Report]│       ║
║  │ Souvenir Store      │  14    │ 4.9    │[Report]│       ║
║  └─────────────────────┴────────┴────────┴────────┘       ║
║                                                            ║
║  [Manage Users] [System Settings] [Audit Logs] [Logout]    ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
```

### Key Super Admin Functions

#### 1. Manage Department Administrators

**Path**: Dashboard → Manage Users

**Functions**:
- **View all admin accounts**
- **Create new department admin**:
  ```
  Department: [DPVC ▼]
  Name: [New Admin Name]
  Email: [admin@example.com]
  Password: [Generate] or [Custom]
  [Create Admin]
  ```
- **Edit admin details**
- **Deactivate/Activate accounts**
- **Reset passwords**

#### 2. Generate Cross-Department Reports

Generate comparative reports across multiple departments:

```
┌─────────────────────────────────────────────────────────────┐
│        Generate Cross-Department Report                     │
│                                                             │
│  Departments:  ☑ DPVC                                       │
│                ☑ Global Pagoda                              │
│                ☑ Dhammalaya                                 │
│                ☐ Food Court                                 │
│                ☐ Souvenir Store                             │
│                                                             │
│  Period:       [Last 30 Days ▼]                            │
│                                                             │
│  [Generate Consolidated Report]                             │
└─────────────────────────────────────────────────────────────┘
```

#### 3. System Settings

**Path**: Dashboard → System Settings

Configure:
- **Report Schedule**: Change automated report timing
- **Email Settings**: Configure email server and templates
- **Rate Limiting**: Adjust submission limits
- **Data Retention**: Set how long to keep old feedback
- **Backup Settings**: Configure automated backups

#### 4. Audit Logs

**Path**: Dashboard → Audit Logs

View system activity:
```
┌─────────────────────────────────────────────────────────────┐
│ Date/Time       │ User             │ Action                 │
├─────────────────────────────────────────────────────────────┤
│ 2026-01-23 09:00│ dpvc-admin       │ Generated report       │
│ 2026-01-23 08:45│ system           │ Sent automated report  │
│ 2026-01-22 16:30│ pagoda-admin     │ Viewed feedback list   │
│ 2026-01-22 14:20│ admin            │ Created new user       │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Understanding Reports

### Report Structure

Every report (whether department-specific or cross-department) follows this structure:

#### 1. Cover Page
- Report title and department name
- Date range covered
- Generation timestamp
- Logo and branding

#### 2. Executive Summary
Key metrics at a glance:
- **Total Feedback**: Number of submissions
- **Average Rating**: Overall satisfaction score
- **Response Rate**: Percentage with comments
- **Top Insights**: 3-5 key takeaways

#### 3. Statistical Analysis
- **Rating Distribution**: How many 1-star, 2-star, etc.
- **Question-wise Breakdown**: Individual question analysis
- **Trend Analysis**: Week-over-week changes
- **Comparison**: vs. previous period

#### 4. Visual Charts
- **Bar Charts**: Rating distributions
- **Line Graphs**: Trends over time
- **Pie Charts**: Category breakdowns
- **Heat Maps**: Peak submission times

#### 5. Detailed Comments
All text feedback organized by:
- **Positive Comments**: Ratings 4-5
- **Neutral Comments**: Rating 3
- **Negative Comments**: Ratings 1-2

#### 6. Recommendations
AI-generated insights and suggestions based on feedback patterns.

### Reading Report Metrics

**Understanding Ratings**:
```
5.0 - Exceptional     (★★★★★)
4.0-4.9 - Very Good   (★★★★☆)
3.0-3.9 - Good        (★★★☆☆)
2.0-2.9 - Fair        (★★☆☆☆)
1.0-1.9 - Needs Work  (★☆☆☆☆)
```

**Net Promoter Score (NPS)**:
- Based on "Would you recommend?" question (0-10 scale)
- **Promoters**: Score 9-10 (Highly likely to recommend)
- **Passives**: Score 7-8 (Neutral)
- **Detractors**: Score 0-6 (Unlikely to recommend)
- **NPS Formula**: % Promoters - % Detractors

**Example**:
```
Out of 100 responses:
- 70 gave 9-10 (Promoters: 70%)
- 20 gave 7-8 (Passives: 20%)
- 10 gave 0-6 (Detractors: 10%)

NPS = 70% - 10% = 60 (Excellent!)
```

**NPS Interpretation**:
- **Above 50**: Excellent
- **30-50**: Good
- **0-30**: Average
- **Below 0**: Needs Improvement

---

## ⚙️ Automated Features

### 1. Weekly Report Generation

**Schedule**: Every Sunday at 9:00 AM (IST)

**What Happens**:
1. System automatically queries last 7 days' feedback
2. Generates PDF report for each department
3. Sends email to department admins
4. Archives report in system database

**Departments Included**:
- DPVC
- Global Pagoda
- Dhammalaya
- Food Court
- Souvenir Store

**Email Format**:
```
From: Feedback System <noreply@globalpagoda.org>
To: dpvc-admin@globalpagoda.org
Subject: Weekly Feedback Report - DPVC - Jan 16-23, 2026

Dear DPVC Administrator,

Please find attached your weekly feedback report for the period
January 16-23, 2026.

Summary:
- Total Feedback: 12
- Average Rating: 4.8 / 5.0
- Comments Received: 11 (91.7%)

Key Insights:
✓ Excellent ratings for teacher guidance (4.9/5)
✓ Very positive comments about meditation hall
⚠ Some concerns about accommodation (3.8/5)

Please review the attached PDF for detailed analysis.

Best regards,
Global Vipassana Pagoda Feedback System
```

### 2. Daily Backups

**Schedule**: Every day at 2:00 AM (IST)

**What's Backed Up**:
- All feedback data
- User accounts
- Department configurations
- Generated reports metadata

**Retention**: 30 days (older backups automatically deleted)

**Location**: `/app/backups/` in MongoDB container

### 3. Data Cleanup

**Schedule**: Monthly (1st day of month at 3:00 AM)

**What's Cleaned**:
- Old anonymous session data (>90 days)
- Expired JWT tokens
- Temporary files
- Old backup files (>30 days)

**Note**: Actual feedback data is **never** automatically deleted.

---

## 🔧 Troubleshooting

### Common Issues and Solutions

#### Issue 1: Cannot Submit Feedback

**Symptom**: "Failed to submit feedback" or "Network error"

**Solutions**:
1. **Check internet connection**
2. **Clear browser cache**:
   - Chrome: Ctrl+Shift+Delete
   - Firefox: Ctrl+Shift+Delete
   - Safari: Cmd+Option+E
3. **Try different browser**
4. **Disable browser extensions** (AdBlock, etc.)
5. **Check if all required questions are answered**

#### Issue 2: Rate Limit Error

**Symptom**: "Too many requests. Please try again in 15 minutes."

**Solution**:
- Wait for 15 minutes before submitting again
- This is a security feature to prevent spam
- If you need to submit multiple feedback for different departments, space them out

#### Issue 3: Admin Login Fails

**Symptom**: "Invalid credentials" or "Access denied"

**Solutions**:
1. **Verify email and password** (case-sensitive)
2. **Check Caps Lock is OFF**
3. **Try password reset**:
   - Click "Forgot Password?" on login page
   - Enter your email
   - Check email for reset link
4. **Contact Super Admin** if issue persists

#### Issue 4: Dashboard Shows No Data

**Symptom**: Dashboard displays "No feedback received yet"

**Possible Causes & Solutions**:

**A. No feedback submitted yet**
- Solution: Submit test feedback to verify system is working

**B. Date filter too restrictive**
- Solution: Change date range to "All Time" or "Last 30 Days"

**C. Browser cache issue**
- Solution: Hard refresh page (Ctrl+Shift+R or Cmd+Shift+R)

**D. Not logged in as correct department**
- Solution: Logout and login with correct department credentials

**E. Data not loading (network issue)**
- Solution: Check browser console (F12) for errors
- Contact Super Admin if you see red errors

#### Issue 5: Email Reports Not Received

**Symptom**: Automated weekly reports not arriving in inbox

**Solutions**:
1. **Check Spam/Junk folder**
2. **Add noreply@globalpagoda.org to contacts**
3. **Verify email address in system**:
   - Login → Settings → Update Email
4. **Check email server settings** (Super Admin only)
5. **Manually generate report** to test:
   - Dashboard → Generate Report → Check if you receive it

#### Issue 6: PDF Report Won't Download

**Symptom**: "Failed to download report" or blank PDF

**Solutions**:
1. **Allow pop-ups** in browser for this site
2. **Check download folder** - file might be there
3. **Try different browser**
4. **Check PDF viewer** - Update Adobe Reader or use Chrome's built-in viewer
5. **Contact Super Admin** - They can email the report to you

---

## ❓ FAQ

### General Questions

**Q: Is feedback really anonymous?**
A: Yes! When you check "Submit Anonymously", we don't store your name or email. Only ratings and comments are saved with a unique session ID (no personal info).

**Q: Can I edit feedback after submission?**
A: No. Once submitted, feedback cannot be edited or deleted. Please review carefully before submitting.

**Q: How long does it take for my feedback to appear in reports?**
A: Immediately! Your feedback is included in real-time dashboard stats and will appear in the next generated report.

**Q: Can I submit feedback for multiple departments?**
A: Yes! Just return to the landing page and select another department. Note: You can submit 10 feedbacks per 15 minutes max.

**Q: What happens to old feedback?**
A: All feedback is retained indefinitely unless Super Admin manually deletes it. Backups are kept for 30 days.

### For Administrators

**Q: How do I change my password?**
A: Login → Click profile icon → Settings → Change Password

**Q: Can I customize report schedule?**
A: Department Admins cannot. Super Admin can change schedule in System Settings.

**Q: Why are some feedback entries anonymous?**
A: Users chose "Submit Anonymously" option. You'll see "Anonymous" instead of name/email.

**Q: Can I export data to Excel?**
A: Currently, only PDF reports are generated. Excel export feature coming soon. Contact Super Admin for raw data if needed.

**Q: How do I add a new question?**
A: Questions are system-defined and can only be modified by Super Admin with developer access.

### Technical Questions

**Q: What browsers are supported?**
A: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+. Mobile browsers also supported.

**Q: Is my data secure?**
A: Yes! We use:
- HTTPS encryption (in production)
- JWT token authentication
- Password hashing (bcrypt)
- Rate limiting
- SQL injection prevention
- XSS protection

**Q: Where is data stored?**
A: In a MongoDB database running in a Docker container. Data is backed up daily.

**Q: Can I access this from mobile?**
A: Yes! The system is fully responsive and works on smartphones and tablets.

**Q: What if the system goes down?**
A: Contact your IT administrator. The system runs in Docker containers which can be quickly restarted. All data persists in the database.

---

## 📞 Support and Contact

### Getting Help

**For Users/Visitors**:
- Check [Troubleshooting](#troubleshooting) section first
- Contact department directly for feedback-related queries

**For Department Administrators**:
- Email: admin@globalpagoda.org
- Check [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for technical issues

**For Super Administrators**:
- Review [SYSTEM_COMPLETE.md](./SYSTEM_COMPLETE.md) for system architecture
- Check Docker logs: `docker-compose logs backend`
- Database access: Contact DevOps team

### Reporting Bugs

If you find a bug or issue:

1. **Note the error message** (screenshot if possible)
2. **Note what you were doing** when error occurred
3. **Check browser console** (F12) for error details
4. **Email report to**: admin@globalpagoda.org

Include:
- Date and time
- Your role (user/admin)
- Browser and version
- Steps to reproduce
- Expected vs actual behavior

### Feature Requests

Want a new feature? Submit request to:
- Email: admin@globalpagoda.org
- Subject: "Feature Request - [Brief Description]"

Include:
- Description of feature
- Why it would be useful
- How you envision it working

---

## 📚 Additional Resources

### Documentation Files

| File | Purpose |
|------|---------|
| [README.md](./README.md) | Quick start guide |
| [SYSTEM_COMPLETE.md](./SYSTEM_COMPLETE.md) | Complete system documentation |
| [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) | Technical troubleshooting |
| [ACTUAL_FIX_REPORT.md](./ACTUAL_FIX_REPORT.md) | Recent fixes and updates |
| [docker-compose.yml](./docker-compose.yml) | Docker configuration |

### Training Videos

(Coming Soon)
- How to Submit Feedback (3 min)
- Department Admin Dashboard Tour (10 min)
- Super Admin Complete Guide (30 min)
- Generating and Reading Reports (15 min)

---

## 🎓 Best Practices

### For Users

✅ **DO**:
- Provide honest, constructive feedback
- Be specific in comments
- Submit feedback soon after your visit (while fresh)
- Use appropriate rating scales

❌ **DON'T**:
- Submit spam or test feedback
- Include personal sensitive information
- Use offensive or abusive language
- Submit multiple identical feedbacks

### For Department Administrators

✅ **DO**:
- Check dashboard weekly
- Read all feedback comments
- Act on constructive criticism
- Share insights with team
- Generate reports before meetings
- Respond to patterns (multiple similar complaints)

❌ **DON'T**:
- Ignore negative feedback
- Share login credentials
- Delete feedback (contact Super Admin if needed)
- Use personal email for admin work

### For Super Administrators

✅ **DO**:
- Monitor system health daily
- Review cross-department trends
- Back up data regularly (automated + manual)
- Update department admins on system changes
- Keep documentation updated
- Test features after updates

❌ **DON'T**:
- Give Super Admin access to department staff
- Modify database directly without backup
- Change system settings without testing
- Ignore security warnings

---

## 🚀 Quick Reference Card

### URLs

| Purpose | URL |
|---------|-----|
| Landing Page | http://localhost:3030 |
| Admin Login | http://localhost:3030/admin |
| API Health | http://localhost:3030/api/health |

### Default Credentials

| Role | Email | Password |
|------|-------|----------|
| Super Admin | admin@globalpagoda.org | Admin@2026 |
| DPVC Admin | dpvc-admin@globalpagoda.org | DPVC@2026 |
| Pagoda Admin | pagoda-admin@globalpagoda.org | Pagoda@2026 |

### Quick Actions

| Action | Steps |
|--------|-------|
| Submit Feedback | Home → Select Dept → Fill Form → Submit |
| View Dashboard | Login → Dashboard |
| Generate Report | Login → Dashboard → Generate Report |
| View Feedback | Login → Dashboard → View All Feedback |
| Logout | Dashboard → Logout button |

---

## 📋 Checklists

### First-Time User Checklist

- [ ] Can access http://localhost:3030
- [ ] Can see 5 department cards
- [ ] Can click on a department
- [ ] Form loads with questions
- [ ] Can fill ratings and comments
- [ ] Can submit feedback successfully
- [ ] Receives confirmation message

### Department Admin Checklist

- [ ] Can login with credentials
- [ ] Dashboard loads with data
- [ ] Can view feedback list
- [ ] Can filter and search feedback
- [ ] Can generate PDF report
- [ ] Receives weekly automated reports
- [ ] Can logout successfully

### Super Admin Checklist

- [ ] Can see all departments' data
- [ ] Can access all department reports
- [ ] Can manage user accounts
- [ ] Can view audit logs
- [ ] Can change system settings
- [ ] All containers running healthy
- [ ] Automated backups working

---

**🎉 Congratulations! You now know how to use the Feedback System!**

For technical support, contact: admin@globalpagoda.org

---

*Last Updated: January 23, 2026*
*Version: 1.0.0*
*Feedback System - Global Vipassana Pagoda*
