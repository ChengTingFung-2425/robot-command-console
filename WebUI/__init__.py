# WebUI 套件初始化
# Note: Import only necessary modules here
# routes, models, errors will be imported as needed by create_app()
try:
    from WebUI.app import models, email, forms, logging_monitor  # noqa: F401
except ImportError:
    # Allow imports to fail during test setup
    pass
