const mongoose = require('mongoose');
const bcrypt = require('bcryptjs');
const { User, Department, Feedback } = require('./src/models');

const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://mongodb:27017/feedback_system';

async function initializeDatabase() {
  try {
    console.log('🔌 Connecting to MongoDB...');
    await mongoose.connect(MONGODB_URI);
    console.log('✅ Connected to MongoDB');

    // Create Super Admin
    console.log('\n👤 Creating Super Admin...');
    const existingAdmin = await User.findOne({ email: 'admin@globalpagoda.org' });

    if (!existingAdmin) {
      const hashedPassword = await bcrypt.hash('Admin@2026', 10);
      await User.create({
        name: 'Super Administrator',
        email: 'admin@globalpagoda.org',
        password: hashedPassword,
        role: 'super_admin',
        department_code: null,
        active: true
      });
      console.log('✅ Super Admin created: admin@globalpagoda.org / Admin@2026');
    } else {
      console.log('ℹ️  Super Admin already exists');
    }

    // Create Department Admins
    console.log('\n👥 Creating Department Admins...');
    const deptAdmins = [
      { name: 'DPVC Administrator', email: 'dpvc-admin@globalpagoda.org', password: 'DPVC@2026', department_code: 'dpvc' },
      { name: 'Pagoda Administrator', email: 'pagoda-admin@globalpagoda.org', password: 'Pagoda@2026', department_code: 'global_pagoda' },
      { name: 'Dhammalaya Administrator', email: 'dhammalaya-admin@globalpagoda.org', password: 'Dhammalaya@2026', department_code: 'dhammalaya' },
      { name: 'Food Court Administrator', email: 'food-admin@globalpagoda.org', password: 'Food@2026', department_code: 'food_court' },
      { name: 'Store Administrator', email: 'store-admin@globalpagoda.org', password: 'Store@2026', department_code: 'souvenir_store' }
    ];

    for (const admin of deptAdmins) {
      const existing = await User.findOne({ email: admin.email });
      if (!existing) {
        const hashedPassword = await bcrypt.hash(admin.password, 10);
        await User.create({
          name: admin.name,
          email: admin.email,
          password: hashedPassword,
          role: 'department_admin',
          department_code: admin.department_code,
          active: true
        });
        console.log(`✅ ${admin.name}: ${admin.email} / ${admin.password}`);
      }
    }

    // Count data
    const userCount = await User.countDocuments();
    const deptCount = await Department.countDocuments();
    const feedbackCount = await Feedback.countDocuments();

    console.log('\n📊 Database Status:');
    console.log(`   Users: ${userCount}`);
    console.log(`   Departments: ${deptCount}`);
    console.log(`   Feedbacks: ${feedbackCount}`);

    console.log('\n✅ Database initialization complete!');
    process.exit(0);
  } catch (error) {
    console.error('❌ Error:', error.message);
    process.exit(1);
  }
}

initializeDatabase();
