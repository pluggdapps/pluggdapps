# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

"""
While working with frameworks, developers are expected to organise and stitch
together their programs in a particular way. Since this is common for all
programs developed using the framework it is typical for frameworks to supply
scaffolding logics to get developers started. In pluggdapps, scaffolding logic
is specified by :class:`pluggdapps.interfaces.IScaffold` interface, and 
there is a collection of plugins implementing that interface supplying different
types of scaffolding logic. Typically these plugins also implement 
:class:`pluggdapps.interfaces.ICommand` interface so that scaffolding 
templates can be invoked directly from pa-script command line.
"""

# Generate scaffold logic for web-application under a project
import pluggdapps.scaffolds.webapp
