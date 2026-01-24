const express = require('express');
const router = express.Router();
const { Department } = require('../models');
const { getQuestionsByDepartment } = require('../config/questions');

// GET /api/departments - Get all active departments (public)
router.get('/', async (req, res, next) => {
  try {
    const departments = await Department.find({ active: true })
      .select('code name description')
      .sort({ name: 1 });

    res.json({
      success: true,
      data: {
        departments
      }
    });
  } catch (error) {
    next(error);
  }
});

// GET /api/departments/:code - Get department details with questions (public)
router.get('/:code', async (req, res, next) => {
  try {
    const { code } = req.params;

    const department = await Department.findOne({ code, active: true });

    if (!department) {
      return res.status(404).json({
        success: false,
        message: 'Department not found'
      });
    }

    res.json({
      success: true,
      data: {
        department: {
          code: department.code,
          name: department.name,
          description: department.description,
          questions: department.questions || [],
          tablet_config: department.tablet_config || {}
        }
      }
    });
  } catch (error) {
    next(error);
  }
});

module.exports = router;
