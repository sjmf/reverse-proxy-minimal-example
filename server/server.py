#!/usr/bin/env python3
import logging
import os

from flask import Flask, Response, url_for, request


# Set up class for configuration
class Config:
    FLASK_ENV = os.environ.get('FLASK_ENV', 'production')
    FLASK_RUN_PORT = os.environ.get('FLASK_RUN_PORT', 5000)
    APPLICATION_ROOT = os.environ.get('PROXY_PATH', '/').strip() or '/'


# Factory function for flask app
def create_app(config_class=Config):
    _app = Flask(__name__)
    _app.config.from_object(config_class)

    # Fix path when running behind a proxy (e.g. nginx, traefik, etc)
    from werkzeug.middleware.proxy_fix import ProxyFix
    _app.wsgi_app = ProxyFix(_app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)

    return _app


app = create_app()
log = app.logger

'''
Application Routes
'''


@app.route('/test', methods=['GET'])
def index():
    return 'REDIRECTING', 303, {'Location': url_for('success')}


@app.route('/success', methods=['GET'])
def success():
    return Response("Success!", mimetype='text/plain'), 200


'''
    Gunicorn logging options. Not run in dev server
'''
if __name__ != '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers.extend(gunicorn_logger.handlers)
    app.logger.setLevel(gunicorn_logger.level)

    app.logger.debug("FLASK_ENV=" + app.config['FLASK_ENV'])
