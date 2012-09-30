# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 Netscale Computing

from   pluggdapps.webapp   import WebApp
import pluggdapps.utils    as h

_default_settings = h.ConfigDict()
_default_settings.__doc__ = \
    "Configuration settings for root web-app."""


class RootApp( WebApp ):

    def onboot( self ):
        super().onboot()

    def shutdown( self ):
        super().shutdown()

    def start( self, request ):
        super().start( request )

    def onfinish( self, request ):
        request.onfinish()
        super().onfinish( request )

    #---- ISettings interface methods

    @classmethod
    def default_settings( cls ):
        return _default_settings

