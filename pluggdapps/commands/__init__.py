# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

"""This package contain a collection of sub-command plugins for `pa` script.
Sub-commands should implement :class:`pluggdapps.interfaces.ICommand`
interface.

How to implement a sub-command plugin
-------------------------------------

Just like any other plugin, derive your class from `Plugin` base class and
declare that the class implements :class:`pluggdapps.interfaces.ICommand`
interface. Refer to `ICommand` interface class to learn more about sub-command
callbacks.
"""

import re

def mainargs( interface, pattern, argv ):
    """Get a list of sub-commands, implementing ``interface``, supported by
    command line. ``pattern`` will be matched with plugin's canonical name and
    only matching sub-command plugins will be returned. To match all plugins
    implementing ``interface``, pass pattern as ``*``.

    Take only the command-line parameters uptil a subcommand and return them."""
    from   pluggdapps.plugin import PluginMeta
    import pluggdapps.utils as h
    
    if isinstance(interface, str) :
        interface = PluginMeta._interfmap[interface]['cls']

    if pattern :
        pattc = re.compile(pattern)
        subcmds = [ name.split('.', 1)[1]
                    for name in PluginMeta._implementers[ interface ].keys()
                    if re.match(pattc, name) ]
    else :
        subcmds = [ name.split('.', 1)[1]
                    for name in PluginMeta._implementers[ interface ].keys() ]

    return h.takewhile( lambda x : x not in subcmds, argv )

import pluggdapps.commands.commands
import pluggdapps.commands.ls
import pluggdapps.commands.serve
import pluggdapps.commands.pviews
import pluggdapps.commands.unittest
import pluggdapps.commands.confdoc
