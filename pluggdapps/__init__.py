# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

""" 
Pluggdapps, at its core, is a component system in python. It provides a
platform to specify interfaces and implement them as plugins.

Plugins and interfaces can be defined in any number of packages, where
modules containing them are imported by package's `__init__.py` file. When
`pluggdapps` is imported for the first time, it will probe for all packages
in current environment's working set. When finding a package which defines
the following entry-point (refer setuptools to know more about package
entry-points),

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

import imp, sys
import pkg_resources    as pkg
from   os.path          import join

__version__ = '0.42dev'

"""Collect a complete list of pluggdapps packages from python
package-environment and gather them in `papackages`."""
pkgs = pkg.WorkingSet().by_key  # A dictionary of pkg-name and object
papackages = {}
for pkgname, d in list( pkgs.items() ) :
    if not d.get_entry_info( 'pluggdapps', 'package' ) : continue
    papackages.setdefault(
        pkgname, { 'package' : d,
                   'location' : join(d.location, d.project_name),
                 }
    )

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

def package( pa ) :
    """Entry point that returns a dictionary of key,value information about
    the package.

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

def loadpackages():
    packages = list(papackages.keys())
    packages.remove( 'pluggdapps' )
    for pkgname in sorted(packages) :
        if pkgname in sys.modules : continue
        f, path, descr = imp.find_module(pkgname)
        imp.load_module( pkgname, f, path, descr )
    pluggdapps.plugin.plugin_init() # Initialize plugin data structures


def callpackages( pa ):
    """Call `package` entrypoint for each pluggdapps package."""
    for pkgname, info in sorted( papackages.items() ) :
        info = h.call_entrypoint(info['package'], 'pluggdapps', 'package', pa)
        papackages[pkgname].update( info )
    pluggdapps.plugin.plugin_init() # Initialize plugin data structures

