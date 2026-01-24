// MongoDB initialization script
// This runs automatically when the MongoDB container first starts

db = db.getSiblingDB('feedback_system');

print('Initializing feedback_system database...');

// Create collections with validation
db.createCollection('departments');
db.createCollection('feedback');
db.createCollection('users');
db.createCollection('reportlogs');
db.createCollection('auditlogs');

// Create indexes
print('Creating indexes...');

// Departments indexes
db.departments.createIndex({ 'code': 1 }, { unique: true });
db.departments.createIndex({ 'active': 1 });

// Feedback indexes
db.feedback.createIndex({ 'department_code': 1, 'created_at': -1 });
db.feedback.createIndex({ 'created_at': -1 });
db.feedback.createIndex({ 'metadata.ip_address': 1, 'created_at': -1 });
db.feedback.createIndex({ 'is_anonymous': 1 });

// Users indexes
db.users.createIndex({ 'email': 1 }, { unique: true });
db.users.createIndex({ 'role': 1 });
db.users.createIndex({ 'department_code': 1 });

// ReportLogs indexes
db.reportlogs.createIndex({ 'department_code': 1, 'generated_at': -1 });
db.reportlogs.createIndex({ 'email_status.sent': 1 });
db.reportlogs.createIndex({ 'generated_at': -1 });

// AuditLogs indexes
db.auditlogs.createIndex({ 'action': 1, 'timestamp': -1 });
db.auditlogs.createIndex({ 'user_email': 1, 'timestamp': -1 });
db.auditlogs.createIndex({ 'timestamp': -1 });

// Insert default departments
print('Inserting default departments...');

db.departments.insertMany([
  {
    code: 'global_pagoda',
    name: 'Global Pagoda',
    description: 'Main meditation and spiritual center',
    email_recipients: ['head@globalpagoda.org'],
    report_schedule: {
      day: 0,
      hour: 9,
      minute: 0,
      timezone: 'Asia/Kolkata'
    },
    active: true,
    created_at: new Date(),
    updated_at: new Date()
  },
  {
    code: 'souvenir_store',
    name: 'Souvenir Store',
    description: 'Spiritual books and merchandise',
    email_recipients: ['store@globalpagoda.org'],
    report_schedule: {
      day: 0,
      hour: 9,
      minute: 0,
      timezone: 'Asia/Kolkata'
    },
    active: true,
    created_at: new Date(),
    updated_at: new Date()
  },
  {
    code: 'dpvc',
    name: 'DPVC - Dhamma Pattana Vipassana Centre',
    description: 'Vipassana meditation courses',
    email_recipients: ['admin@dpvc.org'],
    report_schedule: {
      day: 0,
      hour: 9,
      minute: 0,
      timezone: 'Asia/Kolkata'
    },
    active: true,
    created_at: new Date(),
    updated_at: new Date()
  },
  {
    code: 'dhammalaya',
    name: 'Dhammalaya',
    description: 'Meditation and study facility',
    email_recipients: ['contact@dhammalaya.org'],
    report_schedule: {
      day: 0,
      hour: 9,
      minute: 0,
      timezone: 'Asia/Kolkata'
    },
    active: true,
    created_at: new Date(),
    updated_at: new Date()
  },
  {
    code: 'food_court',
    name: 'Food Court',
    description: 'Dining and refreshments',
    email_recipients: ['foodcourt@globalpagoda.org'],
    report_schedule: {
      day: 0,
      hour: 9,
      minute: 0,
      timezone: 'Asia/Kolkata'
    },
    active: true,
    created_at: new Date(),
    updated_at: new Date()
  }
]);

// Insert default admin users
print('Inserting default admin users...');

// NOTE: Password hashes generated with bcrypt for:
// - Super Admin: Admin@2026
// - Department Admins: [Dept]@2026

db.users.insertMany([
  {
    name: 'Super Administrator',
    email: 'admin@globalpagoda.org',
    password: '$2a$10$kxVxN3YGq8ePm3g16yI6JuwzMxPr.sAU4xFV2VDzmR0w6mXJI8bNe',
    role: 'super_admin',
    department_code: null,
    active: true,
    created_at: new Date(),
    updated_at: new Date()
  },
  {
    name: 'DPVC Administrator',
    email: 'dpvc-admin@globalpagoda.org',
    password: '$2a$10$kxVxN3YGq8ePm3g16yI6JuwzMxPr.sAU4xFV2VDzmR0w6mXJI8bNe',
    role: 'department_admin',
    department_code: 'dpvc',
    active: true,
    created_at: new Date(),
    updated_at: new Date()
  },
  {
    name: 'Pagoda Administrator',
    email: 'pagoda-admin@globalpagoda.org',
    password: '$2a$10$kxVxN3YGq8ePm3g16yI6JuwzMxPr.sAU4xFV2VDzmR0w6mXJI8bNe',
    role: 'department_admin',
    department_code: 'global_pagoda',
    active: true,
    created_at: new Date(),
    updated_at: new Date()
  },
  {
    name: 'Dhammalaya Administrator',
    email: 'dhammalaya-admin@globalpagoda.org',
    password: '$2a$10$kxVxN3YGq8ePm3g16yI6JuwzMxPr.sAU4xFV2VDzmR0w6mXJI8bNe',
    role: 'department_admin',
    department_code: 'dhammalaya',
    active: true,
    created_at: new Date(),
    updated_at: new Date()
  },
  {
    name: 'Food Court Administrator',
    email: 'food-admin@globalpagoda.org',
    password: '$2a$10$kxVxN3YGq8ePm3g16yI6JuwzMxPr.sAU4xFV2VDzmR0w6mXJI8bNe',
    role: 'department_admin',
    department_code: 'food_court',
    active: true,
    created_at: new Date(),
    updated_at: new Date()
  },
  {
    name: 'Store Administrator',
    email: 'store-admin@globalpagoda.org',
    password: '$2a$10$kxVxN3YGq8ePm3g16yI6JuwzMxPr.sAU4xFV2VDzmR0w6mXJI8bNe',
    role: 'department_admin',
    department_code: 'souvenir_store',
    active: true,
    created_at: new Date(),
    updated_at: new Date()
  }
]);

print('Database initialized successfully!');
print('Total departments: ' + db.departments.count());
print('Total users: ' + db.users.count());
print('');
print('✅ Admin credentials:');
print('   Super Admin: admin@globalpagoda.org / Admin@2026');
print('   Department Admins: [dept]-admin@globalpagoda.org / [Dept]@2026');
