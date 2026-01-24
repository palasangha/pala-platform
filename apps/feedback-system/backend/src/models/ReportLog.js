const mongoose = require('mongoose');

const emailStatusSchema = new mongoose.Schema({
  sent: {
    type: Boolean,
    default: false
  },
  sent_at: Date,
  recipients: [String],
  failures: [String],
  retry_count: {
    type: Number,
    default: 0
  },
  last_error: String
}, { _id: false });

const summaryStatsSchema = new mongoose.Schema({
  total_feedback: Number,
  avg_rating: Number,
  response_rate: String,
  anonymous_count: Number,
  with_comments_count: Number
}, { _id: false });

const reportLogSchema = new mongoose.Schema({
  department_code: {
    type: String,
    required: true,
    lowercase: true,
    trim: true,
    index: true
  },
  report_type: {
    type: String,
    enum: ['weekly', 'monthly', 'custom'],
    default: 'weekly'
  },
  period_start: {
    type: Date,
    required: true
  },
  period_end: {
    type: Date,
    required: true
  },
  generated_at: {
    type: Date,
    default: Date.now
  },
  pdf_path: {
    type: String,
    required: true
  },
  file_size_bytes: Number,
  email_status: {
    type: emailStatusSchema,
    required: true,
    default: () => ({
      sent: false,
      retry_count: 0
    })
  },
  summary_stats: summaryStatsSchema,
  triggered_by: {
    type: String,
    default: 'system'
  }
}, {
  timestamps: {
    createdAt: 'created_at',
    updatedAt: 'updated_at'
  }
});

// Indexes
reportLogSchema.index({ department_code: 1, generated_at: -1 });
reportLogSchema.index({ 'email_status.sent': 1 });
reportLogSchema.index({ generated_at: -1 });

module.exports = mongoose.model('ReportLog', reportLogSchema);
