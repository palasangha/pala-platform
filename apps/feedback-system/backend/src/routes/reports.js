const express = require('express');
const router = express.Router();
const path = require('path');
const fs = require('fs');
const { ReportLog } = require('../models');
const { verifyToken, filterDepartmentAccess } = require('../middleware/auth');
const schedulerService = require('../services/scheduler-service');
const { createAuditLog, getIpAddress } = require('../utils/audit');

// GET /api/reports - List all report logs
router.get('/', verifyToken, filterDepartmentAccess, async (req, res, next) => {
  try {
    const {
      department_code,
      start_date,
      end_date,
      email_status,
      page = 1,
      limit = 20
    } = req.query;

    const query = {};

    // Apply department filter based on role
    if (req.departmentFilter.department_code) {
      query.department_code = req.departmentFilter.department_code;
    } else if (department_code) {
      query.department_code = department_code;
    }

    // Date filter
    if (start_date || end_date) {
      query.generated_at = {};
      if (start_date) query.generated_at.$gte = new Date(start_date);
      if (end_date) query.generated_at.$lte = new Date(end_date);
    }

    // Email status filter
    if (email_status) {
      query['email_status.sent'] = email_status === 'sent';
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

// GET /api/reports/:id - Get report details
router.get('/:id', verifyToken, async (req, res, next) => {
  try {
    const report = await ReportLog.findById(req.params.id);

    if (!report) {
      return res.status(404).json({
        success: false,
        message: 'Report not found'
      });
    }

    // Check access rights
    if (req.user.role === 'dept_admin' &&
        report.department_code !== req.user.department_code) {
      return res.status(403).json({
        success: false,
        message: 'Access denied'
      });
    }

    res.json({
      success: true,
      data: { report }
    });
  } catch (error) {
    next(error);
  }
});

// GET /api/reports/:id/download - Download PDF report
router.get('/:id/download', verifyToken, async (req, res, next) => {
  try {
    const report = await ReportLog.findById(req.params.id);

    if (!report) {
      return res.status(404).json({
        success: false,
        message: 'Report not found'
      });
    }

    // Check access rights
    if (req.user.role === 'dept_admin' &&
        report.department_code !== req.user.department_code) {
      return res.status(403).json({
        success: false,
        message: 'Access denied'
      });
    }

    // Check if file exists
    if (!report.pdf_path || !fs.existsSync(report.pdf_path)) {
      return res.status(404).json({
        success: false,
        message: 'Report file not found'
      });
    }

    // Audit log
    await createAuditLog({
      action: 'report_downloaded',
      userEmail: req.user.email,
      resourceType: 'report',
      resourceId: report._id.toString(),
      details: {
        department_code: report.department_code,
        filename: path.basename(report.pdf_path)
      },
      ipAddress: getIpAddress(req)
    });

    // Send file
    res.download(report.pdf_path, path.basename(report.pdf_path));
  } catch (error) {
    next(error);
  }
});

// POST /api/reports/trigger - Manually trigger report generation
router.post('/trigger', verifyToken, async (req, res, next) => {
  try {
    const { department_code } = req.body;

    if (!department_code) {
      return res.status(400).json({
        success: false,
        message: 'department_code is required'
      });
    }

    // Check access rights
    if (req.user.role === 'dept_admin' &&
        department_code !== req.user.department_code) {
      return res.status(403).json({
        success: false,
        message: 'Access denied. You can only generate reports for your department.'
      });
    }

    // Trigger report generation
    const result = await schedulerService.triggerManualReport(
      department_code,
      req.user.email
    );

    res.json({
      success: true,
      message: 'Report generated successfully',
      data: {
        report_id: result.reportLog._id,
        email_sent: result.emailSent,
        generated_at: result.reportLog.generated_at,
        download_url: `/api/reports/${result.reportLog._id}/download`
      }
    });
  } catch (error) {
    next(error);
  }
});

// POST /api/reports/:id/resend - Resend email for existing report
router.post('/:id/resend', verifyToken, async (req, res, next) => {
  try {
    const report = await ReportLog.findById(req.params.id);

    if (!report) {
      return res.status(404).json({
        success: false,
        message: 'Report not found'
      });
    }

    // Check access rights
    if (req.user.role === 'dept_admin' &&
        report.department_code !== req.user.department_code) {
      return res.status(403).json({
        success: false,
        message: 'Access denied'
      });
    }

    // Get department info
    const Department = require('../models').Department;
    const department = await Department.findOne({ code: report.department_code });

    if (!department) {
      return res.status(404).json({
        success: false,
        message: 'Department not found'
      });
    }

    // Resend email
    const emailService = require('../services/email-service');
    const emailResult = await emailService.sendWithRetry(
      department.email_recipients,
      department.name,
      {
        filepath: report.pdf_path,
        filename: path.basename(report.pdf_path),
        stats: report.summary_stats
      }
    );

    // Update report log
    report.email_status = {
      ...report.email_status,
      sent: emailResult.sent,
      sent_at: emailResult.sent ? new Date() : report.email_status.sent_at,
      retry_count: (report.email_status.retry_count || 0) + 1,
      last_error: emailResult.error || null
    };

    if (!emailResult.sent) {
      report.email_status.failures.push(emailResult.error);
    }

    await report.save();

    // Audit log
    await createAuditLog({
      action: emailResult.sent ? 'report_resent' : 'report_resend_failed',
      userEmail: req.user.email,
      resourceType: 'report',
      resourceId: report._id.toString(),
      details: {
        department_code: report.department_code,
        email_sent: emailResult.sent
      },
      ipAddress: getIpAddress(req)
    });

    res.json({
      success: true,
      message: emailResult.sent ? 'Email resent successfully' : 'Email resend failed',
      data: {
        email_sent: emailResult.sent,
        error: emailResult.error || null
      }
    });
  } catch (error) {
    next(error);
  }
});

module.exports = router;
