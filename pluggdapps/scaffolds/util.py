# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

import os
from   os.path      import join, dirname, abspath, basename

def template_to_source( sourcedir, targetdir, _vars ):
    targetdirs = {}
    print( "  Source-dir : %r" % basename( sourcedir ) )
    print( "  Target-dir : %r" % basename( targetdir ) )
    for dirpath, dirnames, filenames in os.walk( sourcedir ) :
        targetdir = targetdirs.get( dirpath, targetdir )
        for dirname in dirnames :
            t_dirname = dirname.format( **_vars )
            print("    %s ..." % t_dirname )
            os.makedirs( join( targetdir, t_dirname ))
            targetdirs[ join(dirpath, dirname) ] = join(targetdir, t_dirname)

        for filename in filenames :
            t_filename = filename.format( **_vars )
            print("    %s ..." % t_filename )
            txt = open( join(dirpath, filename) ).read().format( **_vars )
            open( join(targetdir, t_filename), 'w' ).write( txt )

