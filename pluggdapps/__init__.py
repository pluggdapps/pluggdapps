# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

""" 
Pluggdapps, at its core, is a component architecture in python. It provides a
platform to specify interfaces and implement them as plugins.

Plugins and interfaces can be defined by any number of packages, provided
modules containing them are imported by package's `__init__.py` file. When
`pluggdapps` is imported for the first time, it will probe for 
all packages in current environment's working set. When finding a package
which defines the following entry-point (refer setuptools to know more about
package entry-points),

.. code-block:: ini
    :linenos:

    [pluggdapps]
      package=<entry-point>

the package will be considered as pluggdapps compatible and will be imported 
into the environment during platform startup. Corresponding packages must, in
turn, load interfaces and plugins defined by the them. Finally, when all 
packages are loaded (and blueprint for all interface-specs and 
plugin-definitions are gathered) platform will be initialized by calling 
:func:`pluggdapps.plugin.plugin_init`.

The platform gets instantiated, and initialized by calling the platform class'
`boot()` method. Refer to :mod:`pluggdapps.platform` module for more
information on pluggdapps platform and how it gets booted.

**package()** entrypoint. Like mentioned above, every pluggdapps project must
implement `package` entrypoint, a function callabled that will be called
during platform booting. The callable can return a dictionary of information
about the package which is documented in :func:`package` function.

Refer to :ref:`glossary` for terminologies used.
"""

import pkg_resources    as pkg

import pluggdapps.utils as h

# pluggdapps core
import pluggdapps.plugin
import pluggdapps.platform
import pluggdapps.interfaces

# plugins
import pluggdapps.config    # Load plugins for configuration backends.
import pluggdapps.erl       # Load netscale interfaces.
import pluggdapps.commands  # Load pa-script sub-command framework
import pluggdapps.scaffolds # Load scaffolding framework
import pluggdapps.web       # Load web framework

# applications
import pluggdapps.docroot   # Application to serve static files.
import pluggdapps.webadmin  # Application to configure platform through
                            # browser.

__version__ = '0.31dev'

pkgs = pkg.WorkingSet().by_key # A dictionary of pkg-name and object
papackages = {}

def package( pa ) :
    """Entry point that returns a dictionary of key,value information about the
    package.

    ``pa``,
        platform object deriving from :class:`pluggdapps.platform.Pluggdapps`.

    Returns a dictionary of information about the package. Recognised keys
    are,

    ttlplugins,
        list of template files. If package implements tayra template plugins,
        then a list of template files implementing the plugin must be
        supplied in :term:`asset specification` format.
    """
    return {
        'ttlplugins' : []
    }

# A gotcha here !
#   The following lines executed when `pluggdapps` package is imported. As a
#   side-effect, it loops on valid pluggdapps packages to which this package
#   is also part of. Hence, make sure that package() entry-point is defined
#   before executing the following lines.
def loadpackages():
    for pkgname, d in sorted( list( pkgs.items() ), key=lambda x : x[0] ):
        if d.get_entry_info( 'pluggdapps', 'package' ) :
            __import__( pkgname )
    # Initialize plugin data structures
    pluggdapps.plugin.plugin_init()

# Called during actual boot.
def initialize( pa ):
    from  pluggdapps.plugin import PluginMeta
    for pkgname, d in sorted( list( pkgs.items() ), key=lambda x : x[0] ):
        if d.get_entry_info( 'pluggdapps', 'package' ) :
            info = h.call_entrypoint( d,  'pluggdapps', 'package', pa )
            info.setdefault( 'package', d )
            info.setdefault( 'location', d.location )
            papackages[ pkgname ] = info
    # Re-initialize _interfs list for each plugin class, so that plugin_init()
    # will not create duplicate entries.
    [ setattr( info['cls'], '_interfs', [] )
                for nm, info in PluginMeta._pluginmap.items() ]
    # Initialize plugin data structures
    pluggdapps.plugin.plugin_init()

