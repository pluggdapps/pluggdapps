# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

"""Contains utility functions to create scaffolding logic for developers
using pluggdapps frameworks."""

import os
from   os.path      import join, dirname, abspath, basename, relpath

__all__ = [ 'template_to_source' ]

def template_to_source( sourceroot, targetroot, _vars ):
    """Walk though ``sourceroot``, reading each file and sub-directory,
    creating the scaffolding logic under ``targetroot``, using a dictionary 
    of variables ``_vars``."""
    maptree = {}
    print( "  Source-dir : %r" % sourceroot )
    print( "  Target-dir : %r" % targetroot )
    for dirpath, dirnames, filenames in os.walk( sourceroot ) :
        targetdir = maptree.get( dirpath, targetroot )

        # Rename, if required, and copy sub-directories
        for dirname in dirnames :
            t_dir = join(targetdir, dirname.format(**_vars) )
            s_dir = join(dirpath, dirname)
            print("    making dir %s/ ..." % relpath(t_dir, targetroot))
            os.makedirs( t_dir, exist_ok=True )
            maptree[ s_dir ] = t_dir

        for filename in filenames :
            t_file = join(targetdir, filename.format( **_vars ))
            s_file = join(dirpath, filename)
            if t_file.endswith( '.tmpl' ) :
                t_file = t_file[:-5]
            print("    copying file %s ..." % relpath(t_file, targetroot) )
            txt = open( s_file ).read().format( **_vars )
            open( t_file, 'w' ).write( txt )

