# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 Netscale Computing

"""Right now pluggdapps does not mandate any conventions in exception
handling. Nevertheless this module can provide an oppurtunity to do 
sophisticated error handling like sending an automated email when ever a
deployment fails with an exceptions."""

__all__ = [ 'Error' ]

class Error( Exception ):
    pass
