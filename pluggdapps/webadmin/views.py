# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

from   pluggdapps.platform  import DEFAULT, pluggdapps_defaultsett,\
                                   mountloc_defaultsett
from   pluggdapps.plugin    import pluginname, PluginMeta
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
    common_url( request, c )
    c['defaults'] = {}
    for name, info in PluginMeta._pluginmap.items() :
        c['defaults'][ h.plugin2sec(name) ] = info['cls'].default_settings()
        c['defaults'][ 'DEFAULT' ] = DEFAULT()
        c['defaults'][ 'pluggdapps' ] = pluggdapps_defaultsett()
        c['defaults'][ 'mountloc' ] = mountloc_defaultsett()
    c['netpaths'] = request.pa.netpaths
    c['settings'] = request.pa.settings
    html = response.render(
                request, c, file='pluggdapps:webadmin/templates/config.ttl' )
    response.write( html )
    response.flush( finishing=True )

def put_config( request, c ):
    pass


#---- Local functions

def common_url( req, c ):
    c['url_jquery'] = req.pathfor( 'staticfiles', path='jquery-1.8.3.min.js' )
