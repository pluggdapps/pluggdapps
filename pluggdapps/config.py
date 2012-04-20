# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

# TODO : 
#   1. Right now all packages in the environment are loaded. Instead filter
#      for pluggdapps packages and load them.

import logging
from   ConfigParser         import SafeConfigParser
from   copy                 import deepcopy

from   pluggdapps.plugin    import default_settings, applications, plugin_info

log = logging.getLogger( __name__ )

def loadsettings( inifile=None ):
    """Load root settings, application settings, and section-wise settings for
    each application. Every plugin will have its own section."""
    from pluggdapps import ROOTAPP
    appsettings = default_appsettings()
    # Override plugin defaults for each application with configuration from its
    # ini-file
    inisettings = load_inisettings( inifile ) if inifile else {}
    for appname, sections in inisettings.items() :
        if appname != ROOTAPP :
            appcls = plugin_info(appname)['cls']
            appcls.normalize_settings( appsettings[appname]['DEFAULT'] )
        for p, sett in sections.items() :
            sett = dict( sett.items() )
            appsettings[appname].setdefault(p, {}).update( sett )
            if p.startswith('plugin:') :
                plugincls = plugin_info(p[7:])['cls']
                plugincls.normalize_settings( appsettings[appname][p] )
    return appsettings

def default_appsettings():
    """Compose `appsettings` from plugin's default settings."""
    from pluggdapps import ROOTAPP
    # Default settings for applications and plugins.
    appdefaults, plugindefaults = { ROOTAPP : {} }, {}
    appnames = applications()
    for p, sett in default_settings().items() :
        sett = dict( sett.items() )
        if p in appnames :
            appdefaults[p] = sett
        else :
            plugindefaults['plugin:%s'%p] = sett
    # Compose `appsettings`
    appsettings = { ROOTAPP : { 'DEFAULT' : {} } }
    appsettings[ROOTAPP].update( deepcopy( plugindefaults ))
    for appname in appnames :
        sett = { 'DEFAULT' : {} }
        sett['DEFAULT'].update( deepcopy( appdefaults[appname] ))
        sett.update( deepcopy( plugindefaults ))
        appsettings[appname] = sett
    return appsettings

def load_inisettings( inifile ):
    """Parse master ini configuration file and its refered ini files to
    construct a dictionary of settings for applications."""
    from pluggdapps import ROOTAPP
    log.info("Loading master configurations from %r", inifile) 
    inisettings, cp = {}, SafeConfigParser()
    cp.read( inifile )
    rootsett = { 'DEFAULT' : cp.defaults() }
    for secname in cp.sections() :
        secname = secname.strip()
        if secname.startswith( 'app:' ) :
            appname = secname[4:].lower() 
            inisettings[appname] = loadapp( dict(cp.items( secname )))
        else :
            rootsett[secname] = deepload( secname, dict( cp.items( secname )))
    inisettings[ROOTAPP] = rootsett
    return inisettings
         

def loadapp( options ):
    """Load application settings and section-wise settings for application
    using `options` from master configuration file. `use` option if present
    will be used to load application configuration."""
    appsett = { 'DEFAULT' : options }
    cp.SafeConfigParser()
    useoption = options.get( 'use', '' )
    if useoption.startswith( 'config', '' ) :
        inifile = useoption.split(':')[1].strip()
        log.info("Loading application configuration file %r", inifile)
        cp.read( inifile )
        appsett['DEFAULT'].update( cp.defaults() )
        appsett.update( dict([ 
            ( sec, deepload( sec, dict( cp.items( sec ))) )
            for sec in cp.sections() ])
        )
    return appsett

def deepload( section, options ):
    """Check for nested configuration file under `use` option in `options`,
    if present parse their default section update this `options`."""
    cp = SafeConfigParser()
    useoption = options.get( 'use', '' )
    if useoption.startswith( 'config:' ) :
        inifile = useoption.split(':')[1].strip()
        log.info("Loading %r section's configuration from %r", inifile)
        cp.read( inifile )
        options.update( cp.defaults() )
    return options

def getsettings( appname, sec=None, plugin=None, key=None ):
    from pluggdapps import appsettings
    sec = sec or ('plugin:'+plugin if plugin else None)
    appsett = appsettings[appname]
    if sec == None :
        if key != None :
            return appsett.get( 'DEFAULT', {} ).get( key, None )
        return appsett
    elif key == None :
        return appsett.get( sec, {} )
    else :
        return appsett.get( sec, {} ).get( key, None )
