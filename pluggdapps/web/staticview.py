# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

import os, mimetypes
from   os.path          import join, isfile

import pluggdapps.utils             as h
from   pluggdapps.plugin            import Plugin, implements
from   pluggdapps.web.interfaces import IHTTPView

class StaticView( Plugin ):
    """Plugin to serve static files over HTTP."""
    implements( IHTTPView )

    def __init__( self, viewname, view ):
        """:meth:`pluggdapps.web.interfaces.IHTTPView.__init__` interface
        method.
        """
        self.viewname = viewname
        self.view = view

    def __call__( self, request, c ):
        """:meth:`pluggdapps.web.interfaces.IHTTPView.__call__` interface
        method.
        """
        resp = request.response
        assetpath = h.abspath_from_asset_spec( self.view['rootloc'] )
        docfile = join( assetpath, request.matchdict['path'] )

        if docfile and isfile( docfile ) :
            # Collect information about the document, for response.
            resp.set_status( b'200' )
            stat = os.stat( docfile )
            (typ, enc) = mimetypes.guess_type( docfile )
            if typ :
                resp.media_type = typ
            if enc :
                resp.content_coding = enc
            # Populate the context
            c.etag['body'] = open( docfile, 'rb' ).read()
            c['last_modified'] = h.http_fromdate( stat.st_mtime )
            cc = ('public,max-age=%s' % str(self['max_age']) ).encode('utf-8')
            resp.set_header( 'cache_control', cc )
            # Send Response
            resp.write( c['body'] )
            resp.flush( finishing=True )
        else :
            resp.pa.logwarn( "Not found %r" % docfile )
            resp.set_status( b'404' )
            resp.flush( finishing=True )

    def onfinish( self, request ):
        """:meth:`pluggdapps.web.interfaces.IHTTPView.__call__` interface
        method.
        """
        pass

    #---- ISettings interface methods

    @classmethod
    def default_settings( cls ):
        return _default_settings

    @classmethod
    def normalize_settings( cls, sett ):
        sett['max_age'] = h.asint( sett['max_age'] )
        return sett

_default_settings = h.ConfigDict()
_default_settings.__doc__ = StaticView.__doc__

_default_settings['max_age']  = {
    'default' : 60*60*24,   # 1 day
    'types'   : (int,),
    'help'    : "Response max_age in seconds. How long this file can remain "
                "fresh in a HTTP cache."
}

