const nodemailer = require('nodemailer');
const { google } = require('googleapis');
const fs = require('fs');
const logger = require('../utils/logger');

class EmailService {
  constructor() {
    this.transporter = null;
    this.isConfigured = false;
    this.initializeTransporter();
  }

  async initializeTransporter() {
    try {
      // Try SMTP configuration first (simpler setup)
      if (process.env.SMTP_HOST && process.env.SMTP_USER && process.env.SMTP_PASS) {
        logger.info('Using SMTP configuration...');
        
        this.transporter = nodemailer.createTransport({
          host: process.env.SMTP_HOST,
          port: parseInt(process.env.SMTP_PORT) || 587,
          secure: process.env.SMTP_SECURE === 'true',
          auth: {
            user: process.env.SMTP_USER,
            pass: process.env.SMTP_PASS
          }
        });

        await this.transporter.verify();
        this.isConfigured = true;
        logger.success(`Email service initialized with SMTP (${process.env.SMTP_HOST})`);
        return;
      }

      // Try Gmail with App Password
      if (process.env.GMAIL_USER && process.env.GMAIL_APP_PASSWORD) {
        logger.info('Using Gmail SMTP with App Password...');
        
        this.transporter = nodemailer.createTransport({
          service: 'gmail',
          auth: {
            user: process.env.GMAIL_USER,
            pass: process.env.GMAIL_APP_PASSWORD
          }
        });

        await this.transporter.verify();
        this.isConfigured = true;
        logger.success('Email service initialized with Gmail SMTP');
        return;
      }

      // Fallback to Gmail OAuth (legacy)
      const requiredEnvVars = [
        'GMAIL_CLIENT_ID',
        'GMAIL_CLIENT_SECRET',
        'GMAIL_REFRESH_TOKEN',
        'GMAIL_FROM_EMAIL'
      ];

      const missingVars = requiredEnvVars.filter(
        varName => !process.env[varName] || process.env[varName].startsWith('placeholder')
      );

      if (missingVars.length > 0) {
        logger.warn('Email service not configured.');
        logger.warn('Please set either:');
        logger.warn('  - SMTP_HOST, SMTP_USER, SMTP_PASS (for any SMTP)');
        logger.warn('  - GMAIL_USER, GMAIL_APP_PASSWORD (for Gmail)');
        logger.warn('  - Gmail OAuth credentials (advanced)');
        return;
      }

      // Create OAuth2 client
      const oauth2Client = new google.auth.OAuth2(
        process.env.GMAIL_CLIENT_ID,
        process.env.GMAIL_CLIENT_SECRET,
        process.env.GMAIL_REDIRECT_URI
      );

      oauth2Client.setCredentials({
        refresh_token: process.env.GMAIL_REFRESH_TOKEN
      });

      // Get access token
      const accessToken = await oauth2Client.getAccessToken();

      // Create transporter
      this.transporter = nodemailer.createTransport({
        service: 'gmail',
        auth: {
          type: 'OAuth2',
          user: process.env.GMAIL_FROM_EMAIL,
          clientId: process.env.GMAIL_CLIENT_ID,
          clientSecret: process.env.GMAIL_CLIENT_SECRET,
          refreshToken: process.env.GMAIL_REFRESH_TOKEN,
          accessToken: accessToken.token
        }
      });

      // Verify connection
      await this.transporter.verify();
      this.isConfigured = true;
      logger.success('Email service initialized with Gmail OAuth');
    } catch (error) {
      logger.error('Failed to initialize email service:', error.message);
      this.isConfigured = false;
    }
  }

  async sendWeeklyReport(recipients, departmentName, reportData) {
    if (!this.isConfigured) {
      logger.warn('Email service not configured. Skipping email send.');
      return {
        sent: false,
        error: 'Email service not configured (Gmail OAuth credentials missing)'
      };
    }

    try {
      const { filepath, filename, stats } = reportData;

      // Read PDF file
      if (!fs.existsSync(filepath)) {
        throw new Error(`Report file not found: ${filepath}`);
      }

      const mailOptions = {
        from: {
          name: 'Feedback System - Global Vipassana Pagoda',
          address: process.env.SMTP_FROM || process.env.GMAIL_USER || process.env.GMAIL_FROM_EMAIL
        },
        to: recipients.join(', '),
        subject: `Weekly Feedback Report - ${departmentName} - ${this.getCurrentWeekRange()}`,
        html: this.generateEmailHTML(departmentName, stats),
        attachments: [
          {
            filename,
            path: filepath,
            contentType: 'application/pdf'
          }
        ]
      };

      const info = await this.transporter.sendMail(mailOptions);

      logger.success(`Email sent to ${recipients.join(', ')}: ${info.messageId}`);

      return {
        sent: true,
        messageId: info.messageId,
        recipients,
        sentAt: new Date()
      };
    } catch (error) {
      logger.error('Email send failed:', error);
      return {
        sent: false,
        error: error.message,
        recipients
      };
    }
  }

  async sendWithRetry(recipients, departmentName, reportData, maxRetries = 3) {
    let lastError = null;

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      logger.info(`Email send attempt ${attempt}/${maxRetries} for ${departmentName}`);

      const result = await this.sendWeeklyReport(recipients, departmentName, reportData);

      if (result.sent) {
        return result;
      }

      lastError = result.error;

      // Wait before retry (exponential backoff)
      if (attempt < maxRetries) {
        const waitTime = Math.pow(2, attempt) * 1000; // 2s, 4s, 8s
        logger.info(`Waiting ${waitTime / 1000}s before retry...`);
        await new Promise(resolve => setTimeout(resolve, waitTime));
      }
    }

    return {
      sent: false,
      error: lastError,
      recipients,
      retryCount: maxRetries
    };
  }

  generateEmailHTML(departmentName, stats) {
    return `
<!DOCTYPE html>
<html>
<head>
  <style>
    body {
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      line-height: 1.6;
      color: #333;
      max-width: 600px;
      margin: 0 auto;
      padding: 20px;
    }
    .header {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 30px;
      border-radius: 10px;
      text-align: center;
      margin-bottom: 30px;
    }
    .header h1 {
      margin: 0;
      font-size: 24px;
    }
    .header p {
      margin: 10px 0 0 0;
      opacity: 0.9;
    }
    .stats {
      background: #f8f9fa;
      border-left: 4px solid #667eea;
      padding: 20px;
      margin: 20px 0;
      border-radius: 5px;
    }
    .stats h3 {
      margin-top: 0;
      color: #667eea;
    }
    .stat-item {
      display: flex;
      justify-content: space-between;
      padding: 8px 0;
      border-bottom: 1px solid #e9ecef;
    }
    .stat-item:last-child {
      border-bottom: none;
    }
    .stat-label {
      font-weight: 500;
      color: #6c757d;
    }
    .stat-value {
      font-weight: bold;
      color: #667eea;
    }
    .content {
      line-height: 1.8;
    }
    .footer {
      margin-top: 40px;
      padding-top: 20px;
      border-top: 2px solid #e9ecef;
      text-align: center;
      color: #6c757d;
      font-size: 14px;
    }
    .button {
      display: inline-block;
      padding: 12px 24px;
      background: #667eea;
      color: white;
      text-decoration: none;
      border-radius: 5px;
      margin: 20px 0;
    }
  </style>
</head>
<body>
  <div class="header">
    <h1>📊 Weekly Feedback Report</h1>
    <p>${departmentName}</p>
    <p>${this.getCurrentWeekRange()}</p>
  </div>

  <div class="content">
    <p>Dear Team,</p>

    <p>Please find attached the weekly feedback report for <strong>${departmentName}</strong> covering the period <strong>${this.getCurrentWeekRange()}</strong>.</p>

    <div class="stats">
      <h3>Key Highlights</h3>
      <div class="stat-item">
        <span class="stat-label">Total Responses</span>
        <span class="stat-value">${stats.totalFeedback}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">Average Rating</span>
        <span class="stat-value">${stats.avgRating} / ${stats.maxRating}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">Responses with Comments</span>
        <span class="stat-value">${stats.withComments}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">Response Trend</span>
        <span class="stat-value">${this.getTrendIndicator(stats)}</span>
      </div>
    </div>

    <p>The detailed report includes:</p>
    <ul>
      <li>📈 Summary statistics and trends</li>
      <li>📊 Question-wise analysis with distributions</li>
      <li>💬 All user comments verbatim</li>
      <li>📋 Recommendations for improvement</li>
    </ul>

    <p>For questions or to access the admin dashboard, please visit:<br>
    <a href="https://feedback.globalpagoda.org/admin" class="button">Access Dashboard</a></p>

    <p>Best regards,<br>
    <strong>Feedback Management System</strong><br>
    Global Vipassana Pagoda</p>
  </div>

  <div class="footer">
    <p>🤖 This is an automated email. Please do not reply.</p>
    <p>Generated on ${new Date().toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })}</p>
  </div>
</body>
</html>
    `.trim();
  }

  getCurrentWeekRange() {
    const now = new Date();
    const sunday = new Date(now);
    sunday.setDate(now.getDate() - now.getDay());

    const saturday = new Date(sunday);
    saturday.setDate(sunday.getDate() + 6);

    const format = (date) => date.toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    });

    return `${format(sunday)} - ${format(saturday)}`;
  }

  getTrendIndicator(stats) {
    const avgRating = parseFloat(stats.avgRating);
    if (avgRating >= 8) return '↑ Excellent';
    if (avgRating >= 6) return '→ Good';
    if (avgRating >= 4) return '↓ Needs Attention';
    return '⚠️ Critical';
  }
}

module.exports = new EmailService();
