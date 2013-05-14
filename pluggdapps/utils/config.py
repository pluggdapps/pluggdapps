# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

"""Utility functions and classes to describe configuration settings for
plugins and process them.
"""

import textwrap

__all__ = [ 'ConfigDict', 'settingsfor', 'sec2plugin', 'plugin2sec',
            'is_plugin_section', 'conf_descriptionfor', 'conf_catalog',
            'section_settings', 'netpath_settings' ]

class ConfigDict( dict ):
    """A collection of configuration settings. When a fresh key, a.k.a 
    configuration parameter is added to this dictionary, it can be provided
    as :class:`ConfigItem` object or as a dictionary containing key,value pairs
    similar to ConfigItem.

    Used as return type for default_settings() method specified in 
    :class:`pluggdapps.plugin.ISettings`
    """
    def __init__( self, *args, **kwargs ):
        self._spec = {}
        super().__init__( *args, **kwargs )

    def __setitem__( self, name, value ):
        if not isinstance( value, (ConfigItem, dict) ) :
            raise Exception("ConfigDict value either be ConfigItem or dict")

        value = value if isinstance(value, ConfigItem) else ConfigItem(value)
        self._spec[name] = value
        val = value['default']
        return super().__setitem__( name, val )

    def specifications( self ):
        return self._spec

    def merge( self, *settings ):
        settings = list( settings )
        settings.reverse()
        for sett in settings :
            for k in sett.keys() :
                if k in self : continue
                self[k] = sett[k]


class ConfigItem( dict ):
    """Convenience class to encapsulate config parameter description, which
    is a dictionary of following keys,

    ``default``,
        Default value for this settings a.k.a configuration parameter.
        Compulsory field.
    ``types``,
        Either a tuple of valid types, or a string of comma separated values.
        Allowed types are, ``str``, ``int``, ``bool``, ``csv``.
        Compulsory field.
    ``help``,
        Help string describing the purpose and scope of settings parameter.
        Compulsory field.
    ``webconfig``,
        Boolean, specifying whether the settings parameter is configurable via
        web. Optional field. Default is True.
    ``options``,
        List of optional values that can be used for configuring this 
        parameter. Optional field.
    """
    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )
        self['webconfig'] = self.get('webconfig', True)
        types = self.get('types', tuple())
        self['types'] = types if isinstance( types, tuple ) else (types,)

    @property
    def default( self ):
        return self['default']

    @property
    def types( self ):
        if isinstance( self['types'], str ) :
            return tuple( parsecsvlines( self['types'] ))
        else :
            return self['types']

    @property
    def help( self ):
        return self.get('help', '')

    @property
    def webconfig( self ):
        return self.get('webconfig', True)

    @property
    def options( self ):
        opts = self.get( 'options', '' )
        return opts() if isinstance( opts, collections.Callable ) else opts


def settingsfor( prefix, sett ):
    """Filter settings keys ``sett.keys()`` starting with ``prefix`` and return
    a dictionary of corresponding options. Prefix is pruned of from returned
    settings' keys."""
    l = len(prefix)
    return { k[l:] : sett[k] for k in sett if k.startswith(prefix) }


map_plugin2sec = { 'DEFAULT' : 'DEFAULT',
                   'mountloc' : 'mountloc',
                   'pluggdapps' : 'pluggdapps',
                 }
def plugin2sec( pluginname ):
    """Convert ``pluginname`` to plugin section name in ini-file. For Eg,
    for plugin-name ``httpepollserver``, will return
    ``plugin:httpepollserver``.
    """
    if pluginname.startswith( 'plugin:' ) :
        return pluginname
    else :
        return map_plugin2sec.get( pluginname, 'plugin:'+pluginname )

def sec2plugin( secname ):
    """Reverse of :meth:`plugin2sec`."""
    if secname.startswith('plugin:') :
        return secname[7:]
    else :
        return secname

def is_plugin_section( secname ):
    """Check whether ``secname`` starts with ``plugin:``."""
    return secname.startswith('plugin:')


def conf_descriptionfor( plugin, info=None ):
    """Gather description information for configuration settings for
    ``plugin`` section, which might derive from other plugin class and
    therefore we need to read the default_settings() from its base classes as
    well.

    Returns a dictionary of configuration key and its ConfigItem value.
    """
    from pluggdapps.plugin      import PluginMeta
    from pluggdapps.platform    import DEFAULT, pluggdapps_defaultsett

    if plugin == 'DEFAULT' : # Description of configuration settings.
        describe = DEFAULT()
    elif plugin == 'pluggdapps' :
        describe = pluggdapps_defaultsett()
    else :
        info = info or PluginMeta._pluginmap[ plugin ]
        bases = reversed( info['cls'].mro() )
        describe = info['cls'].default_settings()
        for b in bases :
            if hasattr( b, 'default_settings' ) :
                describe.update( dict( b.default_settings().items() ))
                describe._spec.update( b.default_settings()._spec )
    return describe

def conf_catalog( plugin, info=None ):
    """Use this helper function to generate a catalog of configuration
    settings for ``plugin``,
    """
    describe = conf_descriptionfor( plugin, info=info )
    s, items = '', describe._spec.items() 
    if items :
        for key, d in items :
            s += key + '\n    '
            s += '\n    '.join( textwrap.wrap( d['help'], 70 )) + '\n\n'
    else :
        s = '-- configuration is not supported by plugin --\n'
    return s

def section_settings( pa, netpath, section ):
    """Return configuration settings for ``section`` under the context of
    ``netpath``. ``pa`` must be an instance of :class:`Webapps` platform class.
    """
    appsettings = netpath_settings( pa, netpath )
    return appsettings[section]

def netpath_settings( pa, netpath ):
    """Return configuration settings for web app mounted on ``netpath``.
    ``pa`` must be an instance of :class:`Webapps` platform class.
    """
    return pa.settings \
            if netpath == 'platform' else pa.netpaths[netpath].appsettings
