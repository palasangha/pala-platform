from flask import Blueprint

def register_blueprints(app):
    """Register all blueprints"""
    from app.routes.auth import auth_bp
    from app.routes.projects import projects_bp
    from app.routes.ocr import ocr_bp
    from app.routes.bulk import bulk_bp
    from app.routes.archipelago import archipelago_bp
    from app.routes.workers import workers_bp
    from app.routes.containers import containers_bp
    from app.routes.files import files_bp
    from app.routes.supervisor import supervisor_bp
    from app.routes.swarm import swarm_bp
    from app.routes.system import system_bp
    from app.routes.langchain_routes import langchain_bp
    from app.routes.ocr_chains import ocr_chains_bp
    from app.routes.images import images_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(projects_bp, url_prefix='/api/projects')
    app.register_blueprint(ocr_bp, url_prefix='/api/ocr')
    app.register_blueprint(bulk_bp)
    app.register_blueprint(archipelago_bp)
    app.register_blueprint(workers_bp)
    app.register_blueprint(containers_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(supervisor_bp)
    app.register_blueprint(swarm_bp)
    app.register_blueprint(system_bp)
    app.register_blueprint(langchain_bp)
    app.register_blueprint(ocr_chains_bp)
    app.register_blueprint(images_bp)
