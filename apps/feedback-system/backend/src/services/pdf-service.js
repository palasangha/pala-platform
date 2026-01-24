const PDFDocument = require('pdfkit');
const fs = require('fs');
const path = require('path');
const { Feedback } = require('../models');
const { getQuestionsByDepartment } = require('../config/questions');
const chartService = require('./chart-service');
const logger = require('../utils/logger');

class PDFService {
  async generateWeeklyReport(departmentCode, departmentName, startDate, endDate) {
    try {
      logger.info(`Generating report for ${departmentCode} (${startDate} to ${endDate})`);

      // Fetch feedback data
      const feedbacks = await Feedback.find({
        department_code: departmentCode,
        created_at: {
          $gte: new Date(startDate),
          $lte: new Date(endDate)
        }
      }).lean();

      if (feedbacks.length === 0) {
        logger.warn(`No feedback found for ${departmentCode}`);
        return null;
      }

      // Calculate statistics
      const stats = this.calculateStatistics(feedbacks, departmentCode);

      // Generate PDF
      const filename = `${departmentCode}_weekly_${this.formatDate(startDate)}_to_${this.formatDate(endDate)}.pdf`;
      const filepath = path.join('/app/reports', filename);

      const doc = new PDFDocument({ size: 'A4', margin: 50 });
      const stream = fs.createWriteStream(filepath);

      doc.pipe(stream);

      // Generate report content
      await this.addHeader(doc, departmentName, startDate, endDate);
      await this.addSummarySection(doc, stats);
      await this.addQuestionAnalysis(doc, stats, departmentCode);
      await this.addCommentsSection(doc, feedbacks);
      this.addFooter(doc);

      doc.end();

      // Wait for PDF to be written
      await new Promise((resolve, reject) => {
        stream.on('finish', resolve);
        stream.on('error', reject);
      });

      const fileSize = fs.statSync(filepath).size;
      logger.success(`Report generated: ${filename} (${fileSize} bytes)`);

      return {
        filename,
        filepath,
        fileSize,
        stats
      };
    } catch (error) {
      logger.error('PDF generation error:', error);
      throw error;
    }
  }

  addHeader(doc, departmentName, startDate, endDate) {
    doc.fontSize(20)
       .fillColor('#2c3e50')
       .text('Global Vipassana Pagoda', { align: 'center' })
       .fontSize(16)
       .text('Weekly Feedback Report', { align: 'center' })
       .moveDown();

    doc.fontSize(12)
       .fillColor('#7f8c8d')
       .text(`Department: ${departmentName}`, { align: 'center' })
       .text(`Period: ${this.formatDate(startDate)} to ${this.formatDate(endDate)}`, { align: 'center' })
       .text(`Generated: ${new Date().toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })}`, { align: 'center' })
       .moveDown(2);

    doc.moveTo(50, doc.y)
       .lineTo(550, doc.y)
       .stroke()
       .moveDown();
  }

  async addSummarySection(doc, stats) {
    doc.fontSize(14)
       .fillColor('#2c3e50')
       .text('Executive Summary', { underline: true })
       .moveDown(0.5);

    const summaryData = [
      ['Total Responses', stats.totalFeedback],
      ['Average Rating', `${stats.avgRating} / ${stats.maxRating}`],
      ['Response Rate', `${stats.withComments} responses with comments`],
      ['Anonymous Submissions', `${stats.anonymousCount} (${stats.anonymousPercent}%)`],
      ['Completion Rate', '100%']
    ];

    const tableTop = doc.y;
    const itemHeight = 25;
    const col1X = 70;
    const col2X = 350;

    summaryData.forEach((row, i) => {
      const y = tableTop + (i * itemHeight);

      doc.fontSize(11)
         .fillColor('#34495e')
         .text(row[0], col1X, y)
         .fillColor('#2980b9')
         .text(row[1].toString(), col2X, y);

      doc.moveTo(50, y + 20)
         .lineTo(550, y + 20)
         .strokeColor('#ecf0f1')
         .stroke();
    });

    doc.moveDown(3);
  }

  async addQuestionAnalysis(doc, stats, departmentCode) {
    const questions = getQuestionsByDepartment(departmentCode);

    doc.addPage()
       .fontSize(14)
       .fillColor('#2c3e50')
       .text('Question-wise Analysis', { underline: true })
       .moveDown(1);

    for (const question of questions) {
      const questionStats = stats.questionStats[question.id];
      if (!questionStats) continue;

      doc.fontSize(12)
         .fillColor('#34495e')
         .text(`${question.text}`, { continued: false })
         .fontSize(10)
         .fillColor('#7f8c8d')
         .text(`Type: ${question.type} | Average: ${questionStats.avg}`)
         .moveDown(0.5);

      // Distribution
      const distribution = Object.entries(questionStats.distribution)
        .map(([rating, count]) => `${rating}: ${count} (${((count / stats.totalFeedback) * 100).toFixed(1)}%)`)
        .join(' | ');

      doc.fontSize(9)
         .fillColor('#95a5a6')
         .text(distribution)
         .moveDown(1.5);

      // Add page break if needed
      if (doc.y > 700) {
        doc.addPage();
      }
    }
  }

  async addCommentsSection(doc, feedbacks) {
    doc.addPage()
       .fontSize(14)
       .fillColor('#2c3e50')
       .text('User Comments', { underline: true })
       .moveDown(1);

    const feedbacksWithComments = feedbacks.filter(f => f.comment && f.comment.trim());

    if (feedbacksWithComments.length === 0) {
      doc.fontSize(11)
         .fillColor('#7f8c8d')
         .text('No comments received during this period.');
      return;
    }

    feedbacksWithComments.forEach((feedback, index) => {
      const date = new Date(feedback.created_at).toLocaleString('en-IN', {
        timeZone: 'Asia/Kolkata',
        dateStyle: 'medium',
        timeStyle: 'short'
      });

      const userInfo = feedback.is_anonymous
        ? '(Anonymous)'
        : `${feedback.user_name || 'Unknown'} (${feedback.user_email || 'No email'})`;

      doc.fontSize(10)
         .fillColor('#34495e')
         .text(`${index + 1}. ${date} - ${userInfo}`, { continued: false })
         .fontSize(10)
         .fillColor('#2c3e50')
         .text(feedback.comment, { align: 'justify', indent: 20 })
         .moveDown(1);

      // Add page break if needed
      if (doc.y > 720) {
        doc.addPage();
      }
    });
  }

  addFooter(doc) {
    // Add footer to the last page only (current page)
    doc.fontSize(8)
       .fillColor('#95a5a6')
       .text(
         'Report generated by Feedback Management System | Global Vipassana Pagoda',
         50,
         doc.page.height - 50,
         { align: 'center' }
       )
       .text(
         `Generated on ${new Date().toLocaleDateString('en-IN')}`,
         50,
         doc.page.height - 35,
         { align: 'center' }
       );
  }

  calculateStatistics(feedbacks, departmentCode) {
    const questions = getQuestionsByDepartment(departmentCode);
    const stats = {
      totalFeedback: feedbacks.length,
      avgRating: 0,
      maxRating: 10,
      withComments: feedbacks.filter(f => f.comment && f.comment.trim()).length,
      anonymousCount: feedbacks.filter(f => f.is_anonymous).length,
      anonymousPercent: 0,
      questionStats: {}
    };

    stats.anonymousPercent = ((stats.anonymousCount / stats.totalFeedback) * 100).toFixed(1);

    // Calculate question statistics
    questions.forEach(question => {
      const ratings = [];
      const distribution = {};

      feedbacks.forEach(feedback => {
        // Handle both Map and plain object (from .lean())
        const rating = feedback.ratings instanceof Map
          ? feedback.ratings.get(question.id)
          : feedback.ratings[question.id];

        if (rating !== undefined) {
          ratings.push(rating);
          distribution[rating] = (distribution[rating] || 0) + 1;
        }
      });

      if (ratings.length > 0) {
        stats.questionStats[question.id] = {
          avg: (ratings.reduce((a, b) => a + b, 0) / ratings.length).toFixed(2),
          distribution,
          total: ratings.length
        };
      }
    });

    // Calculate overall average
    const allRatings = [];
    feedbacks.forEach(feedback => {
      if (feedback.ratings instanceof Map) {
        feedback.ratings.forEach(rating => allRatings.push(rating));
      } else {
        Object.values(feedback.ratings).forEach(rating => allRatings.push(rating));
      }
    });

    if (allRatings.length > 0) {
      stats.avgRating = (allRatings.reduce((a, b) => a + b, 0) / allRatings.length).toFixed(2);
    }

    return stats;
  }

  formatDate(date) {
    const d = new Date(date);
    return d.toISOString().split('T')[0].replace(/-/g, '');
  }
}

module.exports = new PDFService();
