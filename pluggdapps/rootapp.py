# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

import logging

from   pluggdapps.config        import ConfigDict
from   pluggdapps.application   import Application
import pluggdapps.utils         as h

log = logging.getLogger(__name__)

_default_settings = ConfigDict()
_default_settings.__doc__ = \
    "Configuration settings for root application."""

_default_settings['debug']  = {
    'default' : False,
    'types'   : (bool,),
    'help'    : "To execute platform in debug mode.",
}
_default_settings['encoding']  = {
    'default' : 'utf-8',
    'types'   : (str,),
    'help'    : "String encoding to handle unicode text.",
}
_default_settings['logging.level']  = {
    'default' : 'debug',
    'types'   : (str,),
    'options' : [ 'debug', 'info', 'warning', 'error', 'none' ],
    'help'    : "Set Python log level. If 'none', logging configuration won't "
                "be touched.",
}
_default_settings['logging.stderr'] = {
    'default' : True,
    'types'   : (bool,),
    'help'    : "Send log output to stderr (colorized if possible).",
}
_default_settings['logging.filename'] = {
    'default' : 'apps.log',
    'types'   : (str,),
    'help'    : "Path prefix for log files. Note that if you are "
                "running multiple processes, log_file_prefix must be "
                "different for each of them (e.g. include the port number).",
}
_default_settings['logging.file_maxsize'] = {
    'default' : 100*1024*1024,
    'types'   : (int,),
    'help'    : "max size of log files before rollover.",
}
_default_settings['logging.file_maxbackups'] = {
    'default' : 10,
    'types'   : (int,),
    'help'    : "number of log files to keep.",
}
_default_settings['logging.color'] = {
    'default' : True,
    'types'   : (bool,),
    'help'    : "If logs have to be send to terminal should you want it "
                "colored."
}


class RootApp( Application ):

    def onboot( self, settings ):
        pass

    def start( self, request ):
        pass

    def router( self, request ):
        pass

    def onfinish( self, request ):
        request.onfinish()

    def shutdown( self, settings ):
        pass

    # ISettings interface methods
    @classmethod
    def default_settings( cls ):
        return _default_settings

    @classmethod
    def normalize_settings( cls, settings ):
        settings['debug'] = h.asbool( settings['debug'] )
        settings['logging.stderr'] = h.asbool( settings['logging.stderr'] )
        settings['logging.file_maxsize'] = \
                h.asint( settings['logging.file_maxsize'] )
        settings['logging.file_maxbackups'] = \
                h.asint( settings['logging.file_maxbackups'] )
        settings['logging.color'] = h.asbool( settings['logging.color'] )
        # Logging level
        level = settings['logging.level']
        level = getattr(logging, level.upper()) if level != 'none' else None
        settings['logging.level'] = level
        return settings
