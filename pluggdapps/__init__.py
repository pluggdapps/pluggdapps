# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

""" 
Pluggdapps in a nutshell :
==========================

Pluggdapps, at its core, is a component architechture in python. It provides a
platform to specify interfaces and define plugins that can implement one or more
interfaces.  An interface specification is a python psuedo-class defining a
collection of attributes and methods, where methods are mostly used as
callbacks and attributes are used to preserve some context across callbacks.
Once interfaces are defined they are implemented by plugin classes. A
plugin class can implement more than one interface. When a plugin implements an
interface, it define methods and attributes specified by that interface. 
Plugin developers must stick to the semantic meaning of the interface(s) that
the plugin is going to implement.

Every plugin is nothing but a dictionary of configuration settings. It is the
responsibility of the platform to instantiate a plugin with its
configuration settings.

Plugins and interfaces can be defined by any number of packages. Make sure
that the modules containing them are imported by the package's __init__.py
file. When `pluggdapps` is imported for the first time, the package's init
module will probe for all packages in current environment's working set. Upon
finding a package which defines the following entry-point (refer setuptools to
know more about package entry-points).::

    [pluggdapps]
      package=<entry-point>

the package will be considered as pluggdapps compatible and load the
package, which in turn should load interfaces and plugins defined by the
package. Finally, when all packages are loaded (and all interface-specs and
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

__version__ = '0.2dev'

def package() :
    """Entry point that returns a dictionary of key,value details about the
    package.
    """
    return {}

# A gotcha here !
#   The following lines executed when `pluggdapps` package is imported. As a
#   side-effect, it loops on valid pluggdapps packages to which this package
#   is also part of. Hence, make sure that package() entry-point is defined
#   before executing the following lines.
packages = []
pkgs = pkg.WorkingSet().by_key # A dictionary of pkg-name and object
for pkgname, d in sorted( list( pkgs.items() ), key=lambda x : x[0] ):
    info = h.call_entrypoint(d,  'pluggdapps', 'package' )
    if info == None : continue
    __import__( pkgname )
    packages.append( pkgname )

import pluggdapps.erl       # Load netscale interfaces.
import pluggdapps.commands  # Load pa-script commands
import pluggdapps.web       # Load web-framework
import pluggdapps.scaffolds # Load web-framework

# Load applications
import pluggdapps.docroot   # Application to serve static files.

# Initialize plugin data structures
pluggdapps.plugin.plugin_init()
