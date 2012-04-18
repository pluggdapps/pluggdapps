# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

import httplib, datetime, calendar, email

from   pluggdapps.plugin     import Plugin, implements
from   pluggdapps.interfaces import IResponse
import pluggdapps.util       as h

from tornado import escape
from tornado import locale
from tornado import stack_context
from tornado import template
from tornado.escape import utf8, _unicode
from tornado.util import b, bytes_type, import_object, ObjectDict

# TODO :
#   1. user locale (server side).
#   2. Browser locale.

_default_settings = h.ConfigDict()
_default_settings.__doc__ = \
    "Configuration settings for HTTPResponse implementing IResponse interface."

class HTTPResponse( Plugin ):
    implements( IResponse )

    def __init__( self, appname, request ):
        Plugin.__init__( self, appname )

        self._headers_written = False
        self._finished = False
        self._auto_finish = True
        self._transforms = None  # will be set in _execute

        self.clear()

    def clear( self ):
        """Resets all headers and content for this response."""
        from pluggdapps import __version__
        # The performance cost of ``HTTPHeaders`` is significant
        # (slowing down a benchmark with a trivial handler by more than 10%),
        # and its case-normalization is not generally necessary for
        # headers we generate on the server side, so use a plain dict
        # and list instead.
        self._initialize_headers()
        self._write_buffer = []
        self._status_code = 200

    def set_status( self, status_code ):
        """Sets the status code for our response."""
        assert status_code in httplib.responses
        self._status_code = status_code

    def get_status( self ):
        """Returns the status code for our response."""
        return self._status_code

    def set_header( self, name, value ):
        """Sets the given response header name and value.

        If a datetime is given, we automatically format it according to the
        HTTP specification. If the value is not a string, we convert it to
        a string. All header values are then encoded as UTF-8.
        """
        self._headers[name] = self._convert_header_value(value)

    def add_header( self, name, value ):
        """Adds the given response header and value.

        Unlike `set_header`, `add_header` may be called multiple times
        to return multiple values for the same header.
        """
        self._list_headers.append((name, self._convert_header_value(value)))

    def write( self, chunk, callback=None ):
        assert isinstance(chunk, bytes)
        self.connection.write( chunk, callback=callback )

    def finish( self ):
        self.connection.finish()
        self._finish_time = time.time()
    
    def _initialize_headers( self ):
        self._headers = {
            "Server": "PluggdappsServer/%s" % __version__
            "Content-Type": "text/html; charset=UTF-8",
        }
        self._list_headers = []
        self.set_default_headers()
        if not self.request.supports_http_1_1():
            if self.request.headers.get("Connection") == "Keep-Alive":
                self.set_header("Connection", "Keep-Alive")

    def _convert_header_value( self, value ):
        if isinstance( value, bytes ):
            pass
        elif isinstance( value, unicode ):
            value = value.encode('utf-8')
        elif isinstance( value, (int, long) ):
            # return immediately since we know the converted value will be safe
            return str(value)
        elif isinstance( value, datetime.datetime ):
            t = calendar.timegm( value.utctimetuple() )
            return email.utils.formatdate( t, localtime=False, usegmt=True )
        else:
            raise TypeError( "Unsupported header value %r" % value )
        # If \n is allowed into the header, it is possible to inject
        # additional headers or split the request. Also cap length to
        # prevent obviously erroneous values.
        if len(value) > 4000 or re.match( b"[\x00-\x1f]", value ):
            raise ValueError( "Unsafe header value %r", value )
        return value

