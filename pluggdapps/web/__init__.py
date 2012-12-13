# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

"""This package specify and define a web-framework compatible with
:class:`pluggdapps.platform.Webapps` platform and every aspect of the
framework is abstracted into ``Interface``. These interfaces are specified in
module :mod:`pluggdapps.web.webinterfaces`, this combined with
:class:`pluggdapps.interfaces.IWebApp` interface provides the complete
collection of interfaces required to build the framework. With these
interfaces in place, :mod:`pluggdapps.web` directory provide the necessary 
plugins implementing the framework interfaces. Thus it is possible to
customize parts of the frame-work, by defining new plugins, or define an
entirely new framework, by defining a new platform class, as per the
developer's wishes. And best of all, these plugins can co-exist in the same
environment and choosen by configuration files.
"""

import pluggdapps.web.cookie
import pluggdapps.web.errorpage
import pluggdapps.web.gzip
import pluggdapps.web.matchrouter
import pluggdapps.web.request
import pluggdapps.web.resource
import pluggdapps.web.response
import pluggdapps.web.server
import pluggdapps.web.staticfile
import pluggdapps.web.views
import pluggdapps.web.webapp
import pluggdapps.web.webinterfaces
