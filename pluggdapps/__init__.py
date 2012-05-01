# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

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
ROOTAPP = 'rootapp'

settings = {}    # This is a dummy object, use the corresponding app's 
                 # plugin to access its settings
"""Dictionary of plugin configurations for each aplication. The following
gives a hierarchy of configuration sources and its priority.

  * A dictionary of settings will be parsed and populated for every loaded
    application, defined by its plugin. Typical structure of settings
    dictionary will be,

      { 'DEFAULT'    : { <option> : <value>, ... },
        <pluginname> : { <option> : <value>, ... },
        ...
      }

  * Since every application is also a plugin, their default settings, defined
    by :meth:`ISettings.default_settings` will be populated under ``DEFAULT``
    section of the settings dictionary.

  * Similarly, every loaded plugin's default settings will be popluated
    under the corresponding plugin-section of the settings dictionary.

  * Settings in ``DEFAULT`` section can be overridden in the master ini 
    file by,

      [app:<appname>]
        key = value
        ....

  * Master configuration file, also called platform configuration file, can 
    specify separate configuration files for each loaded application like,

     [app:<appname>]
        use = config:<app-ini-file>
    
    and all sections and its configuration inside <app-ini-file> will override
    the default settings.

  * Similar to ini files, settings can also be read from web-admin's backend
    storage. If one is available, then the sections and configuration for a 
    valid application found in the backend storage will override the
    applications settings parsed so far.

  * structure stored in web-admin's backend will be similar to this settings
    dictionary for every valid application.
"""

def package() :
    """Entry point that returns a dictionary of key,value details about the
    package.
    """
    return {}
