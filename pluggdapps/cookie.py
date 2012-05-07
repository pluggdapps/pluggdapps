# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

import logging, hmac, hashlib, base64
import http.cookies

from   pluggdapps.config        import ConfigDict
from   pluggdapps.plugin        import Plugin, implements
from   pluggdapps.interfaces    import ICookie
import pluggdapps.utils         as h

log = logging.getLogger( __name__ )

_default_settings = ConfigDict()
_default_settings.__doc__ = \
    "Configuration settings for HTTPCookie."

_default_settings['secret']  = {
    'default' : 'secure cookie signature',
    'types'   : (str,),
    'help'    : "Use this to sign the cookie value before sending it with the "
                "response.",
}
_default_settings['max_age_seconds']  = {
    'default' : 3600 * 24 * 30,
    'types'   : (int,),
    'help'    : "Maximum age, in seconds, for a cookie to live after its "
                "creation time. The default is 30 days.",
}

class HTTPCookie( Plugin ):
    implements( ICookie )

    def parse_cookies( self, headers ):
        """Parse cookies from header fields and return a SimpleCookie object
        from python's standard library."""
        cookies = http.cookies.SimpleCookie()
        try    : 
            cookies.load( h.native_str( headers['Cookie']  ))
        except : 
            log.warning( "Unable to parse cookie : %s", headers['cookies'] )
        return cookies

    def set_cookie( self, cookies, name, value, **kwargs ) :
        """Sets the given cookie name/value with the given options. Key-word
        arguments typically contains,
          domain, expires_days, expires, path
        Additional keyword arguments are set on the Cookie.Morsel directly.

        ``cookies`` is from Cookie module and updated inplace.

        See http://docs.python.org/library/cookie.html#morsel-objects
        for available attributes.
        """
        domain = kwargs.pop( 'domain', None )
        expires_days = kwargs.pop( 'expires_days', None )
        expires = kwargs.pop( 'expires', None )
        path = kwargs.pop( 'path', '/' )

        # The cookie library only accepts type str, in both python 2 and 3
        name = h.native_str(name)
        value = h.native_str(value)
        if re.search( r"[\x00-\x20]", name + value ):
            # Don't let us accidentally inject bad stuff
            raise ValueError("Invalid cookie %r: %r" % (name, value))
        if name in cookies :
            del cookies[name]
        cookies[name] = value
        morsel = cookies[name]
        if domain :
            morsel["domain"] = domain
        if expires_days is not None and not expires:
            expires = dt.datetime.utcnow() + dt.timedelta( days=expires_days )
        if expires:
            timestamp = calendar.timegm( expires.utctimetuple() )
            morsel["expires"] = email.utils.formatdate(
                timestamp, localtime=False, usegmt=True )
        if path:
            morsel["path"] = path
        for k, v in list( kwargs.items() ) :
            if k == 'max_age' :
                k = 'max-age'
            morsel[k] = v
        return cookies

    def create_signed_value( self, name, value ):
        timestamp = h.utf8( str(int(time.time())) )
        value = base64.b64encode( h.utf8(value) )
        signature = self._create_signature(
                            self['secret'], name, value, timestamp )
        value = b"|".join([ value, timestamp, signature ])
        return value

    def decode_signed_value( self, name, value ):
        if not value :
            return None
        parts = h.utf8(value).split(b"|")
        if len(parts) != 3:
            return None
        signature = self._create_signature(
                            self['secret'], name, parts[0], parts[1] )
        if not self._time_independent_equals( parts[2], signature ):
            log.warning( "Invalid cookie signature %r", value )
            return None
        timestamp = int(parts[1])
        if timestamp < (time.time() - self['max_age_seconds']) :
            log.warning( "Expired cookie %r", value )
            return None
        if timestamp > (time.time() + self['max_age_seconds']) :
            # _cookie_signature does not hash a delimiter between the
            # parts of the cookie, so an attacker could transfer trailing
            # digits from the payload to the timestamp without altering the
            # signature.  For backwards compatibility, sanity-check timestamp
            # here instead of modifying _cookie_signature.
            log.warning("Cookie timestamp in future; possible tampering %r", value)
            return None
        if parts[1].startswith( b"0" ) :
            log.warning("Tampered cookie %r", value)
        try:
            return base64.b64decode( parts[0] )
        except Exception:
            return None

    def _create_signature( self, secret, *parts ):
        hash = hmac.new( h.utf8(secret), digestmod=hashlib.sha1 )
        [ hash.update( h.utf8(part) ) for part in parts ]
        return h.utf8( hash.hexdigest() )

    def _time_independent_equals( self, a, b ):
        if len(a) != len(b) : return False
        result = 0
        if type(a[0]) is int :  # python3 byte strings
            for x, y in zip(a, b):
                result |= x ^ y
        else:                   # python2
            for x, y in zip(a, b):
                result |= ord(x) ^ ord(y)
        return result == 0

    # ISettings interface methods
    @classmethod
    def default_settings( cls ):
        return _default_settings

    @classmethod
    def normalize_settings( cls, settings ):
        settings['max_age_seconds'] = h.asint( settings['max_age_seconds'] )
        return settings

