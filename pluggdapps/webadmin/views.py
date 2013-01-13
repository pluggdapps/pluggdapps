# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

from   pluggdapps.plugin    import pluginname
import pluggdapps.utils     as h

def get_json_config( request, c ):
    response = request.response
    netpath = request.matchdict.get( 'netpath', 'platform' )
    section = request.matchdict.get( 'section', None )
    if netpath == 'platform' :
        settings = request.pa.settings
    else :
        settings = request.pa.netpaths[netpath].appsettings
    setts = settings[section] if section else settings
    json = h.json_encode( setts )
    response.write( json )
    response.flush( finishing=True )

def get_html_config( request, c ):
    response = request.response
    c['netpaths'] = request.pa.netpaths
    c['settings'] = request.pa.settings
    html = response.render( 
                request, c, file='pluggdapps:webadmin/templates/config.ttl' )
    response.write( html )
    response.flush( finishing=True )

def put_config( request, c ):
    pass
