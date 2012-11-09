# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 Netscale Computing

"""Cookie handling API. Basic cookie processing functions are available from
its standard library http.cookies. This plugin implements :class:`IHTTPCookie`
interface."""

import hmac, hashlib, base64, re, calendar, email, time
from   http.cookies import CookieError, SimpleCookie

from   pluggdapps.plugin            import implements, Plugin
from   pluggdapps.web.webinterfaces import IHTTPCookie
import pluggdapps.utils             as h


_default_settings = h.ConfigDict()
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
    implements( IHTTPCookie )

    def parse_cookies( self, headers ):
        cookies = SimpleCookie()
        try    : 
            cookies.load( headers.get( 'Cookie', '' )  )
        except CookieError :
            self.webapp.pa.logwarn(
                "Unable to parse cookie : %s" % headers['cookies'], [] )
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
        if re.search( r"[\x00-\x20]", name + value ):
            # Don't let us accidentally inject bad stuff
            raise ValueError("Invalid cookie %r: %r" % (name, value))

        if name in cookies :
            del cookies[name]

        cookies[name] = value
        morsel = cookies[name]

        domain = kwargs.pop( 'domain', None )
        if domain :
            morsel["domain"] = domain

        expires_days = kwargs.pop( 'expires_days', None )
        expires = kwargs.pop( 'expires', None )
        if expires_days is not None and not expires :
            expires = dt.datetime.utcnow() + dt.timedelta( days=expires_days )
        if expires :
            timestamp = calendar.timegm( expires.utctimetuple() )
            morsel["expires"] = \
                email.utils.formatdate(timestamp, localtime=False, usegmt=True)

        path = kwargs.pop( 'path', '/' )
        if path:
            morsel["path"] = path

        for k, v in kwargs.items() :
            morsel[ k.replace('_', '-') ] = v
        return cookies

    def create_signed_value( self, name, value ):
        """From name and value, using current timestamp encode a base64 value
        and create a signature for the same.
        
        Finally return a bytes value like,
            <base64-encoded-value>|<timestamp>|<signature>

        <signature> is generated using `secret`, `name`, base64 encoded 
        `value` and timestamp-in-seconds.
        """
        encoding = self.webapp['encoding']
        secret = self['secret'].encode( encoding )
        name = name.encode( encoding )
        val64 = base64.b64encode( value.encode( encoding ))
        timestamp = str( int( time.time() )).encode( encoding )
        signature = self._create_signature( secret, name, val64, timestamp )
        signature = signature.encode( encoding )
        signedval = b"|".join([ val64, timestamp, signature ])
        return signedval.decode( 'latin1' )

    def decode_signed_value( self, name, signedval ):
        """Reverse of `create_signed_value`.

        `signedval` is expected to be in,
            <base64-encoded-value>|<timestamp>|<signature>
        Returns orignal value.
        """
        if not signedval : return None

        encoding = self.webapp['encoding']
        secret = self['secret'].encode( encoding )
        name = name.encode( encoding )
        value = signedval.encode( encoding )

        parts = value.split(b"|")
        if len(parts) != 3 : return None

        val64, timestamp, signature = parts
        args = [ name, val64, timestamp ]
        signature_ = self._create_signature( secret, *args )
        signature_ = signature_.encode( encoding )

        if not self._time_independent_equals( signature, signature_ ):
            self.webapp.pa.logwarn("Invalid cookie signature %r" % value,[])
            return None

        timestamp_val = int( timestamp )
        if timestamp_val < (time.time() - self['max_age_seconds']) :
            self.webapp.pa.logwarn( "Expired cookie %r" % value, [] )
            return None

        if timestamp_val > (time.time() + self['max_age_seconds']) :
            # _cookie_signature does not hash a delimiter between the
            # parts of the cookie, so an attacker could transfer trailing
            # digits from the payload to the timestamp without altering the
            # signature.  For backwards compatibility, sanity-check timestamp
            # here instead of modifying _cookie_signature.
            self.webapp.pa.logwarn(
              "Cookie timestamp in future; possible tampering %r" % value, [] )
            return None

        if timestamp.startswith( b"0" ) :
            self.webapp.pa.logwarn( "Tampered cookie %r" % value, [] )
        try:
            return base64.b64decode( val64 ).decode( self.webapp['encoding'] )
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
        return _default_settings

    @classmethod
    def normalize_settings( cls, sett ):
        sett['max_age_seconds'] = h.asint( sett['max_age_seconds'] )
        return sett

