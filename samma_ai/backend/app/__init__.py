"""
Samma AI Backend - Flask Application Factory
"""

from flask import Flask
from flask_cors import CORS
from flask_pymongo import PyMongo

mongo = PyMongo()


def create_app(config_name='development'):
    """Application factory pattern."""
    app = Flask(__name__)

    # Load configuration
    from config.settings import config
    app.config.from_object(config[config_name])

    # Initialize extensions
    CORS(app, origins=app.config.get('CORS_ORIGINS', ['*']))
    mongo.init_app(app)

    # Register blueprints
    from app.routes.chat import chat_bp
    from app.routes.lookup import lookup_bp
    from app.routes.health import health_bp
    from app.routes.models_routes import models_bp
    from app.routes.agents_routes import agents_bp

    app.register_blueprint(chat_bp, url_prefix='/api')
    app.register_blueprint(lookup_bp, url_prefix='/api')
    app.register_blueprint(health_bp, url_prefix='/api')
    app.register_blueprint(models_bp, url_prefix='/api')
    app.register_blueprint(agents_bp, url_prefix='/api')

    return app
