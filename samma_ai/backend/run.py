"""
Samma AI Backend - Application Entry Point
"""

import os
from app import create_app

# Get environment from env var, default to development
env = os.environ.get('FLASK_ENV', 'development')
app = create_app(env)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    debug = env == 'development'

    print(f"""
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    🧘 Samma AI Backend
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    Environment: {env}
    Port: {port}
    Debug: {debug}

    Endpoints:
      POST /api/chat     - Chat with Samma AI
      GET  /api/lookup   - Pali word lookup
      GET  /api/sutta    - Fetch sutta by reference
      GET  /api/search   - Full-text search
      GET  /api/health   - Health check
      GET  /api/status   - Detailed status
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """)

    app.run(host='0.0.0.0', port=port, debug=debug)
