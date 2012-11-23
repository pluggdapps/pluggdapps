# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

"""Provides a collection of :class:`IScaffold` plugins."""

class Scaffolding( Plugin ):
    """Base class for all scaffolding plugins."""

    implements( IScaffold )

    #---- IScaffold API methods.

    def __init__( self, target, template_dir=None ):
        pass

    def query_cmdline( self ):
        pass

    def printhelp( self ):
        sett = self.default_settings()
        print( self.description )
        for name, d in sett.specifications().items() :
            print("  %20s [%s]" % (name, d['default']))
            pprint( d['help'], indent=4 )
            print()
