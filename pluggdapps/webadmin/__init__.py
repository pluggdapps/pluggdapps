# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy


"""Configuration is normally done in .ini files. To facilitate safe and easy
administration, a web application ``webadmin`` is automatically hosted by the
platform.

* access and change configuration settings for all installed plugin.
* access and change application-wise configuration settings for plugins.
* webadmin also comes with interactive debugging via web to catch and
  introspect exceptions during development.
"""

# - Make sure that to import this package in parent package's __init__ 
#   module.
# - Import necessary modules from 'docroot' web-application so as to load
#   their plugins and interfaces during pluggdapps-bootup.

import pluggdapps.webadmin.webadmin
import pluggdapps.webadmin.resource
import pluggdapps.webadmin.router
import pluggdapps.webadmin.views
