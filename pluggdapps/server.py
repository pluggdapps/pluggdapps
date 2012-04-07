# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

from   BaseHTTPServer

from   plugincore   import Plugin, implements
from   interfaces   import IHTTPServer
from   utils        import ConfigDict
                    

class HTTPServer( BaseHTTPServer.HTTPServer ):
    pass


class RequestHandler( BaseHTTPServer.BaseHTTPRequestHandler ):

    def do_HEAD( self ) :
        pass

    def do_GET( self ) :
        pass

    def do_PUT( self ) :
        pass

    def do_POST( self ) :
        pass

    def do_DELETE( self ) :
        pass

    """HTTP methods TRACE and CONNECT are not relevant right now."""


class SimpleServer( Plugin ):
    implements( IHTTPServer )

    def serve( appsettings ):
        rootsett = appsettings['root']
        server_address = (rootsett['host'], rootsett['port'])
        server = HTTPServer( server_address, RequestHanlder )
        server.serve_forever()

    # ISettings interface methods.
    def normalize_settings( self, settings ):
        return settings

    def default_settings():

    def web_admin( self, settings ):
        """Web admin interface is not allowed for this plugin."""
        pass
