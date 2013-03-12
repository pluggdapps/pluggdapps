# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

"""Package constants. Does not depend on other package modules."""

from os.path import dirname, join

__all__ = [ 
    'DEFAULT_INI',      # Default configuration file to use
    'URLSEP',           # URL separater character
    'SPECIAL_SECS',     # List of special sections in configuration file
]

DEFAULT_INI = join( dirname(__file__), 'confs', 'develop.ini' )
URLSEP      = '/'
SPECIAL_SECS = [ 'pluggdapps', 'mountloc' ]

CONTENT_IDENTITY = 'identity'
CONTENT_GZIP = 'gzip'
