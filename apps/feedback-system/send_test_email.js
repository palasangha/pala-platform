#!/usr/bin/env node

const nodemailer = require('nodemailer');
const fs = require('fs');
const path = require('path');

// Email configuration from environment
const transporter = nodemailer.createTransport({
  host: process.env.SMTP_HOST || 'smtp.gmail.com',
  port: parseInt(process.env.SMTP_PORT) || 587,
  secure: false,
  auth: {
    user: process.env.GMAIL_FROM_EMAIL || process.env.SMTP_USER,
    pass: process.env.GMAIL_APP_PASSWORD || process.env.SMTP_PASS
  }
});

// Get test recipient from command line or use default
const testRecipient = process.argv[2] || 'tod@vridhamma.org';
const reportPath = process.argv[3] || '/app/volumes/reports/shop_weekly_20260118_to_20260125.pdf';

async function sendTestEmail() {
  try {
    console.log(`📧 Preparing to send test email to: ${testRecipient}`);
    console.log(`📄 Attaching report: ${path.basename(reportPath)}`);

    // Check if file exists
    if (!fs.existsSync(reportPath)) {
      throw new Error(`Report file not found: ${reportPath}`);
    }

    const mailOptions = {
      from: `"Global Pagoda Feedback System" <${process.env.GMAIL_FROM_EMAIL || process.env.SMTP_FROM}>`,
      to: testRecipient,
      subject: '📊 Test Weekly Feedback Report - Global Vipassana Pagoda',
      html: `
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
          <h2 style="color: #3498db;">📊 Test Weekly Feedback Report</h2>
          
          <p>Dear Administrator,</p>
          
          <p>This is a <strong>test email</strong> from the Global Vipassana Pagoda Feedback System.</p>
          
          <div style="background-color: #f0f8ff; padding: 15px; border-left: 4px solid #3498db; margin: 20px 0;">
            <p style="margin: 0;"><strong>Report Details:</strong></p>
            <ul style="margin: 10px 0;">
              <li>Department: Shop</li>
              <li>Period: January 18 - January 25, 2026</li>
              <li>Type: Weekly Report</li>
            </ul>
          </div>
          
          <p>The weekly feedback report is attached as a PDF document.</p>
          
          <hr style="border: 0; border-top: 1px solid #ddd; margin: 20px 0;">
          
          <p style="color: #666; font-size: 12px;">
            This is an automated test email from the Feedback System.<br>
            Report stored at: <code>/volumes/reports/</code><br>
            Generated: ${new Date().toLocaleString()}
          </p>
          
          <p style="color: #27ae60; font-weight: bold;">
            ✅ Email system is working correctly!
          </p>
        </div>
      `,
      attachments: [
        {
          filename: path.basename(reportPath),
          path: reportPath,
          contentType: 'application/pdf'
        }
      ]
    };

    console.log('📤 Sending email...');
    const info = await transporter.sendMail(mailOptions);
    
    console.log('✅ Email sent successfully!');
    console.log(`📬 Message ID: ${info.messageId}`);
    console.log(`📧 To: ${testRecipient}`);
    console.log(`📎 Attachment: ${path.basename(reportPath)}`);
    
    return { success: true, messageId: info.messageId };
  } catch (error) {
    console.error('❌ Error sending email:', error.message);
    throw error;
  }
}

sendTestEmail()
  .then(() => {
    console.log('\n🎉 Test email completed successfully!');
    process.exit(0);
  })
  .catch((error) => {
    console.error('\n💥 Test email failed:', error);
    process.exit(1);
  });
