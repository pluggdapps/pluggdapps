# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

# Load all interface specifications and plugins defined by this package.
import pluggdapps.platform
import pluggdapps.interfaces
import pluggdapps.plugin
import pluggdapps.commands
import pluggdapps.evserver
import pluggdapps.request
import pluggdapps.response
import pluggdapps.application

__version__ = '0.1dev'
ROOTAPP = 'root'

appsettings = { 'root' : {} }
"""Dictionary of plugin configurations. Note that,

  * Every mountable application is a plugin object implementing
    :class:`IApplication` interface specification.

  * Platform configuration file (master ini file) can specify separate 
    configuration files for each loaded application like,
     [app:<appname>]
        use = config:<ini-file>

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


def package( appsettings ) :
    """Entry point that returns a dictionary of key,value details about the
    package.
    """
    return {}
