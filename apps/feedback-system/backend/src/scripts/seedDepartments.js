const mongoose = require('mongoose');
const { Department } = require('../models');

const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://feedbackadmin:feedback_secure_password_2026@mongodb:27017/feedback_system?authSource=admin';

// CORRECTED: 5 Departments with proper question schemas
const departments = [
  {
    code: 'shop',
    name: 'Shop',
    description: 'Souvenir and merchandise shop',
    email_recipients: ['shop@globalpagoda.org'],
    questions: [
      {
        key: 'product_variety',
        label: 'How would you rate the variety of products available?',
        type: 'rating_10',
        icon: '🛍️',
        required: true,
        order: 1
      },
      {
        key: 'product_quality',
        label: 'How satisfied are you with product quality?',
        type: 'smiley_5',
        icon: '⭐',
        required: true,
        order: 2
      },
      {
        key: 'staff_assistance',
        label: 'How was your experience with staff assistance?',
        type: 'rating_10',
        icon: '👥',
        required: true,
        order: 3
      },
      {
        key: 'pricing',
        label: 'How do you rate the pricing?',
        type: 'smiley_5',
        icon: '💰',
        required: true,
        order: 4
      },
      {
        key: 'recommend',
        label: 'Would you recommend our shop to others?',
        type: 'binary_yes_no',
        icon: '👍',
        required: true,
        order: 5
      }
    ],
    tablet_config: {
      primary_color: '#e74c3c',
      welcome_message: 'Thank you for visiting our shop!'
    }
  },
  {
    code: 'dhamma_lane',
    name: 'Dhammalaya',
    description: 'Meditation walkway and peaceful environment',
    email_recipients: ['dhammalane@globalpagoda.org'],
    questions: [
      {
        key: 'peacefulness',
        label: 'How peaceful did you find the environment?',
        type: 'rating_10',
        icon: '🕉️',
        required: true,
        order: 1
      },
      {
        key: 'maintenance',
        label: 'How well-maintained were the facilities?',
        type: 'smiley_5',
        icon: '✨',
        required: true,
        order: 2
      },
      {
        key: 'signage',
        label: 'How clear and helpful was the signage?',
        type: 'rating_10',
        icon: '🗺️',
        required: true,
        order: 3
      },
      {
        key: 'seating_comfort',
        label: 'How comfortable were the seating areas?',
        type: 'smiley_5',
        icon: '🪑',
        required: true,
        order: 4
      },
      {
        key: 'visit_again',
        label: 'Would you visit again?',
        type: 'binary_yes_no',
        icon: '🔄',
        required: true,
        order: 5
      }
    ],
    tablet_config: {
      primary_color: '#27ae60',
      welcome_message: 'Welcome to Dhammalaya!'
    }
  },
  {
    code: 'food_court',
    name: 'Food Court',
    description: 'Dining and refreshments area',
    email_recipients: ['foodcourt@globalpagoda.org'],
    questions: [
      {
        key: 'food_quality',
        label: 'How would you rate the food quality?',
        type: 'rating_10',
        icon: '🍽️',
        required: true,
        order: 1
      },
      {
        key: 'food_hygiene',
        label: 'How satisfied are you with food hygiene?',
        type: 'smiley_5',
        icon: '🧼',
        required: true,
        order: 2
      },
      {
        key: 'food_variety',
        label: 'How was the variety of food options?',
        type: 'rating_10',
        icon: '🥗',
        required: true,
        order: 3
      },
      {
        key: 'service_speed',
        label: 'How do you rate the service speed?',
        type: 'smiley_5',
        icon: '⚡',
        required: true,
        order: 4
      },
      {
        key: 'dining_cleanliness',
        label: 'How clean was the dining area?',
        type: 'rating_10',
        icon: '✨',
        required: true,
        order: 5
      }
    ],
    tablet_config: {
      primary_color: '#f39c12',
      welcome_message: 'We hope you enjoyed your meal!'
    }
  },
  {
    code: 'dpvc',
    name: 'Dhammapattana Vipassana Centre (DPVC)',
    description: 'Vipassana meditation course center',
    email_recipients: ['admin@dpvc.org'],
    questions: [
      {
        key: 'course_quality',
        label: 'How would you rate the meditation course quality?',
        type: 'rating_10',
        icon: '🧘',
        required: true,
        order: 1
      },
      {
        key: 'teacher_guidance',
        label: 'How helpful was the teacher guidance?',
        type: 'smiley_5',
        icon: '👨‍🏫',
        required: true,
        order: 2
      },
      {
        key: 'accommodation',
        label: 'How comfortable were the accommodation facilities?',
        type: 'rating_10',
        icon: '🛏️',
        required: true,
        order: 3
      },
      {
        key: 'meditation_hall',
        label: 'How was the meditation hall environment?',
        type: 'smiley_5',
        icon: '🏛️',
        required: true,
        order: 4
      },
      {
        key: 'recommend_course',
        label: 'Would you recommend this course to others?',
        type: 'binary_yes_no',
        icon: '🙏',
        required: true,
        order: 5
      }
    ],
    tablet_config: {
      primary_color: '#9b59b6',
      welcome_message: 'Thank you for participating in the course!'
    }
  },
  {
    code: 'global_pagoda',
    name: 'Global Vipassana Pagoda',
    description: 'Main meditation and spiritual center',
    email_recipients: ['head@globalpagoda.org'],
    questions: [
      {
        key: 'visit_inspiration',
        label: 'How inspiring was your visit to the Pagoda?',
        type: 'rating_10',
        icon: '🏛️',
        required: true,
        order: 1
      },
      {
        key: 'guided_tour',
        label: 'How satisfied are you with the guided tour?',
        type: 'smiley_5',
        icon: '🎤',
        required: true,
        order: 2
      },
      {
        key: 'premises_maintenance',
        label: 'How well-maintained did you find the premises?',
        type: 'rating_10',
        icon: '🌳',
        required: true,
        order: 3
      },
      {
        key: 'exhibits_quality',
        label: 'How informative were the exhibits/displays?',
        type: 'smiley_5',
        icon: '📚',
        required: true,
        order: 4
      },
      {
        key: 'visit_likelihood',
        label: 'How likely are you to visit again?',
        type: 'rating_10',
        icon: '⭐',
        required: true,
        order: 5
      }
    ],
    tablet_config: {
      primary_color: '#3498db',
      welcome_message: 'Thank you for visiting the Global Vipassana Pagoda!'
    }
  }
];

async function seedDepartments() {
  try {
    console.log('🔌 Connecting to MongoDB...');
    await mongoose.connect(MONGODB_URI);
    console.log('✅ Connected to MongoDB\n');

    console.log('🏢 Seeding Departments with Question Schemas...\n');

    for (const deptData of departments) {
      const existing = await Department.findOne({ code: deptData.code });
      
      if (existing) {
        // Update existing department with new schema
        await Department.updateOne(
          { code: deptData.code },
          { $set: deptData }
        );
        console.log(`✅ Updated: ${deptData.name} (${deptData.code})`);
        console.log(`   Questions: ${deptData.questions.length}`);
        console.log(`   Color: ${deptData.tablet_config.primary_color}`);
      } else {
        // Create new department
        await Department.create(deptData);
        console.log(`✨ Created: ${deptData.name} (${deptData.code})`);
        console.log(`   Questions: ${deptData.questions.length}`);
        console.log(`   Color: ${deptData.tablet_config.primary_color}`);
      }
      console.log('');
    }

    // Summary
    const totalDepts = await Department.countDocuments();
    console.log(`\n📊 Total Departments: ${totalDepts}`);
    console.log('✅ Department seeding complete!\n');

    // Create indexes
    console.log('🔧 Creating indexes...');
    await Department.createIndexes();
    console.log('✅ Indexes created!\n');

    process.exit(0);
  } catch (error) {
    console.error('❌ Error:', error.message);
    console.error(error);
    process.exit(1);
  }
}

seedDepartments();
