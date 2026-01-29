const jwt = require('jsonwebtoken');
const { User } = require('../models');
const { ROLES } = require('../config/constants');

// Verify JWT token
const verifyToken = async (req, res, next) => {
  try {
    const token = req.headers.authorization?.split(' ')[1];

    if (!token) {
      return res.status(401).json({
        success: false,
        message: 'Access denied. No token provided.'
      });
    }

    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    const user = await User.findById(decoded.id);

    if (!user || !user.active) {
      return res.status(401).json({
        success: false,
        message: 'Invalid token or user inactive.'
      });
    }

    req.user = user;
    next();
  } catch (error) {
    return res.status(401).json({
      success: false,
      message: 'Invalid or expired token.'
    });
  }
};

// Super admin only
const requireSuperAdmin = (req, res, next) => {
  if (req.user.role !== ROLES.SUPER_ADMIN) {
    return res.status(403).json({
      success: false,
      message: 'Access denied. Super admin privileges required.'
    });
  }
  next();
};

// Department admin - can only access their own department
const requireDeptAdmin = (departmentCode) => {
  return (req, res, next) => {
    if (req.user.role === ROLES.SUPER_ADMIN) {
      // Super admin can access any department
      return next();
    }

    if (req.user.role === ROLES.DEPT_ADMIN && req.user.department_code === departmentCode) {
      return next();
    }

    return res.status(403).json({
      success: false,
      message: 'Access denied. You can only access your own department.'
    });
  };
};

// Filter departments based on user role
const filterDepartmentAccess = (req, res, next) => {
  if (req.user.role === ROLES.DEPT_ADMIN) {
    req.departmentFilter = { department_code: req.user.department_code };
  } else {
    req.departmentFilter = {};
  }
  next();
};

module.exports = {
  verifyToken,
  requireSuperAdmin,
  requireDeptAdmin,
  filterDepartmentAccess
};
