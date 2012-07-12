# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

"""HTTP utility functions."""

import logging, re, sys, calendar, email, hashlib, socket
from collections import UserDict
import datetime as dt
import urllib.request, urllib.error
from urllib.parse import urlsplit, unquote, parse_qs, urlunsplit, quote, \
                         urlencode, urljoin

from pluggdapps.utils.exc import Error
from pluggdapps.utils.lib import parsecsv

strptime = dt.datetime.strptime
strftime = dt.datetime.strftime

__all__ = [
    'port_and_scheme', 'parse_startline', 'parse_url', 'make_url',
    'parse_xscheme', 'parse_remoteip', 'parse_body',
    'convert_header_value', 'compute_etag', 'HTTPFile', 
    'HTTPHeaders', 'url_concat', 'parse_multipart_form_data',
]

log = logging.getLogger( __name__ )


def _valid_ip( ip ):
    try:
        res = socket.getaddrinfo( ip, 0, socket.AF_UNSPEC,
                                  socket.SOCK_STREAM,
                                  0, socket.AI_NUMERICHOST )
        return bool(res)
    except socket.gaierror as e:
        if e.args[0] == socket.EAI_NONAME:
            return False
        raise
    return True

def port_and_scheme( scheme, port='' ):
    if port :
        if scheme == 'http' and str(port) == '80' :
            port = ''
        elif scheme == 'https' and str(port) == '443' :
            port = ''
    else :
        if scheme == 'http' :
            port = '80'
        elif scheme == 'https' : 
            port = '443'
    return str(port)

def parse_startline( startline ):
    """Every HTTP request starts with a start line specifying method, uri and
    version. Parse them and return a tuple of (method, uri, version). All
    elements in the return tuple will be available as strings."""
    try :
        method, uri, version = [ x.strip(' \t') for x in startline.split(" ") ]
    except :
        log.error("Malformed HTTP version in HTTP Request-Line %r", startline)
        method = uri = version = None
    if not version.startswith("HTTP/") :
        log.error( "Unknown HTTP Version %r", version )
    return method, uri, version

def parse_url( uri, host=None, scheme=None ):
    """Parse uri using urlsplit() method into its component parts.
    
    ``uri``,
        uri is expected in string format, decoded using 'utf-8' encoding.

    ``host``,
        Many times uri, as found in the request startline, have `abs_path`
        alone, in which case, optional host name as found in the `Host` header
        can be supplied. It will be applied on the urlsplit() result. Note
        that as per RFC definition Host header can also contain port address.

    ``scheme``,
        Default scheme to use while parsing the url. Directly passed to
        urlsplit()

    Returns a UserDict with following keys,
        scheme, netloc, path, query, fragment, username, password, hostname,
        port, script

    Among these key values,

    * `path` value will be unquoted using urllib.parse.unquote()

    * `query` value will be unquoted using urllib.parse.parse_qs()

    * and, all values are available as strings.
    
    Refer to Section 5.2 in RFC 2616.txt 
    """
    try :
        host, port = host.split(':', 1)
    except :
        host, port = host, None
    r = urlsplit( uri )
    host = r.hostname or host
    port = r.port or port
    scheme = r.scheme or scheme
    path = unquote( r.path )  # With default encoding
    query = parse_qs( r.query ) # With default encoding
    r = UserDict( scheme=scheme, netloc=r.netloc, path=path, query=query,
                  fragment=r.fragment, username=r.username, 
                  password=r.password, hostname=host, port=port, script='' )
    return r

def make_url( baseurl, path, query, fragment ):
    """Using the baseurl and the remaining variable part of a url namely
    path, query, fragment construct a full url that can be sent in response
    and interpreted by Clients.
    
    * `path` will be quoted using urllib.parse.quote()

    * `query` is expected as a dictionary key,value pairs, value being a list.
       Will be encoded using urllib.parse.urlencode()

    If ``baseurl`` is not supplied, relative url is returned. 
    """
    path = quote( path ) if path else ''
    query = urlencode( query ) if query else ''
    fragment = fragment if fragment else ''
    relurl = urlunsplit( '', '', path, query, fragment )
    return urljoin( baseurl, relurl ) if baseurl else relurl

def parse_xscheme( hdrs, xheaders ):
    if xheaders : # AWS uses X-Forwarded-Proto
        scheme = hdrs.get("X-Scheme", hdrs.get("X-Forwarded-Proto", None))
        if scheme not in ("http", "https"):
            scheme = "http"
    else :
        scheme = None
    return scheme

def parse_remoteip( addr, hdrs, xheaders ):
    if xheaders : # Squid uses X-Forwarded-For, others use X-Real-Ip
        remote_ip = hdrs.get("X-Real-Ip", hdrs.get("X-Forwarded-For", None))
        if not valid_ip( remote_ip ):
            remote_ip = addr
    else :
        remote_ip = addr
    return remote_ip


rfc1123_format = "%a, %d %b %Y %H:%M:%S %Z"
rfc1036_format = "%A, %d-%b-%y %H:%M:%S %Z"
asctime_format = "%a %b %d %H:%M:%S %Y"
def http_normalizedate( datestr ):
    """HTTP applications have historically allowed three different formats
    for the representation of date/time stamps:

      Sun, 06 Nov 1994 08:49:37 GMT  ; RFC 822, updated by RFC 1123
      Sunday, 06-Nov-94 08:49:37 GMT ; RFC 850, obsoleted by RFC 1036
      Sun Nov  6 08:49:37 1994       ; ANSI C's asctime() format

    The first format is preferred as an Internet standard. This function
    heuristically parses the date format (from request header) and changes the
    format to RFC 1123 format.
    """
    try :
        dtime = strptime( datestr, rfc1123_format )
    except :
        dtime = None
    if dtime == None :
        for fmt in [ rfc1036_format, asctime_format ] :
            try :
                dtime = strptime( datestr, fmt )
                break
            except :
                pass
        else :
            raise Error( "Unknown date format in http header - %r" % datestr )
    return dtime.strftime( rfc1123_format ) 


def http_todate( datestr ):
    """Convert date-time string, RFC 1123 normalized format, to python datetime
    object."""
    return strptime( datestr, rfc1123_format )


def http_fromdate( dtime ):
    """Convert python datetime object to RFC 1123 date format."""
    return strftime( dtime, rfc1123_format )


def parse_fieldvalue( field, value ):
    pass

def convert_header_value( value ):
    """Transform `value` to marshal them as HTTP header value.

    If a datetime is given it is automatically formatted according to the
    HTTP specification. If the value is not a string, it is converted to
    a string. All header values are then encoded as UTF-8."""
    if isinstance( value, str ) :
        value = value.encode( 'utf-8' )
    elif isinstance( value, int ) :
        # return immediately since we know the converted value will be safe
        return str(value).encode( 'utf-8' )
    elif isinstance( value, dt.datetime ) :
        t = calendar.timegm( value.utctimetuple() )
        return email.utils.formatdate( t, localtime=False, usegmt=True )
    else:
        raise Error( "Unsupported header value %r" % value )
    # If \n is allowed into the header, it is possible to inject
    # additional headers or split the request. Also cap length to
    # prevent obviously erroneous values.
    if len(value) > 4000 or re.match( b"[\x00-\x1f]", value ):
        raise Error( "Unsafe header value %r", value )
    return value


def compute_etag( write_buffer ) :
    """Computes the etag header to be used for this request's response."""
    hasher = hashlib.sha1()
    [ hasher.update(x) for x in write_buffer ]
    return '"%s"' % hasher.hexdigest()

class HTTPFile( UserDict ):
    """Represents an HTTP file, whose instance variables are also accessible
    as dictionary keys.

    Instance variables,

    ``filename``,
        Uploaded file's name from HTTP request.
    ``body``,
        Request body.
    ``content_type``,
        This value comes from HTTP header and cannot be trusted outright given
        that it can be easily forged.
    """
    pass


def url_concat( url, args ):
    """Concatenate url and argument dictionary regardless of whether
    url has existing query parameters.

    >>> url_concat("http://example.com/foo?a=b", dict(c="d"))
    'http://example.com/foo?a=b&c=d'
    """
    if not args : return url
    if url[-1] not in ('?', '&'):
        url += '&' if ('?' in url) else '?'
    return url + urlencode( args )

def parse_body( method, headers, body ):
    arguments, files = {}, {}
    content_type = headers.get( "Content-Type", "" )
    if method in ("POST", "PUT"):
        if content_type.startswith( "application/x-www-form-urlencoded" ):
            for name, values in parse_qs( body ).items() :
                values = [ x for x in values if x ]
                if values :
                    arguments.setdefault( name, [] ).extend( values )
        elif content_type.startswith( "multipart/form-data" ):
            fields = content_type.split(";")
            for field in fields:
                k, sep, v = field.strip().partition("=")
                if k == "boundary" and v :
                    args, files = parse_multipart_form_data( v, body )
                    arguments.update( args )
                    files.update( files )
                    break
            else:
                log.warning( "Invalid multipart/form-data" )
    return arguments, files


def parse_multipart_form_data( boundary, data ):
    """Parses a multipart/form-data body.

    The boundary and data parameters are both byte strings.
    The dictionaries given in the arguments and files parameters
    will be updated with the contents of the body."""
    # The standard allows for the boundary to be quoted in the header,
    # although it's rare (it happens at least for google app engine
    # xmpp).  I think we're also supposed to handle backslash-escapes
    # here but I'll save that until we see a client that uses them
    # in the wild.
    arguments, files = {}, {}
    if boundary.startswith(b'"') and boundary.endswith(b'"'):
        boundary = boundary[1:-1]
    if data.endswith(b"\r\n"):
        footer_length = len(boundary) + 6
    else:
        footer_length = len(boundary) + 4
    parts = data[:-footer_length].split(b"--" + boundary + b"\r\n")
    for part in parts:
        if not part:
            continue
        eoh = part.find(b"\r\n\r\n")
        if eoh == -1:
            log.warning( "multipart/form-data missing headers" )
            continue
        headers = HTTPHeaders.parse( part[:eoh].decode("utf-8") )
        disp_header = headers.get( "Content-Disposition", "" )
        disposition, disp_params = _parse_header(disp_header)
        if disposition != "form-data" or not part.endswith(b"\r\n"):
            log.warning( "Invalid multipart/form-data" )
            continue
        value = part[eoh + 4:-2]
        if not disp_params.get("name"):
            log.warning( "multipart/form-data value missing name" )
            continue
        name = disp_params["name"]
        if disp_params.get("filename"):
            ctype = headers.get("Content-Type", "application/unknown")
            files.setdefault( name, [] ).append(
                HTTPFile( filename=disp_params["filename"], body=value,
                          content_type=ctype )
            )
        else:
            arguments.setdefault(name, []).append(value)

# _parseparam and _parse_header are copied and modified from python2.7's cgi.py
# The original 2.7 version of this code did not correctly support some
# combinations of semicolons and double quotes.
def _parseparam(s):
    while s[:1] == ';':
        s = s[1:]
        end = s.find(';')
        while end > 0 and (s.count('"', 0, end) - s.count('\\"', 0, end)) % 2:
            end = s.find(';', end + 1)
        if end < 0:
            end = len(s)
        f = s[:end]
        yield f.strip()
        s = s[end:]

def _parse_header(line):
    """Parse a Content-type like header.
    Return the main content-type and a dictionary of options."""
    parts = _parseparam(';' + line)
    key = next( parts )
    pdict = {}
    for p in parts:
        i = p.find('=')
        if i >= 0:
            name = p[:i].strip().lower()
            value = p[i + 1:].strip()
            if len(value) >= 2 and value[0] == value[-1] == '"':
                value = value[1:-1]
                value = value.replace('\\\\', '\\').replace('\\"', '"')
            pdict[name] = value
    return key, pdict


class HTTPHeaders( dict ):
    """A dictionary that maintains Http-Header-Case for all keys.

    Supports multiple values per key via a pair of new methods,
    add() and get_list().  The regular dictionary interface returns a single
    value per key, with multiple values joined by a comma.

    >>> h = HTTPHeaders({"content-type": "text/html"})
    >>> h.keys()
    ['Content-Type']
    >>> h["Content-Type"]
    'text/html'

    >>> h.add("Set-Cookie", "A=B")
    >>> h.add("Set-Cookie", "C=D")
    >>> h["set-cookie"]
    'A=B,C=D'
    >>> h.get_list("set-cookie")
    ['A=B', 'C=D']

    >>> for (k,v) in sorted(h.get_all()):
    ...    print '%s: %s' % (k,v)
    ...
    Content-Type: text/html
    Set-Cookie: A=B
    Set-Cookie: C=D
    """
    general_headers = [
       'Cache-Control', 'Connection', 'Date', 'Pragma', 'Trailer', 
       'Transfer-Encoding', 'Upgrade', 'Via', 'Warning',
    ]
    request_headers = [
       'Accept', 'Accept-Charset', 'Accept-Encoding', 'Accept-Language',
       'Authorization', 'Expect', 'From', 'Host', 'If-Match',
       'If-Modified-Since', 'If-None-Match', 'If-Range', 'If-Unmodified-Since',
       'Max-Forwards', 'Proxy-Authorization', 'Range', 'Referer', 'TE',
       'User-Agent',
    ]
    response_headers = [
       'Accept-Ranges', 'Age', 'ETag', 'Location', 'Proxy-Authenticate',
       'Retry-After', 'Server', 'Vary', 'WWW-Authenticate', 
    ]
    entity_headers = [
       'Allow', 'Content-Encoding', 'Content-Language', 'Content-Length',
       'Content-Location', 'Content-MD5', 'Content-Range', 'Content-Type',
       'Expires', 'Last-Modified',
    ]

    def __init__( self, *args, **kwargs ):
        # Don't pass args or kwargs to dict.__init__, as it will bypass
        # our __setitem__
        super().__init__()
        self._as_list = {}
        self._last_key = None
        if args and isinstance( args[0], HTTPHeaders ) :   # Copy constructor
            [ self.add(k,v) for k,v in args[0].get_all() ]
        else:                                   # Dict-style initialization
            self.update( *args, **kwargs )

    # Additional public methods
    def add( self, name, value ):
        """Adds a new value for the given key."""
        norm_name = HTTPHeaders._normalize_name( name )
        self._last_key = norm_name
        if norm_name in self :
            # bypass our override of __setitem__ since it modifies _as_list
            super().__setitem__( norm_name, self[norm_name] + ',' + value )
            self._as_list[norm_name].append(value)
        else:
            self[norm_name] = value

    def get_list( self, name ):
        """Returns all values for the given header as a list."""
        norm_name = HTTPHeaders._normalize_name(name)
        return self._as_list.get( norm_name, [] )

    def get_all( self ):
        """Returns an iterable of all (name, value) pairs.

        If a header has multiple values, multiple pairs will be
        returned with the same name.
        """
        for name, li in self._as_list.items() :
            for value in li :
                yield (name, value)

    def parse_line( self, line ):
        """Updates the dictionary with a single header line.

        >>> h = HTTPHeaders()
        >>> h.parse_line("Content-Type: text/html")
        >>> h.get('content-type')
        'text/html'
        """
        if line[0].isspace() : # continuation of a multi-line header
            new_part = ' ' + line.lstrip()
            self._as_list[ self._last_key ][-1] += new_part
            super().__setitem__( 
                    self._last_key, self[self._last_key] + new_part )
        else:
            name, value = line.split( ":", 1 )
            self.add( name.strip(), value.strip() )

    @classmethod
    def parse( cls, headers ):
        """Returns a dictionary of HTTPHeaders instance from HTTP header text.

        >>> h = HTTPHeaders.parse(
        >>>         "Content-Type: text/html\\r\\nContent-Length: 42\\r\\n")
        >>> sorted(h.items())
        [('Content-Length', '42'), ('Content-Type', 'text/html')]
        """
        obj = cls()
        [ obj.parse_line( line ) for line in headers.splitlines() if line ]

        return obj

    # dict implementation overrides

    def __setitem__( self, name, value ):
        norm_name = HTTPHeaders._normalize_name(name)
        super().__setitem__( norm_name, value)
        self._as_list[norm_name] = [value]

    def __getitem__( self, name ):
        return super().__getitem__( HTTPHeaders._normalize_name(name) )

    def __delitem__( self, name ):
        norm_name = HTTPHeaders._normalize_name(name)
        super().__delitem__( norm_name )
        del self._as_list[norm_name]

    def __contains__( self, name ):
        norm_name = HTTPHeaders._normalize_name( name )
        return super().__contains__( norm_name )

    def get( self, name, default=None ):
        return super().get( HTTPHeaders._normalize_name(name), default )

    def update(self, *args, **kwargs):
        # dict.update bypasses our __setitem__
        for k, v in dict(*args, **kwargs).items() :
            self[k] = v

    _norm_patt = re.compile(r'^[A-Z0-9][a-z0-9]*(-[A-Z0-9][a-z0-9]*)*$')
    _normalized_headers = {}

    @staticmethod
    def _normalize_name( name ):
        """Converts a name to Http-Header-Case.

        >>> HTTPHeaders._normalize_name("coNtent-TYPE")
        'Content-Type'
        """
        try:
            return HTTPHeaders._normalized_headers[name]
        except KeyError:
            if HTTPHeaders._norm_patt.match(name) :
                normalized = name
            else:
                normalized = "-".join(w.capitalize() for w in name.split("-"))
            HTTPHeaders._normalized_headers[name] = normalized
            return normalized


class RequestHeader( HTTPHeaders ):
    """Sub class of HTTPHeaders that handles request headers."""

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )

    @classmethod
    def parse( cls, headers ):
        super().parse( headers )
        if 'Date' in self :
            self['Date'] = http_normalizedate( self['Date'] )

class ResponseHeader( HTTPHeaders ):
    """Sub class of HTTPHeaders that constructs response headers."""

    def __init__( self, reqheaders, *args, **kwargs ):
        self.reqhdrs = reqheaders
        super().__init__( *args, **kwargs )
        self['Date'] = http_fromdate( dt.datetime.now() )
