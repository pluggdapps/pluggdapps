# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

import Cookie, socket, time, urlparse
from   copy import deepcopy

from   pluggdapps.plugincore import Plugin, implements, pluginname
from   pluggdapps.interfaces import IRequest
from   pluggdapps.evserver   import httpiostream
import pluggdapps.util       as h

_default_settings = h.ConfigDict()
_default_settings.__doc__ = \
    "Configuration settings for HTTPRequest implementing IRequest interface."

class HTTPRequest( Plugin ):
    implements( IRequest )

    do_methods = ('GET', 'HEAD', 'POST', 'DELETE', 'PUT', 'OPTIONS')

    # IRequest interface methods and attributes
    def __init__( self, appname, connection, method, uri, version, headers,
                  remote_ip, host, protocol, files ):

        super(Plugin, self).__init__( pluginname(application) )
        if connection :
            stream, xheaders = connection.stream, connection.xheaders
        else :
            stream, xheaders = None, None
        self.application = application
        self.connection = connection
        self.platform = connection.platform
        
        # Startline
        self.method, self.uri, self.version = method, uri, version
        # Header
        self.headers = headers or httputil.HTTPHeaders()
        # Body
        self.body = ""

        if xheaders :
            # Squid uses X-Forwarded-For, others use X-Real-Ip
            self.remote_ip = self.headers.get(
                "X-Real-Ip", self.headers.get("X-Forwarded-For", remote_ip))
            if not self._valid_ip(self.remote_ip):
                self.remote_ip = remote_ip
            # AWS uses X-Forwarded-Proto
            self.protocol = self.headers.get(
                "X-Scheme", self.headers.get("X-Forwarded-Proto", protocol))
            if self.protocol not in ("http", "https"):
                self.protocol = "http"
        else :
            self.remote_ip = remote_ip
            if protocol :
                self.protocol = protocol
            elif isinstance(stream, httpiostream.SSLIOStream) :
                self.protocol = "https"
            else :
                self.protocol = "http"
        self.host = host or self.headers.get("Host") or "127.0.0.1"
        self.files = files or {}
        self.received = time.time()
        self.full_url = self.protocol + "://" + self.host + self.uri

        scheme, netloc, path, query, fragment = urlparse.urlsplit(native_str(uri))
        self.path = path
        self.query = query
        arguments = parse_qs_bytes(query)
        self.arguments = {}
        for name, values in arguments.iteritems():
            values = [v for v in values if v]
            if values:
                self.arguments[name] = values

        # Root settings
        self.rootsettings = deepcopy( self.platform.appsettings.get('root', {}) )

    def supports_http_1_1( self ):
        return self.version == "HTTP/1.1"

    @property
    def cookies( self ):
        if not hasattr( self, "_cookies" ):
            self._cookies = Cookie.SimpleCookie()
            if "Cookie" in self.headers:
                try:
                    self._cookies.load( native_str( self.headers["Cookie"]  )
                except Exception:
                    self._cookies = {}
        return self._cookies

    @property
    def elapsedtime( self ):
        return time.time() - self.receivedat

    @property
    def servicetime( self ):
        return time.time() - self.receivedat

    def get_ssl_certificate(self):
        try:
            return self.connection.stream.socket.getpeercert()
        except ssl.SSLError:
            return None

    def __repr__(self):
        attrs = ("protocol", "host", "method", "uri", "version", "remote_ip",
                 "body")
        args = ", ".join(["%s=%r" % (n, getattr(self, n)) for n in attrs])
        return "%s(%s, headers=%s)" % (
            self.__class__.__name__, args, dict(self.headers))

    def _valid_ip(self, ip):
        try:
            res = socket.getaddrinfo(ip, 0, socket.AF_UNSPEC,
                                     socket.SOCK_STREAM,
                                     0, socket.AI_NUMERICHOST)
            return bool(res)
        except socket.gaierror, e:
            if e.args[0] == socket.EAI_NONAME:
                return False
            raise
        return True

    # ISettings interface methods
    def default_settings( self ):
        return _default_settings

    def normalize_settings( self, settings ):
        return settings

