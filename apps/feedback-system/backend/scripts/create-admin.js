#!/usr/bin/env node

require('dotenv').config({ path: '../.env' });
const mongoose = require('mongoose');
const readline = require('readline');
const User = require('../src/models/User');
const logger = require('../src/utils/logger');

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

const question = (query) => new Promise((resolve) => rl.question(query, resolve));

async function createAdmin() {
  try {
    // Connect to MongoDB
    await mongoose.connect(process.env.MONGO_URI);
    logger.success('Connected to MongoDB');

    console.log('\n=== Create Super Admin User ===\n');

    // Get user input
    const email = await question('Email: ');
    const password = await question('Password (min 8 chars): ');
    const fullName = await question('Full Name: ');

    // Validate input
    if (!email || !password || !fullName) {
      throw new Error('All fields are required');
    }

    if (password.length < 8) {
      throw new Error('Password must be at least 8 characters');
    }

    // Check if user already exists
    const existingUser = await User.findOne({ email });
    if (existingUser) {
      throw new Error('User with this email already exists');
    }

    // Create super admin user
    const user = new User({
      email: email.toLowerCase().trim(),
      password_hash: password,
      full_name: fullName.trim(),
      role: 'super_admin',
      department_code: null,
      active: true
    });

    await user.save();

    logger.success('Super admin user created successfully!');
    console.log('\nUser Details:');
    console.log(`Email: ${user.email}`);
    console.log(`Name: ${user.full_name}`);
    console.log(`Role: ${user.role}`);
    console.log(`\nYou can now login at http://localhost:3000/api/auth/login`);

  } catch (error) {
    logger.error('Error creating admin:', error.message);
  } finally {
    rl.close();
    await mongoose.disconnect();
    process.exit(0);
  }
}

createAdmin();
