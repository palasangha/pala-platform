// Department codes and names
const DEPARTMENTS = [
  {
    code: 'global_pagoda',
    name: 'Global Pagoda',
    description: 'Main meditation and spiritual center'
  },
  {
    code: 'souvenir_store',
    name: 'Souvenir Store',
    description: 'Spiritual books and merchandise'
  },
  {
    code: 'dpvc',
    name: 'DPVC - Dhamma Pattana Vipassana Centre',
    description: 'Vipassana meditation courses'
  },
  {
    code: 'dhammalaya',
    name: 'Dhammalaya',
    description: 'Meditation and study facility'
  },
  {
    code: 'food_court',
    name: 'Food Court',
    description: 'Dining and refreshments'
  }
];

// User roles
const ROLES = {
  SUPER_ADMIN: 'super_admin',
  DEPT_ADMIN: 'dept_admin'
};

// Question types
const QUESTION_TYPES = {
  STAR: 'star',        // 1-5 stars
  EMOJI: 'emoji',      // 5 emoji faces
  NUMERIC: 'numeric'   // 1-10 scale
};

// Report statuses
const REPORT_STATUS = {
  PENDING: 'pending',
  GENERATING: 'generating',
  GENERATED: 'generated',
  SENT: 'sent',
  FAILED: 'failed'
};

// Access modes
const ACCESS_MODES = {
  WEB: 'web',
  QR_KIOSK: 'qr_kiosk'
};

module.exports = {
  DEPARTMENTS,
  ROLES,
  QUESTION_TYPES,
  REPORT_STATUS,
  ACCESS_MODES
};
