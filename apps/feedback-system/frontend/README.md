# Flutter Web Frontend

This is the Flutter web frontend for the Feedback Management System.

## Structure

```
lib/
├── main.dart                 # Entry point with routing
├── services/
│   └── api_service.dart     # API client for backend
├── pages/
│   ├── landing_page.dart    # Department selector
│   ├── feedback_form_page.dart  # Dynamic feedback form
│   ├── thank_you_page.dart  # Success page
│   └── admin/
│       ├── login_page.dart  # Admin authentication
│       └── dashboard_page.dart  # Admin dashboard
└── widgets/                 # Reusable components
```

## Features

### Public Pages
- **Landing Page** - Department selection with responsive grid
- **Feedback Form** - Dynamic form based on department questions
  - Star ratings (1-5)
  - Emoji ratings (1-5)
  - Numeric slider (0-10)
  - Anonymous toggle
  - Comment section
- **Thank You Page** - Confirmation with auto-redirect

### Admin Pages
- **Login** - Secure authentication with JWT
- **Dashboard** - Statistics and recent feedback
  - Overview stats (total, avg rating, comments, anonymous)
  - Department-wise breakdown
  - Recent feedback list
  - Recent reports
  - Manual report trigger

## API Integration

All API calls are handled through `ApiService`:
- Base URL: `http://localhost:3001/api` (configurable)
- Endpoints: departments, feedback, auth, admin, reports
- Error handling with user-friendly messages

## Responsive Design

- Mobile-first approach
- Adaptive layouts for:
  - Mobile: Single column
  - Tablet: 2 columns
  - Desktop: 3+ columns
- Touch-friendly UI elements

## Development

```bash
# Get dependencies
flutter pub get

# Run in Chrome
flutter run -d chrome

# Build for web
flutter build web --release
```

## Docker Deployment

The Dockerfile uses multi-stage build:
1. Stage 1: Compile Flutter web with `flutter:stable` image
2. Stage 2: Serve with `nginx:alpine` for minimal footprint

Nginx configuration includes:
- SPA routing (always serve index.html)
- API proxy to backend container
- Gzip compression
- Cache headers for static assets
- Health check endpoint

## Environment Variables

Set `API_URL` during build to change backend URL:
```bash
flutter build web --dart-define=API_URL=https://api.example.com
```

## Browser Support

- Chrome (recommended)
- Firefox
- Safari
- Edge

Note: Uses HTML renderer for better compatibility.
