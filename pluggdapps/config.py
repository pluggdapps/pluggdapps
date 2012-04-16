# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

# TODO : 
#   1. Right now all packages in the environment are loaded. Instead filter
#      for pluggdapps packages and load them.

from   ConfigParser         import SafeConfigParser

from   pluggdapps.plugin    import default_settings, applications, plugin_info

def loadsettings( inifile={} ):
    """Load root settings, application settings, and section-wise settings for
    each application. Every plugin will have its own section."""
    inisettings = load_inisettings( inifile ) if inifile else {}
    # Initialize appsettings with plugin defaults.
    defsettings = default_settings()
    appsettings = { 'root' : { 'DEFAULT' : {} } }
    for appname in applications() :
        appsettings[appname] = { 'DEFAULT' : {} }
        appsettings[appname].update( defsettings )
    # Override plugin defaults for each application with configuration from its
    # ini-file
    for appname, sections in inisettings.items() :
        for p, sett in sections.items() :
            appsettings[appname].setdefault(p, {}).update( sett )
            plugin_info(p)['cls'].normalize_settings( appsettings[appname][p] )
    return appsettings


def load_inisettings( inifile ):
    inisettings, cp = {}, SafeConfigParser()
    cp.read( inifile )
    rootsett = { 'DEFAULT' : cp.defaults() }
    for secname in cp.sections() :
        secname = secname.strip()
        if secname.startswith( 'app:' ) :
            appname = secname[4:].lower() 
            inisettings[appname] = loadapp( dict(cp.options( secname )))
        else :
            rootsett[secname] = deepload( dict( cp.options( secname )))
    inisettings['root'] = rootsett
    return inisettings
         

def loadapp( options ):
    """Load application settings and section-wise settings for application
    using `options` from master configuration file. `use` option if present
    will be used to load application configuration."""
    appsett = { 'DEFAULT' : options }
    cp.SafeConfigParser()
    useoption = options.get( 'use', '' )
    if useoption.startswith( 'config', '' ) :
        cp.read( useoption.split(':')[1].strip() )
        appsett['DEFAULT'].update( cp.defaults() )
        appsett.update( dict([ 
            ( sec, deepload( dict( cp.options( sec ))) )
            for sec in cp.sections() ])
        )
    return appsett


def deepload( options ) :
    """Check for nested configuration file under `use` option in `options`,
    if present parse their default section update this `options`."""
    cp = SafeConfigParser()
    useoption = options.get( 'use', '' )
    if useoption.startswith( 'config:' ) :
        cp.read( useoption.split(':')[1].strip() )
        options.update( cp.defaults() )
    return options
