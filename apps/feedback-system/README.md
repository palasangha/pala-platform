# Flutter Web Feedback System - Complete Documentation

## Table of Contents
1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Features](#features)
4. [Tech Stack](#tech-stack)
5. [Codebase Structure](#codebase-structure)
6. [Database Schema](#database-schema)
7. [Installation & Setup](#installation--setup)
8. [API Documentation](#api-documentation)
9. [Frontend Guide](#frontend-guide)
10. [Deployment](#deployment)
11. [Monitoring & Maintenance](#monitoring--maintenance)
12. [Development Guide](#development-guide)
13. [Security](#security)
14. [Troubleshooting](#troubleshooting)

---

## Overview

A **zero-cost, self-hosted, Docker-based feedback management system** built for Global Vipassana Pagoda and its departments. The system allows visitors to submit feedback through multiple interfaces (web, tablet kiosks), enables role-based admin access, and automatically generates and emails weekly PDF reports.

### Key Highlights

- **Free & Self-Hosted**: Zero recurring costs using open-source technologies
- **Scalable**: MongoDB + Node.js backend handles high traffic
- **Flexible**: Supports multiple departments with custom questions
- **Automated**: Scheduled weekly reports with PDF generation
- **Secure**: JWT authentication, role-based access, audit logging
- **User-Friendly**: Flutter Web frontend with tablet-optimized UI

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Docker Network                           │
│                                                                   │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐     │
│  │  Frontend   │◄─────┤   Backend   │◄─────┤   MongoDB   │     │
│  │ Flutter Web │      │  Node.js    │      │   Database  │     │
│  │   + Nginx   │      │   Express   │      │             │     │
│  └─────────────┘      └─────────────┘      └─────────────┘     │
│        │                     │                     │             │
│    Port 3030            Port 3001                  │             │
│        │                     │                     │             │
│        │              ┌─────────────┐              │             │
│        │              │   Backup    │──────────────┘             │
│        │              │   Service   │                            │
│        │              └─────────────┘                            │
│        │                     │                                   │
│        │                     │                                   │
└────────┼─────────────────────┼───────────────────────────────────┘
         │                     │
         ▼                     ▼
    Web Browsers          PDF Reports
    (Users/Admins)        Email Service
```

### Component Breakdown

#### 1. Frontend (Flutter Web + Nginx)
- **Technology**: Flutter 3.0+, Dart
- **Build**: Multi-stage Docker build (Flutter → Nginx)
- **Routes**:
  - `/` - Landing page (department selection)
  - `/feedback/:departmentCode` - Feedback form
  - `/thank-you` - Submission confirmation
  - `/admin` - Admin login
  - `/admin/dashboard` - Admin dashboard
- **State Management**: Provider pattern
- **HTTP Client**: `http` package for API calls

#### 2. Backend API (Node.js + Express)
- **Technology**: Node.js 20 LTS, Express 4.x
- **Key Services**:
  - **Authentication**: JWT-based auth with bcrypt password hashing
  - **PDF Generation**: PDFKit + Chart.js for weekly reports
  - **Email Service**: Nodemailer with Gmail OAuth 2.0 / SMTP
  - **Scheduler**: Node-cron for automated report generation
  - **Audit Logging**: Complete activity tracking
- **Middleware**:
  - Helmet.js (Security headers)
  - CORS (Cross-origin requests)
  - Express Rate Limit (Spam prevention)
  - Custom error handler

#### 3. Database (MongoDB 7.x)
- **Collections**:
  - `departments` - Department configurations
  - `users` - Admin accounts
  - `feedback` - Submitted feedback
  - `reportlogs` - Report generation history
  - `auditlogs` - Admin activity tracking
- **Indexes**: Optimized compound indexes for queries
- **Connection**: Internal Docker network only (not exposed)

#### 4. Backup Service
- **Technology**: Bash scripts + mongodump
- **Schedule**: Configurable via cron (default: 3 AM daily)
- **Retention**: Configurable (default: 30 days)
- **Format**: Compressed tar.gz archives

---

## Features

### User Features
- ✅ **Department Selection** - Browse and select departments
- ✅ **Dynamic Forms** - Department-specific questions with different rating types:
  - Star ratings (1-5)
  - Emoji ratings (1-5)
  - Numeric scale (1-10)
- ✅ **Flexible Identity** - Optional name/email or anonymous submission
- ✅ **Access Modes** - Web browser or tablet kiosk mode
- ✅ **Comments** - Optional text feedback (max 2000 chars)
- ✅ **Responsive Design** - Works on desktop, tablet, mobile

### Admin Features
- ✅ **Role-Based Access Control** - Two roles:
  - **Super Admin**: Full access to all departments
  - **Department Admin**: Access to specific department only
- ✅ **Dashboard** - Real-time statistics and insights
- ✅ **Feedback Management** - View, filter, search feedback
- ✅ **User Management** - Create/update admin accounts (super admin only)
- ✅ **Report Scheduling** - Configure weekly report timing per department
- ✅ **Audit Logs** - Track all admin actions

### Automated Features
- ✅ **Weekly Reports** - Auto-generated PDF reports with:
  - Executive summary
  - Question-wise analysis
  - Statistical distributions
  - User comments verbatim
- ✅ **Email Delivery** - Automatic email to configured recipients
- ✅ **Backup Service** - Daily MongoDB backups with retention policy
- ✅ **Health Checks** - Docker health monitoring for all services

---

## Tech Stack

| Component | Technology | Version | Why |
|-----------|-----------|---------|-----|
| **Frontend** | Flutter Web | 3.0+ | Cross-platform UI, single codebase |
| | Dart | 3.0+ | Strong typing, async support |
| | Nginx | Alpine | Fast static file serving |
| **Backend** | Node.js | 20 LTS | Non-blocking I/O, huge ecosystem |
| | Express | 4.18+ | Minimal, flexible web framework |
| | Mongoose | 8.0+ | Elegant MongoDB ODM |
| **Database** | MongoDB | 7.x | Flexible schema, free, production-ready |
| **PDF** | PDFKit | 0.14+ | Server-side PDF generation |
| | Chart.js | 4.4+ | Beautiful charts |
| | Canvas | 2.11+ | Server-side chart rendering |
| **Email** | Nodemailer | 6.9+ | Email sending library |
| | Google APIs | 130+ | Gmail OAuth 2.0 |
| **Scheduler** | node-cron | 3.0+ | Cron-like task scheduling |
| **Security** | bcryptjs | 2.4+ | Password hashing |
| | jsonwebtoken | 9.0+ | JWT token generation |
| | helmet | 7.1+ | Security headers |
| **DevOps** | Docker | 20+ | Containerization |
| | Docker Compose | 3.8+ | Multi-container orchestration |

**Total Cost**: $0 (all open-source + free Gmail API limit: 500 emails/day)

---

## Codebase Structure

```
feedback-system/
├── backend/                      # Node.js REST API
│   ├── src/
│   │   ├── config/               # Configuration files
│   │   │   ├── constants.js      # System constants (departments, roles, types)
│   │   │   ├── database.js       # MongoDB connection setup
│   │   │   └── questions.js      # Department-specific questions
│   │   │
│   │   ├── models/               # Mongoose schemas
│   │   │   ├── User.js           # Admin user schema (with bcrypt)
│   │   │   ├── Department.js     # Department schema (with questions, schedule)
│   │   │   ├── Feedback.js       # Feedback schema (with metadata)
│   │   │   ├── ReportLog.js      # Report generation logs
│   │   │   ├── AuditLog.js       # Admin activity logs
│   │   │   └── index.js          # Model exports
│   │   │
│   │   ├── routes/               # Express routes
│   │   │   ├── auth.js           # Login, logout, /me endpoint
│   │   │   ├── departments.js    # Department listing + questions
│   │   │   ├── feedback.js       # Feedback submission + retrieval
│   │   │   ├── admin.js          # Admin CRUD, dashboard stats
│   │   │   └── reports.js        # Report logs, manual generation
│   │   │
│   │   ├── middleware/           # Express middleware
│   │   │   ├── auth.js           # JWT verification + role checking
│   │   │   ├── validators.js     # Request validation (express-validator)
│   │   │   └── errorHandler.js   # Global error handler
│   │   │
│   │   ├── services/             # Business logic
│   │   │   ├── pdf-service.js    # PDF report generation (PDFKit)
│   │   │   ├── email-service.js  # Email sending (Nodemailer)
│   │   │   ├── scheduler-service.js # Weekly report scheduling (node-cron)
│   │   │   ├── chart-service.js  # Chart generation (Chart.js)
│   │   │   ├── dashboard-service.js # Dashboard statistics
│   │   │   └── permission-service.js # Permission checks
│   │   │
│   │   ├── utils/                # Helper utilities
│   │   │   ├── jwt.js            # JWT token generation/verification
│   │   │   ├── logger.js         # Custom console logger
│   │   │   └── audit.js          # Audit log creation
│   │   │
│   │   ├── scripts/              # Utility scripts
│   │   │   ├── seedDepartments.js # Initialize departments
│   │   │   └── seedAdminUsers.js  # Create admin users
│   │   │
│   │   └── server.js             # Express app entry point
│   │
│   ├── scripts/                  # External scripts
│   │   └── create-admin.js       # CLI to create admin users
│   │
│   ├── Dockerfile                # Multi-stage Docker build
│   ├── package.json              # NPM dependencies
│   └── .dockerignore             # Docker ignore rules
│
├── frontend/                     # Flutter Web App
│   ├── lib/
│   │   ├── main.dart             # App entry + routing
│   │   │
│   │   ├── pages/                # Page widgets
│   │   │   ├── landing_page.dart         # Department selection
│   │   │   ├── feedback_form_page.dart   # Web feedback form
│   │   │   ├── tablet_feedback_form.dart # Tablet-optimized form
│   │   │   ├── thank_you_page.dart       # Submission confirmation
│   │   │   └── admin/
│   │   │       ├── login_page.dart       # Admin login
│   │   │       └── dashboard_page.dart   # Admin dashboard
│   │   │
│   │   ├── widgets/              # Reusable widgets
│   │   │   ├── tablet_widgets.dart       # Tablet UI components
│   │   │   └── tablet_rating_widgets.dart # Rating input widgets
│   │   │
│   │   └── services/             # API integration
│   │       └── api_service.dart  # HTTP client wrapper
│   │
│   ├── web/                      # Web-specific files (index.html, favicon)
│   ├── Dockerfile                # Multi-stage Flutter build + Nginx
│   ├── nginx.conf                # Nginx configuration
│   ├── pubspec.yaml              # Dart dependencies
│   └── .dockerignore             # Docker ignore rules
│
├── backup/                       # Backup Service
│   ├── backup.sh                 # Backup script (mongodump)
│   ├── restore.sh                # Restore script (mongorestore)
│   └── Dockerfile                # Backup container with cron
│
├── scripts/                      # Database initialization
│   └── init-db.js                # MongoDB init script (creates user)
│
├── volumes/                      # Persistent data (git-ignored)
│   ├── mongodb/                  # MongoDB data files
│   ├── backups/                  # Backup archives (.tar.gz)
│   └── reports/                  # Generated PDF reports
│
├── tests/                        # Playwright E2E tests
│   └── feedback-submission.spec.js
│
├── docker-compose.yml            # Multi-container orchestration
├── .env                          # Environment variables (secrets)
├── .gitignore                    # Git ignore rules
├── package.json                  # Root package.json (for tests)
├── playwright.config.js          # Playwright config
└── README.md                     # This file
```

---

## Database Schema

### 1. Users Collection
```javascript
{
  _id: ObjectId,
  email: String,              // Unique, lowercase
  password_hash: String,       // bcrypt hashed (10 rounds)
  role: String,                // 'super_admin' | 'dept_admin'
  department_code: String,     // null for super_admin
  full_name: String,           // Display name
  active: Boolean,             // Account status
  last_login: Date,            // Last login timestamp
  created_at: Date,
  updated_at: Date
}
```

**Indexes**:
- `email` (unique)
- `role`
- `department_code`

### 2. Departments Collection
```javascript
{
  _id: ObjectId,
  code: String,                // Unique identifier (e.g., 'global_pagoda')
  name: String,                // Display name (e.g., 'Global Pagoda')
  description: String,         // Department description
  questions: [                 // Department-specific questions
    {
      key: String,             // Question ID
      label: String,           // Question text
      type: String,            // 'rating_10' | 'smiley_5' | 'binary_yes_no'
      icon: String,            // Icon emoji
      required: Boolean,       // Is required
      order: Number            // Display order
    }
  ],
  email_recipients: [String],  // Email addresses for reports
  report_schedule: {           // Weekly report schedule
    day: Number,               // 0-6 (0 = Sunday)
    hour: Number,              // 0-23
    minute: Number,            // 0-59
    timezone: String           // e.g., 'Asia/Kolkata'
  },
  tablet_config: {             // Tablet display settings
    primary_color: String,     // Hex color
    logo_url: String,          // Logo image URL
    welcome_message: String    // Welcome text
  },
  active: Boolean,             // Department status
  created_at: Date,
  updated_at: Date
}
```

**Indexes**:
- `code` (unique)
- `active`
- `active, code` (compound)

### 3. Feedback Collection
```javascript
{
  _id: ObjectId,
  department_code: String,     // Reference to department
  user_name: String,           // Optional (null if anonymous)
  user_email: String,          // Optional (null if anonymous)
  is_anonymous: Boolean,       // Anonymous flag
  access_mode: String,         // 'web' | 'qr_kiosk' | 'tablet' | 'mobile'
  ratings: Map<String, Number>, // Question ID → Rating value
  comment: String,             // Optional comment (max 2000 chars)
  metadata: {                  // Submission metadata
    ip_address: String,
    user_agent: String,
    submission_time: Date,
    session_id: String,
    device_type: String        // 'tablet' | 'mobile' | 'desktop' | 'unknown'
  },
  created_at: Date
}
```

**Indexes** (CRITICAL for performance):
- `department_code, created_at`
- `department_code, created_at, is_anonymous` (compound)
- `created_at`
- `metadata.ip_address, created_at`
- `is_anonymous`
- `access_mode, created_at`

**Virtual Field**:
- `average_rating` (calculated from ratings map)

### 4. ReportLogs Collection
```javascript
{
  _id: ObjectId,
  department_code: String,     // Which department
  report_type: String,         // 'weekly' | 'monthly'
  status: String,              // 'pending' | 'generating' | 'generated' | 'sent' | 'failed'
  start_date: Date,            // Report period start
  end_date: Date,              // Report period end
  filename: String,            // PDF filename
  filepath: String,            // Full path
  file_size: Number,           // Bytes
  email_sent: Boolean,         // Email success
  email_recipients: [String],  // Recipients
  email_result: Object,        // Email result details
  error_message: String,       // Error if failed
  created_at: Date,
  updated_at: Date
}
```

### 5. AuditLogs Collection
```javascript
{
  _id: ObjectId,
  user_id: ObjectId,           // Admin who performed action
  user_email: String,          // Admin email
  action: String,              // Action description
  resource: String,            // Resource type (e.g., 'user', 'department')
  resource_id: String,         // Resource ID
  details: Object,             // Additional details
  ip_address: String,          // Request IP
  user_agent: String,          // Request user agent
  created_at: Date
}
```

---

## Installation & Setup

### Prerequisites

- **Docker** 20.10+ (with Docker Compose)
- **2GB RAM** minimum (4GB recommended)
- **10GB disk space** (for database + backups)
- **Linux/macOS/Windows** with WSL2

### Quick Start

#### 1. Clone Repository

```bash
cd /path/to/feedback-system
```

#### 2. Configure Environment

The `.env` file contains all configuration. For production, update:

```bash
# Generate secure secrets
openssl rand -base64 32  # Use for JWT_SECRET and MONGO_ROOT_PASSWORD

# Edit .env
MONGO_ROOT_PASSWORD=<strong-password>
JWT_SECRET=<random-32-char-string>

# Email configuration (choose ONE method)
# Option 1: Gmail with App Password (simplest)
GMAIL_USER=your-email@gmail.com
GMAIL_APP_PASSWORD=your-app-password

# Option 2: Generic SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-password
```

**How to get Gmail App Password**:
1. Go to Google Account → Security
2. Enable 2-Step Verification
3. Generate App Password under "App passwords"
4. Use the 16-character password in `GMAIL_APP_PASSWORD`

#### 3. Start Services

```bash
# Build and start all containers
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f backend
```

Expected output:
```
[✓] MongoDB: healthy
[✓] Backend: healthy (port 3001)
[✓] Frontend: healthy (port 3030)
[✓] Backup: running
```

#### 4. Initialize Database

The database is **automatically seeded** with 5 departments:
- Global Pagoda
- Shop
- DPVC (Dhamma Pattana Vipassana Centre)
- Dhammalaya
- Food Court

Create the first super admin:

```bash
docker-compose exec backend node scripts/create-admin.js
```

Follow the prompts:
- Email: `admin@example.com`
- Password: (min 8 chars)
- Full Name: `Admin User`

#### 5. Access the System

- **Frontend**: http://localhost:3030
- **Backend API**: http://localhost:3001/api
- **Health Check**: http://localhost:3001/api/health

---

## API Documentation

### Base URL
```
http://localhost:3001/api
```

### Public Endpoints (No Auth)

#### Health Check
```http
GET /health
```

**Response**:
```json
{
  "success": true,
  "message": "Feedback System API is running",
  "timestamp": "2026-01-25T10:30:00.000Z",
  "environment": "development",
  "uptime": 12345.67
}
```

#### List Departments
```http
GET /departments
```

**Response**:
```json
{
  "success": true,
  "data": [
    {
      "_id": "...",
      "code": "global_pagoda",
      "name": "Global Pagoda",
      "description": "Main meditation and spiritual center",
      "active": true,
      "tablet_config": {
        "primary_color": "#3498db",
        "welcome_message": "We value your feedback!"
      }
    }
  ],
  "count": 5
}
```

#### Get Department Questions
```http
GET /departments/:code
```

**Example**: `GET /departments/global_pagoda`

**Response**:
```json
{
  "success": true,
  "data": {
    "code": "global_pagoda",
    "name": "Global Pagoda",
    "questions": [
      {
        "key": "cleanliness",
        "label": "How would you rate the cleanliness of the premises?",
        "type": "smiley_5",
        "icon": "😊",
        "required": true,
        "order": 1
      }
    ]
  }
}
```

#### Submit Feedback
```http
POST /feedback
Content-Type: application/json
```

**Request Body**:
```json
{
  "department_code": "global_pagoda",
  "user_name": "John Doe",
  "user_email": "john@example.com",
  "is_anonymous": false,
  "access_mode": "web",
  "ratings": {
    "cleanliness": 5,
    "meditation_hall": 5,
    "staff_behavior": 4,
    "facilities": 4,
    "spiritual_atmosphere": 9,
    "guidance": 5,
    "overall_experience": 9
  },
  "comment": "Wonderful experience! Very peaceful."
}
```

**Response**:
```json
{
  "success": true,
  "message": "Feedback submitted successfully",
  "data": {
    "_id": "...",
    "department_code": "global_pagoda",
    "created_at": "2026-01-25T10:30:00.000Z"
  }
}
```

**Rate Limiting**: 10 requests per 15 minutes per IP

### Admin Endpoints (Require JWT)

#### Login
```http
POST /auth/login
Content-Type: application/json
```

**Request**:
```json
{
  "email": "admin@example.com",
  "password": "yourpassword"
}
```

**Response**:
```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "_id": "...",
      "email": "admin@example.com",
      "role": "super_admin",
      "full_name": "Admin User"
    }
  }
}
```

**Token Expiry**: 7 days (configurable via `JWT_EXPIRY`)

#### Get Current User
```http
GET /auth/me
Authorization: Bearer <token>
```

#### Dashboard Statistics
```http
GET /admin/dashboard
Authorization: Bearer <token>
```

**Response**:
```json
{
  "success": true,
  "data": {
    "totalFeedback": 1234,
    "feedbackThisWeek": 89,
    "feedbackToday": 12,
    "averageRating": 4.5,
    "departmentStats": [
      {
        "department": "global_pagoda",
        "count": 456,
        "avgRating": 4.6
      }
    ]
  }
}
```

#### List Feedback
```http
GET /feedback?department_code=global_pagoda&limit=10&skip=0
Authorization: Bearer <token>
```

**Query Parameters**:
- `department_code` (optional): Filter by department
- `limit` (default: 20): Results per page
- `skip` (default: 0): Offset for pagination
- `start_date` (optional): Filter from date
- `end_date` (optional): Filter to date

#### Manage Users (Super Admin Only)
```http
GET /admin/users
POST /admin/users
PUT /admin/users/:id
Authorization: Bearer <token>
```

**Create User**:
```json
{
  "email": "newadmin@example.com",
  "password": "password123",
  "full_name": "New Admin",
  "role": "dept_admin",
  "department_code": "global_pagoda"
}
```

---

## Frontend Guide

### Routes

| Path | Page | Description |
|------|------|-------------|
| `/` | Landing Page | Department selection grid |
| `/feedback/:code` | Feedback Form | Web/tablet feedback form |
| `/thank-you` | Thank You | Post-submission page |
| `/admin` | Admin Login | JWT authentication |
| `/admin/dashboard` | Dashboard | Admin panel with stats |

### API Integration

The `ApiService` class (`frontend/lib/services/api_service.dart`) provides:

```dart
class ApiService {
  static const baseUrl = 'http://localhost:3001/api';

  // Public methods
  Future<List<Department>> fetchDepartments();
  Future<Department> fetchDepartmentDetails(String code);
  Future<void> submitFeedback(FeedbackSubmission data);

  // Admin methods
  Future<LoginResponse> login(String email, String password);
  Future<DashboardStats> fetchDashboardStats(String token);
  Future<List<Feedback>> fetchFeedback(String token, {filters});
}
```

### State Management

Uses **Provider** pattern for dependency injection:

```dart
MultiProvider(
  providers: [
    Provider<ApiService>(create: (_) => ApiService()),
  ],
  child: MaterialApp.router(...)
)
```

Access in widgets:
```dart
final apiService = Provider.of<ApiService>(context, listen: false);
```

### Tablet Mode

Tablet-optimized UI features:
- Larger touch targets (min 60x60 px)
- Emoji-based ratings (visual feedback)
- Auto-submit on completion
- Simplified navigation
- Department-specific theming

---

## Deployment

### Production Checklist

Before deploying to production:

1. **Update `.env`**:
   ```bash
   NODE_ENV=production
   MONGO_ROOT_PASSWORD=<very-strong-password>
   JWT_SECRET=<cryptographically-random-string>
   ```

2. **Configure Email**:
   - Set up Gmail OAuth or SMTP credentials
   - Test email delivery: `docker-compose exec backend node scripts/test-email.js`

3. **Update `docker-compose.yml`**:
   - Uncomment frontend environment variable for production API URL
   - Configure proper domain names

4. **SSL/TLS**:
   - Use a reverse proxy (Nginx/Caddy) for HTTPS
   - Example Caddy config:
     ```
     feedback.yourdomain.org {
       reverse_proxy frontend:80
     }

     api.yourdomain.org {
       reverse_proxy backend:3000
     }
     ```

5. **Firewall**:
   - Only expose ports 80/443 externally
   - Block direct access to MongoDB (27017)

6. **Monitoring**:
   - Set up health check monitoring (UptimeRobot, etc.)
   - Configure log aggregation (e.g., Loki, ELK stack)

### Scaling Considerations

For high traffic (>10,000 feedback/month):

1. **Database Replication**: Use MongoDB replica set
2. **Load Balancing**: Multiple backend instances behind load balancer
3. **Caching**: Add Redis for session storage
4. **CDN**: Serve frontend static files via CDN

---

## Monitoring & Maintenance

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f mongodb
docker-compose logs -f backup
```

### Container Health

```bash
# Check container status
docker-compose ps

# View resource usage
docker stats

# Inspect specific container
docker inspect feedback-backend
```

### Database Management

```bash
# Connect to MongoDB shell
docker-compose exec mongodb mongosh -u feedbackadmin -p

# Use database
use feedback_system

# Show collections
show collections

# Count feedback
db.feedback.countDocuments()

# List departments
db.departments.find().pretty()

# Find recent feedback
db.feedback.find().sort({created_at: -1}).limit(5).pretty()
```

### Manual Backup

```bash
# Trigger backup manually
docker-compose exec backup /usr/local/bin/backup.sh

# List backups
docker-compose exec backup ls -lh /backups
```

### Restore from Backup

```bash
# List available backups
docker-compose exec backup ls -lh /backups

# Restore specific backup
docker-compose exec backup /usr/local/bin/restore.sh 20260123_030000.tar.gz
```

### Report Generation

Reports are automatically generated based on department schedules. To manually generate:

```bash
# Via API (requires admin token)
curl -X POST http://localhost:3001/api/reports/generate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"department_code": "global_pagoda"}'
```

---

## Development Guide

### Local Development (without Docker)

#### Backend
```bash
cd backend
npm install
cp ../.env .env
npm run dev
```

The backend will run on port 3000 with hot reload (nodemon).

#### Frontend
```bash
cd frontend
flutter pub get
flutter run -d chrome --web-port 8080
```

Access at http://localhost:8080

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NODE_ENV` | development | Environment mode |
| `PORT` | 3000 | Backend port |
| `MONGO_URI` | (auto) | MongoDB connection string |
| `JWT_SECRET` | (required) | JWT signing key |
| `JWT_EXPIRY` | 7d | Token expiration |
| `GMAIL_USER` | - | Gmail account |
| `GMAIL_APP_PASSWORD` | - | Gmail app password |
| `RATE_LIMIT_WINDOW_MS` | 900000 | Rate limit window (15 min) |
| `RATE_LIMIT_MAX_REQUESTS` | 10 | Max requests per window |
| `BACKUP_RETENTION_DAYS` | 30 | Backup retention period |

### Adding New Departments

1. **Edit** `backend/src/config/constants.js`:
   ```javascript
   {
     code: 'new_dept',
     name: 'New Department',
     description: 'Department description'
   }
   ```

2. **Add questions** in `backend/src/config/questions.js`:
   ```javascript
   new_dept: [
     {
       id: 'question_1',
       text: 'Your question?',
       type: QUESTION_TYPES.STAR,
       required: true
     }
   ]
   ```

3. **Seed database**:
   ```bash
   docker-compose exec backend node src/scripts/seedDepartments.js
   ```

### Running Tests

```bash
# Install Playwright
npm install

# Run E2E tests
npx playwright test

# Run with UI
npx playwright test --ui
```

---

## Security

### Security Measures

| Feature | Implementation | Notes |
|---------|---------------|-------|
| **Authentication** | JWT tokens (7d expiry) | Stored in localStorage (frontend) |
| **Password Hashing** | bcrypt (10 rounds) | Salt included automatically |
| **Database Access** | Internal network only | Port 27017 not exposed |
| **Rate Limiting** | 10 req/15min per IP | On feedback submission |
| **Security Headers** | Helmet.js | XSS, CSP, HSTS, etc. |
| **CORS** | Configurable origins | Default: allow all (configure for prod) |
| **Input Validation** | express-validator | All API endpoints |
| **Audit Logging** | All admin actions | Stored in auditlogs collection |
| **Docker Security** | Non-root users | All containers run as nodejs/nginx |
| **Secrets** | Environment variables | Never committed to git |

### Security Checklist

Before going live:

- [ ] Change default passwords in `.env`
- [ ] Generate strong JWT secret (32+ chars)
- [ ] Configure CORS to allow only your domain
- [ ] Enable HTTPS with valid SSL certificate
- [ ] Review admin user accounts
- [ ] Test rate limiting
- [ ] Enable firewall (UFW/iptables)
- [ ] Set up automated backups
- [ ] Configure log retention
- [ ] Test backup restoration
- [ ] Review audit logs regularly

### Common Vulnerabilities

The system is protected against:

- ✅ SQL Injection (NoSQL → MongoDB parameterized queries)
- ✅ XSS (Helmet.js CSP headers)
- ✅ CSRF (SameSite cookies, JWT tokens)
- ✅ Brute Force (Rate limiting on login)
- ✅ Password Leaks (bcrypt hashing)
- ✅ Command Injection (No shell execution from user input)
- ✅ Path Traversal (Validated file paths)
- ✅ Mass Assignment (Explicit field validation)

---

## Troubleshooting

### Backend won't start

**Symptom**: Container exits immediately

```bash
# Check logs
docker-compose logs backend

# Common issues:
# 1. MongoDB not ready
docker-compose ps mongodb  # Should show "healthy"

# 2. Environment variables
docker-compose config  # Verify .env is loaded

# 3. Port conflict
lsof -i :3001  # Check if port is in use
```

**Solution**:
```bash
# Restart services in order
docker-compose restart mongodb
docker-compose restart backend
```

### Can't connect to database

**Symptom**: `MongoNetworkError: failed to connect`

```bash
# Check MongoDB health
docker-compose ps mongodb

# Check logs
docker-compose logs mongodb

# Test connection manually
docker-compose exec mongodb mongosh -u feedbackadmin -p
```

**Solution**:
```bash
# Ensure MongoDB is healthy before starting backend
docker-compose up -d mongodb
# Wait 10 seconds
docker-compose up -d backend
```

### Frontend shows "Network Error"

**Symptom**: API calls fail in browser

1. **Check backend health**:
   ```bash
   curl http://localhost:3001/api/health
   ```

2. **Check browser console** for CORS errors

3. **Verify API base URL** in frontend code:
   ```dart
   // frontend/lib/services/api_service.dart
   static const baseUrl = 'http://localhost:3001/api';
   ```

**Solution**:
```bash
# Ensure backend is running
docker-compose ps backend

# Check CORS configuration in backend/src/server.js
```

### Email not sending

**Symptom**: Reports generated but email fails

```bash
# Check email service logs
docker-compose logs backend | grep -i email

# Test email configuration
docker-compose exec backend node -e "
const emailService = require('./src/services/email-service');
emailService.sendWeeklyReport(['test@example.com'], 'Test', {
  filepath: '/app/reports/test.pdf',
  filename: 'test.pdf',
  stats: { totalFeedback: 10, avgRating: 4.5 }
});
"
```

**Common issues**:
1. Invalid Gmail App Password
2. 2FA not enabled on Gmail
3. Missing SMTP credentials

**Solution**:
```bash
# Verify .env credentials
cat .env | grep GMAIL

# Test SMTP connection
docker-compose exec backend node -e "
const nodemailer = require('nodemailer');
const transport = nodemailer.createTransport({
  service: 'gmail',
  auth: {
    user: process.env.GMAIL_USER,
    pass: process.env.GMAIL_APP_PASSWORD
  }
});
transport.verify().then(console.log).catch(console.error);
"
```

### Backup fails

**Symptom**: No backup files in `volumes/backups/`

```bash
# Check backup service logs
docker-compose logs backup

# Check cron schedule
docker-compose exec backup crontab -l

# Run manual backup
docker-compose exec backup /usr/local/bin/backup.sh
```

**Solution**:
```bash
# Verify MongoDB credentials in .env
# Ensure backup service has network access to mongodb
docker-compose exec backup ping mongodb
```

### Port already in use

**Symptom**: `Error starting userland proxy: listen tcp4 0.0.0.0:3001: bind: address already in use`

```bash
# Find process using port
lsof -i :3001
# or
netstat -tulpn | grep 3001

# Kill process
kill -9 <PID>
```

**Alternative**: Change port in `.env`:
```bash
PORT=3002
```

Then update `docker-compose.yml`:
```yaml
ports:
  - "3002:3000"
```

### High Memory Usage

**Symptom**: Container crashes due to OOM

```bash
# Check resource usage
docker stats

# Increase Docker memory limit (Docker Desktop)
# Settings → Resources → Memory → Increase to 4GB
```

For MongoDB specifically:
```yaml
# docker-compose.yml
mongodb:
  deploy:
    resources:
      limits:
        memory: 1G
```

---

## Support & Contributing

### Getting Help

1. **Check logs**: `docker-compose logs -f`
2. **Verify configuration**: `docker-compose config`
3. **Test connectivity**: `docker-compose exec backend curl http://mongodb:27017`
4. **Review this README**: Search for specific issues

### Reporting Issues

When reporting issues, include:
- Operating system & version
- Docker version (`docker --version`)
- Error logs (`docker-compose logs`)
- Steps to reproduce
- Expected vs actual behavior

### License

MIT License - Global Vipassana Pagoda

---

## Quick Reference

### Essential Commands

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f backend

# Restart service
docker-compose restart backend

# Create admin user
docker-compose exec backend node scripts/create-admin.js

# Manual backup
docker-compose exec backup /usr/local/bin/backup.sh

# Access MongoDB shell
docker-compose exec mongodb mongosh -u feedbackadmin -p

# Check health
curl http://localhost:3001/api/health

# View container stats
docker stats
```

### Default Ports

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 3030 | Flutter Web (Nginx) |
| Backend | 3001 | Node.js API |
| MongoDB | - | Internal only (not exposed) |

### Default Credentials

**Admin Account**: Create using `create-admin.js` script (see Installation)

**MongoDB**:
- User: `feedbackadmin` (from `.env`)
- Password: See `MONGO_ROOT_PASSWORD` in `.env`
- Database: `feedback_system`

---

**Last Updated**: 2026-01-25
**Version**: 1.0.0
**Documentation**: Complete
