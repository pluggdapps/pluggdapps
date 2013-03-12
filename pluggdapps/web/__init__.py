# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

"""This package specify and define a web-framework compatible with
:class:`pluggdapps.platform.Webapps` platform. The framework is defined by a
collection of interface specification and implemented as plugins. Thus the
framework itself can be customised and even parts of it can be replaced with
other plugins. Interfaces defining the framework are specified in
module :mod:`pluggdapps.web.interfaces`, this combined with
:class:`pluggdapps.interfaces.IWebApp` interface provides the complete
collection of interfaces required to build the framework. All plugins
implementing the framework are defined under the package :mod:`pluggdapps.web`.
"""

import pluggdapps.web.cookie
import pluggdapps.web.catch_debug
import pluggdapps.web.gzip
import pluggdapps.web.httpneg
import pluggdapps.web.matchrouter
import pluggdapps.web.request
import pluggdapps.web.response
import pluggdapps.web.server
import pluggdapps.web.staticview
import pluggdapps.web.views
import pluggdapps.web.webapp
import pluggdapps.web.interfaces
