# -*- coding: utf-8 -*-

import pkg_resources, logging
from   os.path  import isabs, sep

from   pluggdapps.compat    import string_types
from   pluggdapps.path      import package_name, package_path

log = logging.getLogger( __name__ )

def parse_assetspec( spec, pname ):
    """Parse the asset specification ``spec`` in the context of package name
    ``pname``. If pname is package object, it is resolved as pname.__name__.

    Return a tuple of (packagename, filename), where packagename is the name
    of the package relative to which the file asset ``filename`` is
    located."""

    if isabs(spec) : return None, spec

    if pname and not isinstance(pname, string_types) :
        pname = pname.__name__ # as package

    filename = spec
    if ':' in spec :
        pname, filename = spec.split(':', 1)
    elif pname is None :
        pname, filename = None, spec
    return pname, filename

def asset_spec_from_abspath( abspath, package ):
    """Try to convert an absolute path to a resource in a package to
    a resource specification if possible; otherwise return the
    absolute path."""
    if getattr(package, '__name__', None) == '__main__':
        return abspath
    pp = package_path(package) + sep
    if abspath.startswith(pp):
        relpath = abspath[len(pp):]
        return '%s:%s' % (package_name(package),
                          relpath.replace(sep, '/'))
    return abspath

def abspath_from_asset_spec( spec, pname=None ):
    if pname is None :
        return spec
    pname, filename = parse_assetspec( spec, pname )
    if pname is None:
        return filename
    return pkg_resources.resource_filename(pname, filename)


# Unit-test
from pluggdapps.unittest import UnitTestBase
from os.path import basename

class UnitTest_Asset( UnitTestBase ):
    
    def test( self ):
        self.test_parse_assetspec()
        self.test_asset_spec_from_abspath()
        self.test_abspath_from_asset_spec()

    def test_parse_assetspec( self ):
        import pluggdapps
        log.info("Testing parse_assetspec() ...")
        basenm = basename(__file__)
        assert parse_assetspec(__file__, None) == (None, __file__)
        assert parse_assetspec(basenm, 'pluggdapps') == ('pluggdapps', basenm)
        assert parse_assetspec(basenm, None) == (None, basenm)
        assert parse_assetspec('pluggdapps:asset.py', None) == ('pluggdapps', 'asset.py')

    def test_asset_spec_from_abspath( self ):
        import pluggdapps
        import os
        log.info("Testing asset_spec_from_abspath() ...")
        basenm = basename(__file__)
        assert asset_spec_from_abspath(__file__, pluggdapps) == 'pluggdapps:'+basenm
        assert asset_spec_from_abspath(__file__, os) == __file__

    def test_abspath_from_asset_spec( self ):
        log.info("Testing abspath_from_asset_spec() ...")
        assert abspath_from_asset_spec( __file__, None ) == __file__
        assert abspath_from_asset_spec('pluggdapps:asset.py', '') == __file__.rstrip('c')
        assert abspath_from_asset_spec('asset.py', 'pluggdapps') == __file__.rstrip('c')
