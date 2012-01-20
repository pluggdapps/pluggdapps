# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

from pluggdapps.component   import Interface, Attribute

__all__ = [ 'ICommand' ]

class ICommand( Interface ):

    def argparse( argv ):
        """Parse command line arguments using argv list and return a tuple of
        (options, args)."""

    def run( options, args ):
        """Run the command using command line options and non-option parameters,
        args, which were previously parsed using argparse() method."""

