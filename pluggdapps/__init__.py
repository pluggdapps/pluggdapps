# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

from   ConfigParser     import SafeConfigParser
from   plugincore       import plugin_init
import pkg_resources    as pkg

# Load all interface specifications defined by this package.
import plugincore
import interfaces
import commands

# TODO : 
#   1. Right now all packages in the environment are loaded. Instead filter
#      for pluggdapps packages and load them.

__version__ = '0.1dev'

appsettings = {}
"""Dictionary of plugin configurations. Note that,

  * Every mountable application is a plugin object implementing
    :class:`IApplication` interface specification.

  * Platform configuration file (master ini file) can specify separate 
    configuration files for each loaded application like,
     [app:*]
        use = <configuration-file>

  * `appsettings` dictionary will have the following structure,
      { <appname> : { 'DEFAULT'    : { <option> : <value>, ... },
                      <pluginname> : { <option> : <value>, ... },
                      ...
                    },
        ...
      }
    where, <appname> is plugin-name implementing :class:`IApplication`
    interface.

  * `appsettings` structure will be populated based on default settings, by
    parsing configuration files (ini files) and web-admin's storage backend.

  * settings in configuration file will override default settings and
    web-admin's settings will override settings from configuration file.

  * structure stored in web-admin's backend will be similar to the
    `appsettings` structure described above.

  * `appsettings` will be populated during platform boot-up time.
"""


def boot( inifile=None ):
    """Boot platform using an optional master configuration file `inifile`."""
    _appsettings = loadsettings( inifile ) if inifile else {}
    rootsett = _appsettings.get( 'root', {} )
    loadpackages( rootsett )
    plugin_init()


def loadsettings( inifile ):
    """Load root settings, application settings, and section-wise settings for
    each application."""
    global appsettings
    cp = SafeConfigParser()
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
    `options` from master configuration file."""
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


def loadpackages( rootsett ) :
    """Import all packages from this python environment."""
    pkgnames = pkg.WorkingSet().by_key.keys()
    [ __import__(pkgname) for pkgname in sorted( pkgnames ) ]
    log.info( "%s pluggdapps packages loaded" % len( _package.keys() ))
