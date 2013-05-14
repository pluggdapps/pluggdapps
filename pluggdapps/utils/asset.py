# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

"""Utility functions to parse and locate file assets using 
asset-specification format."""

import pkg_resources, os
from   os.path  import isabs, abspath, join, dirname

from   pluggdapps.utils.lib  import longest_prefix

__all__ = [
    'parse_assetspec', 'asset_spec_from_abspath', 'abspath_from_asset_spec',
    'packagedin'
]

def parse_assetspec( spec, pname ):
    """Parse the asset specification ``spec`` in the context of package name
    ``pname``. If pname is package object, it is resolved as pname.__name__.  
    Return a tuple of (packagename, filename), where packagename is the name
    of the package relative to which the file asset ``filename`` is located.
    """

    if isabs(spec) : return None, spec

    if pname and not isinstance(pname, str) :
        pname = pname.__name__ # as package

    filename = spec
    if ':' in spec :
        pname, filename = spec.split(':', 1)
    elif pname is None :
        pname, filename = None, spec
    return pname, filename

def asset_spec_from_abspath( abspath, papackages ):
    """Use the dictionary of ``papackages``, gathered during platform boot
    time by calling package() entrypoint and convert abspath to
    asset-specification format."""
    locations = { pinfo['location'] : p for p, pinfo in papackages.items() }
    prefix = longest_prefix( locations.keys(), abspath )
    pkg = locations[prefix] if prefix else None
    if pkg :
        return ( pkg + ':' + abspath[ len(prefix) : ].lstrip(os.sep) )
    else :
        return None

def abspath_from_asset_spec( spec, pname='', relativeto=None ):
    """Convert assert sepcification into absolute path. if ``pname`` is
    supplied, it will be used to parse the asset-spec"""
    if pname is None :
        return spec
    pname, filename = parse_assetspec( spec, pname )
    if pname :
        return pkg_resources.resource_filename(pname, filename)
    else :
        if relativeto and filename[0] != os.sep :
            return join( relativeto, filename )
        elif filename[0] != os.sep :
            return abspath( filename )
        else :
            return filename

def packagedin( abspath ):
    """Return the package name that contains the asset `abspath`."""
    from pluggdapps import papackages # Keep this line, don't shuffle around !!

    locations = { pinfo['location'] : p for p, pinfo in papackages.items() }
    prefix = longest_prefix( locations.keys(), abspath )
    return locations[prefix] if prefix else None

