const mongoose = require('mongoose');
const { User, Department } = require('../models');

const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://feedbackadmin:feedback_secure_password_2026@mongodb:27017/feedback_system?authSource=admin';

// Admin credentials for all departments + super admin
const admins = [
  {
    email: 'superadmin@globalpagoda.org',
    password: 'SuperAdmin@2026!',
    full_name: 'Super Administrator',
    role: 'super_admin',
    department_code: null,
    active: true
  },
  {
    email: 'shop@globalpagoda.org',
    password: 'ShopAdmin@2026!',
    full_name: 'Shop Administrator',
    role: 'dept_admin',
    department_code: 'shop',
    active: true
  },
  {
    email: 'dhammalane@globalpagoda.org',
    password: 'DhammaLane@2026!',
    full_name: 'Dhammalaya Administrator',
    role: 'dept_admin',
    department_code: 'dhamma_lane',
    active: true
  },
  {
    email: 'foodcourt@globalpagoda.org',
    password: 'FoodCourt@2026!',
    full_name: 'Food Court Administrator',
    role: 'dept_admin',
    department_code: 'food_court',
    active: true
  },
  {
    email: 'dpvc@globalpagoda.org',
    password: 'DPVC@2026!',
    full_name: 'DPVC Administrator',
    role: 'dept_admin',
    department_code: 'dpvc',
    active: true
  },
  {
    email: 'head@globalpagoda.org',
    password: 'Pagoda@2026!',
    full_name: 'Global Pagoda Administrator',
    role: 'dept_admin',
    department_code: 'global_pagoda',
    active: true
  }
];

async function seedAdminUsers() {
  try {
    console.log('🔌 Connecting to MongoDB...');
    await mongoose.connect(MONGODB_URI);
    console.log('✅ Connected to MongoDB\n');

    console.log('👥 Creating Admin Users...\n');

    for (const adminData of admins) {
      const existing = await User.findOne({ email: adminData.email });
      
      if (existing) {
        console.log(`⚠️  User already exists: ${adminData.email}`);
        // Update password if needed
        existing.password_hash = adminData.password; // Will be hashed by pre-save hook
        existing.full_name = adminData.full_name;
        existing.role = adminData.role;
        existing.department_code = adminData.department_code;
        existing.active = adminData.active;
        await existing.save();
        console.log(`✅ Updated: ${adminData.full_name}`);
      } else {
        const user = new User({
          email: adminData.email,
          password_hash: adminData.password, // Will be hashed by pre-save hook
          full_name: adminData.full_name,
          role: adminData.role,
          department_code: adminData.department_code,
          active: adminData.active
        });
        await user.save();
        console.log(`✨ Created: ${adminData.full_name}`);
      }
      
      console.log(`   Email: ${adminData.email}`);
      console.log(`   Role: ${adminData.role}`);
      if (adminData.department_code) {
        console.log(`   Department: ${adminData.department_code}`);
      }
      console.log('');
    }

    // Summary
    const totalAdmins = await User.countDocuments();
    console.log(`\n📊 Total Admin Users: ${totalAdmins}`);
    console.log('✅ Admin user seeding complete!\n');

    process.exit(0);
  } catch (error) {
    console.error('❌ Error:', error.message);
    console.error(error);
    process.exit(1);
  }
}

seedAdminUsers();
