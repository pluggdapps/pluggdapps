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
interface. Note that there is a convention to prefix class name `Command`
string.  For instance, class name of plugin implementing `pviews` sub-command
is :class:`CommandPViews`. Refer to `ICommand` interface class to learn more
about sub-command callbacks.
"""

import pluggdapps.commands.commands
import pluggdapps.commands.ls
import pluggdapps.commands.serve
import pluggdapps.commands.pviews
import pluggdapps.commands.unittest
import pluggdapps.commands.confdoc
