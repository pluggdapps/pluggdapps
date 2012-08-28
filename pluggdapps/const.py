# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 Netscale Computing

"""Package constants. Does not depend on other package modules."""

from os.path import dirname, join

__all__ = [ 
    'ROOTAPP',          # Root application name
    'DEFAULT_INI',      # Default configuration file to use
    'DEBUG',            # Whether to run platform in debug mode
    'DEFAULT_ENCODING', # Default encoding to convert between bytes and string
    'DEFAULT_INI',      # Default config file to be used
]

ROOTAPP     = 'rootapp'
DEFAULT_INI = join( dirname(__file__), 'develop.ini' )
DEFAULT_ENCODING = 'utf-8'
DEBUG       = False
URLSEP      = '/'
ROUTE_PATH_SUFFIX = 'remains'
MOUNT_SUBDOMAIN = 'subdomain'
MOUNT_SCRIPT = 'script'
MOUNT_TYPES = [ MOUNT_SUBDOMAIN, MOUNT_SCRIPT ]
DEFAULT_INI = join( dirname(__file__), 'tests', 'confs', 'develop.ini' )
