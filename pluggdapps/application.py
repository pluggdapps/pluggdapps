# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

import logging

from   pluggdapps.plugin     import Plugin, Interface, implements
from   pluggdapps.interfaces import IApplication

log = logging.getLogger(__name__)

_default_settings = h.ConfigDict()
_default_settings.__doc__ = \
    "Configuration settings for Application base class for all applications."

_default_settings['request_factory']  = {
    'default' : 'httprequest',
    'types'   : (str,),
    'help'    : "Request class whose instance will be the single argument "
                "passed on to request handler callable.",
}
_default_settings['response_factory']  = {
    'default' : 'httpresponse',
    'types'   : (str,),
    'help'    : "Response class whose instance will be used to compose http "
                "response corresponding to request generated via "
                "`request_factory` parameter."
}
_default_settings['cookie_secret']  = {
    'default' : 'secure cookie signature',
    'types'   : (str,),
    'help'    : "Use this to sign the cookie value before sending it with the "
                "response."
}

class RootApplication( Plugin ):
    implements( IApplication )

    def boot( self, settings ):
        pass

    def start( self, request ):
        pass

    def router( self, request ):
        pass

    def finish( self, request ):
        pass

    def shutdown( self, settings ):
        pass

    # ISettings interface methods
    @classmethod
    def default_settings( cls ):
        return _default_settings

    @classmethod
    def normalize_settings( cls, settings ):
        return settings

