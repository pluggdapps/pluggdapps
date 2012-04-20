# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

# TODO :
#   * Improve function asbool() implementation.

from   __future__ import absolute_import, division, with_statement
import os, sys, re, fcntl, urllib, logging
from   urlparse import parse_qs  # Python 2.6+

from   pluggdapps.plugin import whichmodule

log = logging.getLogger( __name__ )

def parsecsv( line ):
    """Parse a single line of comma separated values, into a list of strings"""
    vals = line and line.split( ',' ) or []
    vals = filter( None, [ v.strip(' \t') for v in vals ] )
    return vals


def parsecsvlines( lines ):
    """Parse a multi-line text where each line contains comma separated values.
    """
    return parsecsv( ', '.join(lines.splitlines()) )


def subclassof( cls, supers ):
    """Check whether cls is a subclass of one of the super-classes passed in
    `supers`."""
    for sup in supers :
        if issubclass( cls, sup ) : return sup
    return None


class ConfigDict( dict ):
    """A collection of configuration settings. When a fresh key, a.k.a 
    configuration parameter is added to this dictionary, it can be provided
    as `ConfigItem` object or as a dictionary containing key,value pairs
    supported by ConfigItem.

    Used as return type for default_settings() method specified in 
    :class:`ISettings`
    """
    def __init__( self, *args, **kwargs ):
        self._spec = {}
        dict.__init__( self, *args, **kwargs )

    def __setitem__( self, name, value ):
        if not isinstance( value, (ConfigItem, dict) ) :
            raise Exception( "Type received %r not `ConfigItem` or `dict`'" )

        value = value if isinstance(value, ConfigItem) else ConfigItem(value)
        self._spec[name] = value
        val = value['default']
        return dict.__setitem__( self, name, val )

    def specifications( self ):
        return self._spec


class ConfigItem( dict ):
    """Convenience class to encapsulate config parameter description, which
    is a dictionary of following keys,

    ``default``,
        Default value for this settings a.k.a configuration parameter.
        Compulsory field.
    ``format``,
        Comma separated value of valid format. Allowed formats are,
            str, unicode, basestring, int, bool, csv.
        Compulsory field.
    ``help``,
        Help string describing the purpose and scope of settings parameter.
    ``webconfig``,
        Boolean, specifying whether the settings parameter is configurable via
        web. Default is True.
    ``options``,
        List of optional values that can be used for configuring this 
        parameter.
    """
    fmt2str = {
        str     : 'str', unicode : 'unicode',  bool : 'bool', int   : 'int',
        'csv'   : 'csv'
    }
    def _options( self ):
        opts = self.get( 'options', '' )
        return opts() if callable(opts) else opts

    # Compulsory fields
    default = property( lambda s : s['default'] )
    formats = property( lambda s : parsecsvlines( s['formats'] ) )
    help = property( lambda s : s.get('help', '') )
    webconfig = property( lambda s : s.get('webconfig', True) )
    options = property( _options )

def asbool( val, default=None ):
    """Convert a string representation of boolean value to boolean type."""
    try :
        if isinstance(val, basestring) :
            v = True if val.lower() == 'true' else False
        else :
            v = bool(val)
    except :
        v = default
    return v

def asint( val, default=None ):
    """Convert string representation of integer value to integer type."""
    try    : v = int( val )
    except : v = default
    return v

def asfloat( val, default=None ):
    """Convert string representation of float value to floating type."""
    try    : v = float( val )
    except : v = default
    return v

def settingsfor( prefix, sett ):
    """Parse `settings` keys starting with `prefix` and return a dictionary of
    corresponding options."""
    l = len(prefix)
    return dict([ (k[l:], sett[k]) for k in sett if k.startswith(prefix) ])

def timedelta_to_seconds( td ) :
    """Equivalent to td.total_seconds() (introduced in python 2.7)."""
    return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10 ** 6) / float(10 ** 6)

def set_close_exec( *fds ):
    for fd in fds :
        flags = fcntl.fcntl(fd, fcntl.F_GETFD)
        fcntl.fcntl(fd, fcntl.F_SETFD, flags | fcntl.FD_CLOEXEC)

def set_nonblocking( *fds ):
    for fd in fds :
        flags = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

class ObjectDict(dict):
    """Makes a dictionary behave like an object."""
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        self[name] = value

def parse_startline( startline ):
    try :
        method, uri, version = startline.split(" ")
    except :
        method = None
    if not version.startswith("HTTP/") :
        method = version = None
    return method, uri, version

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


def call_entrypoint( distribution, group, name, *args, **kwargs ):
    """If an entrypoint is callable, use this api to both identify the entry
    point, evaluate them by loading and calling it. 
    
    Return the result from the called function. Note that the entrypoint must be
    uniquely identified using
        ``dist``, ``group`` and ``name``.
    """
    devmod = kwargs.pop( 'devmod', False )
    try :
        ep = distribution.get_entry_info( group, name )
        return ep.load()( *args, **kwargs ) if ep else None
    except :
        if devmod : raise
    return None

def docstr( obj ):
    """Return the doc-string for the object."""
    return getattr( obj, '__doc__', '' ) or ''


_UTF8_TYPES = (bytes, type(None))
def utf8( value ):
    """Converts a string argument to a byte string.

    If the argument is already a byte string or None, it is returned unchanged.
    Otherwise it must be a unicode string and is encoded as utf8.
    """
    if isinstance(value, _UTF8_TYPES):
        return value
    assert isinstance(value, unicode)
    return value.encode("utf-8")

_TO_UNICODE_TYPES = (unicode, type(None))
def to_unicode( value ):
    """Converts a string argument to a unicode string.

    If the argument is already a unicode string or None, it is returned
    unchanged.  Otherwise it must be a byte string and is decoded as utf8.
    """
    if isinstance( value, _TO_UNICODE_TYPES ):
        return value
    assert isinstance( value, bytes )
    return value.decode("utf-8")

_BASESTRING_TYPES = (basestring, type(None))
def to_basestring(value):
    """Converts a string argument to a subclass of basestring.

    In python2, byte and unicode strings are mostly interchangeable,
    so functions that deal with a user-supplied argument in combination
    with ascii string constants can use either and should return the type
    the user supplied.  In python3, the two types are not interchangeable,
    so this method is needed to convert byte strings to unicode.
    """
    if isinstance(value, _BASESTRING_TYPES):
        return value
    assert isinstance(value, bytes)
    return value.decode("utf-8")

def recursive_unicode( obj ):
    """Walks a simple data structure, converting byte strings to unicode.
    Supports lists, tuples, and dictionaries.
    """
    if isinstance(obj, dict):
        return dict( (recursive_unicode(k), recursive_unicode(v))
                     for (k, v) in obj.iteritems() )
    elif isinstance(obj, list):
        return list( recursive_unicode(i) for i in obj )
    elif isinstance(obj, tuple):
        return tuple( recursive_unicode(i) for i in obj )
    elif isinstance( obj, bytes ):
        return to_unicode(obj)
    else:
        return obj

# When dealing with the standard library across python 2 and 3 it is
# sometimes useful to have a direct conversion to the native string type
native_str = to_unicode if str is unicode else utf8

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
            return urllib.unquote_plus(to_basestring(value), encoding=encoding)

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

def parse_multipart_form_data(boundary, data, arguments, files):
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


"""Convert objects from JSON format to python. And vice-versa."""
import json
def json_encode( value ):
    """JSON-encodes the given Python object."""
    # JSON permits but does not require forward slashes to be escaped.
    # This is useful when json data is emitted in a <script> tag
    # in HTML, as it prevents </script> tags from prematurely terminating
    # the javscript.  Some json libraries do this escaping by default,
    # although python's standard library does not, so we do it here.
    # http://stackoverflow.com/questions/1580647/json-why-are-forward-slashes-escaped
    return json.dumps( recursive_unicode(value) ).replace( "</", "<\\/" )

def json_decode(value):
    """Returns Python objects for the given JSON string."""
    return json.loads( to_basestring(value) )


# Unit-test

from pluggdapps.unittest import UnitTestBase

class UnitTest_Util( UnitTestBase ):

    def test( self ):
        self.test_whichmodule()
        self.test_parsecsv()

    def test_whichmodule( self ):
        log.info("Testing whichmodule() ...")
        assert whichmodule(UnitTest_Util).__name__ == 'pluggdapps.util'
        assert whichmodule(self).__name__ == 'pluggdapps.util'
        assert whichmodule(whichmodule).__name__ == 'pluggdapps.plugin'

    def test_parsecsv( self ):
        log.info("Testing parsecsv() ...")
