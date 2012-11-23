# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

import os
from   os.path      import join, dirname, abspath, basename

def template_to_source( sourcedir, targetdir, _vars ):
    targetdirs = {}
    for dirpath, dirnames, filenames in os.walk( sourcedir ) :
        targetdir = targetdirs.get( dirpath, targetdir )
        for dirname in dirnames :
            dirname = dirname.format( **_vars )
            os.makedirs( join( targetdir, dirname ))
            print("  %s : %r" % ( join(dirpath, dirname), targetdir) )
            targetdirs[ join(dirpath, dirname) ] = join(targetdir, dirname)

        for filename in filenames :
            filename = filename.format( **_vars )
            txt = open( join(dirpath, filename) ).read().format( **_vars )
            open( join(targetdir, filename), 'w' ).write( txt )
            print("  %s : %r" % 
                        ( join(dirpath, filename), join(targetdir, filename)) )

