# -*- coding: utf-8 -*-

"""'docroot' web-application"""

# - Make sure that to import this package in parent package's __init__ 
#   module.
# - Import necessary modules from 'docroot' web-application so as to load
#   their plugins and interfaces during pluggdapps-bootup.

import docroot
import interfaces
import resource
import router
import view
