# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

import logging, sys, time, os.path
import logging.handlers

# For pretty log messages, if available
try :
    import curses
except ImportError :
    curses = None

from pluggdapps.plugin import query_plugin

def setup( logsett ):
    """Setup and configure python's standard logging. After calling this
    function, rest of the system can acquire a log object by,
        log = logging.getLogger(__name__)
    and perform necessary logging."""
    root_logger = logging.getLogger()
    root_logger.setLevel( logsett['level'] )

    # Set up color if we are in a tty and curses is installed
    color = logsett['color']
    color = color if color_available() else False

    log = None
    if logsett['filename'] :
        filename = logsett['filename']
        channel = logging.handlers.RotatingFileHandler(
                        filename=filename,
                        maxBytes=logsett['file_maxsize'],
                        backupCount=logsett['file_maxbackups'] )
        logsett['color'] = False
        channel.setFormatter( LogFormatter( logsett ) )
        root_logger.addHandler( channel )
        log = log or logging.getLogger(__name__)
        log.debug( "Setting up log file %r ...", filename )

    if logsett['stderr'] :
        channel = logging.StreamHandler()
        logsett['color'] = color
        channel.setFormatter( LogFormatter( logsett ) )
        root_logger.addHandler( channel )
        log = log or logging.getLogger(__name__)
        log.debug( "Setting up log stream in stderr ..." )


def color_available() :
    if curses and sys.stderr.isatty() :
        try:
            curses.setupterm()
            if curses.tigetnum("colors") > 0 :
                return True
        except Exception :
            pass
    return False


def logfileusing( index, filename ):
    name, ext = os.path.splitext(filename)
    filename = name + str(index) + ext if index else filename
    return filename


class LogFormatter( logging.Formatter ):
    def __init__(self, logsett, *args, **kwargs):
        super().__init__( *args, **kwargs )
        self.logsett = logsett
        self._color = logsett['color']
        if self._color :
            self._normal, self._colors = self._docoloring()

    def format(self, record):
        try:
            record.message = record.getMessage()
        except Exception as e:
            record.message = "Bad message (%r): %r" % (e, vars(record))
        record.asctime = time.strftime(
            "%y:%m:%d %H:%M:%S", self.converter(record.created))
        prefix = self.logsett['format'] % vars(record)
        if self._color:
            prefix = self._colors.get(record.levelno, self._normal) + \
                        prefix + self._normal
        formatted = prefix + " " + record.message
        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            formatted = formatted.rstrip() + "\n" + record.exc_text
        return formatted.replace("\n", "\n    ")

    def _docoloring( self ):
        # The curses module has some str/bytes confusion in
        # python3.  Until version 3.2.3, most methods return
        # bytes, but only accept strings.  In addition, we want to
        # output these strings with the logging module, which
        # works with strings.
        fg_color = ( curses.tigetstr("setaf") or 
                     curses.tigetstr("setf") or "" )
        if (3, 0) < sys.version_info < (3, 2, 3) :
            fg_color = str(fg_color, "ascii")
        normal = str(curses.tigetstr("sgr0"), "ascii")
        colors = {
            logging.DEBUG  : str(curses.tparm(fg_color, 4), "ascii"), # Blue
            logging.INFO   : str(curses.tparm(fg_color, 2), "ascii"), # Green
            logging.WARNING: str(curses.tparm(fg_color, 3), "ascii"), # Yellow
            logging.ERROR  : str(curses.tparm(fg_color, 1), "ascii"), # Red
        }
        return normal, colors

