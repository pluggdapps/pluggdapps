# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# TODO :
#  * Load all interface specifications and plugins defined by this package.

import pkg_resources as pkg

import pluggdapps.plugin
import pluggdapps.interfaces
import pluggdapps.platform
import pluggdapps.commands
import pluggdapps.evserver
import pluggdapps.request
import pluggdapps.response
import pluggdapps.application
import pluggdapps.rootapp

from   pluggdapps.const  import *
import pluggdapps.utils  as h
from   pluggdapps.plugin import plugin_init

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

# Initialize plugin data structures
plugin_init()
