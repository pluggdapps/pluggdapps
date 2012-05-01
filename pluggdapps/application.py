# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

import logging

from   pluggdapps.config     import ConfigDict
from   pluggdapps.plugin     import Plugin, Singleton, Interface, implements
from   pluggdapps.interfaces import IApplication
import pluggdapps.helper     as h

log = logging.getLogger(__name__)

_default_settings = ConfigDict()
_default_settings.__doc__ = \
    "Configuration settings for Application base class for all applications."

_default_settings['debug']  = {
    'default' : False,
    'types'   : (bool,),
    'help'    : "",
}
_default_settings['IRequest']  = {
    'default' : 'httprequest',
    'types'   : (str,),
    'help'    : "Plugin class whose instance will be the single argument "
                "passed on to request handler callable.",
}
_default_settings['IResponse']  = {
    'default' : 'httpresponse',
    'types'   : (str,),
    'help'    : "Plugin class whose instance will be used to compose http "
                "response corresponding to request generated via "
                "`IRequest` parameter."
}
_default_settings['ICookie']  = {
    'default' : 'httpcookie',
    'types'   : (str,),
    'help'    : "Plugin class implementing ICookie interface specification. "
                "methods from this plugin will be used to process both "
                "request cookies and response cookies. This can be overriden "
                "at corresponding request / response plugin settings."
}
_default_settings['IRouter']  = {
    'default' : 'routematch',
    'types'   : (str,),
    'help'    : ""
}

class Application( Singleton ):
    implements( IApplication )

    def onboot( self, settings ):
        pass

    def start( self, request ):
        pass

    def router( self, request ):
        pass

    def onfinish( self, request ):
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


class RootApp( Application ):

    def onboot( self, settings ):
        pass

    def start( self, request ):
        pass

    def router( self, request ):
        pass

    def onfinish( self, request ):
        request.onfinish()

    def shutdown( self, settings ):
        pass

    # ISettings interface methods
    @classmethod
    def default_settings( cls ):
        return _default_settings

    @classmethod
    def normalize_settings( cls, settings ):
        return settings

