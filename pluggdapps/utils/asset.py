# -*- coding: utf-8 -*-

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
    supplied it will be used to parse the asset-spec"""
    if pname is None :
        return spec
    pname, filename = parse_assetspec( spec, pname )
    if pname :
        return pkg_resources.resource_filename(pname, filename)
    else :
        return filename


# Unit-test
from pluggdapps.unittest import UnitTestBase
from os.path import basename

class UnitTest_Asset( UnitTestBase ):
    
    def setup( self ):
        super().setup()

    def test( self ):
        self.test_parse_assetspec()
        self.test_asset_spec_from_abspath()
        self.test_abspath_from_asset_spec()
        super().test()

    def teardown( self ):
        super().teardown()

    def test_parse_assetspec( self ):
        import pluggdapps
        self.log.info("Testing parse_assetspec() ...")
        basenm = basename(__file__)
        assert parse_assetspec(__file__, None) == (None, __file__)
        assert parse_assetspec(basenm, 'pluggdapps') == ('pluggdapps', basenm)
        assert parse_assetspec(basenm, None) == (None, basenm)
        assert parse_assetspec('pluggdapps:asset.py', None) == \
               ('pluggdapps', 'asset.py')

    def test_asset_spec_from_abspath( self ):
        import pluggdapps
        import os
        self.log.info("Testing asset_spec_from_abspath() ...")
        assert asset_spec_from_abspath(__file__, pluggdapps) == \
               'pluggdapps:utils/asset.py'
        assert asset_spec_from_abspath(__file__, os) == __file__

    def test_abspath_from_asset_spec( self ):
        self.log.info("Testing abspath_from_asset_spec() ...")
        assert abspath_from_asset_spec( __file__, None ) == __file__
        assert abspath_from_asset_spec('pluggdapps:utils/asset.py', '') == \
               __file__.rstrip('c')
        assert abspath_from_asset_spec('utils/asset.py', 'pluggdapps') == \
               __file__.rstrip('c')
