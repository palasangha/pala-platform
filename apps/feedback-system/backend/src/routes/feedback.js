const express = require('express');
const router = express.Router();
const rateLimit = require('express-rate-limit');
const { Feedback, Department } = require('../models');
const { validateFeedbackSubmission } = require('../middleware/validators');
const { verifyToken, filterDepartmentAccess } = require('../middleware/auth');
const { getIpAddress } = require('../utils/audit');
const { randomUUID } = require('crypto');

// Rate limiter for feedback submission
const feedbackLimiter = rateLimit({
  windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS) || 900000, // 15 minutes
  max: parseInt(process.env.RATE_LIMIT_MAX_REQUESTS) || 10,
  message: {
    success: false,
    message: 'Too many feedback submissions from this IP. Please try again later.'
  },
  standardHeaders: true,
  legacyHeaders: false
});

// POST /api/feedback - Submit feedback (public, rate-limited)
router.post('/', feedbackLimiter, validateFeedbackSubmission, async (req, res, next) => {
  try {
    const {
      department_code,
      user_name,
      user_email,
      is_anonymous,
      access_mode,
      ratings,
      comment
    } = req.body;

    // Verify department exists
    const department = await Department.findOne({ code: department_code, active: true });
    if (!department) {
      return res.status(404).json({
        success: false,
        message: 'Department not found or inactive'
      });
    }

    // Create feedback
    const feedback = new Feedback({
      department_code,
      user_name: is_anonymous ? null : user_name,
      user_email: is_anonymous ? null : user_email,
      is_anonymous: is_anonymous || false,
      access_mode: access_mode || 'web',
      ratings: new Map(Object.entries(ratings)),
      comment: comment || null,
      metadata: {
        ip_address: getIpAddress(req),
        user_agent: req.headers['user-agent'],
        submission_time: new Date(),
        session_id: randomUUID()
      }
    });

    await feedback.save();

    res.status(201).json({
      success: true,
      message: 'Feedback submitted successfully',
      data: {
        feedback_id: feedback._id,
        submitted_at: feedback.created_at
      }
    });
  } catch (error) {
    next(error);
  }
});

// GET /api/feedback - List feedback (admin only)
router.get('/', verifyToken, filterDepartmentAccess, async (req, res, next) => {
  try {
    const {
      department_code,
      start_date,
      end_date,
      is_anonymous,
      has_comment,
      page = 1,
      limit = 50
    } = req.query;

    const query = { ...req.departmentFilter };

    // Apply filters
    if (department_code) {
      query.department_code = department_code;
    }

    if (start_date || end_date) {
      query.created_at = {};
      if (start_date) query.created_at.$gte = new Date(start_date);
      if (end_date) query.created_at.$lte = new Date(end_date);
    }

    if (is_anonymous !== undefined) {
      query.is_anonymous = is_anonymous === 'true';
    }

    if (has_comment === 'true') {
      query.comment = { $ne: null, $ne: '' };
    }

    const skip = (parseInt(page) - 1) * parseInt(limit);

    const [feedbacks, total] = await Promise.all([
      Feedback.find(query)
        .sort({ created_at: -1 })
        .skip(skip)
        .limit(parseInt(limit))
        .lean(),
      Feedback.countDocuments(query)
    ]);

    res.json({
      success: true,
      data: {
        feedbacks,
        pagination: {
          total,
          page: parseInt(page),
          limit: parseInt(limit),
          pages: Math.ceil(total / parseInt(limit))
        }
      }
    });
  } catch (error) {
    next(error);
  }
});

// GET /api/feedback/:id - Get feedback details (admin only)
router.get('/:id', verifyToken, async (req, res, next) => {
  try {
    const feedback = await Feedback.findById(req.params.id);

    if (!feedback) {
      return res.status(404).json({
        success: false,
        message: 'Feedback not found'
      });
    }

    // Check department access
    if (req.user.role === 'dept_admin' &&
        feedback.department_code !== req.user.department_code) {
      return res.status(403).json({
        success: false,
        message: 'Access denied'
      });
    }

    res.json({
      success: true,
      data: {
        feedback
      }
    });
  } catch (error) {
    next(error);
  }
});

// GET /api/feedback/stats/summary - Get feedback statistics (admin only)
router.get('/stats/summary', verifyToken, filterDepartmentAccess, async (req, res, next) => {
  try {
    const { department_code, start_date, end_date } = req.query;

    const query = { ...req.departmentFilter };

    if (department_code) {
      query.department_code = department_code;
    }

    if (start_date || end_date) {
      query.created_at = {};
      if (start_date) query.created_at.$gte = new Date(start_date);
      if (end_date) query.created_at.$lte = new Date(end_date);
    }

    const [total, anonymous, withComments] = await Promise.all([
      Feedback.countDocuments(query),
      Feedback.countDocuments({ ...query, is_anonymous: true }),
      Feedback.countDocuments({
        ...query,
        comment: { $ne: null, $ne: '' }
      })
    ]);

    res.json({
      success: true,
      data: {
        total_feedback: total,
        anonymous_count: anonymous,
        with_comments: withComments,
        identified_count: total - anonymous
      }
    });
  } catch (error) {
    next(error);
  }
});

module.exports = router;
