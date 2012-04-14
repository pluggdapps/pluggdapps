# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

from   pluggdapps.plugincore import Plugin, implements
from   pluggdapps.interfaces import IResponse
import pluggdapps.util       as h

_default_settings = h.ConfigDict()
_default_settings.__doc__ = \
    "Configuration settings for HTTPResponse implementing IResponse interface."

class HTTPResponse( Plugin ):
    implements( IResponse )

    def __init__( self, appname, request ):
        super(Plugin, self).__init__( appname )
        self.connection = request.connection

    def write(self, chunk, callback=None):
        assert isinstance(chunk, bytes)
        self.connection.write( chunk, callback=callback )

    def finish(self):
        self.connection.finish()
        self._finish_time = time.time()

