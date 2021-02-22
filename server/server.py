from flask import Flask, url_for, Response, request
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_host=1, x_port=1, x_proto=1, x_prefix=1)


@app.route("/")
def index():
    return "<pre>url_for('index', _external=True) = {}\n\n{}"\
        .format(url_for('index', _external=True), request.headers)


@app.route('/test', methods=['GET'])
def test():
    return 'See Other', 303, {'Location': url_for('success')}


@app.route('/success', methods=['GET'])
def success():
    return Response("Successfully redirected!", mimetype='text/plain'), 200
