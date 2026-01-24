const nodemailer = require('nodemailer');

async function setupTestEmail() {
  try {
    // Create a test account with Ethereal
    const testAccount = await nodemailer.createTestAccount();
    
    console.log('=== Test Email Account Created ===');
    console.log('SMTP Host:', testAccount.smtp.host);
    console.log('SMTP Port:', testAccount.smtp.port);
    console.log('User:', testAccount.user);
    console.log('Pass:', testAccount.pass);
    console.log('');
    console.log('Add these to your .env file:');
    console.log(`SMTP_HOST=${testAccount.smtp.host}`);
    console.log(`SMTP_PORT=${testAccount.smtp.port}`);
    console.log(`SMTP_USER=${testAccount.user}`);
    console.log(`SMTP_PASS=${testAccount.pass}`);
    console.log(`SMTP_FROM=${testAccount.user}`);
    
    return testAccount;
  } catch (error) {
    console.error('Error creating test account:', error);
  }
}

setupTestEmail();
