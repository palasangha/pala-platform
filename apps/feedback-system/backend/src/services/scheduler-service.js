const cron = require('node-cron');
const { Department, ReportLog } = require('../models');
const pdfService = require('./pdf-service');
const emailService = require('./email-service');
const { createAuditLog } = require('../utils/audit');
const logger = require('../utils/logger');

class SchedulerService {
  constructor() {
    this.jobs = new Map();
    this.isInitialized = false;
  }

  async initialize() {
    if (this.isInitialized) {
      logger.warn('Scheduler already initialized');
      return;
    }

    try {
      logger.info('Initializing report scheduler...');

      // Load all active departments and schedule their reports
      const departments = await Department.find({ active: true });

      for (const dept of departments) {
        await this.scheduleDepartmentReport(dept);
      }

      this.isInitialized = true;
      logger.success(`Scheduler initialized with ${departments.length} departments`);
    } catch (error) {
      logger.error('Scheduler initialization failed:', error);
      throw error;
    }
  }

  async scheduleDepartmentReport(department) {
    const { code, name, report_schedule } = department;
    const { day, hour, minute } = report_schedule;

    // Convert day number to cron day (0=Sunday in our DB, but cron uses 0=Sunday too)
    // Cron format: minute hour day-of-month month day-of-week
    const cronExpression = `${minute} ${hour} * * ${day}`;

    logger.info(`Scheduling ${code}: ${cronExpression} (${this.getCronDescription(day, hour, minute)})`);

    // Stop existing job if any
    if (this.jobs.has(code)) {
      this.jobs.get(code).stop();
    }

    // Create new cron job
    const job = cron.schedule(
      cronExpression,
      async () => {
        await this.generateAndSendReport(department);
      },
      {
        scheduled: true,
        timezone: report_schedule.timezone || 'Asia/Kolkata'
      }
    );

    this.jobs.set(code, job);
  }

  async generateAndSendReport(department) {
    const { code, name, email_recipients } = department;

    logger.info(`📊 Starting scheduled report generation for ${name}`);

    try {
      // Calculate date range (last 7 days)
      const endDate = new Date();
      const startDate = new Date();
      startDate.setDate(endDate.getDate() - 7);

      // Generate PDF
      const reportData = await pdfService.generateWeeklyReport(
        code,
        name,
        startDate,
        endDate
      );

      if (!reportData) {
        logger.warn(`No feedback data for ${code}. Skipping report.`);

        // Log empty report
        await ReportLog.create({
          department_code: code,
          report_type: 'weekly',
          period_start: startDate,
          period_end: endDate,
          generated_at: new Date(),
          pdf_path: null,
          email_status: {
            sent: false,
            failures: ['No feedback data available']
          },
          summary_stats: {
            total_feedback: 0,
            avg_rating: 0
          },
          triggered_by: 'scheduler'
        });

        return;
      }

      // Send email with retry
      const emailResult = await emailService.sendWithRetry(
        email_recipients,
        name,
        reportData
      );

      // Create report log
      const reportLog = await ReportLog.create({
        department_code: code,
        report_type: 'weekly',
        period_start: startDate,
        period_end: endDate,
        generated_at: new Date(),
        pdf_path: reportData.filepath,
        file_size_bytes: reportData.fileSize,
        email_status: {
          sent: emailResult.sent,
          sent_at: emailResult.sentAt || null,
          recipients: email_recipients,
          failures: emailResult.sent ? [] : [emailResult.error],
          retry_count: emailResult.retryCount || 0,
          last_error: emailResult.error || null
        },
        summary_stats: {
          total_feedback: reportData.stats.totalFeedback,
          avg_rating: parseFloat(reportData.stats.avgRating),
          anonymous_count: reportData.stats.anonymousCount,
          with_comments_count: reportData.stats.withComments
        },
        triggered_by: 'scheduler'
      });

      // Create audit log
      await createAuditLog({
        action: emailResult.sent ? 'report_sent' : 'report_failed',
        userEmail: 'system',
        resourceType: 'report',
        resourceId: reportLog._id.toString(),
        details: {
          department_code: code,
          email_sent: emailResult.sent,
          recipients: email_recipients
        }
      });

      if (emailResult.sent) {
        logger.success(`✅ Report generated and sent for ${name}`);
      } else {
        logger.error(`❌ Report generated but email failed for ${name}: ${emailResult.error}`);
      }
    } catch (error) {
      logger.error(`Report generation failed for ${code}:`, error);

      // Log failure
      await createAuditLog({
        action: 'report_failed',
        userEmail: 'system',
        resourceType: 'report',
        resourceId: null,
        details: {
          department_code: code,
          error: error.message
        }
      });
    }
  }

  async updateDepartmentSchedule(departmentCode) {
    const department = await Department.findOne({ code: departmentCode });
    if (!department) {
      throw new Error(`Department ${departmentCode} not found`);
    }

    await this.scheduleDepartmentReport(department);
    logger.info(`Schedule updated for ${departmentCode}`);
  }

  async triggerManualReport(departmentCode, userEmail) {
    const department = await Department.findOne({ code: departmentCode });
    if (!department) {
      throw new Error(`Department ${departmentCode} not found`);
    }

    logger.info(`Manual report triggered for ${departmentCode} by ${userEmail}`);

    // Calculate date range
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(endDate.getDate() - 7);

    // Generate PDF
    const reportData = await pdfService.generateWeeklyReport(
      departmentCode,
      department.name,
      startDate,
      endDate
    );

    if (!reportData) {
      throw new Error('No feedback data available for the selected period');
    }

    // Send email
    const emailResult = await emailService.sendWithRetry(
      department.email_recipients,
      department.name,
      reportData
    );

    // Create report log
    const reportLog = await ReportLog.create({
      department_code: departmentCode,
      report_type: 'weekly',
      period_start: startDate,
      period_end: endDate,
      generated_at: new Date(),
      pdf_path: reportData.filepath,
      file_size_bytes: reportData.fileSize,
      email_status: {
        sent: emailResult.sent,
        sent_at: emailResult.sentAt || null,
        recipients: department.email_recipients,
        failures: emailResult.sent ? [] : [emailResult.error],
        retry_count: emailResult.retryCount || 0
      },
      summary_stats: {
        total_feedback: reportData.stats.totalFeedback,
        avg_rating: parseFloat(reportData.stats.avgRating)
      },
      triggered_by: userEmail
    });

    // Audit log
    await createAuditLog({
      action: 'manual_report_trigger',
      userEmail,
      resourceType: 'report',
      resourceId: reportLog._id.toString(),
      details: {
        department_code: departmentCode,
        email_sent: emailResult.sent
      }
    });

    return {
      reportLog,
      emailSent: emailResult.sent,
      filepath: reportData.filepath
    };
  }

  getCronDescription(day, hour, minute) {
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    return `Every ${days[day]} at ${hour.toString().padStart(2, '0')}:${minute.toString().padStart(2, '0')}`;
  }

  stop() {
    this.jobs.forEach((job, code) => {
      job.stop();
      logger.info(`Stopped scheduler for ${code}`);
    });
    this.jobs.clear();
    this.isInitialized = false;
  }
}

module.exports = new SchedulerService();
