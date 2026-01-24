const { body, param, query, validationResult } = require('express-validator');
const { DEPARTMENTS } = require('../config/constants');
const { getQuestionsByDepartment, validateRating } = require('../config/questions');

// Handle validation errors
const handleValidationErrors = (req, res, next) => {
  const errors = validationResult(req);
  if (!errors.isEmpty()) {
    return res.status(400).json({
      success: false,
      message: 'Validation failed',
      errors: errors.array()
    });
  }
  next();
};

// Feedback submission validation
const validateFeedbackSubmission = [
  body('department_code')
    .trim()
    .notEmpty()
    .withMessage('Department code is required')
    .isIn(DEPARTMENTS.map(d => d.code))
    .withMessage('Invalid department code'),

  body('user_name')
    .optional()
    .trim()
    .isLength({ min: 2, max: 100 })
    .withMessage('Name must be between 2 and 100 characters'),

  body('user_email')
    .optional()
    .trim()
    .isEmail()
    .withMessage('Invalid email address')
    .normalizeEmail(),

  body('is_anonymous')
    .optional()
    .isBoolean()
    .withMessage('is_anonymous must be a boolean'),

  body('access_mode')
    .optional()
    .isIn(['web', 'qr_kiosk'])
    .withMessage('Invalid access mode'),

  body('ratings')
    .isObject()
    .withMessage('Ratings must be an object')
    .custom(async (ratings, { req }) => {
      const deptCode = req.body.department_code;
      
      // Get department with questions from database
      const Department = require('../models/Department');
      const department = await Department.findOne({ code: deptCode, active: true });
      
      if (!department) {
        throw new Error('Department not found');
      }

      const questions = department.questions || [];

      // Check all required questions are answered
      for (const question of questions) {
        const questionKey = question.key;
        const questionLabel = question.label;
        
        if (question.required && !ratings[questionKey]) {
          throw new Error(`Rating for "${questionLabel}" is required`);
        }

        // Validate rating value
        if (ratings[questionKey]) {
          if (!validateRating(question.type, ratings[questionKey])) {
            throw new Error(`Invalid rating value for "${questionLabel}"`);
          }
        }
      }

      return true;
    }),

  body('comment')
    .optional()
    .trim()
    .isLength({ max: 2000 })
    .withMessage('Comment must not exceed 2000 characters'),

  // Custom validation: If not anonymous, name and email are required
  body().custom((body) => {
    if (!body.is_anonymous) {
      if (!body.user_name || body.user_name.trim().length === 0) {
        throw new Error('Name is required for non-anonymous feedback');
      }
      if (!body.user_email || body.user_email.trim().length === 0) {
        throw new Error('Email is required for non-anonymous feedback');
      }
    }
    return true;
  }),

  handleValidationErrors
];

// Login validation
const validateLogin = [
  body('email')
    .trim()
    .notEmpty()
    .withMessage('Email is required')
    .isEmail()
    .withMessage('Invalid email address')
    .normalizeEmail(),

  body('password')
    .notEmpty()
    .withMessage('Password is required'),

  handleValidationErrors
];

// Create admin validation
const validateCreateAdmin = [
  body('email')
    .trim()
    .notEmpty()
    .withMessage('Email is required')
    .isEmail()
    .withMessage('Invalid email address')
    .normalizeEmail(),

  body('password')
    .notEmpty()
    .withMessage('Password is required')
    .isLength({ min: 8 })
    .withMessage('Password must be at least 8 characters'),

  body('full_name')
    .trim()
    .notEmpty()
    .withMessage('Full name is required')
    .isLength({ min: 2, max: 100 })
    .withMessage('Full name must be between 2 and 100 characters'),

  body('role')
    .notEmpty()
    .withMessage('Role is required')
    .isIn(['super_admin', 'dept_admin'])
    .withMessage('Invalid role'),

  body('department_code')
    .if(body('role').equals('dept_admin'))
    .trim()
    .notEmpty()
    .withMessage('Department code is required for department admin')
    .isIn(DEPARTMENTS.map(d => d.code))
    .withMessage('Invalid department code'),

  handleValidationErrors
];

// Update schedule validation
const validateUpdateSchedule = [
  body('day')
    .optional()
    .isInt({ min: 0, max: 6 })
    .withMessage('Day must be between 0 (Sunday) and 6 (Saturday)'),

  body('hour')
    .optional()
    .isInt({ min: 0, max: 23 })
    .withMessage('Hour must be between 0 and 23'),

  body('minute')
    .optional()
    .isInt({ min: 0, max: 59 })
    .withMessage('Minute must be between 0 and 59'),

  body('timezone')
    .optional()
    .trim()
    .notEmpty()
    .withMessage('Timezone cannot be empty'),

  handleValidationErrors
];

module.exports = {
  validateFeedbackSubmission,
  validateLogin,
  validateCreateAdmin,
  validateUpdateSchedule,
  handleValidationErrors
};
