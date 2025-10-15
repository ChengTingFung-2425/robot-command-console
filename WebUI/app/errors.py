
# imports
from flask import render_template
from . import app, db

# functions
@app.errorhandler(404)
def not_found_error(error):
    """404 Not Found 錯誤處理"""
    return render_template("404.html.j2"), 404

@app.errorhandler(500)
def internal_error(error):
    """500 Internal Server Error 錯誤處理，並回滾資料庫"""
    db.session.rollback()
    return render_template("500.html.j2"), 500
