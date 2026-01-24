const mongoose = require('mongoose');

const reportScheduleSchema = new mongoose.Schema({
  day: {
    type: Number,
    required: true,
    min: 0,
    max: 6,
    default: 0 // Sunday
  },
  hour: {
    type: Number,
    required: true,
    min: 0,
    max: 23,
    default: 9
  },
  minute: {
    type: Number,
    required: true,
    min: 0,
    max: 59,
    default: 0
  },
  timezone: {
    type: String,
    default: 'Asia/Kolkata'
  }
}, { _id: false });

// NEW: Question schema for department-specific questions
const questionSchema = new mongoose.Schema({
  key: {
    type: String,
    required: true
  },
  label: {
    type: String,
    required: true
  },
  type: {
    type: String,
    required: true,
    enum: ['rating_10', 'smiley_5', 'binary_yes_no']
  },
  icon: {
    type: String,
    default: '⭐'
  },
  required: {
    type: Boolean,
    default: true
  },
  order: {
    type: Number,
    required: true
  }
}, { _id: false });

// NEW: Tablet configuration
const tabletConfigSchema = new mongoose.Schema({
  primary_color: {
    type: String,
    default: '#3498db'
  },
  logo_url: String,
  welcome_message: {
    type: String,
    default: 'We value your feedback!'
  }
}, { _id: false });

const departmentSchema = new mongoose.Schema({
  code: {
    type: String,
    required: true,
    unique: true,
    lowercase: true,
    trim: true
  },
  name: {
    type: String,
    required: true,
    trim: true
  },
  description: {
    type: String,
    trim: true
  },
  // NEW: Department-specific questions
  questions: {
    type: [questionSchema],
    default: []
  },
  email_recipients: [{
    type: String,
    required: true,
    lowercase: true,
    trim: true
  }],
  report_schedule: {
    type: reportScheduleSchema,
    required: true,
    default: () => ({
      day: 0,
      hour: 9,
      minute: 0,
      timezone: 'Asia/Kolkata'
    })
  },
  // NEW: Tablet display configuration
  tablet_config: {
    type: tabletConfigSchema,
    default: () => ({
      primary_color: '#3498db',
      welcome_message: 'We value your feedback!'
    })
  },
  active: {
    type: Boolean,
    default: true
  }
}, {
  timestamps: {
    createdAt: 'created_at',
    updatedAt: 'updated_at'
  }
});

// Indexes
departmentSchema.index({ code: 1 });
departmentSchema.index({ active: 1 });
departmentSchema.index({ active: 1, code: 1 }); // Compound index for active departments

module.exports = mongoose.model('Department', departmentSchema);
