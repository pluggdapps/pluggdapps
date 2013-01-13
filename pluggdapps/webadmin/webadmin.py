# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy


from   pluggdapps.web.webapp        import WebApp
import pluggdapps.utils             as h

_default_settings = h.ConfigDict()
_default_settings.__doc__ = \
    "Configuration settings for webadmin application "

_default_settings['encoding']  = {
    'default' : 'utf-8',
    'types'   : (str,),
    'help'    : "Default character encoding to use on HTTP response.",
}
_default_settings['language']  = {
    'default' : 'en',
    'types'   : (str,),
    'help'    : "Default language to use for content negotiation."
}
_default_settings['IHTTPRouter']  = {
    'default' : 'WebAdminRouter',
    'types'   : (str,),
    'help'    : "Name of the plugin implementing :class:`IHTTPRouter` "
                "interface. A request is resolved for a view-callable by this "
                "router plugin."
}

class WebAdmin( WebApp ):

    def startapp( self ):
        super().startapp()

    def dorequest( self, request, body=None, chunk=None, trailers=None ):
        super().dorequest( request, body=body, chunk=chunk, trailers=trailers )

    def dochunk( self, request, chunk=None, trailers=None ):
        super().dochunk( request, chunk=chunk, trailers=trailers )

    def onfinish( self, request ):
        super().onfinish( request )

    def shutdown( self ):
        super().shutdown()


    #---- ISettings interface methods

    @classmethod
    def default_settings( cls ):
        return _default_settings

    @classmethod
    def normalize_settings( cls, sett ):
        return sett


