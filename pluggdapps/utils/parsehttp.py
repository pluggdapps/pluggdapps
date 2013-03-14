# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

"""Utility functions to parse and manipulate HTTP messages."""

import re, sys, calendar, email, time
from   collections  import UserDict
import datetime     as dt
from   urllib.parse import urlsplit, unquote, parse_qs, urlunsplit, quote, \
                           urlencode, urljoin
import urllib.request, urllib.error

from pluggdapps.utils.lib import parsecsv, print_exc

strptime = dt.datetime.strptime
strftime = dt.datetime.strftime

DEFAULT_QVALUE = 1.0

__all__ = [
    #-- Attributes
    'hdr_str2camelcase', 'hdr_camelcase2str',
    #-- Functions
    'port_for_scheme', 'parse_startline', 'parse_url', 'make_url',
    'compare_url', 'parse_netpath', 'parse_formbody',
    'parse_connection', 'parse_date', 'http_fromdate', 'http_todate',
    'parse_transfer_encoding', 'make_transfer_encoding', 'parse_accept',
    'make_accept', 'parse_accept_charset', 'make_accept_charset',
    'parse_accept_encoding', 'make_accept_encoding',
    'parse_accept_language', 'make_accept_language', 'parse_content_length', 
    'parse_content_type', 'parse_content_disposition',
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

re_qparam = r"q=([0-9]\.[0-9]{0,3})"

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
    version. Parse them and return a tuple of (method, uri, version).
    
    ``startline`` is expected in bytes and all the elements in returned tuple
    will be in byte-strings as well."""
    return [ x.strip( b' \t' ) for x in startline.split(b' ') ]


def parse_url( uri, host=None, scheme=None ):
    """Using stdlib's urllib.parse.urlsplit() API, parse ``uri`` into its
    component parts.
    
    ``uri``,
        byte-string of request-url, decoded using 'utf-8' encoding.

    ``host``,
        byte-string from HTTP `Host` header.
        Many times uri, as found in the request startline, have `abs_path`
        alone, in which case, optional host name as found in the `Host` header
        can be supplied. It will be applied on the urlsplit() result.
        
        Note that as per RFC definition Host header can also contain port
        address.

    ``scheme``,
        Default scheme to use while parsing the url. Directly passed to
        urllib.parse.urlsplit().

    Returns a UserDict with following keys,
        scheme, netloc, path, query, fragment, username, password, hostname,
        port, script - all of them in string type.

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
    fn = lambda x : x.decode('utf-8') if isinstance(x, bytes) else None
    kwargs = { 'scheme'   : (r.scheme or scheme),
               'netloc'   : r.netloc,
               'host'     : (r.hostname or host),
               'port'     : (r.port or port),
               'username' : r.username,
               'password' : r.password,
               'fragment' : r.fragment,
               'script'   : b'',
             }
    kwargs = { k : fn(v) for k, v in kwargs.items() }
    kwargs['path'] = unquote( r.path.decode('utf8') )
    kwargs['query'] = parse_qs( r.query ) # With default encoding
    r = UserDict( **kwargs )
    return r

def make_url( baseurl, path, query, fragment ):
    """Using the baseurl and the remaining variable part of a url namely
    path, query, fragment construct a full url that can be sent in response
    and interpreted by clients.
    
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
    relurl = urlunsplit([ '', '', path, query, fragment ])
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

    ``body``
        Byte string of HTTP request body.
    """

    arguments, multiparts = {}, {}
    if not( content_type and body ) : return arguments, multiparts

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
    key, lower-cased string, is represented as a byte-string of comma separated 
    values. `Refer RFC2616 for more information`.
    """

    @classmethod
    def parse( cls, hdrdata ):
        """Returns HTTPHeaders object."""
        def consume( obj, line ):
            name, value = line.split( b":", 1 )
            name = name.strip()
            name = hdr_camelcase2str.get(name, name.replace(b'-',b'_').lower())
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
        consume( obj, prev_line ) if prev_line else None    # Corner case

        return obj


def parse_parameters( ls=[] ):
    """Parse parameter from list of byte-strings `ls`,

    .. code-block:: ini
        :linenos:

        parameter  = attribute "=" value
        attribute  = token
        value      = token | quoted-string

    Return a list of (attr,value) tuple where both ``attr`` and ``value`` are
    byte-strings.
    """
    params = []
    for s in ls :
        try :
            attr, val = re.match( s, re_param.encode('utf-8') ).groups()
            params.append( (attr.lower(), val) )
        except : continue
    return params

def make_parameters( params=[] ):
    """Reverse of parse_parameters().

    ``params``
        list of (attr, value) pairs. Both attr and value are expected to be in
        byte-string.

    Return byte-string of parameters.
    """
    return b';'.join( attr + '=' + val for attr, val in params )

def parse_directives( ls=[] ):
    """Parse directives from list of byte-string ``ls``.

    Return a list of tokens as (attr, value) where ``attr`` and ``value`` are
    byte-strings.
    """
    tokens = []
    for s in ls :
        try :
            a,b,c = re.match( re_dirtive.encode('utf-8'), s ).groups()
            tokens.append( (a, b or c) if (b or c) else a )
        except : continue
    return tokens

def make_directives( tokens=[] ):
    """Reverse of parse_directives().

    Return a byte-string of directive.
    """
    return b';'.join([ ( t[0] + b'=' + t[1] if isinstance(t, tuple) else t )
                       for t in tokens ])

def parse_rules( s=b'' ):
    """Parse comma seperated rules from byte-string ``s``.
    
    ``( *LWS element *( *LWS "," *LWS element ))``

    Return a list of byte-string rules.
    """
    return list( filter( None, [x.strip(b' \r\n\t') for x in s.split(b',')] ))

def make_rules( rs=[] ):
    """Reverse of parse_rules()
    Return byte-string of comma separated rules.
    """
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
    for v in parse_rules( value ) :
        try :
            tok, qvalue = v.split(b';')
        except :
            tok, qvalue = v, DEFAULT_QVALUE
        else :
            _, qvalue = re.match( re_param.encode('utf-8'), qvalue ).groups()
            qvalue = float( qvalue )
        vals.append( (tok, qvalue) )

    fn = lambda tok_q : ( -1.0 if tok_q[0] == b'*' else tok_q[1] )
    return sorted( vals, key=fn, reverse=True )

def make_simplevalue_q( tokenrules ):
    """Make header value with qvalue from tokens,

    ``tokens``,
        [ (tok, qvalue), ... ]

    where, `tok` is byte-string and `qvalue` is float.
    """
    fn = lambda tok_q : tok_q[0] + str(tok_q[1]).encode( 'utf8' )
    return make_rules( map( fn, tokenrules ))

#---- Generic headers

def parse_connection( value ):
    """Return a list of lowercased token values, in byte-strings, from 
    Connection header field.
    """
    if value == None : return None
    return list( map( lambda x : x.lower(), parse_rules( value )))

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
    value = value.decode('utf-8') if isinstance( value, bytes ) else value
    for fmt in [ rfc1123_format, rfc1036_format, asctime_format ] :
        try :
            dtime = strptime( value, fmt )
            break
        except :
            pass
    else :
        return None
    return time.mktime( dtime.timetuple() )

def http_todate( datestr ):
    """Convert date-time string, RFC 1123 normalized format, to python datetime
    object."""
    return strptime( datestr, rfc1123_format )

def http_fromdate( dtime, tzinfo=None ):
    """Convert timestamp adjusting it to GMT using RFC 1123 date format. 
    Return string."""
    return time.strftime( rfc1123_format, time.gmtime( dtime ))[:-3] + 'GMT'

def parse_transfer_encoding( value=b'' ):
    """Parse Transfer-Encoding header value,

    .. code-block:: ini
        :linenos:

        transfer-coding      = "chunked" | transfer-extension
        transfer-extension   = token *( ";" parameter )

    ``value``,
        byte-string of Transfer-Encoding header value to parse.

    Returns ``[ ( token, param ), ... ]``, where, ``token`` and ``param`` 
    are byte-strings. ``token`` is also lower-cased.
    """
    tokenrules = []
    for rule in parse_rules(value) :
        try    : token, params = rule.split( b';', 1 )
        except : token, params = rule, b''
        tokenrules.append( (token.lower(), params) )
    return tokenrules

def make_transfer_encoding( tokenrules=[], prefix=b'' ):
    """Reverse of parse_transfer_encoding().

    ``tokenrules``,
        list of rules, the format of the data is the same as what is return by
        this function for parsing Transfer-Encoding header value.

    ``prefix``,
        While making value byte-string from tokens, if this kwarg is present,
        as byte-string, join this with byte-string generated from
        `tokenrules`,

    Return byte-string.
    """
    fn = lambda r : r[0] + b';'.join( make_directives( r[1] ))
    value = b'; '.join( prefix, make_rules( map( fn, tokenrules )))
    return b'Transfer-Encoding:' + value

#---- Request headers

def parse_accept( value=b'' ):
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

    Returns ``[ ( '<type>/<subtype>', q, param ), ... ]``, where, ``param`` is
    a byte-string representing media-type parameters and ``q`` is quality
    value in float for media-type.
    """
    mranges = []
    rangeq = {}
    for rule in parse_rules( value ) :
        try    : mt, params = rule.split( b';', 1 )
        except : mt, params = rule, b''
        q = re.search( re_qparam.encode('utf-8'), params )
        q = float( q.groups()[0] ) if q else None

        if mt == b'*/*' :
            rangeq.setdefault( b'*', q or DEFAULT_QVALUE )
        elif mt.endswith( b'/*' ) :
            rangeq.setdefault( mt.split(b'/',1)[0],  q or DEFAULT_QVALUE )

        mranges.append( (mt.strip().decode('utf-8'), q, params) )

    mranges = [( mt, q or rangeq.get(mt.split('/', 1)[0], DEFAULT_QVALUE),
                 params ) for mt, q, params in mranges ]

    def quality_sort( mrange ):
        mt, q, params = mrange
        return q + len( params.split(b';') )

    return sorted( mranges, key=quality_sort, reverse=True )

def make_accept( tokenrules=[], prefix=b'' ):
    """Reverse of parse_accept()

    ``tokenrules``,
        list of rules, the format of the data is the same as what is return by
        this function for parsing Accept header value.

    ``prefix``,
        While making value byte-string from tokens, if this kwarg is present,
        as byte-string, join this with byte-string generated from
        `tokenrules`,

    Return byte-string.
    """
    fn = lambda r : r[0]+b'/'+r[1] + b';'.join( make_directives( r[2] ))
    return b'Accept:' + b'; '.join( prefix, make_rules(map(fn, tokenrules)) )

def parse_accept_charset( value=b'' ):
    """Parse Accept-Charset header value,::

      Accept-Charset = "Accept-Charset" ":"
                1#( ( charset | "*" )[ ";" "q" "=" qvalue ] )

    ``value``,
        byte-string of Accept-Charset header value to parse.

    Returns, ``[ (charset, qvalue), ... ]``, where, ``charset`` is in string
    and ``qvalue`` is in float. The returned list is sorted by qvalue which is
    in float.
    """
    lowercase = lambda x : (x[0].decode('utf8').lower(), x[1])
    return list( map( lowercase, parse_simplevalue_q(value) ))

def make_accept_charset( value=b'', tokenrules=[], prefix=b'' ):
    """Reverse of parse_accept_charset()

    ``tokenrules``,
        list of rules, the format of the data is the same as what is return by
        this function for parsing Accept-Charset header value.

    ``prefix``,
        While making value byte-string from tokens, if this kwarg is present,
        as byte-string, join this with byte-string generated from
        `tokenrules`,

    Return byte-string.
    """
    value = b'; '.join( prefix, make_simplevalue_q( tokenrules ))
    return b'Accept-Charset:' + value


def parse_accept_encoding( value=b'' ):
    """Parse Accept-Encoding header value,::

      Accept-Encoding  = "Accept-Encoding" ":"
                            1#( codings [ ";" "q" "=" qvalue ] )
      codings          = ( content-coding | "*" )

    ``value``,
        byte-string of Accept-Encoding header value to parse.

    Returns, ``[ (content-coding, qvalue), ... ]``, where ``content-coding``
    is in string and ``qvalue`` is in float. Returned list is sorted by
    qvalue.
    """
    lowercase = lambda x : (x[0].decode('utf8').lower(), x[1])
    tokenrules = list( map( lowercase, parse_simplevalue_q(value) ))
    tokens = dict(tokenrules)
    if ('identity' not in tokens) and (tokens.get('*', 1.0) != 0.0) :
        tokenrules.append( ('identity', 1.0) )
    return tokenrules

def make_accept_encoding( tokenrules=[], prefix=b'' ):
    """Reverse of parse_accept_encoding()

    ``tokenrules``,
        list of rules, the format of the data is the same as what is return by
        this function for parsing Accept-Encoding header value.

    ``prefix``,
        While making value byte-string from tokens, if this kwarg is present,
        as byte-string, join this with byte-string generated from
        `tokenrules`,

    Return byte-string.
    """
    value = b'; '.join( prefix, make_simplevalue_q( tokenrules ))
    return b'Accept-Encoding:' + value

def parse_accept_language( value=b'' ):
    """Parse Accept-Language header value,::

      Accept-Language = "Accept-Language" ":"
                        1#( language-range [ ";" "q" "=" qvalue ] )
      language-range  = ( ( 1*8ALPHA *( "-" 1*8ALPHA ) ) | "*" )

    ``value``,
        byte-string of Accept-Language header value to parse.

    Returns, ``[ (language, qvalue), ... ]``, where ``language`` is in string
    and ``qvalue`` is in float. The returned list is sorted by qvalue.
    """
    lowercase = lambda x : (x[0].decode('utf8').lower(), x[1])
    return list( map( lowercase, parse_simplevalue_q(value) ))

def make_accept_language( tokenrules=[], prefix=b'' ):
    """Reverse of parse_accept_language()

    ``tokenrules``,
        list of rules, the format of the data is the same as what is return by
        this function for parsing Accept-Language header value.

    ``prefix``,
        While making value byte-string from tokens, if this kwarg is present,
        as byte-string, join this with byte-string generated from
        `tokenrules`,

    Return byte-string.
    """
    value = b'; '.join( prefix, make_simplevalue_q( tokenrules ))
    return b'Accept-Encoding:' + value

#---- Response headers

#---- Entity headers

def parse_content_length( value ):
    """Return length as integer type."""
    try    : return int(value) if value else value
    except : return None

def parse_content_type( value ):
    """Parse content type using grammar,::

      Content-Type   = "Content-Type" ":" media-type
      media-type     = type "/" subtype *( ";" parameter )
      type           = token
      subtype        = token
      parameter      = attribute "=" value
      attribute      = token
      value          = token | quoted-string

    Returns, ``[ type, subtype, [ (attr, value), ... ]`` where all elements
    are in byte-string.
    """
    if value == None : return value

    parts = value.lstrip().split( b';' )
    typ, subtype = parts[0].split( b'/' )
    params = parse_parameters( parts[1:] ) if parts[1:] else []
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

    Returns, ``( token, [ (attr, value), ... ] )``, where all elements are in
    byte-string.
    """
    if not value : return value

    ps = value.split( b';' )
    params = parse_parameters( parts[1:] ) if parts[1:] else []
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
