# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

"""Utility functions to parse and locate file assets using
asset-specification.

    TODO : Document asset specification in detail.
"""

import pkg_resources
from   os.path  import isabs, sep

from   pluggdapps.utils.path import package_name, package_path

__all__ = [
    'parse_assetspec', 'asset_spec_from_abspath', 'abspath_from_asset_spec',
]

def parse_assetspec( spec, pname ):
    """Parse the asset specification ``spec`` in the context of package name
    ``pname``. If pname is package object, it is resolved as pname.__name__.  
    Return a tuple of (packagename, filename), where packagename is the name
    of the package relative to which the file asset ``filename`` is located."""

    if isabs(spec) : return None, spec

    if pname and not isinstance(pname, str) :
        pname = pname.__name__ # as package

    filename = spec
    if ':' in spec :
        pname, filename = spec.split(':', 1)
    elif pname is None :
        pname, filename = None, spec
    return pname, filename

def asset_spec_from_abspath( abspath, package ):
    """Try to convert an absolute path to a resource in a package in resource
    specification format if possible; otherwise return the absolute path. In
    asset specification format path separator is always '/'"""
    if getattr(package, '__name__', None) == '__main__':
        return abspath
    pp = package_path(package) + sep
    if abspath.startswith(pp):
        relpath = abspath[len(pp):]
        return '%s:%s' % (package_name(package), relpath.replace(sep, '/'))
    return abspath

def abspath_from_asset_spec( spec, pname='' ):
    """Convert assert sepcification into absolute path. if ``pname`` is
    supplied, it will be used to parse the asset-spec"""
    if pname is None :
        return spec
    pname, filename = parse_assetspec( spec, pname )
    if pname :
        return pkg_resources.resource_filename(pname, filename)
    else :
        return filename


