# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

import pprint

from   pluggdapps.platform  import DEFAULT, pluggdapps_defaultsett,\
                                   mountloc_defaultsett
from   pluggdapps.plugin    import pluginname, PluginMeta
import pluggdapps.utils     as h

def get_index( request, c ):
    response = request.response
    common_url( request, c )
    c['url_config_platform'] = request.pathfor( 
                'htmlconfig1', netpath='platform', section='DEFAULT' )
    html = response.render(
                request, c, file='pluggdapps:webadmin/templates/index.ttl' )
    response.write( html )
    response.flush( finishing=True )

def get_html_config( request, c ):
    response = request.response
    common_url( request, c )
    netpath = request.matchdict['netpath']
    section = request.matchdict['section']
    sec = h.sec2plugin(section) if ':' in section else section
    c['describe'] = PluginMeta._pluginmap[ sec ]
    if netpath == 'platform' :
        c['secsetts'] = request.pa.settings[ section ]
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

def put_config( request, c ):
    pass

def frame_debug( request, c ):
    from pluggdapps.exc.handle import frame_index
    frameid = request.matchdict['frameid']
    response = request.response
    if frameid not in frame_index :
        response.set_status( b'404' )
    else :
        try :
            expression = request.params['expression'][0]
            result = eval( expression, *frame_index[frameid] )
            response.write( pprint.pformat( result ))
        except :
            request.pa.logerror( h.print_exc() )
            response.set_status( b'500' )
    response.flush( finishing=True )


#---- Local functions

def common_url( req, c ):
    c['url_jquery'] = req.pathfor( 'staticfiles', path='jquery-1.8.3.min.js' )
