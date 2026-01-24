const mongoose = require('mongoose');

const auditLogSchema = new mongoose.Schema({
  action: {
    type: String,
    required: true,
    enum: [
      'login',
      'logout',
      'report_generated',
      'report_sent',
      'report_failed',
      'admin_created',
      'admin_updated',
      'department_updated',
      'feedback_viewed',
      'feedback_exported',
      'schedule_updated',
      'manual_report_trigger'
    ]
  },
  user_email: {
    type: String,
    lowercase: true,
    trim: true
  },
  resource_type: {
    type: String,
    enum: ['user', 'department', 'feedback', 'report', 'schedule', 'system']
  },
  resource_id: String,
  details: {
    type: mongoose.Schema.Types.Mixed,
    default: {}
  },
  ip_address: String,
  timestamp: {
    type: Date,
    default: Date.now,
    index: true
  }
});

// Indexes
auditLogSchema.index({ action: 1, timestamp: -1 });
auditLogSchema.index({ user_email: 1, timestamp: -1 });
auditLogSchema.index({ timestamp: -1 });

module.exports = mongoose.model('AuditLog', auditLogSchema);
