# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

import logging
import logging.handlers

# For pretty log messages, if available
try:
    import curses
except ImportError:
    curses = None


def setup( logsett ):
    if options.logging != 'none':
        level = getattr( logging, logsett['level'].upper() )
        logging.getLogger().setLevel( level )

    root_logger = logging.getLogger()
    filename = logsett['filename']
    color = logsett['color']
    stderr = logsett['stderr']
    if filename :
        channel = logging.handlers.RotatingFileHandler(
                        filename=filename,
                        maxBytes=logsett['file_maxsize'],
                        backupCount=logsett['file_maxbackups'] )
        channel.setFormatter( _LogFormatter(color=color) )
        root_logger.addHandler( channel )

    stderr = logsett['stderr']
    if stderr or (not root_logger.handlers) :
        # Set up color if we are in a tty and curses is installed
        color = color if color_available() else False
        channel = logging.StreamHandler()
        channel.setFormatter( _LogFormatter(color=color) )
        root_logger.addHandler( channel )


def color_available() :
    if curses and sys.stderr.isatty() :
        try:
            curses.setupterm()
            if curses.tigetnum("colors") > 0:
                return True
        except Exception :
            pass
    return False
