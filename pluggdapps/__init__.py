# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

"""Pluggdapps package.

When `pluggdapps` is loaded, package's init module will probe for other
packages in the current environment's working set, and look up for 

[pluggdapps]
   package=<entry-point>

entry point callable. Upon finding one, it will the corresponding package and 
call the entry point, gathering a dictionary of information about the loaded
package. Meanwhile, the loading of a pluggdapps package itself should load all the
interface and plugin class implemented by that package. Thus, when a call to
plugin_init() is made, which is after calling the `package` entry-point of
all pluggdapps packages, we can expect that a complete system of interfaces
and plugins will be loaded and available for query.
"""

import pkg_resources as pkg

# Import pluggdapps core
import pluggdapps.const
import pluggdapps.utils       as h
import pluggdapps.plugin
import pluggdapps.platform
import pluggdapps.interfaces

from   pluggdapps.plugin      import plugin_init

__version__ = '0.1dev'

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

# Load modules
import pluggdapps.ncloud

# Load packages
import pluggdapps.web
import pluggdapps.commands

# Initialize plugin data structures
plugin_init()

