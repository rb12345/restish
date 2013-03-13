from __future__ import absolute_import, print_function, unicode_literals
__metaclass__ = type

import cgi
import unittest
import webtest

from restish import app, http, url


def make_environ(path='/bar', base_url='http://localhost:1234/foo', **k):
    return http.Request.blank(path, **k).environ


class TestRequestCreation(unittest.TestCase):

    def test_init(self):
        template = http.Request.blank('/').environ
        assert http.Request(template).environ == template

    def test_blank(self):
        assert isinstance(http.Request.blank('/'), http.Request)


class TestRequestAttributes(unittest.TestCase):

    def test_composition(self):
        request = http.Request(make_environ())
        self.assertTrue(request.environ)

    def test_url_types(self):
        request = http.Request(make_environ())
        self.assertTrue(isinstance(request.host_url, url.URL))
        self.assertTrue(isinstance(request.application_url, url.URL))
        self.assertTrue(isinstance(request.application_path, url.URL))
        self.assertTrue(isinstance(request.path_url, url.URL))
        self.assertTrue(isinstance(request.url, url.URL))
        self.assertTrue(isinstance(request.path, url.URL))
        self.assertTrue(isinstance(request.path_qs, url.URL))

    def test_application_path(self):
        r = http.Request.blank('/')
        self.assertEquals(r.application_path, b'')
        r = http.Request.blank('/', base_url='/foo')
        self.assertEquals(r.application_path, b'/foo')
        r = http.Request.blank('/', base_url='/foo/')
        self.assertEquals(r.application_path, b'/foo/')


class TestResponseCreation(unittest.TestCase):

    def test_init_with_bytes(self):
        return http.Response('200 OK', [('Content-Type', 'text/plain')],
                             [b"bytes"])

    def test_init_with_iter(self):
        def gen():
            yield ''
        return http.Response('200 OK', [('Content-Type', 'text/plain')], gen())

    def test_init_with_none(self):
        return http.Response('200 OK', [], None)

    def test_init_with_none_maintains_content_length(self):
        response = http.Response('200 OK', [('Content-Length', 10)], None)
        assert response.headers['Content-Length'] == 10

    def test_no_implicit_headers(self):
        r = http.Response('200 OK', [], None)
        assert r.headers == {'Content-Length': '0'}


class TestSuccessResponseFactories(unittest.TestCase):

    def test_ok(self):
        r = http.ok([('Content-Type', 'text/plain')], [b'Yay!'])
        assert r.status.startswith('200')
        assert r.headers['Content-Type'] == 'text/plain'
        self.assertEqual(r.body, b'Yay!')

    def test_created(self):
        location = b'http://localhost/abc'
        r = http.created(location, [('Content-Type', 'text/plain')],
                         [location])
        assert r.status.startswith('201')
        assert r.headers['Content-Type'] == 'text/plain'
        assert r.headers[b'Location'] == location
        assert r.body == location


class TestRedirectionResponseFactories(unittest.TestCase):

    def test_moved_permanently(self):
        location = b'http://localhost/abc?a=1&b=2'
        r = http.moved_permanently(location)
        # Pass through WebTest for lint-like checks
        webtest.TestApp(app.RestishApp(r)).get('/')
        # Test response details.
        assert r.status.startswith('301')
        assert r.headers['Location'] == location
        assert r.headers['Content-Length']
        assert '301 Moved Permanently' in r.body
        assert cgi.escape(location) in r.body

    def test_moved_permanently_headers(self):
        r = http.moved_permanently(b'/',
                                   headers=[(b'Set-Cookie', b'name=value')])
        # Pass through WebTest for lint-like checks
        webtest.TestApp(app.RestishApp(r)).get('/')
        # Test response details.
        assert r.headers['Location'] == '/'
        assert r.headers['Set-Cookie'] == 'name=value'

    def test_found(self):
        location = b'http://localhost/abc?a=1&b=2'
        r = http.found(location)
        # Pass through WebTest for lint-like checks
        webtest.TestApp(app.RestishApp(r)).get('/')
        # Test response details.
        assert r.status.startswith('302')
        assert r.headers['Location'] == location
        assert r.headers['Content-Length']
        assert '302 Found' in r.body
        assert cgi.escape(location) in r.body

    def test_found_headers(self):
        r = http.found(b'/', [(b'Set-Cookie', b'name=value')])
        # Pass through WebTest for lint-like checks
        webtest.TestApp(app.RestishApp(r)).get('/')
        # Test response details.
        assert r.headers['Location'] == '/'
        assert r.headers['Set-Cookie'] == 'name=value'

    def test_see_other(self):
        location = b'http://localhost/abc?a=1&b=2'
        r = http.see_other(location)
        # Pass through WebTest for lint-like checks
        webtest.TestApp(app.RestishApp(r)).get('/')
        # Test response details.
        assert r.status.startswith('303')
        assert r.headers['Location'] == location
        assert r.headers['Content-Length']
        assert '303 See Other' in r.body
        assert cgi.escape(location) in r.body

    def test_see_other_headers(self):
        r = http.see_other(b'/', [(b'Set-Cookie', b'name=value')])
        # Pass through WebTest for lint-like checks
        webtest.TestApp(app.RestishApp(r)).get('/')
        # Test response details.
        assert r.headers['Location'] == '/'
        assert r.headers['Set-Cookie'] == 'name=value'

    def test_not_modified(self):
        r = http.not_modified()
        assert r.status.startswith('304')
        r = http.not_modified([('ETag', '123')])
        assert r.status.startswith('304')
        assert r.headers['Content-Length'] == '0'
        self.assertEqual(r.body, b'')


class TestClientErrorResponseFactories(unittest.TestCase):

    def test_bad_request(self):
        r = http.bad_request()
        assert r.status.startswith('400')
        assert r.headers[b'Content-Type'] == 'text/plain'
        assert '400 Bad Request' in r.body
        r = http.bad_request([('Content-Type', 'text/html')],
                             b'<p>400 Bad Request</p>')
        assert r.status.startswith('400')
        assert r.headers['Content-Type'] == 'text/html'
        assert r.body == b'<p>400 Bad Request</p>'
        exc = http.BadRequestError()
        r = exc.make_response()
        assert r.status.startswith('400')

    def test_unauthorized(self):
        r = http.unauthorized([('Content-Type', 'text/html')],
                              [b'<p>Unauthorized</p>'])
        assert r.status.startswith('401')
        assert r.headers['Content-Type'] == 'text/html'
        assert r.body == b'<p>Unauthorized</p>'
        exc = http.UnauthorizedError([('Content-Type', 'text/html')],
                                     [b'<p>Unauthorized</p>'])
        r = exc.make_response()
        assert r.status.startswith('401')

    def test_forbidden(self):
        r = http.forbidden()
        assert r.status.startswith('403')
        assert r.headers[b'Content-Type'] == 'text/plain'
        assert b'403 Forbidden' in r.body
        r = http.forbidden([('Content-Type', 'text/html')],
                           b'<p>403 Forbidden</p>')
        assert r.status.startswith('403')
        assert r.headers[b'Content-Type'] == 'text/html'
        assert r.body == b'<p>403 Forbidden</p>'
        exc = http.ForbiddenError()
        r = exc.make_response()
        assert r.status.startswith('403')

    def test_not_found(self):
        r = http.not_found()
        assert r.status.startswith('404')
        assert r.headers[b'Content-Type'] == 'text/plain'
        assert '404 Not Found' in r.body
        r = http.not_found([('Content-Type', 'text/html')],
                           [b'<p>404 Not Found</p>'])
        assert r.status.startswith('404')
        assert r.headers[b'Content-Type'] == 'text/html'
        assert r.body == b'<p>404 Not Found</p>'
        exc = http.NotFoundError()
        r = exc.make_response()
        assert r.status.startswith('404')

    def test_method_not_allowed(self):
        r = http.method_not_allowed('GET, POST')
        assert r.status.startswith('405')
        assert r.headers[b'Content-Type'] == 'text/plain'
        assert r.headers[b'Allow'] == 'GET, POST'
        assert '405 Method Not Allowed' in r.body
        r = http.method_not_allowed(['GET', 'POST'])
        assert r.headers[b'Allow'] == 'GET, POST'
        exc = http.MethodNotAllowedError(['GET', 'POST'])
        r = exc.make_response()
        assert r.status.startswith('405')

    def test_not_acceptable(self):
        r = http.not_acceptable([('Content-Type', 'text/plain')],
                                [b'406 Not Acceptable'])
        assert r.status.startswith('406')
        assert r.headers['Content-Type'] == 'text/plain'
        assert b'406 Not Acceptable' in r.body
        exc = http.NotAcceptableError([('Content-Type', 'text/plain')],
                                      b'406 Not Acceptable')
        r = exc.make_response()
        assert r.status.startswith('406')

    def test_conflict(self):
        r = http.conflict([('Content-Type', 'text/plain')], [b'409 Conflict'])
        assert r.status.startswith('409')
        assert r.headers['Content-Type'] == 'text/plain'
        assert b'409 Conflict' in r.body
        exc = http.ConflictError([('Content-Type', 'text/plain')],
                                 b'409 Conflict')
        r = exc.make_response()
        assert r.status.startswith('409')


class TestServerErrorResponseFactories(unittest.TestCase):

    tests = [
        (http.internal_server_error, http.InternalServerError, [], {}, b'500'),
        (http.bad_gateway, http.BadGatewayError, [], {}, b'502'),
        (http.service_unavailable,
         http.ServiceUnavailableError, [], {}, b'503'),
        (http.gateway_timeout, http.GatewayTimeoutError, [], {}, b'504'),
    ]

    def test_responses(self):
        for func, exc_cls, a, k, status in self.tests:
            r1 = func(*a, **k)
            r2 = exc_cls(*a, **k).make_response()
            self.assertEqual(r1.status[:3], status)
            self.assertEqual(r2.status[:3], status)
            self.assertEqual(r1.headers[b'Content-Type'],
                             r2.headers[b'Content-Type'])
            self.assertEqual(r1.headers[b'Content-Type'], b'text/plain')
            assert status in r1.body and status in r2.body


if __name__ == '__main__':
    unittest.main()
