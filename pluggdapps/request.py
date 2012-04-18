# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

import Cookie, socket, time, urlparse, logging
from   copy import deepcopy

from   pluggdapps.plugin     import Plugin, implements, pluginname
from   pluggdapps.interfaces import IRequest
from   pluggdapps.evserver   import httpiostream
import pluggdapps.util       as h

log = logging.getLogger( __name__ )

_default_settings = h.ConfigDict()
_default_settings.__doc__ = \
    "Configuration settings for HTTPRequest implementing IRequest interface."

class HTTPRequest( Plugin ):
    implements( IRequest )

    do_methods = ('GET', 'HEAD', 'POST', 'DELETE', 'PUT', 'OPTIONS')

    # IRequest interface methods and attributes
    def __init__( self, appname, app, conn, address, startline, headers, body ):
        Plugin.__init__( self, pluginname(application) )
        if conn :
            stream, xheaders = conn.stream, conn.xheaders
        else :
            stream, xheaders = None, None
        self.application = application
        self.connection = conn
        self.platform = conn.platform
        
        # Startline
        self.method, self.uri, self.version = self._parse_startline(startline)
        # Header
        self.headers = headers or h.HTTPHeaders()
        # Body
        self.body = ""

        self.protocol = self._parse_protocol( stream, headers, xheaders )
        self.remote_ip = self._parse_remoteip( address, headers, xheaders )
        self.host = self.headers.get("Host") or "127.0.0.1"
        self.files = {}
        self.received = time.time()
        self.full_url = self.protocol + "://" + self.host + self.uri

        scheme, netloc, self.path, self.query, fragment = \
                urlparse.urlsplit( native_str(uri) )
        self.arguments = self._parse_query( query )
        # Updates self.arguments and self.files based on request-body
        self._parse_body( method, headers, body ) 

    def _parse_startline( self, startline ):
        method, uri, version = h.parse_startline( startline )
        if version == None :
            log.error( "Malformed HTTP version in HTTP Request-Line" )
        elif method == None :
            log.error( "Malformed HTTP request line" )
        return method, uri, version

    def _parse_protocol( self, stream, hdrs, xheaders ):
        if xheaders : # AWS uses X-Forwarded-Proto
            protocol = hdrs.get("X-Scheme", hdrs.get("X-Forwarded-Proto", None))
            if protocol not in ("http", "https"):
                protocol = "http"
        else :
            if isinstance( stream, httpiostream.SSLIOStream ) :
                protocol = "https"
            else :
                protocol = "http"
        return protocol

    def _parse_remoteip( self, addr, hdrs, xheaders ):
        if xheaders : # Squid uses X-Forwarded-For, others use X-Real-Ip
            remote_ip = hdrs.get("X-Real-Ip", hdrs.get("X-Forwarded-For", addr))
            if not self._valid_ip( remote_ip ):
                remote_ip = address
        else :
            remote_ip = address
        return remote_ip

    def _parse_query( self, query ):
        arguments = {}
        for name, values in parse_qs_bytes(query).iteritems():
            values = filter( None, values )
            if values:
                arguments[name] = values
        return arguments

    def _parse_body( self, method, headers, body ):
        content_type = headers.get( "Content-Type", "" )
        if method in ("POST", "PUT"):
            if content_type.startswith( "application/x-www-form-urlencoded" ):
                _args = h.parse_qs_bytes( h.native_str(body) )
                for name, values in _args.iteritems():
                    values = filter(None, values)
                    if values:
                        self.arguments.setdefault( name, [] ).extend( values )
            elif content_type.startswith("multipart/form-data"):
                fields = content_type.split(";")
                for field in fields:
                    k, sep, v = field.strip().partition("=")
                    if k == "boundary" and v:
                        h.parse_multipart_form_data(
                            h.utf8(v), body, self.arguments, self.files )
                        break
                else:
                    log.warning( "Invalid multipart/form-data" )

    def supports_http_1_1( self ):
        return self.version == "HTTP/1.1"

    @property
    def cookies( self ):
        if not hasattr( self, "_cookies" ):
            self._cookies = Cookie.SimpleCookie()
            if "Cookie" in self.headers:
                try :
                    self._cookies.load( native_str( self.headers["Cookie"]  ))
                except Exception :
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
    @classmethod
    def default_settings( cls ):
        return _default_settings

    @classmethod
    def normalize_settings( cls, settings ):
        return settings

