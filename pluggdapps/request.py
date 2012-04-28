# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

import socket, time, urlparse, logging, re
from   copy import deepcopy

from   pluggdapps.config     import ConfigDict
import pluggdapps.helper     as h
from   pluggdapps.compat     import url_quote
from   pluggdapps.plugin     import Plugin, implements, query_plugin
from   pluggdapps.interfaces import IRequest, IResponse, ICookie
from   pluggdapps.parsehttp  import parse_scheme, parse_url, parse_startline,\
                                    parse_remoteip, parse_query, parse_body

log = logging.getLogger( __name__ )

_default_settings = ConfigDict()
_default_settings.__doc__ = \
    "Configuration settings for HTTPRequest implementing IRequest interface."

_default_settings['ICookie']  = {
    'default' : 'httpcookie',
    'types'   : (str,),
    'help'    : "Plugin class implementing ICookie interface specification. "
                "methods from this plugin will be used to process request "
                "cookies. Overrides :class:`ICookie` if defined in "
                "application plugin."
}

class HTTPRequest( Plugin ):
    implements( IRequest )

    do_methods = ('GET', 'HEAD', 'POST', 'DELETE', 'PUT', 'OPTIONS')

    elapsedtime = property( lambda self : time.time() - self.receivedat )

    # IRequest interface methods and attributes
    def __init__( self, conn, address, startline, headers, body ):
        self.receivedat = time.time()
        self.finishedat = None

        xheaders = getattr(conn, 'xheaders', None) if conn else None
        self.connection = conn
        self.platform = conn.platform
        self.docookie = self.query_plugin( 
                ICookie, self['ICookie'] or self.app['ICookie'] )
        
        self.method, self.uri, self.version = parse_startline( startline )
        self.headers = headers or h.HTTPHeaders()
        self.body = body or b""

        scheme = parse_scheme( self.headers, xheaders )
        host = self.headers.get("Host")
        self.host, self.port, self.path, self.query, _ = parse_url(scheme, host)

        self.remote_ip = parse_remoteip( address, self.headers, xheaders )
        self.cookies = self.docookie.parse_cookies( self.headers )
        self.files = {}
        self.arguments = parse_query( query )
        # Updates self.arguments and self.files based on request-body
        args, self.files = self.parse_body( method, self.headers, body )
        self.arguments.update( args )
        # Reponse object
        self.response = self.query_plugin(IResponse, self.app['IResponse'], self)

    def supports_http_1_1( self ):
        return self.version == "HTTP/1.1"

    def get_ssl_certificate(self):
        try    :
            return self.connection.get_ssl_certificate()
        except :
            return None

    def get_argument( self, name, default=None, strip=True ):
        """Returns the value of the argument with the given name.

        If default is not provided, the argument is considered to be
        required, and we throw an exception if it is missing.

        If the argument appears in the url more than once, we return the
        last value.

        The returned value is always unicode.
        """
        args = self.get_arguments( name, strip=strip )
        if args :
            return arg[-1]
        elif default is not None : 
            return default
        else :
            raise Exception( "Missing argument" )

    def get_arguments( self, name, strip=True ):
        """Returns a list of the arguments with the given name.

        If the argument is not present, returns an empty list.

        The returned values are always unicode.
        """
        values = []
        for v in self.arguments.get( name, [] ) :
            v = self.decode_argument( v, name=name )
            if isinstance(v, unicode):
                # Get rid of any weird control chars (unless decoding gave
                # us bytes, in which case leave it alone)
                v = re.sub( r"[\x00-\x08\x0e-\x1f]", " ", v )
            values.append( v.strip() if strip else v )
        return values

    def decode_argument(self, value, name=None):
        """Decodes an argument from the request.

        The argument has been percent-decoded and is now a byte string.
        By default, this method decodes the argument as utf-8 and returns
        a unicode string, but this may be overridden in subclasses.

        This method is used as a filter for both get_argument() and for
        values extracted from the url and passed to get()/post()/etc.

        The name of the argument is provided if known, but may be None
        (e.g. for unnamed groups in the url regex).
        """
        return h.to_unicode( value )

    def get_cookie( self, name, default=None ):
        """Gets the value of the cookie with the given name, else default."""
        return self.cookies[name].value if name in self.cookies else default

    def get_secure_cookie( self, name, value=None ):
        """Returns the given signed cookie if it validates, or None."""
        if value is None :
            value = self.get_cookie(name)
        return self.docookie.decode_signed_value( name, value ) 

    def onfinish( self ):
        """Callback when :meth:`IResponse.finish()` is called."""
        self.connection.finish()
        self.finishedat = time.time()

    def baseurl( self, scheme=None, host=None, port=None ):
        """Construct the base URL upto this application's root path, replacing 
        any of the default scheme, host, or port portions with user-supplied
        variants."""
        host = host or self.host
        port = port or self.port
        url = (scheme or self.scheme) + '://'
        if host :
            url += host
        if port :
            url += ':'+str(port)
        bscript_name = h.utf8( self.app.appscript )
        return url + url_quote( bscript_name, PATH_SAFE )

    def query_plugin( self, *args, **kwargs ):
        query_plugin( self.app, *args, **kwargs )

    def query_plugins( self, *args, **kwargs ):
        query_plugin( self.app, *args, **kwargs )

    def __repr__( self ):
        attrs = ( "scheme", "host", "method", "uri", "version", "remote_ip",
                  "body" )
        args = ", ".join( "%s=%r" % (n, getattr(self, n)) for n in attrs )
        return "%s(%s, headers=%s)" % (
            self.__class__.__name__, args, dict(self.headers))

    # ISettings interface methods
    @classmethod
    def default_settings( cls ):
        return _default_settings

    @classmethod
    def normalize_settings( cls, settings ):
        return settings

