#!/usr/bin/env node

/**
 * Test Email with PDF Report
 * 
 * Usage:
 *   node test-email.js <email> <department>
 * 
 * Example:
 *   node test-email.js admin@example.com food_court
 */

const path = require('path');
const fs = require('fs');

// Load environment
require('dotenv').config();

const emailService = require('./src/services/email-service');
const pdfService = require('./src/services/pdf-service');
const Department = require('./src/models/Department');
const Feedback = require('./src/models/Feedback');
const mongoose = require('mongoose');

async function testEmail() {
  try {
    // Get arguments
    const recipientEmail = process.argv[2] || 'test@example.com';
    const departmentCode = process.argv[3] || 'food_court';

    console.log('=== Testing Email with PDF Report ===\n');
    console.log(`Recipient: ${recipientEmail}`);
    console.log(`Department: ${departmentCode}\n`);

    // Connect to database
    console.log('Connecting to database...');
    await mongoose.connect(process.env.MONGO_URI);
    console.log('✓ Connected\n');

    // Wait for email service to initialize
    await new Promise(resolve => setTimeout(resolve, 2000));

    // Get department
    const department = await Department.findOne({ code: departmentCode });
    if (!department) {
      throw new Error(`Department ${departmentCode} not found`);
    }
    console.log(`✓ Found department: ${department.name}\n`);

    // Get feedback data
    const now = new Date();
    const oneWeekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    
    const feedbacks = await Feedback.find({
      department_code: departmentCode,
      created_at: { $gte: oneWeekAgo }
    }).sort({ created_at: -1 });

    console.log(`✓ Found ${feedbacks.length} feedbacks from last 7 days\n`);

    // Generate PDF report
    console.log('Generating PDF report...');
    const reportData = await pdfService.generateWeeklyReport(
      departmentCode,
      department.name,
      oneWeekAgo,
      now
    );
    console.log(`✓ PDF generated: ${reportData.filename}\n`);

    // Send email
    console.log('Sending email...');
    const result = await emailService.sendWeeklyReport(
      [recipientEmail],
      department.name,
      reportData
    );

    if (result.sent) {
      console.log('\n✅ Email sent successfully!');
      console.log(`Message ID: ${result.messageId}`);
      console.log(`Recipients: ${result.recipients.join(', ')}`);
      console.log(`Sent at: ${result.sentAt}`);
    } else {
      console.log('\n❌ Email failed to send');
      console.log(`Error: ${result.error}`);
    }

    // Cleanup
    console.log('\nCleaning up...');
    if (fs.existsSync(reportData.filepath)) {
      fs.unlinkSync(reportData.filepath);
      console.log('✓ Temporary PDF deleted');
    }

    await mongoose.disconnect();
    console.log('✓ Database disconnected\n');

    process.exit(result.sent ? 0 : 1);

  } catch (error) {
    console.error('\n❌ Error:', error.message);
    console.error(error.stack);
    await mongoose.disconnect();
    process.exit(1);
  }
}

// Run test
testEmail();
