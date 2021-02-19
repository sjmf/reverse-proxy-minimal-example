from flask import Flask, url_for, Response, request
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)

app.wsgi_app = ProxyFix(app.wsgi_app, x_host=1, x_port=1)


@app.route("/")
def index():
    return """<pre>
url_for("index", _external=True) = {}
HTTP_X_FORWARDED_FOR = {}
HTTP_X_FORWARDED_PROTO = {}
HTTP_X_FORWARDED_HOST = {}
HTTP_X_FORWARDED_PORT = {}
HTTP_X_FORWARDED_PREFIX = {}
        """.format(
            url_for("index", _external=True),
            request.headers.get("X_FORWARDED_FOR"),
            request.headers.get("X_FORWARDED_PROTO"),
            request.headers.get("X_FORWARDED_HOST"),
            request.headers.get("X_FORWARDED_PORT"),
            request.headers.get("X_FORWARDED_PREFIX"))


@app.route('/test', methods=['GET'])
def test():
    return 'See Other', 303, {'Location': url_for('success')}


@app.route('/success', methods=['GET'])
def success():
    return Response("Successfully redirected!", mimetype='text/plain'), 200