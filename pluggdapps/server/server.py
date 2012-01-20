# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

from BaseHTTPServer import HTTPServer as BaseHTTPServer
from BaseHTTPServer import BaseHTTPRequestHandler
from pluggdapps     import __version__ 

class RequestHandler( BaseHTTPRequestHandler ):
    server_version = 'WSGIServer/pluggdapps/' + __version__
    sys_version = 'Python/' + sys.version.split()[0]

class HTTPServer( BaseHTTPServer ):

    def run( handler=BaseHTTPRequestHandler, ip='127.0.0.1', port='8000' ):
        server_address = (ip, port)
        httpd = server_class( server_address, handler_class )
        httpd.server_forever()
