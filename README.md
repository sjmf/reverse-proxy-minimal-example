# Docker, Nginx, Gunicorn and Flask
## A minimal working example using Werkzeug ProxyFix

When running Flask apps under gunicorn, it is often desirable to place it behind 
a reverse proxy. Nginx is a popular choice for this. Further, Docker can be used 
to containerize these apps, separating the nginx container from the gunicorn one
running the web app.

In such web applications [1], it can be desirable to run the Flask server
under a path prefix, for example `/api`. Nginx can be configured to ProxyPass
requests made to this URL prefix.

Further, some API routes may not have an immediate result. In this case, we return a
`30x` redirect to another `Location:` to retrieve results. For assembling this
path string, the preferred method is to use Flask's `url_for` method.

The desired behaviour is as follows:
* User's browser requests http://externalserver:8000/api/
* Flask (under gunicorn) triggers the index `/` route for the application server
* A `30x` redirect is returned to the browser, with the header `Location: 
  http://externalserver:8000/api/result`
* The browser makes a HTTP request to this URL, which triggers the Flask app 
  route `/result`, which returns `200 OK` and the result.

## The Problem
Redirects in Flask always seem to point to 
[absolute URLs](https://stackoverflow.com/a/22707491/1681205) [2]. When running 
under Docker, this URL will be incorrect, as the server builds a URL for the 
internal DNS address of the container:

`http://gunicorn:5000/api/` __(wrong!)__


## Enter ProxyFix
The werkzeug middleware [ProxyFix](https://werkzeug.palletsprojects.com/en/1.0.x/middleware/proxy_fix/)
is the suggested fix (or work-around) for this, along with an appropriate 
[nginx config](https://flask.palletsprojects.com/en/1.1.x/deploying/wsgi-standalone/#proxy-setups)
which passes `X-Forwarded-` headers to inform the WSGI server of the user-facing
server's original address.

```python
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_host=1, x_port=1)
```

ProxyFix attempts to solve this by building a URL from the constituent 
parts in the `X-Forwarded-` headers. This is achieved using an Nginx location block:

```
location ^~ /api/ {
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header X-Forwarded-Port $server_port;

    proxy_pass http://gunicorn:5000/api/;
    proxy_redirect off;
}
```

This example only sets x_host and x_for. The version in the repository sets all
headers supported by ProxyFix: see the files `conf/subsite.conf` and `server.py`
for details. The headers to look for must be declared to ProxyFix and defined
in the nginx config.

I previously used a trailing slash in the nginx config to trim the `/api/` 
bit, per [https://serverfault.com/a/562850/172045](https://serverfault.com/a/562850/172045).
However, [David Lukeš' article on mounting Flask under a URL prefix](https://dlukes.github.io/flask-wsgi-url-prefix.html)
provides an example of how to configure this which explicitly 
recommends against that[3]. It was there that I discovered that providing the 
`SCRIPT_NAME` environment variable will tell Flask to use a URL prefix: 

`SCRIPT_NAME=/api`

## Gotchas
Initially, ProxyFix seemed to _completely ignore_ the `X-Forwarded-Port` directive 
in the redirected-to Location, even though it was visible in the HTTP headers 
received by Flask and the [source code](https://github.com/pallets/werkzeug/blob/0fff5272c481d71b991dff296adb960f674a512a/src/werkzeug/middleware/proxy_fix.py#L172)
shows that it definitely checks for and sets the variables based on this.

If we output the full external URL, using ProxyFix, from url_for, the port is trimmed:

`http://localhost/api/` (:8000 missing!)

This is because nginx (in its Docker container) was _running on port 80_, so `X_FORWARDED_PORT`
was actually set to `:80`. Docker mapped this port to :8000 externally. The 'true' port can 
be mapped using an nginx mapping, per
[https://stackoverflow.com/a/63366106/1681205](https://stackoverflow.com/a/63366106/1681205):

```
map $http_host $port {
    default $server_port;
    "~^[^\:]+:(?<p>\d+)$" $p;
}
```

In production, you may be running on port 80 regardless, so this lack of 
redirection would normally be invisible.

Finally, a similar technique can be used to set the URI scheme to the external one:
[https://serverfault.com/a/516382/172045](https://serverfault.com/a/516382/172045)

```
map $http_x_forwarded_proto $real_scheme {
    default $scheme;
    https "https";
}
```

## Solution
This repo contains a minimal worked example of a Flask app running in this configuration.
I am releasing it into the *public domain* (CC0) to assist others running into similar 
problems when combining docker, nginx, gunicorn and flask.

### Corrections and comments
I appreciate corrections and comments. Please raise them as issues to this repository,
or feel free to submit a pull request if you have found and fixed something that 
doesn't work as intended.

---
### Footnotes

**[1]** One example would be using a Vue app with [Vue Router](https://router.vuejs.org/guide/essentials/history-mode.html)
in HTML5 history mode. In that case, all requests other than `/api/` prefixed
requests go to the single page app.

**[2]** The HTTP RFC for 3xx redirects [was updated](https://tools.ietf.org/html/rfc7231)
in 2014 to permit relative Location URIs redirects with e.g. `303 SEE OTHER`. It'd be 
nice if we could just have `url_for` return a relative URL for a redirect, but I have 
so far been unsuccessful in attempts to achieve this. [It has been claimed](https://stackoverflow.com/a/12162726/1681205) that
an `_external` keyword needs to be set to return absolute (rather than 
relative) URLs. In my testing, it appears that `3xx` redirects always return an 
absolute URL anyway, so setting `_external=False` in `url_for` does nothing.

**[3]** Other suggestions include setting `APPLICATION_ROOT` and `SERVER_NAME`. However,
Flask only uses these [when generating URLs outside a request](https://github.com/pallets/flask/issues/3219#issuecomment-496237364).
NB: The development server doesn't handle mounting apps anywhere but the root.
The [suggested fix is to use `DispatcherMiddleware`](https://github.com/pallets/flask/issues/2759#issuecomment-386887290). 
This problem isn't related. It's good to know for debugging, but not useful for 
production deployment.

