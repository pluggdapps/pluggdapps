# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

"""Package constants. Does not depend on other package modules."""

from os.path import dirname, join

__all__ = [ 
    'DEFAULT_INI',      # Default configuration file to use
    'DEBUG',            # Whether to run platform in debug mode
    'DEFAULT_ENCODING', # Default encoding to convert between bytes and string
    'URLSEP',           # URL separater character
    'ROUTE_PATH_SUFFIX',# Prefix for route configuration
    'MOUNT_TYPES',      # List of mount type tokens
    'SPECIAL_SECS',     # List of special sections in configuration file
]

DEFAULT_INI = join( dirname(__file__), 'confs', 'develop.ini' )
DEFAULT_ENCODING = 'utf8'
DEBUG       = False
URLSEP      = '/'
ROUTE_PATH_SUFFIX = 'remains'
SPECIAL_SECS = [ 'pluggdapps', 'mountloc' ]

CONTENT_IDENTITY = 'identity'
CONTENT_GZIP = 'gzip'
