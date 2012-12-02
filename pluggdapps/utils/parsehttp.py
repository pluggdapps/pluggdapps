# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

"""Utility functions to parse and manipulate HTTP messages."""

import re, sys, calendar, email
from   collections  import UserDict
import datetime     as dt
from   urllib.parse import urlsplit, unquote, parse_qs, urlunsplit, quote, \
                           urlencode, urljoin
import urllib.request, urllib.error

from pluggdapps.utils.lib import parsecsv

strptime = dt.datetime.strptime
strftime = dt.datetime.strftime

DEFAULT_QVALUE = 1.0

__all__ = [
    #-- Attributes
    'hdr_str2camelcase', 'hdr_camelcase2str',
    #-- Functions
    'port_for_scheme', 'parse_startline', 'parse_url', 'make_url',
    'compare_url', 'parse_netpath', 'parse_formbody',
    'connection', 'parse_date', 'http_fromdate', 'http_todate',
    'parse_trailer', 'parse_transfer_encoding', 'accept', 'accept_charset',
    'accept_encoding', 'parse_content_length', 'parse_content_type',
    'parse_content_disposition',
    #-- Classes
    'HTTPHeaders',
]

re_OCTET  = r"*"
re_CHAR   = r"[\x00-\x7F]*"
re_UALPHA = r"[A-Z]*"
re_LALPHA = r"[a-z]*"
re_ALPHA  = r"[A-Za-z]*"
re_DIGIT  = r"[0-9]*"
re_HEX    = r"[0-9A-Fa-f]*"
re_CTL    = r"[\x00-\x1F\x7F]*"
re_CR     = r"\xD"
re_LF     = r"\xA"
re_SP     = r" "
re_HT     = r"\x9"
re_DQ     = r"\x22"

# End of line marker. End-of-line marker within an entity-body id defined by
# its associated media-type.
re_CRLF   = r"\xD\xA"

# Implied token separator. All linear white space, including folding, has the
# same semantics as SP.
re_LWS    = r"[\xD\xA][ \t]+"

# Any OCTET except CTLs, but including LWS.
# A CRLF is allowed in the definition of TEXT only as part of a header field
# continuation. It is expected that the folding LWS will be replaced with a
# single SP before interpretation of the TEXT value.
re_TEXT   = r"[\x20-\x7E\x80-\xFF\x9\xA\xD]*"

re_sep    = r"[\(\)<>@,;:\\\"/\[\]?=\{\} \t]" # Token separator

re_token  = r"[^\x00-\x1F\x7F\(\)<>@,;:\\\"/\[\]?=\{\} \t]+" # Token

re_quote  = r"\"[^\"]*\""

re_versn  = r"HTTP/1.1"

re_param  = ( r"(" + re_token + r")" +
              r"=" +
              r"(" + re_quote + r"|" + re_token + r")" )

re_dirtive= ( r"(" + re_token + r")" +
              r"(=" +
              r"(" + re_quote + r"|" + re_token + r"))?" )

hdr_str2camelcase = {
    # request headers
    'accept'              : b'Accept',
    'accept_charset'      : b'Accept-Charset',
    'accept_encoding'     : b'Accept-Encoding',
    'accept_language'     : b'Accept-Language',
    'authorization'       : b'Authorization',
    'expect'              : b'Expect',
    'from'                : b'From',
    'host'                : b'Host',
    'if_match'            : b'If-Match',
    'if_modified_since'   : b'If-Modified-Since',
    'if_none_match'       : b'If-None-Match',
    'if_range'            : b'If-Range',
    'if_unmodified_since' : b'If-Unmodified-Since',
    'max_forwards'        : b'Max-Forwards',
    'proxy_authorization' : b'Proxy-Authorization',
    'range'               : b'Range',
    'referer'             : b'Referer',
    'te'                  : b'TE',
    'user_agent'          : b'User-Agent',
    # response headers
    'accept_ranges'       : b'Accept-Ranges',
    'age'                 : b'Age',
    'etag'                : b'Etag',
    'location'            : b'Location',
    'proxy_authenticate'  : b'Proxy-Authenticate',
    'retry_after'         : b'Retry-After',
    'server'              : b'Server',
    'vary'                : b'Vary',
    'www_authenticate'    : b'WWW-Authenticate',
    # entity headers
    'allow'               : b'Allow',
    'content_encoding'    : b'Content-Encoding',
    'content_language'    : b'Content-Language',
    'content_length'      : b'Content-Length',
    'content_location'    : b'Content-Location',
    'content_md5'         : b'Content-MD5',
    'content_range'       : b'Content-Range',
    'content_type'        : b'Content-Type',
    'expires'             : b'Expires',
    'last_modified'       : b'Last-Modified',

    'cache_control'       : b'Cache-Control',
    'connection'          : b'Connection',
    'date'                : b'Date',
    'etag'                : b'ETag',
    'pragma'              : b'Pragma',
    'referer'             : b'Referer',
    'trailer'             : b'Trailer',
    'transfer_encoding'   : b'Transfer-Encoding',
    'upgrade'             : b'Upgrade',
    'via'                 : b'Via',
    'warning'             : b'Warning',
}

hdr_camelcase2str = {
    # request headers
    b'Accept'               : 'accept',
    b'Accept-Charset'       : 'accept_charset',
    b'Accept-Encoding'      : 'accept_encoding',
    b'Accept-Language'      : 'accept_language',
    b'Authorization'        : 'authorization',
    b'Expect'               : 'expect',
    b'From'                 : 'from',
    b'Host'                 : 'host',
    b'If-Match'             : 'if_match',
    b'If-Modified-Since'    : 'if_modified_since',
    b'If-None-Match'        : 'if_none_match',
    b'If-Range'             : 'if_range',
    b'If-Unmodified-Since'  : 'if_unmodified_since',
    b'Max-Forwards'         : 'max_forwards',
    b'Proxy-Authorization'  : 'proxy_authorization',
    b'Range'                : 'range',
    b'Referer'              : 'referer',
    b'TE'                   : 'te',
    b'User-Agent'           : 'user_agent',
    # response headers
    b'Accept-Ranges'        : 'accept_ranges',
    b'Age'                  : 'age',
    b'Etag'                 : 'etag',
    b'Location'             : 'location',
    b'Proxy-Authenticate'   : 'proxy_authenticate',
    b'Retry-After'          : 'retry_after',
    b'Server'               : 'server',
    b'Vary'                 : 'vary',
    b'WWW-Authenticate'     : 'www_authenticate',
    # entity headers
    b'Allow'                : 'allow',
    b'Content-Encoding'     : 'content_encoding',
    b'Content-Language'     : 'content_language',
    b'Content-Length'       : 'content_length',
    b'Content-Location'     : 'content_location',
    b'Content-MD5'          : 'content_md5',
    b'Content-Range'        : 'content_range',
    b'Content-Type'         : 'content_type',
    b'Expires'              : 'expires',
    b'Last-Modified'        : 'last_modified',

    b'Cache-Control'        : 'cache_control',
    b'Connection'           : 'connection',
    b'Date'                 : 'date',
    b'ETag'                 : 'etag',
    b'Pragma'               : 'pragma',
    b'Referer'              : 'referer',
    b'Trailer'              : 'trailer',
    b'Transfer-Encoding'    : 'transfer_encoding',
    b'Upgrade'              : 'upgrade',
    b'Via'                  : 'via',
    b'Warning'              : 'warning',
}

#---- Map response code to response message

def port_for_scheme( scheme ):
    """Calculate port based on ``scheme`` name. If scheme and port matches,
    port is left empty. Otherwise `port` is explicitly set to port number and
    returned as a string.
    
    ``scheme``, byte-string.
    """
    if scheme == b'http' : return 80
    elif scheme == b'https' : return 443
    else : return None

def parse_startline( startline ):
    """Every HTTP request starts with a start line specifying method, uri and
    version. Parse them and return a tuple of (method, uri, version). All
    elements in the return tuple will be available as byte-strings."""
    return [ x.strip( b' \t' ) for x in startline.split(b' ') ]


def parse_url( uri, host=None, scheme=None ):
    """Parse uri using urlsplit() method into its component parts.
    
    ``uri``,
        uri is expected in string format, decoded using 'utf8' encoding.

    ``host``,
        byte-string from HTTP `Host` header.
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
    
    `Refer to Section 5.2 in RFC 2616.txt`.
    """
    host = host.strip() if host else host
    try :
        host, port = host.split( b':', 1 )
    except :
        host, port = host, None
    r = urlsplit( uri )
    fn = lambda x : (x[0], (x[1].decode('utf8') if x[1] else x[1]))
    kwargs = { 'scheme' : r.scheme or scheme,
               'netloc' : r.netloc,
               'host'   : r.hostname or host,
               'port'   : r.port or port,
               'username' : r.username,
               'password' : r.password,
               'fragment' : r.fragment,
               'script' : b'',
             }
    kwargs = dict( map( fn, kwargs.items() ))
    kwargs['path'] = unquote( r.path.decode('utf8') )  # With default encoding
    kwargs['query'] = parse_qs( r.query ) # With default encoding
    r = UserDict( **kwargs )
    return r

def make_url( baseurl, path, query, fragment ):
    """Using the baseurl and the remaining variable part of a url namely
    path, query, fragment construct a full url that can be sent in response
    and interpreted by Clients.
    
    ``baseurl``,
        string of base-url with scheme and netlocation. Otherwise None,
        in which case relative-url is returned.

    ``path``,
        string of URL path value, will be quoted using urllib.parse.quote()
        before generating the final URL

    ``query``
        is expected as a dictionary key,value pairs, value being a list.
        Will be encoded using urllib.parse.urlencode()

    ``fragment``,
        string of fragment portion of the url.

    Return relative-url or absolute-url as a string.
    """
    path = quote( path ) if path else ''
    query = urlencode( query ) if query else ''
    fragment = fragment if fragment else ''
    relurl = urlunsplit( '', '', path, query, fragment )
    return urljoin( baseurl, relurl ) if baseurl else relurl

scheme2ports = {
    'http'  : '80',
    'https' : '443',
}
def compare_url( url1, url2 ):
    """Compare two URLs ``url1`` and ``url2`` based on RFC2616
    specification."""
    x = urlsplit( url1 )
    y = urlsplit( url2 )
    scheme1 = x.scheme.lower() or b'http'
    scheme2 = y.scheme.lower() or b'http'
    port1 = x.port or scheme2port.get( scheme1, b'80' )
    port2 = y.port or scheme2port.get( scheme2, b'80' )
    if scheme1 != scheme2 : return False
    if x.host.lower() != y.host.lower() : return False
    if port1 != port2 : return False
    if x.path != y.path : return False
    if x.query != y.query : return False
    if x.fragment != y.fragment : return False
    return True

def parse_netpath( netpath ):
    """Parse ``netpath`` string containing host-name and script-path into a
    tuple of ``(netloc, script-path)``. If script-path is absent, return
    ``(netloc, '')``."""
    parts = netpath.split('/', 1)
    netloc = parts.pop( 0 )
    script = '/' + (parts.pop( 0 ) if parts else '')
    return netloc, script 

def parse_formbody( content_type, body ):
    """HTML form values can be submited via POST or PUT methods, in which
    case, request Content-Type will be appropriately set. This function
    supports, ``application/x-www-form-urlencoded``, ``multipart/form-data``
    media-types. Note that files are submitted using multipart/form-data
    media-type.  Returns a dictionary of arguments.

    ``content_type``,
        Value as return from parse_content_type().
    """

    arguments, multiparts = {}, {}
    if content_type[:2] == ( b"application", b"x-www-form-urlencoded" ) :
        for name, values in parse_qs( body ).items() :
            arguments.setdefault( name, [] ).extend( filter( None, values ))

    elif content_type[0] == b"multipart" :
        for headers, value in parse_multipart(content_type, body) :
            distype, disparams = h.parse_content_disposition(
                                    headers.get( "content-disposition", None ))
            disparams = h.multivalue_dict( disparams )
            name = disparams.get( b'name', [None] )[0]

            if not name : continue

            if b'filename' in disparams :
                ctype = headers.get( 'content-type', None )
                ctype = b'/'.join( h.parse_content_type( ctype )[:2] )
                nvalue = [{ 'filename' : disparams[b'filename'],
                            'value'     : value,
                            'content-type' : ctype,
                            'headers'  : headers }]

            elif isinstance( value, list ) :
                nvalue = []
                for headers1, value1 in value :
                    distype1, disparams1 = \
                        h.parse_content_disposition(
                                headers1.get( "content-disposition", None ))
                    disparams1 = h.multivalue_dict( disparams1 )
                    ctype = headers1.get( 'content-type', None )
                    ctype = b'/'.join( h.parse_content_type( ctype )[:2] )
                    nvalue.append({ 'filename' : disparams1[b'filename'],
                                    'value' : value1,
                                    'content-type' : ctype,
                                    'headers' : headers1 })
                                
            else :
                nvalue = [ value ]

            multiparts.setdefault( name, [] ).extend( nvalue )

        return arguments, multiparts

def parse_multipart( content_type, data ):
    """Parses a multipart/form-data (including multipart/mixed) body.

    `content_type` is parsed using parse_content_type().
    Returns a list of multipart tuples,
        [ (Headers, value), ... ]
    """
    # The standard allows for the boundary to be quoted in the header,
    # although it's rare (it happens at least for google app engine
    # xmpp).  I think we're also supposed to handle backslash-escapes
    # here but I'll save that until we see a client that uses them
    # in the wild.
    params = h.multivalue_dict( content_type[2] )
    boundary = params[b'boundary'][0]

    if boundary.startswith(b'"') and boundary.endswith(b'"'):
        boundary = boundary[1:-1]

    data = data.rstrip( b'\r\n' )[ :(len(boundary) + 4) ]
    boundary = b"--" + boundary + b"\r\n"

    multiparts = []
    for part in data.split( boundary ) :
        if not part : continue
        if not part.endswith( b'\r\n' ) :
            raise Exception( 'Invalid multipart/form-data' )

        eoh = part.find(b"\r\n\r\n")
        headers = HTTPHeaders.parse( part[:eoh].decode("utf8") )
        distype, disparams = h.parse_content_disposition(
                                    headers.get( "content-disposition", None ))

        disparams = h.multivalue_dict( disparams )

        if distype not in ( b'form-data', b'file' ) : continue
        content_type1 = parse_content_type( 
                            headers.get( 'content-type', None ))

        value = part[eoh+4:]

        if content_type1[0] == b'multipart' :
            value = parse_multipart( content_type1, value )
        else :
            value = value[:-2] # Remove CRLF
        multiparts.append( (headers, value) )
    return multiparts

#---- Logic to parse HTTP headers

class HTTPHeaders( dict ):
    """Dictionary of HTTP headers for both request and response. Value of each
    key, lower-cased string, is represented as list of byte-string. If a
    header field occur in a request only once, then list of values will have
    only one element. `Refer RFC2616 for more information`.
    """

    @classmethod
    def parse( cls, hdrdata ):
        """Returns HTTPHeaders object."""
        def consume( obj, line ):
            name, value = line.split( b":", 1 )
            name = hdr_camelcase2str[ name.strip() ]
            pvalue = obj.get( name, None )
            obj[ name ] = value if pvalue == None else (pvalue+b', '+value)

        obj, prev_line = cls(), b''
        for line in hdrdata.splitlines() :
            if not line : continue

            if line[:1].isspace() : # continuation of a multi-line header
                prev_line += ' ' + line.lstrip(' \t')
            else :
                consume( obj, prev_line ) if prev_line else None
                prev_line = line

        consume( obj, prev_line ) if prev_line else None

        return obj


def parameters( ps=None, params=None ):
    """Parse parameter from list of byte-string `s`, 

    ``ps``,
        list of byte-string to parse for attribute and value
    ``params``
        list of (attr, value) pairs. Both attr and value are expected to be in
        byte-string.

    parameter               = attribute "=" value
    attribute               = token
    value                   = token | quoted-string

    to construct paramter string, pass a list of (attr, value) pairs in
    `params` kwarg.
    """
    if ps :
        params = []
        for p in ps :
            try :
                attr, val = re.match( p, re_param ).groups()
                params.append( (attr.lower(), val) )
            except :
                continue
        return params
    elif params :
        return b';'.join( attr + '=' + val for attr, val in params )

def directives( ds=b'', tokens=None ):
    """Parse directives from list of byte-string `ds`,

    ``ds``,
        List of byte-string to be parsed for directive.
    ``tokens``
        List of token or (attr, value) pair in byte-string to merge them into
        a single set of directives, separated by ';'.
    """
    if ds :
        tokens = []
        for d in ds :
            a,b,c = re.match( re_dirtive, d ).groups()
            tokens.append( (a, b or c) if (b or c) else a )
        return tokens
    elif tokens :
        return b';'.join( 
                    ( t[0] + b'=' + t[1] if isinstance(t, tuple) else t )
                    for t in tokens 
               )

def rules( s=None, rs=None ):
    """Parse comma seperated rules from `s`.
         ( *LWS element *( *LWS "," *LWS element ))

    ``s``,
        byte-string of rules separated by comma and LWS.
    ``rs``,
        List of rules in bytes-string.

    to contstruct a rule string, pass a list of byte-string in `rs` kwarg.
    """
    if s :
        return [ x.strip(b' \r\n\t') for x in s.split(b',') ]
    elif rs :
        return b', '.join( rs )

def qparam( parameters ):
    """Return the quality value, as float, found in `parameters`,

    ``parameters``,
        list of token or (attr, value) pair, where attr and value are in
        byte-string.
    """
    try :
        for attr, value in parameter :
            if attr == b'q' : return float( value )
        else :
            return None
    except :
        return None

def parse_simplevalue_q( value ):
    """Parse simple header with qvalue and return a list of,
        [ (tok, qvalue), ... ]

    where `tok` is a byte value and `qvalue` is float.
    """
    vals = []
    for v in rules( value ) :
        try :
            tok, qvalue = v.split(b';')
        except :
            tok, qvalue = v, DEFAULT_QVALUE
        else :
            _, qvalue = re.match( re_param, qvalue ).groups()
            qvalue = float( qvalue )
        vals.append( (tok, qvalue) )

    fn = lambda tok_q : -1.0 if tok_q[0] == b'*' else tok_q[1]
    return sorted( vals, key=fn, reverse=True )

def make_simplevalue_q( tokenrules ):
    """Make header value with qvalue from tokens,

    ``tokens``,
        [ (tok, qvalue), ... ]

    where, `tok` is byte-string and `qvalue` is float.
    """
    fn = lambda tok_q : tok_q[0] + str(tok_q[1]).encode( 'utf8' )
    return rules( rs=map( fn, tokenrules ))

#---- Generic headers

def connection( value ):
    """Return a list of lowercased token values from Connection-header-value.
    """
    if value == None : return None
    return list( map( lambda x : x.lower(), rules( value )))

rfc1123_format = "%a, %d %b %Y %H:%M:%S %Z"
rfc1036_format = "%A, %d-%b-%y %H:%M:%S %Z"
asctime_format = "%a %b %d %H:%M:%S %Y"
def parse_date( value ):
    """HTTP applications have historically allowed three different formats
    for the representation of date/time stamps::

      Sun, 06 Nov 1994 08:49:37 GMT  ; RFC 822, updated by RFC 1123
      Sunday, 06-Nov-94 08:49:37 GMT ; RFC 850, obsoleted by RFC 1036
      Sun Nov  6 08:49:37 1994       ; ANSI C's asctime() format

    The first format is preferred as an Internet standard. This function
    heuristically parses the date format (from request header) and changes the
    format to RFC 1123 format.  Returns ``datetime`` object
    """
    for fmt in [ rfc1123_format, rfc1036_format, asctime_format ] :
        try :
            dtime = strptime( datestr, fmt )
            break
        except :
            pass
    else :
        return None
    return dtime

def http_todate( datestr ):
    """Convert date-time string, RFC 1123 normalized format, to python datetime
    object."""
    return strptime( datestr, rfc1123_format )

def http_fromdate( dtime ):
    """Convert python datetime object to RFC 1123 date format."""
    return strftime( dtime, rfc1123_format )

def parse_trailer( value ):
    if value == None : return None
    return rules( value )

def parse_transfer_encoding( value=b'', tokenrules=[], prefix=b'' ):
    """
    Parse Transfer-Encoding header value,::

      transfer-coding         = "chunked" | transfer-extension
      transfer-extension      = token *( ";" parameter )

    ``value``,
        byte-string of Transfer-Encoding header value to parse.

    ``tokenrules``,
        list of rules, the format of the data is the same as what is return by
        this function for parsing Transfer-Encoding header value.

    ``prefix``,
        While making value byte-string from tokens, if this kwarg is present,
        as byte-string, join this with byte-string generated from
        `tokenrules`,

    Returns ``[ ( token, [ param ] ), ... ]``, where, ``param`` is either a
    token or a tuple of ``(attr, value)``.
    """
    if value :
        tokenrules = []
        for rule in rules(value) :
            parts = value.split( b';' )
            params = parameters( parts[1:] ) if parts[1:] else []
            tokenrules.append(
              ( parts[0].lower(), tuple( filter( None, params )))
            )
        return tokenrules

    elif tokenrules :
        fn = lambda r : r[0] + b';'.join( directives( tokens=r[1] ))
        return b'Transfer-Encoding:' + \
                        b'; '.join( prefix, rules(rs=map(fn, tokenrules)) )
    return None

#---- Request headers

def accept( value=b'', tokenrules=[], prefix=b'' ):
    """
    Parse Accept header value,::

      Accept         = "Accept" ":"
                          #( media-range [ accept-params ] )

      media-range    = ( "*/*"
                       | ( type "/" "*" )
                       | ( type "/" subtype )
                       ) *( ";" parameter )
      accept-params  = ";" "q" "=" qvalue *( accept-extension )
      accept-extension = ";" token [ "=" ( token | quoted-string ) ]

    ``value``,
        byte-string of Accept header value to parse.

    ``tokenrules``,
        list of rules, the format of the data is the same as what is return by
        this function for parsing Accept header value.

    ``prefix``,
        While making value byte-string from tokens, if this kwarg is present,
        as byte-string, join this with byte-string generated from
        `tokenrules`,

    Returns ``[ ( type, subtype, [ param ] ), ... ]``, where, ``param`` is
    either a token or a tuple of ``(attr, value)``. And the [ param ] list is
    sorted by q-value.
    """
    if value :
        mranges = []
        for v in rules( value ) :
            parts = v.split( b';' )
            try :
                typ, subtype = parts[0].split( b'/', 1 )
            except :
                typ, subtype = parts[0], b'*'
            mrange = [ typ, subtype, tuple( directives( ds=parts[1:] )) ]

        # sort media-ranges based on qvalue.
        rangeq = {}
        def quality( mrange ):
            q = qparam( mrange[2] )
            if mrange[0:2] == ( b'*', b'*' ) :
                rangeq.setdefault( b'*', q or DEFAULT_QVALUE )
            elif mrange[1] == b'*' :
                rangeq.setdefault( mrange[0], q or DEFAULT_QVALUE )
            return (mrange, q)

        def quality_sort( tok_q ):
            tok, q = tok_q
            q = rangeq.get( tok[0], DEFAULT_QVALUE ) if q == None else q
            key = q + len( tok )
            if tok[0] == b'*' : 
                key = key - 2.0
            elif tok[0] in rangeq :
                key = key - 1.0
            return key

        return sorted( map(quality, mranges), key=quality_sort, reverse=True )

    elif tokenrules :
        fn = lambda r : r[0]+b'/'+r[1] + b';'.join( directives( tokens=r[2] ))
        return b'Accept:' + b'; '.join( prefix, rules(rs=map(fn, tokenrules)) )

    return None

def accept_charset( value=b'', tokenrules=[], prefix=b'' ):
    """
    Parse Accept-Charset header value,::

      Accept-Charset = "Accept-Charset" ":"
                1#( ( charset | "*" )[ ";" "q" "=" qvalue ] )

    ``value``,
        byte-string of Accept-Charset header value to parse.

    ``tokenrules``,
        list of rules, the format of the data is the same as what is return by
        this function for parsing Accept-Charset header value.

    ``prefix``,
        While making value byte-string from tokens, if this kwarg is present,
        as byte-string, join this with byte-string generated from
        `tokenrules`,

    Returns, ``[ (charset, qvalue), ... ]``, where, ``qvalue`` is in float.
    """
    lowercase = lambda x : x[0].lower(), x[1]
    if value :
        return list( map( lowercase, parse_simplevalue_q(value) ))
    else :
        return b'Accept-Charset:' + \
                    b'; '.join( prefix, make_simplevalue_q( tokenrules ))


def accept_encoding( value, tokenrules=[], prefix=b'' ):
    """
    Parse Accept-Encoding header value,::

      Accept-Encoding  = "Accept-Encoding" ":"
                            1#( codings [ ";" "q" "=" qvalue ] )
      codings          = ( content-coding | "*" )

    ``value``,
        byte-string of Accept-Encoding header value to parse.

    ``tokenrules``,
        list of rules, the format of the data is the same as what is return by
        this function for parsing Accept-Encoding header value.

    ``prefix``,
        While making value byte-string from tokens, if this kwarg is present,
        as byte-string, join this with byte-string generated from
        `tokenrules`,

    Returns, ``[ (content-coding, qvalue), ... ]``
    """
    lowercase = lambda x : x[0].lower(), x[1]
    if value :
        return list( map( lowercase, parse_simplevalue_q(value) ))
    else :
        return b'Accept-Encoding:' + \
                    b'; '.join( prefix, make_simplevalue_q( tokenrules ))

#---- Response headers

#---- Entity headers

def parse_content_length( value ):
    """Return length as integer type."""
    return int(value) if value else value

def parse_content_type( value ):
    """Parse content type using grammar,::

      Content-Type   = "Content-Type" ":" media-type
      media-type     = type "/" subtype *( ";" parameter )
      type           = token
      subtype        = token
      parameter      = attribute "=" value
      attribute      = token
      value          = token | quoted-string

    Returns, ``[ type, subtype, [ (attr, value), ... ]``
    """
    if value == None : return value

    parts = value.lstrip().split( b';' )
    typ, subtype = parts[0].split( b'/' )
    params = parameters( parts[1:] ) if parts[1:] else []
    return typ, subtype, filter( None, params )

#---- additional features

def parse_content_disposition( value ):
    """Parse content disposition using grammar,::

      content-disposition = "Content-Disposition" ":"
                            disposition-type *( ";" disposition-parm )
      disposition-type = "attachment" | disp-extension-token
      disposition-parm = filename-parm | disp-extension-parm
      filename-parm = "filename" "=" quoted-string
      disp-extension-token = token
      disp-extension-parm = token "=" ( token | quoted-string )

    Returns, ``( token, [ (attr, value), ... ] )``
    """
    if not value : return value

    ps = value.split( b';' )
    params = parameters( parts[1:] ) if parts[1:] else []
    return ps[0].lower(), filter( None, params )

#---- Yet to be cleaned up.

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
