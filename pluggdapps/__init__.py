# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 Netscale Computing

import pkg_resources as pkg

# Import pluggdapps core
import pluggdapps.const
import pluggdapps.utils       as h
import pluggdapps.config
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
import pluggdapps.cookie
import pluggdapps.errorpage
import pluggdapps.ncloud
import pluggdapps.request
import pluggdapps.resource
import pluggdapps.response
import pluggdapps.rootapp
import pluggdapps.routers
import pluggdapps.views
import pluggdapps.webapp
# Load packages
import pluggdapps.commands

# Initialize plugin data structures
plugin_init()

