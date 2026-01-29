#!/usr/bin/env node

/**
 * Simple Email Test - No Database Required
 *
 * Usage: node simple-test-email.js <email>
 */

require('dotenv').config({ path: '../.env' });
const nodemailer = require('nodemailer');

async function sendTestEmail() {
  try {
    const recipientEmail = process.argv[2] || 'tod@vridhamma.org';

    console.log('=== Simple Email Test ===\n');
    console.log(`📧 To: ${recipientEmail}`);
    console.log(`📤 From: ${process.env.SMTP_FROM || process.env.GMAIL_USER}`);
    console.log(`🔐 SMTP Host: ${process.env.SMTP_HOST}`);
    console.log(`👤 SMTP User: ${process.env.SMTP_USER}\n`);

    // Check if credentials are set
    if (!process.env.SMTP_USER || !process.env.SMTP_PASS) {
      throw new Error('SMTP credentials not found in .env file');
    }

    console.log('🔧 Creating email transporter...');
    const transporter = nodemailer.createTransport({
      host: process.env.SMTP_HOST || 'smtp.gmail.com',
      port: parseInt(process.env.SMTP_PORT) || 587,
      secure: process.env.SMTP_SECURE === 'true',
      auth: {
        user: process.env.SMTP_USER,
        pass: process.env.SMTP_PASS
      }
    });

    console.log('✓ Transporter created\n');

    console.log('🔍 Verifying connection...');
    await transporter.verify();
    console.log('✓ Connection verified\n');

    const mailOptions = {
      from: {
        name: 'Feedback System - Global Vipassana Pagoda',
        address: process.env.SMTP_FROM || process.env.SMTP_USER
      },
      to: recipientEmail,
      subject: '✅ Test Email - Feedback System Setup Verification',
      html: `
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
            .content {
              background: #f8f9fa;
              padding: 20px;
              border-radius: 5px;
              border-left: 4px solid #667eea;
            }
            .success-box {
              background: #d4edda;
              border: 1px solid #c3e6cb;
              color: #155724;
              padding: 15px;
              border-radius: 5px;
              margin: 20px 0;
            }
            .info-item {
              padding: 8px 0;
              border-bottom: 1px solid #e9ecef;
            }
            .footer {
              margin-top: 30px;
              padding-top: 20px;
              border-top: 2px solid #e9ecef;
              text-align: center;
              color: #6c757d;
              font-size: 14px;
            }
          </style>
        </head>
        <body>
          <div class="header">
            <h1>✅ Email System Test</h1>
            <p>Feedback System - Global Vipassana Pagoda</p>
          </div>

          <div class="success-box">
            <h3 style="margin-top: 0;">🎉 Email Configuration Successful!</h3>
            <p style="margin-bottom: 0;">The email system has been successfully configured with the new email address.</p>
          </div>

          <div class="content">
            <h3>📧 Email Configuration Details</h3>
            <div class="info-item">
              <strong>From:</strong> ${process.env.SMTP_FROM || process.env.SMTP_USER}
            </div>
            <div class="info-item">
              <strong>SMTP Host:</strong> ${process.env.SMTP_HOST}
            </div>
            <div class="info-item">
              <strong>SMTP Port:</strong> ${process.env.SMTP_PORT}
            </div>
            <div class="info-item">
              <strong>To:</strong> ${recipientEmail}
            </div>
          </div>

          <div class="content" style="margin-top: 20px;">
            <h3>📊 Weekly Reports Configuration</h3>
            <p>Automated weekly feedback reports will be sent to the following department emails:</p>
            <ul>
              <li><strong>Shop:</strong> shop@globalpagoda.org</li>
              <li><strong>Dhammalaya:</strong> dhammalane@globalpagoda.org</li>
              <li><strong>Food Court:</strong> foodcourt@globalpagoda.org</li>
              <li><strong>DPVC:</strong> admin@dpvc.org</li>
              <li><strong>Global Pagoda:</strong> head@globalpagoda.org</li>
            </ul>
          </div>

          <div class="footer">
            <p>🤖 This is a test email from the Feedback Management System</p>
            <p>Generated on ${new Date().toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })}</p>
            <p>Global Vipassana Pagoda</p>
          </div>
        </body>
        </html>
      `.trim()
    };

    console.log('📤 Sending test email...');
    const info = await transporter.sendMail(mailOptions);

    console.log('\n✅ Email sent successfully!\n');
    console.log(`📬 Message ID: ${info.messageId}`);
    console.log(`📧 Recipient: ${recipientEmail}`);
    console.log(`📤 From: ${process.env.SMTP_FROM || process.env.SMTP_USER}`);
    console.log(`⏰ Sent at: ${new Date().toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })}\n`);

    process.exit(0);

  } catch (error) {
    console.error('\n❌ Error sending test email:');
    console.error(error.message);
    if (error.code) {
      console.error(`Error code: ${error.code}`);
    }
    console.error('\nPlease check:');
    console.error('1. SMTP credentials are correct in .env file');
    console.error('2. App Password is valid and active');
    console.error('3. Gmail account has SMTP enabled');
    console.error('4. Network connection is available\n');
    process.exit(1);
  }
}

sendTestEmail();
