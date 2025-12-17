# imports
import logging
from logging.handlers import RotatingFileHandler, SMTPHandler
import os
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from flask_babel import Babel
from config import Config

# Database and extensions
db = SQLAlchemy(session_options={"expire_on_commit": False})
migrate = Migrate()
login = LoginManager()
mail = Mail()
bootstrap = Bootstrap()
moment = Moment()
babel = Babel()

# Global app instance for backward compatibility
app = None


def create_app(config_name='default'):
    """Create and configure Flask application instance."""
    global app

    flask_app = Flask(__name__)

    # Ensure proper UTF-8 encoding for JSON responses
    flask_app.config['JSON_AS_ASCII'] = False

    # Enable autoescaping for all templates including .html.j2
    flask_app.jinja_env.autoescape = True
    # Add .j2 extension to autoescape list
    flask_app.jinja_env.autoescape_extensions = ('html', 'htm', 'xml', 'j2', 'html.j2')

    # Apply configuration
    if config_name == 'testing':
        flask_app.config['TESTING'] = True
        flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        flask_app.config['SECRET_KEY'] = 'test-secret-key'
        flask_app.config['WTF_CSRF_ENABLED'] = False
        flask_app.config['LANGUAGES'] = ['en', 'es', 'zh']
    else:
        flask_app.config.from_object(Config)

    # Initialize extensions
    db.init_app(flask_app)
    migrate.init_app(flask_app, db)
    login.init_app(flask_app)
    login.login_view = "webui.login"
    mail.init_app(flask_app)
    bootstrap.init_app(flask_app)
    moment.init_app(flask_app)
    babel.init_app(flask_app)

    # Configure logging (only for non-testing)
    if not flask_app.testing and not flask_app.debug:
        root = logging.getLogger()
        if flask_app.config.get("MAIL_SERVER"):
            auth = None
            if flask_app.config.get('MAIL_USERNAME') or flask_app.config.get('MAIL_PASSWORD'):
                auth = (flask_app.config['MAIL_USERNAME'], flask_app.config['MAIL_PASSWORD'])
            secure = None
            if flask_app.config.get('MAIL_USE_TLS'):
                secure = ()
            mail_handler = SMTPHandler(
                mailhost=(flask_app.config['MAIL_SERVER'], flask_app.config['MAIL_PORT']),
                fromaddr='no-reply@' + flask_app.config['MAIL_SERVER'],
                toaddrs=flask_app.config['ADMINS'], subject='Microblog Failure',
                credentials=auth, secure=secure)
            mail_handler.setLevel(logging.ERROR)
            root.addHandler(mail_handler)

        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/microblog.log', maxBytes=10240,
                                           backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO)
        root.addHandler(file_handler)
        root.setLevel(logging.INFO)
        root.info('Microblog startup')

    @babel.localeselector
    def get_locale():
        return request.accept_languages.best_match(flask_app.config['LANGUAGES'])

    # Register blueprint for WebUI routes
    from WebUI.app.routes import bp as webui_bp
    flask_app.register_blueprint(webui_bp)

    # Register blueprint for Auth API routes
    from WebUI.app.auth_api import auth_api_bp
    flask_app.register_blueprint(auth_api_bp)

    # Register error handlers
    from WebUI.app.errors import register_error_handlers
    register_error_handlers(flask_app)

    # Create app context and update global app
    if app is None:
        app = flask_app

    return flask_app


# Create default app instance for backward compatibility
try:
    app = create_app()
except Exception:
    # If we can't create the app in this context (e.g., during testing),
    # we'll create it explicitly in tests
    pass
