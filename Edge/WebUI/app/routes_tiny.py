from flask import Blueprint, render_template

# Define the blueprint for the tiny routes
tiny_routes = Blueprint('tiny_routes', __name__, url_prefix='/ui')

# Example route
@tiny_routes.route('/')
def index():
    return render_template('index.html')

@tiny_routes.route('/static-test')
def static_test():
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Static Test</title>
        <link rel="stylesheet" href="/static/bootstrap.min.css">
        <link rel="stylesheet" href="/static/all.min.css">
    </head>
    <body>
        <h1>Static Resources Test</h1>
        <button class="btn btn-primary">Bootstrap Button</button>
        <script src="/static/jquery-3.7.0.min.js"></script>
        <script src="/static/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    '''