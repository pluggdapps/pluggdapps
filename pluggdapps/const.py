# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

"""Package constants. Does not depend on other package modules."""

from os.path import dirname, join

__all__ = [ 
    'ROOTAPP',      # Root application name
    'DEFAULT_INI',  # Default configuration file to use
]

ROOTAPP     = 'rootapp'
DEFAULT_INI = join( dirname(__file__), 'develop.ini' )
