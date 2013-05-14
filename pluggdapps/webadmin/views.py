# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

import pprint
from   copy                 import deepcopy

from   pluggdapps.platform  import DEFAULT, pluggdapps_defaultsett
from   pluggdapps.plugin    import PluginMeta
import pluggdapps.utils     as h

SPECIAL_SECTIONS = [ 'DEFAULT', 'pluggdapps' ]
"""Only listed special sections are allowed to be configured via web."""

def get_index( request, c ):
    """The index page just shows a list of links to other application 
    functions."""
    response = request.response
    common_context( request, c )
    html = response.render(
                request, c, file='pluggdapps:webadmin/templates/index.ttl' )
    response.write( html )
    response.flush( finishing=True )

def get_html_config( request, c ):
    """Full page to configure application -> sections for all loaded
    applications."""
    response = request.response
    common_context( request, c )
    netpath = request.matchdict['netpath']
    section = request.matchdict['section']
    c['pluginname'] = plugin = h.sec2plugin( section )

    # URL.
    c['url_putconfig'] = \
        request.pathfor( 'updateconfig', netpath=netpath, section=section )
    
    #Context
    c['describe'] = h.conf_descriptionfor( plugin )
    # Gather ConfigDict for DEFAULT section, as a fall back in .ttl file.
    c['DEFAULT'] = DEFAULT()

    # Section settings, TODO : What to do about `here` variables in section.
    setts = deepcopy( h.section_settings( request.pa, netpath, section ))
    c['secsetts'] = ( c['describe'].__doc__, setts )

    # Breadcrumbs
    c['navigate'] = [ (netpath, None), (section, None) ]
    appmenu = [
        ( 'platform',
          request.pathfor('htmlconfig1', netpath='platform', section='DEFAULT')
        )
    ]
    for s in request.pa.netpaths :
        appmenu.append(
            ( s,
              request.pathfor('htmlconfig1', netpath=s, section='DEFAULT')
            ))

    secmenu = []
    for pn in h.netpath_settings( request.pa, netpath ).keys() :
        if pn in ['mountloc'] : continue
        name = h.plugin2sec( pn )
        secmenu.append(
            ( name,
              request.pathfor( 'htmlconfig1', netpath=netpath, section=name )
            ))

    c['crumbsmenu'] = { netpath : appmenu, section : secmenu }

    html = response.render(
                request, c, file='pluggdapps:webadmin/templates/config.ttl' )
    response.write( html )
    response.flush( finishing=True )

def put_config( request, c ):
    response = request.response
    netpath = request.matchdict.get( 'netpath', 'platform' )
    section = request.matchdict.get( 'section', None )
    name = request.params.get( 'key', None )
    value = request.params.get( 'value', None )
    try :
        if name and value :
            name = name[0].strip()
            value = value[0].strip()
            value = value if value != '-' else None
        if name and value :
            request.pa.config(
                    netpath=netpath, section=section, name=name, value=value )
    except :
        request.pa.logerror( h.print_exc() )
        response.set_status(406)
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

def frame_debug( request, c ):
    frame_index = request.webapp.livedebug.frame_index 
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

def common_context( req, c ):
    c['url_jquery'] = req.pathfor( 'staticfiles', path='jquery-1.8.3.min.js' )
    c['url_css'] = req.pathfor( 'staticfiles', path='config.css' )
    c['url_defaultconfig'] = \
        req.pathfor( 'htmlconfig1', netpath='platform', section='DEFAULT' )
    c['interfaces_no'] = len( PluginMeta._interfmap )
    c['plugins_no'] = len( PluginMeta._pluginmap )


