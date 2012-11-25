# -*- coding: utf-8 -*-

"""'docroot' web-application"""

# - Make sure that to import this package in parent package's __init__ 
#   module.
# - Import necessary modules from 'docroot' web-application so as to load
#   their plugins and interfaces during pluggdapps-bootup.

import docroot.docroot
import docroot.router
import docroot.resource
import docroot.view
import docroot.interfaces
