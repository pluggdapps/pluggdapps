# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

"""Utility functions and classes to describe configuration settings for
plugins and process them.
"""

__all__ = [ 'ConfigDict', 'settingsfor', 'sec2plugin', 'plugin2sec',
            'is_plugin_section' ]

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


def plugin2sec( pluginname ):
    """Convert ``pluginname`` to plugin section name in ini-file. For Eg,
    for plugin-name ``httpepollserver``, will return
    ``plugin:httpepollserver``.
    """
    return 'plugin:' + pluginname

def sec2plugin( secname ):
    """Reverse of :meth:`plugin2sec`."""
    return secname[7:]

def is_plugin_section( secname ):
    """Check whether ``secname`` starts with ``plugin:``."""
    return secname.startswith('plugin:')

