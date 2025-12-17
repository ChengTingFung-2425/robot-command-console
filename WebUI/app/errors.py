
# imports
from flask import render_template
from . import db


def register_error_handlers(app):
    """Register error handlers with Flask app"""

    @app.errorhandler(404)
    def not_found_error(error):
        """404 Not Found 錯誤處理"""
        return render_template("404.html.j2"), 404

    @app.errorhandler(500)
    def internal_error(error):
        """500 Internal Server Error 錯誤處理，並回滾資料庫"""
        db.session.rollback()
        return render_template("500.html.j2"), 500


# For backward compatibility, try to register with global app if it exists
try:
    from . import app as global_app
    if global_app is not None:
        register_error_handlers(global_app)
except Exception:
    # Ignore import errors during app initialization or testing
    pass
