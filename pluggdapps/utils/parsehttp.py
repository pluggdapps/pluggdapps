# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 Netscale Computing

"""HTTP utility functions."""

import re, sys, calendar, email
from   collections  import UserDict
import datetime     as dt
from   urllib.parse import urlsplit, unquote, parse_qs, urlunsplit, quote, \
                           urlencode, urljoin
import urllib.request, urllib.error

from pluggdapps.utils.exc import Error
from pluggdapps.utils.lib import parsecsv

strptime = dt.datetime.strptime
strftime = dt.datetime.strftime

DEFAULT_QVALUE = 1.0

__all__ = [
    'response_status',
    'port_for_scheme', 'parse_startline', 'parse_url', 'make_url',
    'parse_xscheme', 'parse_remoteip', 'parse_body',
    'convert_header_value', 'HTTPFile', 'HTTPHeaders', 'url_concat',
    'parse_multipart_form_data',
    # parse generic headers
    'parse_cache_control', 'parse_connection', 'parse_date', 'parse_pragma',
    'parse_trailer', 'parse_transfer_encoding', 'parse_upgrade', 'parse_via',
    'parse_warning',
    # parse request headers
    'parse_accept', 'parse_accept_charset', 'parse_accept_encoding',
    'parse_accept_language', 'parse_authorization', 'parse_expect',
    'parse_from', 'parse_host', 'parse_if_match', 'parse_if_modified_since',
    'parse_if_none_match', 'parse_if_range', 'parse_if_unmodified_since',
    'parse_max_forwards', 'parse_proxy_authorization', 'parse_range',
    'parse_referer', 'parse_te', 'parse_user_agent',
    # parse response headers
    'parse_accept_ranges', 'parse_age', 'parse_etag', 'parse_location',
    'parse_proxy_authenticate', 'parse_retry_after', 'parse_server',
    'parse_vary', 'parse_www_authenticate',
    # parse entity headers
    'parse_allow', 'parse_content_encoding', 'parse_content_language',
    'parse_content_length', 'parse_content_location', 'parse_content_md5',
    'parse_content_range', 'parse_content_type', 'parse_expires',
    'parse_last_modified',
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

#---- Map response code to response message

statuscode = {
    b'100' : b'CONTINUE',
    b'101' : b'SWITCHING PROTOCOLS',
    b'200' : b'OK',
    b'201' : b'CREATED',
    b'202' : b'ACCEPTED',
    b'203' : b'NON-AUTHORITATIVE INFORMATION',
    b'204' : b'NO CONTENT',
    b'205' : b'RESET CONTENT',
    b'206' : b'PARTIAL CONTENT',
    b'226' : b'IM USED',
    b'300' : b'MULTIPLE CHOICES',
    b'301' : b'MOVED PERMANENTLY',
    b'302' : b'FOUND',
    b'303' : b'SEE OTHER',
    b'304' : b'NOT MODIFIED',
    b'305' : b'USE PROXY',
    b'306' : b'RESERVED',
    b'307' : b'TEMPORARY REDIRECT',
    b'400' : b'BAD REQUEST',
    b'401' : b'UNAUTHORIZED',
    b'402' : b'PAYMENT REQUIRED',
    b'403' : b'FORBIDDEN',
    b'404' : b'NOT FOUND',
    b'405' : b'METHOD NOT ALLOWED',
    b'406' : b'NOT ACCEPTABLE',
    b'407' : b'PROXY AUTHENTICATION REQUIRED',
    b'408' : b'REQUEST TIMEOUT',
    b'409' : b'CONFLICT',
    b'410' : b'GONE',
    b'411' : b'LENGTH REQUIRED',
    b'412' : b'PRECONDITION FAILED',
    b'413' : b'REQUEST ENTITY TOO LARGE',
    b'414' : b'REQUEST-URI TOO LONG',
    b'415' : b'UNSUPPORTED MEDIA TYPE',
    b'416' : b'REQUESTED RANGE NOT SATISFIABLE',
    b'417' : b'EXPECTATION FAILED',
    b'500' : b'INTERNAL SERVER ERROR',
    b'501' : b'NOT IMPLEMENTED',
    b'502' : b'BAD GATEWAY',
    b'503' : b'SERVICE UNAVAILABLE',
    b'504' : b'GATEWAY TIMEOUT',
    b'505' : b'HTTP VERSION NOT SUPPORTED',
}

def port_for_scheme( scheme, port='' ):
    """Calculate port based on `scheme` name. If scheme and port matches, port
    is left empty. Otherwise `port` is explicitly set to port number and
    returned as a string."""
    if port :
        if scheme == 'http' and str(port) == '80'     : return ''
        elif scheme == 'https' and str(port) == '443' : return ''
        else : return str(port)
    else :
        return ''


def parse_startline( startline ):
    """Every HTTP request starts with a start line specifying method, uri and
    version. Parse them and return a tuple of (method, uri, version). All
    elements in the return tuple will be available as strings."""
    return [ x.strip( b' \t' ) for x in startline.split(b' ') ]


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

scheme2ports = {
    'http'  : '80',
    'https' : '443',
}
def compare_url( url1, url2 ):
    x = urlsplit( url1 )
    y = urlsplit( url2 )
    scheme1 = x.scheme.lower() or 'http'
    scheme2 = y.scheme.lower() or 'http'
    port1 = x.port or scheme2port.get( scheme1, '80' )
    port2 = y.port or scheme2port.get( scheme2, '80' )
    if scheme1 != scheme2 : return False
    if x.host.lower() != y.host.lower() : return False
    if port1 != port2 : return False
    if x.path != y.path : return False
    if x.query != y.query : return False
    if x.fragment != y.fragment : return False
    return True


#---- Logic to parse HTTP headers

class HTTPHeaders( dict ):
    """Dictionary of HTTP headers for both request and response.

    Value of each key, lower-cased string, is represented as list of
    byte-string. If a header field occur in a request only once, then list
    of values will have only one element.

    Refer RFC2616 for more information.
    """

    @classmethod
    def parse( cls, hdrdata ):
        """Returns HTTPHeaders object."""
        def consume( obj, line ):
            name, value = line.split( b":", 1 )
            name = name.strip().decode(b'utf8').lower()
            pvalue = obj.get( name, None )
            obj[ name ] = value if pvalue == None else (pvalue+', '+value)

        obj, prev_line = cls(), b''
        for line in hdrdata.splitlines() :
            if not line : continue

            if line[0].isspace() : # continuation of a multi-line header
                prev_line += ' ' + line.lstrip(' \t')
            else :
                consume( obj, prev_line ) if prev_line else None
                prev_line = line

        consume( obj, prev_line ) if prev_line else None

        return obj


def parse_hdr_parameter( s ):
    if s :
        name, val = re.match( s, re_param ).groups()
        return name.lower(), val
    return s

def parse_rule( s ):
    return [ x.strip(b' \r\n\t') for x in s.split(b',', s) ]

def parse_product( s ):
    return s.split( b'/' )

#---- Generic headers

def parse_cache_control( value ):
    if value == None : return None

    try :
        token, value = value.split( b'=' )
        token = token.strip()
        value = value.strip()
    except ValueError :
        token = value.strip()
        value = None
    return (token, value) 

def parse_connection( value ):
    if value == None : return None
    return parse_rule( value )

rfc1123_format = "%a, %d %b %Y %H:%M:%S %Z"
rfc1036_format = "%A, %d-%b-%y %H:%M:%S %Z"
asctime_format = "%a %b %d %H:%M:%S %Y"
def parse_date( value ):
    """HTTP applications have historically allowed three different formats
    for the representation of date/time stamps:

      Sun, 06 Nov 1994 08:49:37 GMT  ; RFC 822, updated by RFC 1123
      Sunday, 06-Nov-94 08:49:37 GMT ; RFC 850, obsoleted by RFC 1036
      Sun Nov  6 08:49:37 1994       ; ANSI C's asctime() format

    The first format is preferred as an Internet standard. This function
    heuristically parses the date format (from request header) and changes the
    format to RFC 1123 format.

    Returns `datetime` object
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

def parse_pragma( value ):
    if value == None : return None

    toks = []
    for x in parse_rule( value ) :
        a,b,c = re.match( re_dirtive, x ).groups()
        toks.append( (a, b or c) if (b or c) else a )
    return toks

def parse_trailer( value ):
    if value == None : return None

    return parse_rule( value )

def parse_transfer_encoding( value ):
    """Return a list of parsed transfer-encoding value."""
    if value == None : return None
    toks = []
    for x in parse_rule(value) :
        try :
            parts = value.split( b';' )
            token = parts[0]
            params = filter( None, map( parse_hdr_parameter, parts[1:] ))
            return toks.append( token.lower(), tuple(params) )
        except :
            return toks.append( (None, tuple()) )

def parse_upgrade( value ):
    if value == None : return None

    return list( map( parse_product, parse_rule(value) ))

def parse_via( value ):
    pass

def parse_warning( value ):
    pass

#---- Request headers

def parse_accept( value ):
    """Accept         = "Accept" ":"
                        #( media-range [ accept-params ] )

       media-range    = ( "*/*"
                        | ( type "/" "*" )
                        | ( type "/" subtype )
                        ) *( ";" parameter )
       accept-params  = ";" "q" "=" qvalue *( accept-extension )
       accept-extension = ";" token [ "=" ( token | quoted-string ) ]

    Returns
        ( ( type, subtype, [ params ] ),
          ( type, subtype, [ params ] ),
        )
      where,
        params is list of tuple (attr, value) or just a token.
    """
    toks = []
    for v in parse_rule( value ) :
        try :
            media_range, accept_params = v.split( b';', 1 )
        except :
            media_range, accept_params = v, b''
        toks.append( media_range.split( b'/' ))
        for x in accept_params.split( b';' ) :
            a,b,c = re.match( re_dirtive, x ).groups()
            toks.append( (a, b or c) if (b or c) else a )
        toks[-1] = tuple( toks[-1] )

    # sort media-ranges based on qvalue.
    rangeq = {}
    def quality( tok ):
        for v in tok[2:] :
            try : if v[0] == b'q' : q = float(v[1])
            except : continue
        else :
            q = None
        if tok[0:2] == ( b'*', b'*' ) :
            rangeq.setdefault( b'*', q or DEFAULT_QVALUE )
        elif tok[1] == b'*' :
            rangeq.setdefault( tok[0], q or DEFAULT_QVALUE )
        return (tok, q)

    def quality_sort( tok_q ):
        tok, q = tok_q
        q = rangeq.get( tok[0], 1.0 ) if q == None else q
        if tok[0] == b'*' : 
            key = -2.0
        elif tok[0] in rangeq :
            key = -1.0 
        else :
            key = q + len( tok )
        return key
    return list( sorted( map( quality, toks ), key=quality_sort, reverse=True ))

def parse_accept_charset( value ):
    """Accept-Charset = "Accept-Charset" ":"
              1#( ( charset | "*" )[ ";" "q" "=" qvalue ] )

    Returns,
        (charset, qvalue), where qvalue is in float.
    """
    toks, qstar = [], 0.0
    for v in parse_rule( value ) :
        try :
            charset, qvalue = v.split(b';')
            _, qvalue = re.match( re_param, qvalue ).groups()
            qvalue = float( qvalue )
        except :
            charset, qvalue = v, DEFAULT_QVALUE
        qstar = qvalue if charset == b'*' else qstar

    def quality_sort( tok_q ):
        tok, q = tok_q
        if tok[0] == b'*' : return -1.0
        else : return q

    return sorted( toks, key=quality_sort, reverse=True )

def parse_accept_encoding( value ):
    pass

def parse_accept_language( value ):
    if value == None : return None
    return tuple( [value] + value.split( b'-' ) )

def parse_authorization( value ):
    pass

def parse_expect( value ):
    pass

def parse_from( value ):
    pass

def parse_host( value ):
    pass

def parse_if_match( value ):
    pass

def parse_if_modified_since( value ):
    pass

def parse_if_none_match( value ):
    pass

def parse_if_range( value ):
    pass

def parse_if_unmodified_since( value ):
    pass

def parse_max_forwards( value ):
    pass

def parse_proxy_authorization( value ):
    pass

def parse_range( value ):
    value = value.strip() if value else None
    return value if value == b'bytes' else None

def parse_referer( value ):
    pass

def parse_te( value ):
    """Return a list of parsed transfer-encoding value."""
    pass

def parse_user_agent( value ):
    pass

#---- Response headers

def parse_accept_ranges( value ):
    pass

def parse_age( value ):
    pass

def parse_etag( value ):
    pass

def parse_location( value ):
    pass

def parse_proxy_authenticate( value ):
    pass

def parse_retry_after( value ):
    pass

def parse_server( value ):
    pass

def parse_vary( value ):
    pass

def parse_www_authenticate( value ):
    pass

#---- Entity headers

def parse_allow( value ):
    pass

def parse_content_encoding( value ):
    """Return a token 
        "gzip" | "compress" | "deflate" | "identity"
    """
    return value.strip().lower()


def parse_content_language( value ):
    if value == None : return None
    return tuple( [value] + value.split( b'-' ) )

def parse_content_length( value ):
    """Return length as integer type."""
    return int(value) if value else value

def parse_content_location( value ):
    pass

def parse_content_md5( value ):
    pass

def parse_content_range( value ):
    value = value.strip() if value else None
    return value if value == b'bytes' else None

def parse_content_type( value ):
    try :
        parts = value.split( b';' )
        typ, subtype = parts[0].split( b'/' )
        params = filter( map( parse_hdr_parameter, parts[1:] ))
        return typ, subtype, tuple(params)
    except :
        return tuple( None, None, tuple() )

def parse_expires( value ):
    pass

def parse_last_modified( value ):
    pass

#---- Yet to be cleaned up.

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
                # log.warning( "Invalid multipart/form-data" )
                pass
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
            # log.warning( "multipart/form-data missing headers" )
            continue
        headers = HTTPHeaders.parse( part[:eoh].decode("utf-8") )
        disp_header = headers.get( "Content-Disposition", "" )
        disposition, disp_params = _parse_header(disp_header)
        if disposition != "form-data" or not part.endswith(b"\r\n"):
            # log.warning( "Invalid multipart/form-data" )
            continue
        value = part[eoh + 4:-2]
        if not disp_params.get("name"):
            # log.warning( "multipart/form-data value missing name" )
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
