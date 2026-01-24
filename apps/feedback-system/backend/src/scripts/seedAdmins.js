const mongoose = require('mongoose');
const bcrypt = require('bcryptjs');
const { User, Department } = require('../models');

const MONGO_URI = process.env.MONGO_URI || 'mongodb://feedbackadmin:feedback_secure_password_2026@localhost:27017/feedback_system?authSource=admin';

const admins = [
  // Super Admin - has access to all departments
  {
    email: 'superadmin@globalpagoda.org',
    password: 'SuperAdmin@2026',
    role: 'super_admin',
    full_name: 'Super Administrator',
    department_code: null
  },
  // Department-specific admins
  {
    email: 'admin.globalpagoda@globalpagoda.org',
    password: 'GlobalPagoda@2026',
    role: 'dept_admin',
    full_name: 'Global Pagoda Admin',
    department_code: 'global_pagoda'
  },
  {
    email: 'admin.dpvc@globalpagoda.org',
    password: 'DPVC@2026',
    role: 'dept_admin',
    full_name: 'DPVC Admin',
    department_code: 'dpvc'
  },
  {
    email: 'admin.dhammalaya@globalpagoda.org',
    password: 'Dhammalaya@2026',
    role: 'dept_admin',
    full_name: 'Dhammalaya Admin',
    department_code: 'dhammalaya'
  },
  {
    email: 'admin.foodcourt@globalpagoda.org',
    password: 'FoodCourt@2026',
    role: 'dept_admin',
    full_name: 'Food Court Admin',
    department_code: 'food_court'
  },
  {
    email: 'admin.museum@globalpagoda.org',
    password: 'Museum@2026',
    role: 'dept_admin',
    full_name: 'Museum Admin',
    department_code: 'museum'
  },
  {
    email: 'admin.guesthouse@globalpagoda.org',
    password: 'GuestHouse@2026',
    role: 'dept_admin',
    full_name: 'Guest House Admin',
    department_code: 'guest_house'
  },
  {
    email: 'admin.bookstall@globalpagoda.org',
    password: 'Bookstall@2026',
    role: 'dept_admin',
    full_name: 'Bookstall Admin',
    department_code: 'bookstall'
  },
  {
    email: 'admin.parking@globalpagoda.org',
    password: 'Parking@2026',
    role: 'dept_admin',
    full_name: 'Parking Admin',
    department_code: 'parking'
  },
  {
    email: 'admin.security@globalpagoda.org',
    password: 'Security@2026',
    role: 'dept_admin',
    full_name: 'Security Admin',
    department_code: 'security'
  },
  {
    email: 'admin.maintenance@globalpagoda.org',
    password: 'Maintenance@2026',
    role: 'dept_admin',
    full_name: 'Maintenance Admin',
    department_code: 'maintenance'
  }
];

async function seedAdmins() {
  try {
    await mongoose.connect(MONGO_URI);
    console.log('Connected to MongoDB');

    // Get all departments to verify codes
    const departments = await Department.find({}, 'code');
    const validDeptCodes = departments.map(d => d.code);
    console.log('Valid department codes:', validDeptCodes);

    for (const adminData of admins) {
      // Verify department code exists (except for super admin)
      if (adminData.department_code && !validDeptCodes.includes(adminData.department_code)) {
        console.log(`⚠️  Skipping ${adminData.email} - department '${adminData.department_code}' not found`);
        continue;
      }

      // Check if user already exists
      const existingUser = await User.findOne({ email: adminData.email });
      
      if (existingUser) {
        console.log(`✓ Admin already exists: ${adminData.email}`);
        continue;
      }

      // Hash password manually
      const salt = await bcrypt.genSalt(10);
      const password_hash = await bcrypt.hash(adminData.password, salt);

      // Create new admin
      const admin = new User({
        email: adminData.email,
        password_hash,
        role: adminData.role,
        full_name: adminData.full_name,
        department_code: adminData.department_code,
        active: true
      });

      // Save without triggering pre-save hook (password already hashed)
      await User.collection.insertOne(admin.toObject());
      console.log(`✓ Created admin: ${adminData.email} (${adminData.role})`);
    }

    console.log('\n✅ Admin seeding completed!');
    process.exit(0);
  } catch (error) {
    console.error('Error seeding admins:', error);
    process.exit(1);
  }
}

seedAdmins();
