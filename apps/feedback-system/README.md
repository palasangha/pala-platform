# Flutter Web Feedback System

A **zero-cost, self-hosted, Docker-based feedback management system** for Global Vipassana Pagoda and its departments.

## Features

- ✅ **Department-wise Feedback Forms** - 6-7 rating questions + comments
- ✅ **Multiple Rating Types** - Star ratings, emoji ratings, numeric scales
- ✅ **Flexible Access** - Both QR/kiosk mode and regular web access
- ✅ **User Information** - Name + email (mandatory), with anonymous option
- ✅ **Admin Dashboard** - Role-based access (Super Admin + Department Admins)
- ✅ **Automated Reports** - Weekly PDF reports with charts and statistics
- ✅ **Email Delivery** - Gmail OAuth 2.0 integration
- ✅ **Customizable Schedules** - Per-department report timing
- ✅ **Automated Backups** - Daily MongoDB backups with retention
- ✅ **Audit Logging** - Complete activity tracking
- ✅ **Rate Limiting** - Spam prevention on feedback submission

## Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| **Frontend** | Flutter Web | (Phase 3 - Coming soon) |
| **Backend API** | Node.js + Express | Lightweight, async, great MongoDB support |
| **Database** | MongoDB 7.x | Flexible schema, free, production-grade |
| **PDF Generation** | pdfkit + Chart.js | Server-side PDF with charts |
| **Email** | Gmail OAuth 2.0 | Free (500 emails/day) |
| **Containers** | Docker + Compose | Portable, easy deployment |

**Total Cost**: $0 (all open-source + free Gmail API)

## Project Structure

```
feedback-system/
├── backend/              # Node.js REST API
│   ├── src/
│   │   ├── config/       # Database, constants, questions
│   │   ├── models/       # Mongoose schemas
│   │   ├── routes/       # API routes
│   │   ├── middleware/   # Auth, validation, errors
│   │   ├── services/     # PDF, email (Phase 2)
│   │   ├── utils/        # JWT, logger, audit
│   │   └── server.js     # Entry point
│   ├── scripts/          # create-admin.js
│   ├── Dockerfile
│   └── package.json
│
├── frontend/             # Flutter Web (Phase 3)
├── backup/               # Backup service
│   ├── backup.sh
│   ├── restore.sh
│   └── Dockerfile
│
├── scripts/              # DB initialization
│   └── init-db.js
│
├── volumes/              # Persistent data
│   ├── mongodb/
│   ├── backups/
│   └── reports/
│
├── docker-compose.yml
├── .env
└── README.md
```

## Quick Start

### Prerequisites

- Docker & Docker Compose (v20.10+)
- 2GB RAM minimum
- 10GB disk space

### 1. Clone/Setup

```bash
cd feedback-system
```

### 2. Environment Configuration

The `.env` file is already configured with development defaults. For production, update:

```bash
# Generate secure secrets
MONGO_ROOT_PASSWORD=<strong-password>
JWT_SECRET=<random-32-char-string>

# Gmail OAuth (see docs/GMAIL_OAUTH_SETUP.md)
GMAIL_CLIENT_ID=your-client-id.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=your-client-secret
GMAIL_REFRESH_TOKEN=your-refresh-token
GMAIL_FROM_EMAIL=noreply@yourdomain.org
```

### 3. Start Services

```bash
# Build and start all containers
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f backend
```

### 4. Initialize Database & Create Admin

The database is automatically initialized with 5 departments:
- Global Pagoda
- Souvenir Store
- DPVC
- Dhammalaya
- Food Court

Create the first super admin:

```bash
docker-compose exec backend node scripts/create-admin.js
```

Follow the prompts to enter:
- Email
- Password (min 8 chars)
- Full Name

### 5. Test the API

```bash
# Health check
curl http://localhost:3000/api/health

# List departments
curl http://localhost:3000/api/departments

# Login
curl -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"yourpassword"}'
```

## API Endpoints

### Public Endpoints

```
GET    /api/health                  - Health check
GET    /api/departments             - List all active departments
GET    /api/departments/:code       - Get department with questions
POST   /api/feedback                - Submit feedback (rate-limited)
```

### Admin Endpoints (Require JWT)

```
POST   /api/auth/login              - Admin login
GET    /api/auth/me                 - Get current user
POST   /api/auth/logout             - Logout

GET    /api/admin/dashboard         - Dashboard statistics
GET    /api/admin/users             - List admins (super admin only)
POST   /api/admin/users             - Create admin (super admin only)
PUT    /api/admin/users/:id         - Update admin (super admin only)

GET    /api/feedback                - List feedback (filtered by role)
GET    /api/feedback/:id            - Get feedback details
GET    /api/feedback/stats/summary  - Get statistics

PUT    /api/admin/schedule/:dept    - Update report schedule
GET    /api/admin/reports           - List report logs
```

## Feedback Submission Example

```bash
curl -X POST http://localhost:3000/api/feedback \
  -H "Content-Type: application/json" \
  -d '{
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
    "comment": "Wonderful experience! The meditation hall is very peaceful."
  }'
```

## Admin Authentication Example

```bash
# 1. Login
TOKEN=$(curl -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"yourpassword"}' \
  | jq -r '.data.token')

# 2. Get dashboard stats
curl http://localhost:3000/api/admin/dashboard \
  -H "Authorization: Bearer $TOKEN"

# 3. List feedback
curl "http://localhost:3000/api/feedback?department_code=global_pagoda&limit=10" \
  -H "Authorization: Bearer $TOKEN"
```

## Department Management

### View Departments

```bash
curl http://localhost:3000/api/departments | jq
```

### Get Department Questions

```bash
curl http://localhost:3000/api/departments/global_pagoda | jq
```

## Backup & Restore

### Automatic Backups

Backups run daily at 3 AM (configured in `.env`). View backups:

```bash
docker-compose exec backup ls -lh /backups
```

### Manual Backup

```bash
docker-compose exec backup /usr/local/bin/backup.sh
```

### Restore from Backup

```bash
# List available backups
docker-compose exec backup ls -lh /backups

# Restore specific backup
docker-compose exec backup /usr/local/bin/restore.sh 20260123_030000.tar.gz
```

## Monitoring

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f mongodb
docker-compose logs -f backup
```

### Container Status

```bash
docker-compose ps
docker stats
```

### Database Access

```bash
# MongoDB shell
docker-compose exec mongodb mongosh -u feedbackadmin -p

# Show databases
use feedback_system
show collections
db.feedback.count()
db.departments.find().pretty()
```

## Stopping Services

```bash
# Stop containers (keep data)
docker-compose down

# Stop and remove volumes (DELETES ALL DATA)
docker-compose down -v
```

## Development

### Run Backend Locally (without Docker)

```bash
cd backend
npm install
cp ../.env .env
npm run dev
```

### Hot Reload (Development)

The docker-compose.yml mounts `backend/src` for hot reloading in development mode.

## Troubleshooting

### Backend won't start

```bash
# Check MongoDB is healthy
docker-compose ps
docker-compose logs mongodb

# Check environment variables
docker-compose config
```

### Can't connect to database

```bash
# Ensure MongoDB is running
docker-compose up -d mongodb
docker-compose logs mongodb

# Test connection
docker-compose exec mongodb mongosh -u feedbackadmin -p
```

### Port already in use

```bash
# Find process using port 3000
lsof -i :3000
# or
netstat -tulpn | grep 3000

# Kill process or change PORT in .env
```

## Security Checklist

- ✅ MongoDB not exposed externally (internal Docker network only)
- ✅ JWT authentication with expiry
- ✅ Password hashing with bcrypt (10 rounds)
- ✅ Rate limiting on feedback submission
- ✅ Helmet.js security headers
- ✅ CORS configuration
- ✅ Input validation & sanitization
- ✅ Non-root Docker users
- ✅ Audit logging for admin actions

## Next Steps (Phase 2 & 3)

- [ ] **Phase 2**: PDF generation + email service
- [ ] **Phase 3**: Flutter Web frontend
- [ ] **Phase 4**: Admin dashboard UI
- [ ] **Phase 5**: Complete Docker integration
- [ ] **Phase 6**: Production deployment guide

## Support

For issues or questions:
1. Check logs: `docker-compose logs -f`
2. Verify .env configuration
3. Ensure all containers are running: `docker-compose ps`

## License

MIT License - Global Vipassana Pagoda
