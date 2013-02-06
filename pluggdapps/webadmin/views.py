# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

import pprint

from   pluggdapps.platform  import DEFAULT, pluggdapps_defaultsett
from   pluggdapps.plugin    import pluginname, PluginMeta
import pluggdapps.utils     as h

SPECIAL_SECTIONS = [ 'DEFAULT', 'pluggdapps' ]
"""Only listed special sections are allowed to be configured via web."""

def get_index( request, c ):
    """The index page just shows a list of links to other application 
    functions."""
    response = request.response
    common_url( request, c )
    html = response.render(
                request, c, file='pluggdapps:webadmin/templates/index.ttl' )
    response.write( html )
    response.flush( finishing=True )

def get_html_config( request, c ):
    """Full page to configure application -> sections for all loaded
    applications."""
    response = request.response
    common_url( request, c )
    c['netpath'] = netpath = request.matchdict['netpath']
    c['section'] = section = request.matchdict['section']
    sec = h.sec2plugin(section) if ':' in section else section
    
    # Gather ConfigDict from the specified `netpath` and `section`
    if section == 'DEFAULT' :
        c['describe'] = DEFAULT()
    elif section == 'pluggdapps' :
        c['describe'] = pluggdapps_defaultsett()
    else :
        c['describe'] = PluginMeta._pluginmap[ sec ].default_settings()

    # Gather ConfigDict for DEFAULT section, as a fall back in .ttl file.
    c['DEFAULT'] = DEFAULT()

    # Section settings.
    if netpath == 'platform' :
        c['secsetts'] = request.pa.settings[ section ]
    else :
        c['secsetts'] = request.pa.netpaths[ netpath ].appsettings[ section ]

    # Breadcrumbs
    pluginnames = list(PluginMeta._pluginmap.keys()) + SPECIAL_SECTIONS
    c['navigate'] = [ (netpath, None), (section, None) ]
    c['crumbsmenu'] = {
        netpath : [
            ( s,
              request.pathfor('htmlconfig1', netpath=s, section='pluggdapps')
            ) for s in request.pa.netpaths ],
        section : [
            ( h.plugin2sec( pn ),
              request.pathfor(
                  'htmlconfig1', netpath=netpath, section=h.plugin2sec(pn) )
            ) for pn in pluginnames ]
    }

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
    from pluggdapps.web.exception import frame_index
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
    c['url_jquery'] = \
        req.pathfor( 'staticfiles', path='jquery-1.8.3.min.js' )
    c['url_defaultconfig'] = \
        req.pathfor( 'htmlconfig1', netpath='platform', section='pluggdapps' )

