# Gunicorn & Nginx Flask / Werkzeug ProxyFix Minimal Example

When running Flask apps under gunicorn, it is often desirable to 
place it behind a reverse proxy. Nginx is a popular choice for this.

In some web applications*, it is desirable to run the Flask server
under a path prefix, for example `/api`. Nginx can be configured to ProxyPass
requests made to this URL prefix.

Some API routes may not have an immediate result. In this case, we redirect to
another URL to retrieve results. For redirecting to another route, the 
preferred method is to use `url_for` in Flask. This introduces a problem,
as `url_for` seems to [return absolute URLs](https://stackoverflow.com/a/22707491/1681205) 
for redirects**.

The werkzeug middleware [ProxyFix](https://werkzeug.palletsprojects.com/en/1.0.x/middleware/proxy_fix/)
is the suggested fix to work around this, along with an appropriate [nginx config](https://flask.palletsprojects.com/en/1.1.x/deploying/wsgi-standalone/#proxy-setups)
which passes `X-Forwarded-` headers to inform the WSGI server of the appropriate

```python
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)
```

Without ProxyFix, `url_for` redirects to the wrong address: the internal address
of the server. In the context of this project, this results in a redirect to the URI 
`http://gunicorn:5000`. ProxyFix solves this by building a URL from the constituent 
parts in the `X-Forwarded-` headers. This is achieved using an Nginx location block:

```
location ^~ /api/ {
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $real_scheme;
    proxy_set_header X-Scheme $real_scheme;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header X-Forwarded-Port $server_port;
    proxy_set_header X-Forwarded-Prefix api;

    # Use a trailing slash to trim the /api/ bit: https://serverfault.com/a/562850/172045
    proxy_pass http://gunicorn:5000/;
    proxy_redirect off;
}
```

(It'd be nice if we could just have `url_for` return
a relative URL for a redirect, but I have been unsuccessful in attempts to 
achieve this.***)

However, using ProxyFix has led to some issues. In particular, it 
seems to ignore the `X-Forwarded-Port` directive, even though it is visible
in the HTTP headers received by Flask and the [source code](https://github.com/pallets/werkzeug/blob/0fff5272c481d71b991dff296adb960f674a512a/src/werkzeug/middleware/proxy_fix.py#L154)
definitely checks for and sets variables for this.

Other suggestions include setting `APPLICATION_ROOT` and `SERVER_NAME`. However,
Flask only uses these [when generating URLs outside a request](https://github.com/pallets/flask/issues/3219#issuecomment-496237364)

This repo is a work-in-progress to find a solution, and will be updated in due course. 

---

(*) One example would be using a Vue app with [Vue Router](https://router.vuejs.org/guide/essentials/history-mode.html)
in HTML5 history mode. In that case, all requests other than `/api/` prefixed
requests go to the single page app.

(**) The HTTP RFC for 3xx redirects [was updated](https://tools.ietf.org/html/rfc7231)
in 2014 to permit relative Location URIs redirects with e.g. `303 SEE OTHER`.

(***) [It has been claimed](https://stackoverflow.com/a/12162726/1681205) that
an `_external` keyword needs to be set to return absolute (rather than 
relative) URLS. In my testing, it appears that 3xx redirects always return an 
absolute URL anyway, so the `_external` parameter does nothing.

(****) The development server doesn't handle mounting apps anywhere but the root.
The suggested fix is to use `DispatcherMiddleware` (see link).
This is good to know for debugging, but not useful for production deployment.
[https://github.com/pallets/flask/issues/2759#issuecomment-386887290](https://github.com/pallets/flask/issues/2759#issuecomment-386887290)