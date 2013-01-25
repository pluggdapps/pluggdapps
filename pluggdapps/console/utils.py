# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

def ascii_special( ca, args ):
    ca.stdscr.addstr( '0   00 NUL Null char\n' )
    ca.stdscr.addstr( '1   01 SOH Start of Heading\n' )
    ca.stdscr.addstr( '2   02 STX Start of Text\n' )
    ca.stdscr.addstr( '3   03 ETX End of Text\n' )
    ca.stdscr.addstr( '4   04 EOT End of Transmission\n' )
    ca.stdscr.addstr( '5   05 ENQ Enquiry\n' )
    ca.stdscr.addstr( '6   06 ACK Acknowledgment\n' )
    ca.stdscr.addstr( '7   07 BEL Bell\n' )
    ca.stdscr.addstr( '8   08  BS Back Space\n' )
    ca.stdscr.addstr( '9   09  HT Horizontal Tab\n' )
    ca.stdscr.addstr( '10  0A  LF Line Feed\n' )
    ca.stdscr.addstr( '11  0B  VT Vertical Tab\n' )
    ca.stdscr.addstr( '12  0C  FF Form Feed\n' )
    ca.stdscr.addstr( '13  0D  CR Carriage Return\n' )
    ca.stdscr.addstr( '14  0E  SO Shift Out / X-On\n' )
    ca.stdscr.addstr( '15  0F  SI Shift In / X-Off\n' )
    ca.stdscr.addstr( '16  10 DLE Data Line Escape\n' )
    ca.stdscr.addstr( '17  11 DC1 Device Control 1 (oft.  XON)\n' )
    ca.stdscr.addstr( '18  12 DC2 Device Control 2\n' )
    ca.stdscr.addstr( '19  13 DC3 Device Control 3 (oft.  XOFF\n' )
    ca.stdscr.addstr( '20  14 DC4 Device Control 4\n' )
    ca.stdscr.addstr( '21  15 NAK Negative Acknowledgement\n' )
    ca.stdscr.addstr( '22  16 SYN Synchronous Idle\n' )
    ca.stdscr.addstr( '23  17 ETB End of Transmit Block\n' )
    ca.stdscr.addstr( '24  18 CAN Cancel\n' )
    ca.stdscr.addstr( '25  19  EM End of Medium\n' )
    ca.stdscr.addstr( '26  1A SUB Substitute\n' )
    ca.stdscr.addstr( '27  1B ESC Escape\n' )
    ca.stdscr.addstr( '28  1C  FS File Separator\n' )
    ca.stdscr.addstr( '29  1D  GS Group Separator\n' )
    ca.stdscr.addstr( '30  1E  RS Record Separator\n' )
    ca.stdscr.addstr( '31  1F  US Unit Separator\n' )

def ascii_alphanum( ca, args ):
    y = 0
    for x in range(32, 128) :
        ca.stdscr.addstr( '%3d x%02x %c  ' % (x, x, chr(x)) )
        y += 1
        if (y % 7) == 0 :
            ca.stdscr.addstr("\n")

def ascii_extended( ca, args ):
    y = 0
    for x in range(128, 256) :
        ca.stdscr.addstr( '%3d x%02x %1c  ' % (x, x, chr(x)) )
        y += 1
        if (y % 7) == 0 :
            ca.stdscr.addstr("\n")
