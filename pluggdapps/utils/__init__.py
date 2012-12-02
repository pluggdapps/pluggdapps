# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

"""
Utility functions available for,
  * configuration & settings.
  * path manipulations.
  * asset specification.
  * General functions.
  * Parse and create JSON strings.
  * Parse HTTP messages.
  * Scaffolding logic.

Modules who want to use these functions typically import them as,::

  import pluggdapps.utils as h

And all the utility functions are available as attributes on ``h``.
"""


from pluggdapps.utils.config import *
from pluggdapps.utils.path import *
from pluggdapps.utils.asset import *
from pluggdapps.utils.lib import *
from pluggdapps.utils.jsonlib import *
from pluggdapps.utils.parsehttp import *
from pluggdapps.utils.scaff import *
