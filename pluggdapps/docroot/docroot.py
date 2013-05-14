# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy


from   pluggdapps.web.webapp        import WebApp
from   pluggdapps.web.interfaces    import IHTTPRouter
import pluggdapps.utils             as h

class DocRoot( WebApp ):
    """Application to publish static web sites."""

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


_default_settings = h.ConfigDict()
_default_settings.__doc__ = DocRoot.__doc__

_default_settings['IHTTPRouter']  = {
    'default' : 'pluggdapps.DocRootRouter',
    'types'   : (str,),
    'help'    : "IHTTPRouter plugin to resolve request into view-callables."
}
_default_settings['encoding']  = {
    'default' : 'utf-8',
    'types'   : (str,),
    'help'    : "Default character encoding to use for HTTP response.",
}
_default_settings['favicon'] = {
    'default' : 'favicon.ico',
    'types'   : (str,),
    'help'    : "To use a different file for favorite icon, configure the "
                "file path here. File path must be relative to ``rootloc``."
}
_default_settings['language']  = {
    'default' : 'en',
    'types'   : (str,),
    'help'    : "Default language to use for content negotiation."
}
_default_settings['rootloc'] = {
    'default' : '',
    'types'   : (str,),
    'help'    : "Root location containing the web-site documents."
}
_default_settings['index_page'] = {
    'default' : 'index.html',
    'types'   : (str,),
    'help'    : "Specify the index page for the hosted site."
}

