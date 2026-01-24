const express = require('express');
const router = express.Router();
const { User, Department, Feedback, ReportLog } = require('../models');
const { verifyToken, requireSuperAdmin, filterDepartmentAccess } = require('../middleware/auth');
const { validateCreateAdmin, validateUpdateSchedule } = require('../middleware/validators');
const { createAuditLog, getIpAddress } = require('../utils/audit');
const DashboardService = require('../services/dashboard-service');
const PermissionService = require('../services/permission-service');

// GET /api/admin/dashboard - Dashboard statistics (OPTIMIZED)
router.get('/dashboard', verifyToken, async (req, res, next) => {
  try {
    const { start_date, end_date, department, page, limit } = req.query;

    // Build filters
    const filters = {};
    if (start_date) filters.startDate = start_date;
    if (end_date) filters.endDate = end_date;
    if (department) filters.department = department;
    if (page) filters.page = page;
    if (limit) filters.limit = limit;

    // Get dashboard data using optimized service
    const dashboardData = await DashboardService.getDashboardData(req.user, filters);

    // Format response for backward compatibility
    const response = {
      overall: {
        total_feedback: dashboardData.summary.total_feedback,
        avg_rating: parseFloat(dashboardData.summary.avg_rating?.toFixed(2) || 0),
        with_comments: dashboardData.summary.with_comments,
        anonymous_count: dashboardData.summary.anonymous_count
      },
      by_department: dashboardData.departmentStats,
      recent_feedback: dashboardData.feedbacks.slice(0, 10),
      pagination: dashboardData.pagination
    };

    res.json({
      success: true,
      data: response
    });
  } catch (error) {
    next(error);
  }
});

// GET /api/admin/users - List admin users (super admin only)
router.get('/users', verifyToken, requireSuperAdmin, async (req, res, next) => {
  try {
    const users = await User.find()
      .select('-password_hash')
      .sort({ created_at: -1 });

    res.json({
      success: true,
      data: {
        users
      }
    });
  } catch (error) {
    next(error);
  }
});

// POST /api/admin/users - Create admin user (super admin only)
router.post('/users', verifyToken, requireSuperAdmin, validateCreateAdmin, async (req, res, next) => {
  try {
    const { email, password, full_name, role, department_code } = req.body;

    // Create user
    const user = new User({
      email,
      password_hash: password, // Will be hashed by pre-save hook
      full_name,
      role,
      department_code: role === 'dept_admin' ? department_code : null,
      active: true
    });

    await user.save();

    // Create audit log
    await createAuditLog({
      action: 'admin_created',
      userEmail: req.user.email,
      resourceType: 'user',
      resourceId: user._id.toString(),
      details: { created_user: email, role },
      ipAddress: getIpAddress(req)
    });

    res.status(201).json({
      success: true,
      message: 'Admin user created successfully',
      data: {
        user: {
          id: user._id,
          email: user.email,
          role: user.role,
          full_name: user.full_name,
          department_code: user.department_code
        }
      }
    });
  } catch (error) {
    next(error);
  }
});

// PUT /api/admin/users/:id - Update admin user (super admin only)
router.put('/users/:id', verifyToken, requireSuperAdmin, async (req, res, next) => {
  try {
    const { active, department_code } = req.body;
    const user = await User.findById(req.params.id);

    if (!user) {
      return res.status(404).json({
        success: false,
        message: 'User not found'
      });
    }

    if (active !== undefined) user.active = active;
    if (department_code !== undefined) user.department_code = department_code;

    await user.save();

    // Create audit log
    await createAuditLog({
      action: 'admin_updated',
      userEmail: req.user.email,
      resourceType: 'user',
      resourceId: user._id.toString(),
      details: { updated_user: user.email, changes: req.body },
      ipAddress: getIpAddress(req)
    });

    res.json({
      success: true,
      message: 'User updated successfully',
      data: { user }
    });
  } catch (error) {
    next(error);
  }
});

// PUT /api/admin/schedule/:dept_code - Update report schedule
router.put('/schedule/:dept_code', verifyToken, validateUpdateSchedule, async (req, res, next) => {
  try {
    const { dept_code } = req.params;
    const { day, hour, minute, timezone } = req.body;

    // Check access rights
    if (req.user.role === 'dept_admin' && req.user.department_code !== dept_code) {
      return res.status(403).json({
        success: false,
        message: 'Access denied. You can only update your own department schedule.'
      });
    }

    const department = await Department.findOne({ code: dept_code });
    if (!department) {
      return res.status(404).json({
        success: false,
        message: 'Department not found'
      });
    }

    // Update schedule
    if (day !== undefined) department.report_schedule.day = day;
    if (hour !== undefined) department.report_schedule.hour = hour;
    if (minute !== undefined) department.report_schedule.minute = minute;
    if (timezone) department.report_schedule.timezone = timezone;

    await department.save();

    // Create audit log
    await createAuditLog({
      action: 'schedule_updated',
      userEmail: req.user.email,
      resourceType: 'department',
      resourceId: department._id.toString(),
      details: { department_code: dept_code, new_schedule: department.report_schedule },
      ipAddress: getIpAddress(req)
    });

    res.json({
      success: true,
      message: 'Report schedule updated successfully',
      data: {
        department_code: dept_code,
        report_schedule: department.report_schedule
      }
    });
  } catch (error) {
    next(error);
  }
});

// GET /api/admin/reports - List report logs
router.get('/reports', verifyToken, filterDepartmentAccess, async (req, res, next) => {
  try {
    const { department_code, start_date, end_date, page = 1, limit = 20 } = req.query;

    const query = {};

    // Apply department filter based on role
    if (req.departmentFilter.code) {
      query.department_code = req.departmentFilter.code;
    } else if (department_code) {
      query.department_code = department_code;
    }

    if (start_date || end_date) {
      query.generated_at = {};
      if (start_date) query.generated_at.$gte = new Date(start_date);
      if (end_date) query.generated_at.$lte = new Date(end_date);
    }

    const skip = (parseInt(page) - 1) * parseInt(limit);

    const [reports, total] = await Promise.all([
      ReportLog.find(query)
        .sort({ generated_at: -1 })
        .skip(skip)
        .limit(parseInt(limit))
        .lean(),
      ReportLog.countDocuments(query)
    ]);

    res.json({
      success: true,
      data: {
        reports,
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

module.exports = router;
