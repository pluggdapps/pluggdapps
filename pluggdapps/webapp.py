# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 Netscale Computing

from   urllib.parse import urljoin

from   pluggdapps.config     import ConfigDict
from   pluggdapps.plugin     import implements, IWebApp, query_plugin, \
                                    isimplement, Plugin
from   pluggdapps.interfaces import IController, IRouter
import pluggdapps.utils as h

_default_settings = ConfigDict()
_default_settings.__doc__ = \
    "Configuration settings for WebApp base class inherited by all " \
    "pluggdapps web-applications."

_default_settings['irequest']  = {
    'default' : 'httprequest',
    'types'   : (str,),
    'help'    : "Plugin class whose instance will be the single argument "
                "passed on to request handler callable.",
}
_default_settings['iresponse']  = {
    'default' : 'httpresponse',
    'types'   : (str,),
    'help'    : "Plugin class whose instance will be used to compose http "
                "response corresponding to request generated via "
                "`IRequest` parameter."
}
_default_settings['icookie']  = {
    'default' : 'httpcookie',
    'types'   : (str,),
    'help'    : "Plugin class implementing ICookie interface specification. "
                "methods from this plugin will be used to process both "
                "request cookies and response cookies. This can be overriden "
                "at corresponding request / response plugin settings."
}
_default_settings['irouter']  = {
    'default' : 'routeandmatch',
    'types'   : (str,),
    'help'    : "Plugin name implement :class:`IRouter` interface. A request "
                "is routed through IRouter plugins until a view callable is "
                "resolved and finally dispatched to it."
}

class WebApp( Plugin ):
    implements( IWebApp )

    def onboot( self ):
        """Inheriting plugins should not forget to call its super() method."""
        self.router = query_plugin( self, IRouter, self['irouter'] )
        self.router.onboot()

    def shutdown( self ):
        pass

    def start( self, request ):
        c = request.response.context
        view = self.router.route( request, c )
        if isimplement(view, IController) :
            meth = hasattr( view, request.method, None )
            if meth :
                meth( request, c )
            else :
                view( request, c )
        elif callable( view ):
            view( request, c )
        else :
            raise h.Error( "Unknown view %r" % view )

    def onfinish( self, request ):
        pass

    def urlfor( self, appname, request, name, *traverse, **matchdict ):
        if appname :
            baseurl = self.pa.baseurl( request, appname=appname )
        else :
            baseurl = request.baseurl
        relurl = self.pathfor( request, name, *traverse, **matchdict )
        return urljoin( baseurl, relurl )

    def pathfor( self, request, name, *traverse, **matchdict ):
        query = matchdict.pop( '_query', None )
        anchor = matchdict.pop( '_anchor', None )
        path = self.router.genpath( request, name, *traverse, **matchdict )
        return make_url( None, path, query, fragment )

    #---- ISettings interface methods

    @classmethod
    def default_settings( cls ):
        return _default_settings

