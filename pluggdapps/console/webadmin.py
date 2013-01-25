# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

import curses
from   argparse     import ArgumentParser

from   pluggdapps.platform      import Consoleapps

def curses_status( ca, args ):
    ca.stdscr.addstr(
        "Baudrate      : %s\n" % curses.baudrate() )
    ca.stdscr.addstr(
        "Has color     : %s\n" % curses.has_colors() )
    ca.stdscr.addstr(
        "Change color  : %s\n" % curses.can_change_color() )
    ca.stdscr.addstr(
        "Insert char   : %s\n" % curses.has_ic() )
    ca.stdscr.addstr(
        "Insert line   : %s\n" % curses.has_il() )
    ca.stdscr.addstr(
        "Color numbers : 0-%s\n" % curses.COLORS )
    ca.stdscr.addstr(
        "COLOR_WHITE   : %s\n" % (curses.color_content(curses.COLOR_WHITE),) )
    ca.stdscr.addstr(
        "COLOR_BLACK   : %s\n" % (curses.color_content(curses.COLOR_BLACK),) )
    ca.stdscr.addstr(
        "COLOR_RED     : %s\n" % (curses.color_content(curses.COLOR_RED),) )
    ca.stdscr.addstr(
        "COLOR_GREEN   : %s\n" % (curses.color_content(curses.COLOR_GREEN),) )
    ca.stdscr.addstr(
        "COLOR_BLUE    : %s\n" % (curses.color_content(curses.COLOR_BLUE),) )
    ca.stdscr.addstr(
        "COLOR_YELLOW  : %s\n" % (curses.color_content(curses.COLOR_YELLOW),) )
    ca.stdscr.addstr(
        "COLOR_MAGENTA : %s\n" % (curses.color_content(curses.COLOR_MAGENTA),))
    ca.stdscr.addstr(
        "COLOR_CYAN    : %s\n" % (curses.color_content(curses.COLOR_CYAN),) )
    ca.stdscr.addstr(
        "Erase char    : %s\n" % (curses.erasechar(),) )

    ls = list( filter( lambda x: curses.has_key(x), range(255) ))
    ca.stdscr.addstr(
        "Unknown keys  : %s\n" % ls )

def ascii_table( ca, args ):
    import pluggdapps.console.utils as cutils
    cutils.ascii_alphanum( ca, args )
    ca.stdscr.addstr('\n\nExtended Ascii table \n\n')
    cutils.ascii_extended( ca, args )

def application( ca, args ):
    curses_status( ca, args )    
    c = ca.stdscr.getch()

def mainoptions():
    # setup main script arguments
    description = "Pluggdapps command line script."
    mainparser = ArgumentParser( description=description )
    mainparser.add_argument( '-c', dest='config', 
                             default=None,
                             help="specify config file(s)" )
    return mainparser

def main():
    mainparser = mainoptions()
    args = mainparser.parse_args()
    ca = Consoleapps.boot( args.config )
    try :
        ca.start()
        application( ca, args )
    except :
        ca.shutdown
        raise
    else :
        ca.shutdown()

if __name__ == '__main__' :
    main()

