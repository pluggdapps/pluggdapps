# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

"""Contains utility functions to create scaffolding logic for developers
using pluggdapps frameworks."""

import os, difflib, pprint
from   os.path      import join, dirname, abspath, basename, relpath, isfile

from   pluggdapps.utils.merge import merge3

__all__ = [ 'template_to_source' ]

diff = difflib.Differ()

def template_to_source( sourceroot, targetroot, _vars, **kwargs ):
    """Walk though ``sourceroot``, reading each file and sub-directory,
    creating the scaffolding logic under ``targetroot``, using a dictionary 
    of variables ``_vars``.
    
    optional keyword arguments,

    ``force``,
        if set to True, will blindly copy all the files from template to
        target. Default is False, in which case, an intelligent merge will be
        performed. 

    ``verbose``,
        will print a verbose output.
    """
    maptree = {}
    force, verbose = kwargs.get('force', False), kwargs.get('verbose', True)

    if verbose :
        print( "  Source-dir : %r" % sourceroot )
        print( "  Target-dir : %r" % targetroot )

    for dirpath, dirnames, filenames in os.walk( sourceroot ) :
        targetdir = maptree.get( dirpath, targetroot )

        # Rename, if required, and copy sub-directories
        for dirname in dirnames :
            t_dir = join(targetdir, dirname.format(**_vars) )
            s_dir = join(dirpath, dirname)
            if verbose :
                print("    making dir %s/ ..." % relpath(t_dir, targetroot))
            os.makedirs( t_dir, exist_ok=True )
            maptree[ s_dir ] = t_dir

        for filename in filenames :
            t_file = join(targetdir, filename.format( **_vars ))
            s_file = join(dirpath, filename)

            if t_file.endswith( '.tmpl' ) :
                t_file = t_file[:-5]
                stxt = open( s_file ).read().format( **_vars )
            else :
                stxt = open( s_file ).read()

            t_file_ = relpath(t_file, targetroot)
            if force == False and isfile(t_file) :
                othertxt = open(t_file).readlines()
                mytxt = basetxt = stxt.splitlines(True)
                had_conflict, m = merge3(mytxt, basetxt, othertxt)

                txt = ''.join(m)
                if had_conflict and verbose :
                    print("    copying file %s ... conflict" % t_file_)
                if verbose :
                    print("    copying file %s ... merge" % t_file_)
            else :
                print("    copying file %s ... new" % t_file_)
                txt = stxt
            # open( t_file, 'w' ).write( txt )

