const { AuditLog } = require('../models');
const logger = require('./logger');

// Create an audit log entry
const createAuditLog = async ({
  action,
  userEmail = null,
  resourceType = null,
  resourceId = null,
  details = {},
  ipAddress = null
}) => {
  try {
    const auditLog = new AuditLog({
      action,
      user_email: userEmail,
      resource_type: resourceType,
      resource_id: resourceId,
      details,
      ip_address: ipAddress,
      timestamp: new Date()
    });

    await auditLog.save();
    logger.debug(`Audit log created: ${action}`, { userEmail, resourceType });
  } catch (error) {
    logger.error('Failed to create audit log:', error.message);
  }
};

// Helper to get IP address from request
const getIpAddress = (req) => {
  return req.headers['x-forwarded-for']?.split(',')[0].trim() ||
         req.headers['x-real-ip'] ||
         req.connection.remoteAddress ||
         req.socket.remoteAddress ||
         req.ip;
};

module.exports = {
  createAuditLog,
  getIpAddress
};
