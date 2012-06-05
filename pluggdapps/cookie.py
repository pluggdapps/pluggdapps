# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

"""Cookie handling API. Basic cookie processing functions are available from
its standard library http.cookies. This plugin implements :class:`ICookie`
interface."""

import logging, hmac, hashlib, base64
from   http.cookies import CookieError, SimpleCookie

from   pluggdapps.config        import ConfigDict
from   pluggdapps.plugin        import Plugin
from   pluggdapps.core          import implements
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
        from python's standard library. Cookie string in header is expected to
        be in string."""
        cookies = SimpleCookie()
        try    : 
            cookies.load( headers.get('Cookie', '')  )
        except CookieError :
            log.warning( "Unable to parse cookie : %s", headers['cookies'] )
        return cookies

    def set_cookie( self, cookies, name, value, **kwargs ) :
        """Sets the given cookie name/value with the given options. Key-word
        arguments typically contains,
            domain, expires_days, expires, path

        Additional keyword arguments are set on the Cookie.Morsel directly.
        And the cookie library only accepts string type.

        ``cookies`` is from SimpleCookie and updated inplace.

        See python documentation docs/docs-html-3.2.3/library/http.cookies.html
        for available attributes.
        """
        domain = kwargs.pop( 'domain', None )
        expires_days = kwargs.pop( 'expires_days', None )
        expires = kwargs.pop( 'expires', None )
        path = kwargs.pop( 'path', '/' )

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
            morsel["expires"] = \
                email.utils.formatdate(timestamp, localtime=False, usegmt=True)
        if path:
            morsel["path"] = path
        for k, v in list( kwargs.items() ) :
            if k == 'max_age' :
                k = 'max-age'
            morsel[k] = v
        return cookies

    def create_signed_value( self, name, value ):
        """From name and value, using current timestamp encode a base64 value
        and create a signature for the same.
        
        Finally return a bytes value like,
            <value>|<timestamp>|<signature>
        """
        encoding = self.app['encoding']
        secret = self['secret'].encode( encoding )
        name = name.encode( encoding )
        value = base64.b64encode( value.encode( encoding ))
        timestamp = str( int(time.time()) ).encode( encoding )
        signature = self._create_signature( secret, name, value, timestamp )
        signature = signature.encode( encoding )
        value = b"|".join([ value, timestamp, signature ])
        return value

    def decode_signed_value( self, name, value ):
        if not value : return None

        encoding = self.app['encoding']
        secret = self['secret'].encode( encoding )
        name = name.encode( encoding )
        value = value.encode( encoding )

        parts = value.split(b"|")
        if len(parts) != 3: return None

        args = [ name, parts[0].encode(encoding), parts[1].encode(encoding) ]
        signature = self._create_signature( secret, *args )
        signature = signature.encode( encoding )

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
            log.warning(
                    "Cookie timestamp in future; possible tampering %r", value)
            return None

        if parts[1].startswith( b"0" ) :
            log.warning("Tampered cookie %r", value)
        try:
            return base64.b64decode( parts[0] )
        except Exception:
            return None

    def _create_signature( self, secret, *parts ):
        hash = hmac.new( secret, digestmod=hashlib.sha1 )
        [ hash.update( part ) for part in parts ]
        return hash.hexdigest()

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

    #---- ISettings interface methods

    @classmethod
    def default_settings( cls ):
        super().default_settings()
        return _default_settings

    @classmethod
    def normalize_settings( cls, settings ):
        sett = super().normalize_settings( settings )
        sett['max_age_seconds'] = h.asint( sett['max_age_seconds'] )
        return sett

