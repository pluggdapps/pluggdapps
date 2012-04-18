# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

from   pluggdapps.plugin     import Plugin, implements
from   pluggdapps.interfaces import IResponse
import pluggdapps.util       as h

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
        self.connection = request.connection

    def write(self, chunk, callback=None):
        assert isinstance(chunk, bytes)
        self.connection.write( chunk, callback=callback )

    def finish(self):
        self.connection.finish()
        self._finish_time = time.time()

