const mongoose = require('mongoose');

const metadataSchema = new mongoose.Schema({
  ip_address: String,
  user_agent: String,
  submission_time: {
    type: Date,
    default: Date.now
  },
  session_id: String,
  device_type: {
    type: String,
    enum: ['tablet', 'mobile', 'desktop', 'unknown'],
    default: 'unknown'
  }
}, { _id: false });

const feedbackSchema = new mongoose.Schema({
  department_code: {
    type: String,
    required: true,
    lowercase: true,
    trim: true,
    index: true
  },
  user_name: {
    type: String,
    trim: true,
    default: null
  },
  user_email: {
    type: String,
    lowercase: true,
    trim: true,
    default: null
  },
  is_anonymous: {
    type: Boolean,
    default: false
  },
  access_mode: {
    type: String,
    enum: ['web', 'qr_kiosk', 'tablet', 'mobile'],
    default: 'tablet'  // Changed default to tablet
  },
  ratings: {
    type: Map,
    of: Number,
    required: true
  },
  comment: {
    type: String,
    trim: true,
    maxlength: 2000
  },
  metadata: {
    type: metadataSchema,
    required: true
  }
}, {
  timestamps: {
    createdAt: 'created_at',
    updatedAt: false
  }
});

// CRITICAL Compound Indexes for Performance
feedbackSchema.index({ department_code: 1, created_at: -1 });
feedbackSchema.index({ department_code: 1, created_at: -1, is_anonymous: 1 });
feedbackSchema.index({ created_at: -1 });
feedbackSchema.index({ 'metadata.ip_address': 1, created_at: -1 });
feedbackSchema.index({ is_anonymous: 1 });
feedbackSchema.index({ access_mode: 1, created_at: -1 });

// Virtual for average rating
feedbackSchema.virtual('average_rating').get(function() {
  if (!this.ratings || this.ratings.size === 0) return 0;

  let sum = 0;
  let count = 0;

  this.ratings.forEach((value) => {
    sum += value;
    count++;
  });

  return count > 0 ? (sum / count).toFixed(2) : 0;
});

// Ensure virtuals are included in JSON
feedbackSchema.set('toJSON', { virtuals: true });
feedbackSchema.set('toObject', { virtuals: true });

module.exports = mongoose.model('Feedback', feedbackSchema);
