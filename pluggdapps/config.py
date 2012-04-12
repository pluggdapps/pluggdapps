# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

# TODO : 
#   1. Right now all packages in the environment are loaded. Instead filter
#      for pluggdapps packages and load them.

from   ConfigParser     import SafeConfigParser

def loadsettings( inifile ):
    """Load root settings, application settings, and section-wise settings for
    each application. Every plugin will have its own section."""
    appsettings, cp = {}, SafeConfigParser()
    cp.read( inifile )
    rootsett = { 'DEFAULT' : cp.defaults() }
    for secname in cp.sections() :
        secname = secname.strip()
        if secname.startswith( 'app:' ) :
            appname = secname[4:].lower() 
            appsettings[appname] = loadapp( dict(cp.options( secname )))
        else :
            rootsett[secname] = deepload( dict( cp.options( secname )))
    appsettings['root'] = rootsett
    return appsettings
         

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
