const express = require('express');
const router = express.Router();
const { User } = require('../models');
const { generateToken } = require('../utils/jwt');
const { createAuditLog, getIpAddress } = require('../utils/audit');
const { validateLogin } = require('../middleware/validators');
const { verifyToken } = require('../middleware/auth');

// POST /api/auth/login
router.post('/login', validateLogin, async (req, res, next) => {
  try {
    const { email, password } = req.body;

    // Find user
    const user = await User.findOne({ email });
    if (!user) {
      return res.status(401).json({
        success: false,
        message: 'Invalid email or password'
      });
    }

    // Check if user is active
    if (!user.active) {
      return res.status(401).json({
        success: false,
        message: 'Account is inactive. Please contact administrator.'
      });
    }

    // Verify password
    const isPasswordValid = await user.comparePassword(password);
    if (!isPasswordValid) {
      return res.status(401).json({
        success: false,
        message: 'Invalid email or password'
      });
    }

    // Update last login
    user.last_login = new Date();
    await user.save();

    // Generate JWT token
    const token = generateToken(user._id);

    // Create audit log
    await createAuditLog({
      action: 'login',
      userEmail: user.email,
      resourceType: 'user',
      resourceId: user._id.toString(),
      ipAddress: getIpAddress(req)
    });

    res.json({
      success: true,
      message: 'Login successful',
      data: {
        token,
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

// GET /api/auth/me
router.get('/me', verifyToken, async (req, res) => {
  res.json({
    success: true,
    data: {
      user: {
        id: req.user._id,
        email: req.user.email,
        role: req.user.role,
        full_name: req.user.full_name,
        department_code: req.user.department_code,
        last_login: req.user.last_login
      }
    }
  });
});

// POST /api/auth/logout
router.post('/logout', verifyToken, async (req, res, next) => {
  try {
    // Create audit log
    await createAuditLog({
      action: 'logout',
      userEmail: req.user.email,
      resourceType: 'user',
      resourceId: req.user._id.toString(),
      ipAddress: getIpAddress(req)
    });

    res.json({
      success: true,
      message: 'Logout successful'
    });
  } catch (error) {
    next(error);
  }
});

module.exports = router;
