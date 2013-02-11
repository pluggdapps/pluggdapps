# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

""" 
Pluggdapps in a nutshell :
==========================

Pluggdapps, at its core, is a component architechture in python. It provides a
platform to specify interfaces and define plugins that can implement one or more
interfaces.

Interface,

  An interface specification is a python psuedo-class defining a collection of
  attributes and methods, where methods are mostly used as callbacks and 
  attributes are used to preserve context across callbacks. Once interfaces 
  are defined, they are implemented by one or more plugin classes.

Plugins,

  A plugin class can implement more than one interface. When a plugin 
  implements an interface, it should define methods and attributes specified
  by that interface. Plugin developers must stick to the semantic meaning of
  the interface(s) that the plugin is going to implement.
  Also note that, **every plugin is a dictionary of configuration settings**.
  It is the responsibility of the platform to gather configuration information
  from different sources like ini-file(s) and database, initialize the plugin
  dictionary while instantiating them.

Plugins and interfaces can be defined by any number of packages. Make sure
that the modules containing them are imported by package's __init__.py
file. When `pluggdapps` is imported for the first time, it will probe for 
all packages in current environment's working set. When finding a package
which defines the following entry-point (refer setuptools to know more about
package entry-points),

.. code-block:: ini

    [pluggdapps]
      package=<entry-point>

the package will be considered as pluggdapps compatible and will be imported 
into the environment during platform startup. Corresponding packages must, in
turn, load interfaces and plugins defined by the them. Finally, when all 
packages are loaded (and blueprint for all interface-specs and 
plugin-definitions are gathered) plugin_init() should be called to start
using the plugins.

Platform:
---------

Pluggdapps component architecture is always instantiated in the context of a
platform defined by :class:`pluggdapps.platform.Pluggdapps` or by classes
deriving from :class:`pluggdapps.platform.Pluggdapps`. We expect that most of
the logic written using pluggdapps will, one way or the other, be organised as
plugins. Since all plugins automatically implement
:class:`pluggdapps.plugin.ISettings` interface, a plugin can define
configuration parameters to customize its function and behaviour. It is the
reponsibility of platform classes to aggregate configuration settings from
various sources like .ini files, data-stores during startup and make them
available for plugins when they are instantiated.
"""

import pkg_resources as pkg

import pluggdapps.utils       as h

# pluggdapps core
import pluggdapps.plugin
import pluggdapps.platform
import pluggdapps.interfaces

__version__ = '0.3dev'

papackages = {}

def package( pa ) :
    """Entry point that returns a dictionary of key,value information about the
    package.

    ``pa``,
        platform object deriving from :class:`Pluggdapps`.
    """
    return {
        'ttlplugins' : []
    }

def initialize( pa ):
    for pkgname, d in sorted( list( pkgs.items() ), key=lambda x : x[0] ):
        if d.get_entry_info( 'pluggdapps', 'package' ) :
            info = h.call_entrypoint( d,  'pluggdapps', 'package', pa )
            papackages[ pkgname ] = info
    # Initialize plugin data structures
    pluggdapps.plugin.plugin_init()

import pluggdapps.config    # Load plugins for configuration backends.
import pluggdapps.erl       # Load netscale interfaces.
import pluggdapps.commands  # Load pa-script sub-command framework
import pluggdapps.scaffolds # Load scaffolding framework
import pluggdapps.web       # Load web framework
import pluggdapps.console   # Load console framework

# Load applications
import pluggdapps.docroot   # Application to serve static files.
import pluggdapps.webadmin  # Application to serve static files.

pkgs = pkg.WorkingSet().by_key # A dictionary of pkg-name and object

# A gotcha here !
#   The following lines executed when `pluggdapps` package is imported. As a
#   side-effect, it loops on valid pluggdapps packages to which this package
#   is also part of. Hence, make sure that package() entry-point is defined
#   before executing the following lines.
for pkgname, d in sorted( list( pkgs.items() ), key=lambda x : x[0] ):
    if d.get_entry_info( 'pluggdapps', 'package' ) :
        __import__( pkgname )
# Initialize plugin data structures
pluggdapps.plugin.plugin_init()

