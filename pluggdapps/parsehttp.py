# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

"""HTTP utility functions."""

import logging, re, sys, urllib, calendar, email, hashlib, socket
from   urlparse import urlsplit, parse_qs  # Python 2.6+

from   pluggdapps.bsu       import native_str, utf8
from   pluggdapps.util      import ObjectDict

__all__ = [
    'parse_startline', 'convert_header_value', 'compute_etag', 'HTTPFile', 
    'HTTPHeaders', 'url_unescape', 'parse_qs_bytes', 'url_concat',
    'parse_multipart_form_data',
]

log = logging.getLogger( __name__ )

def _port_for_scheme( scheme ):
    if scheme == 'http' :
        port = 80
    elif scheme == 'https' : 
        port = 443
    else :
        port =None
    return port

def parse_scheme( hdrs, xheaders ):
    if xheaders : # AWS uses X-Forwarded-Proto
        scheme = hdrs.get("X-Scheme", hdrs.get("X-Forwarded-Proto", None))
        if scheme not in ("http", "https"):
            scheme = "http"
    else :
        scheme = None
    return scheme

def parse_url( scheme, host ):
    sch, _, path, query, frag = r = urlparse.urlsplit( native_str(uri) )
    scheme = scheme or sch
    if host and ':' in host :
        host, port = host.split(':', 1)
    elif host and r.port :
        port = r.port
    elif host :
        port = _port_for_scheme( scheme )
    else :
        host = r.hostname
        port = r.port or _port_for_scheme( scheme )
    return host, port, path, query, frag

def parse_startline( startline ):
    """Every HTTP request starts with a start line specifying method, uri and
    version. Parse them and return a tuple of (method, uri, version)."""
    try :
        method, uri, version = startline.split(" ")
    except :
        log.error( "Malformed HTTP version in HTTP Request-Line" )
        method = uri = version = None
    if not version.startswith("HTTP/") :
        log.error( "Unknown HTTP Version %r", version )
    return method, uri, version

def parse_remoteip( addr, hdrs, xheaders ):
    if xheaders : # Squid uses X-Forwarded-For, others use X-Real-Ip
        remote_ip = hdrs.get("X-Real-Ip", hdrs.get("X-Forwarded-For", None))
        if not valid_ip( remote_ip ):
            remote_ip = addr
    else :
        remote_ip = addr
    return remote_ip

def parse_query( self, query ):
    arguments = {}
    for name, values in parse_qs_bytes(query).iteritems():
        values = filter( None, values )
        if values:
            arguments[name] = values
    return arguments

def parse_body( method, headers, body ):
    arguments, files = {}, {}
    content_type = headers.get( "Content-Type", "" )
    if method in ("POST", "PUT"):
        if content_type.startswith( "application/x-www-form-urlencoded" ):
            for name, values in parse_qs_bytes( native_str(body) ).items() :
                values = filter(None, values)
                if values:
                    arguments.setdefault( name, [] ).extend( values )
        elif content_type.startswith( "multipart/form-data" ):
            fields = content_type.split(";")
            for field in fields:
                k, sep, v = field.strip().partition("=")
                if k == "boundary" and v:
                    args, files = parse_multipart_form_data( utf8(v), body )
                    arguments.update( args )
                    files.update( files )
                    break
            else:
                log.warning( "Invalid multipart/form-data" )
    return arguments, files

def convert_header_value( value ):
    """Transform `value` to marshal them as HTTP header value.

    If a datetime is given, we automatically format it according to the
    HTTP specification. If the value is not a string, we convert it to
    a string. All header values are then encoded as UTF-8."""
    if isinstance( value, bytes ):
        pass
    elif isinstance( value, unicode ):
        value = value.encode('utf-8')
    elif isinstance( value, (int, long) ):
        # return immediately since we know the converted value will be safe
        return str(value)
    elif isinstance( value, dt.datetime ):
        t = calendar.timegm( value.utctimetuple() )
        return email.utils.formatdate( t, localtime=False, usegmt=True )
    else:
        raise TypeError( "Unsupported header value %r" % value )
    # If \n is allowed into the header, it is possible to inject
    # additional headers or split the request. Also cap length to
    # prevent obviously erroneous values.
    if len(value) > 4000 or re.match( b"[\x00-\x1f]", value ):
        raise ValueError( "Unsafe header value %r", value )
    return value


def compute_etag( write_buffer ) :
    """Computes the etag header to be used for this request's response."""
    hasher = hashlib.sha1()
    map( hasher.update, write_buffer )
    return '"%s"' % hasher.hexdigest()

class HTTPFile( ObjectDict ):
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
    def __init__( self, *args, **kwargs ):
        # Don't pass args or kwargs to dict.__init__, as it will bypass
        # our __setitem__
        dict.__init__( self )
        self._as_list = {}
        self._last_key = None
        if (len(args) == 1 and len(kwargs) == 0 and
            isinstance(args[0], HTTPHeaders)):
            # Copy constructor
            for k,v in args[0].get_all():
                self.add(k,v)
        else:
            # Dict-style initialization
            self.update(*args, **kwargs)

    # Additional public methods
    def add( self, name, value ):
        """Adds a new value for the given key."""
        norm_name = HTTPHeaders._normalize_name(name)
        self._last_key = norm_name
        if norm_name in self :
            # bypass our override of __setitem__ since it modifies _as_list
            dict.__setitem__( self, norm_name, self[norm_name] + ',' + value )
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
        for name, list in self._as_list.iteritems():
            for value in list:
                yield (name, value)

    def parse_line( self, line ):
        """Updates the dictionary with a single header line.

        >>> h = HTTPHeaders()
        >>> h.parse_line("Content-Type: text/html")
        >>> h.get('content-type')
        'text/html'
        """
        if line[0].isspace():
            # continuation of a multi-line header
            new_part = ' ' + line.lstrip()
            self._as_list[self._last_key][-1] += new_part
            dict.__setitem__(
                self, self._last_key, self[self._last_key] + new_part )
        else:
            name, value = line.split(":", 1)
            self.add(name, value.strip())

    @classmethod
    def parse( cls, headers ):
        """Returns a dictionary from HTTP header text.

        >>> h = HTTPHeaders.parse("Content-Type: text/html\\r\\nContent-Length: 42\\r\\n")
        >>> sorted(h.iteritems())
        [('Content-Length', '42'), ('Content-Type', 'text/html')]
        """
        h = cls()
        for line in headers.splitlines():
            if line:
                h.parse_line(line)
        return h

    # dict implementation overrides

    def __setitem__(self, name, value):
        norm_name = HTTPHeaders._normalize_name(name)
        dict.__setitem__(self, norm_name, value)
        self._as_list[norm_name] = [value]

    def __getitem__(self, name):
        return dict.__getitem__(self, HTTPHeaders._normalize_name(name))

    def __delitem__(self, name):
        norm_name = HTTPHeaders._normalize_name(name)
        dict.__delitem__(self, norm_name)
        del self._as_list[norm_name]

    def __contains__(self, name):
        norm_name = HTTPHeaders._normalize_name(name)
        return dict.__contains__(self, norm_name)

    def get(self, name, default=None):
        return dict.get(self, HTTPHeaders._normalize_name(name), default)

    def update(self, *args, **kwargs):
        # dict.update bypasses our __setitem__
        for k, v in dict(*args, **kwargs).iteritems():
            self[k] = v

    _NORMALIZED_HEADER_RE = re.compile(r'^[A-Z0-9][a-z0-9]*(-[A-Z0-9][a-z0-9]*)*$')
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
            if HTTPHeaders._NORMALIZED_HEADER_RE.match(name):
                normalized = name
            else:
                normalized = "-".join([w.capitalize() for w in name.split("-")])
            HTTPHeaders._normalized_headers[name] = normalized
            return normalized


# python 3 changed things around enough that we need two separate
# implementations of url_unescape.  We also need our own implementation
# of parse_qs since python 3's version insists on decoding everything.
if sys.version_info[0] < 3:
    def url_unescape( value, encoding='utf-8' ):
        """Decodes the given value from a URL.

        The argument may be either a byte or unicode string.

        If encoding is None, the result will be a byte string.  Otherwise,
        the result is a unicode string in the specified encoding.
        """
        if encoding is None:
            return urllib.unquote_plus( utf8(value) )
        else:
            return unicode( urllib.unquote_plus(utf8(value)), encoding )

    parse_qs_bytes = parse_qs
else:
    def url_unescape( value, encoding='utf-8' ):
        """Decodes the given value from a URL.

        The argument may be either a byte or unicode string.

        If encoding is None, the result will be a byte string.  Otherwise,
        the result is a unicode string in the specified encoding.
        """
        if encoding is None:
            return urllib.parse.unquote_to_bytes(value)
        else:
            return urllib.unquote_plus(to_unicode(value), encoding=encoding)

    def parse_qs_bytes(qs, keep_blank_values=False, strict_parsing=False):
        """Parses a query string like urlparse.parse_qs, but returns the
        values as byte strings.

        Keys still become type str (interpreted as latin1 in python3!)
        because it's too painful to keep them as byte strings in
        python3 and in practice they're nearly always ascii anyway.
        """
        # This is gross, but python3 doesn't give us another way.
        # Latin1 is the universal donor of character encodings.
        result = parse_qs( qs, keep_blank_values, strict_parsing,
                           encoding='latin1', errors='strict' )
        encoded = {}
        for k, v in result.iteritems():
            encoded[k] = [i.encode('latin1') for i in v]
        return encoded

def url_concat(url, args):
    """Concatenate url and argument dictionary regardless of whether
    url has existing query parameters.

    >>> url_concat("http://example.com/foo?a=b", dict(c="d"))
    'http://example.com/foo?a=b&c=d'
    """
    if not args:
        return url
    if url[-1] not in ('?', '&'):
        url += '&' if ('?' in url) else '?'
    return url + urllib.urlencode(args)

def parse_multipart_form_data( boundary, data ):
    """Parses a multipart/form-data body.

    The boundary and data parameters are both byte strings.
    The dictionaries given in the arguments and files parameters
    will be updated with the contents of the body.
    """
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
        headers = HTTPHeaders.parse(part[:eoh].decode("utf-8"))
        disp_header = headers.get("Content-Disposition", "")
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
    key = parts.next()
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

def valid_ip( ip ):
    try:
        res = socket.getaddrinfo( ip, 0, socket.AF_UNSPEC,
                                  socket.SOCK_STREAM,
                                  0, socket.AI_NUMERICHOST )
        return bool(res)
    except socket.gaierror, e:
        if e.args[0] == socket.EAI_NONAME:
            return False
        raise
    return True

