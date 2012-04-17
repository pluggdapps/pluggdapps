# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

import logging, sys, time, os.path
import logging.handlers

# For pretty log messages, if available
try:
    import curses
except ImportError:
    curses = None

# TODO :
#   1. Examine more formatting options for message loging. 

def setup( logsett ):
    level = getattr( logging, logsett['level'].upper() )
    logging.getLogger().setLevel( level ) if level != 'none' else None

    root_logger = logging.getLogger()
    filename = logfileusing( None, logsett['filename'] )

    # Set up color if we are in a tty and curses is installed
    color = logsett['color']
    color = color if color_available() else False

    stderr = logsett['stderr']
    if filename :
        channel = logging.handlers.RotatingFileHandler(
                        filename=filename,
                        maxBytes=logsett['file_maxsize'],
                        backupCount=logsett['file_maxbackups'] )
        channel.setFormatter( LogFormatter(color=color) )
        root_logger.addHandler( channel )

    stderr = logsett['stderr']
    if stderr or (not root_logger.handlers) :
        channel = logging.StreamHandler()
        channel.setFormatter( LogFormatter(color=color) )
        root_logger.addHandler( channel )


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
    return name + str(index) + ext if index else filename

class LogFormatter( logging.Formatter ):
    def __init__(self, color, *args, **kwargs):
        logging.Formatter.__init__( self, *args, **kwargs )
        self._color = color
        if color:
            # The curses module has some str/bytes confusion in
            # python3.  Until version 3.2.3, most methods return
            # bytes, but only accept strings.  In addition, we want to
            # output these strings with the logging module, which
            # works with unicode strings.  The explicit calls to
            # unicode() below are harmless in python2 but will do the
            # right conversion in python 3.
            fg_color = (curses.tigetstr("setaf") or
                        curses.tigetstr("setf") or "")
            if (3, 0) < sys.version_info < (3, 2, 3):
                fg_color = unicode(fg_color, "ascii")
            self._colors = {
                logging.DEBUG: unicode(curses.tparm(fg_color, 4),  # Blue
                                       "ascii"),
                logging.INFO: unicode(curses.tparm(fg_color, 2),  # Green
                                      "ascii"),
                logging.WARNING: unicode(curses.tparm(fg_color, 3),  # Yellow
                                         "ascii"),
                logging.ERROR: unicode(curses.tparm(fg_color, 1),  # Red
                                       "ascii"),
            }
            self._normal = unicode(curses.tigetstr("sgr0"), "ascii")

    def format(self, record):
        try:
            record.message = record.getMessage()
        except Exception, e:
            record.message = "Bad message (%r): %r" % (e, record.__dict__)
        record.asctime = time.strftime(
            "%y%m%d %H:%M:%S", self.converter(record.created))
        prefix = '[%(levelname)1.1s %(asctime)s %(module)s:%(lineno)d]' % \
            record.__dict__
        if self._color:
            prefix = (self._colors.get(record.levelno, self._normal) +
                      prefix + self._normal)
        formatted = prefix + " " + record.message
        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            formatted = formatted.rstrip() + "\n" + record.exc_text
        return formatted.replace("\n", "\n    ")


