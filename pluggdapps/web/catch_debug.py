# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

# Originally zExceptions.ExceptionFormatter from Zope, subsequently from
# paste

import sys, traceback, linecache, cgi, time
from   hashlib              import md5
from   os.path              import isfile
from   copy                 import deepcopy

import pluggdapps.utils         as h
from   pluggdapps.plugin        import Plugin, implements
from   pluggdapps.web.interfaces import IHTTPLiveDebug

class CatchAndDebug( Plugin ):
    """An exception collector that finds traceback information plus
    supplements. Produces a data structure that can be used by formatters to
    render them as an interactive web page.

    Magic variables:

    If you define one of these variables in your local scope, you can
    add information to tracebacks that happen in that context.  This
    allows applications to add all sorts of extra information about
    the context of the error, including URLs, environmental variables,
    users, hostnames, etc.  These are the variables we look for:

    ``__traceback_info__``:
        String. This information is added to the traceback, usually fairly
        literally.

    ``__traceback_hide__``:
        Boolean or String.
        
        True, this indicates that the frame should be hidden from abbreviated
        tracebacks.  This way you can hide some of the complexity of the
        larger framework and let the user focus on their own errors.

        'before', all frames before this one will be thrown away.  By setting
        it to ``'after'`` then all frames after this will be thrown away until
        ``'reset'`` is found. In each case the frame where it is set is
        included, unless you append ``'_and_this'`` to the value (e.g.,
        ``'before_and_this'``).

        Note that formatters will ignore this entirely if the frame
        that contains the error wouldn't normally be shown according
        to these rules.

    ``__traceback_decorator__``:
        Callable. Takes frames, a list of ExceptionFrame object, modifies them
        inplace or return an entirely new object. What ever be the case, it is
        expected to return a list of frames.  This gives the object the
        ability to manipulate the traceback arbitrarily.

    The actually interpretation of these values is largely up to the
    reporters and formatters or the rendering template.
    
    The list of frames goes innermost first.  Each frame has these
    attributes; some values may be None if they could not be
    determined. Each frame is an instance of :class:`ExceptionFrame`.

    Note that all attributes are optional, and under certain
    circumstances may be None or may not exist at all -- the collector
    can only do a best effort, but must avoid creating any exceptions
    itself.

    Formatters may want to use ``__traceback_hide__`` as a hint to
    hide frames that are part of the 'framework' or underlying system.
    There are a variety of rules about special values for this
    variables that formatters should be aware of.
    
    TODO:

    More attributes in __traceback_supplement__?  Maybe an attribute
    that gives a list of local variables that should also be
    collected?  Also, attributes that would be explicitly meant for
    the entire request, not just a single frame.  Right now some of
    the fixed set of attributes (e.g., source_url) are meant for this
    use, but there's no explicit way for the supplement to indicate
    new values, e.g., logged-in user, HTTP referrer, environment, etc.
    Also, the attributes that do exist are Zope/Web oriented.

    More information on frames?  cgitb, for instance, produces
    extensive information on local variables.  There exists the
    possibility that getting this information may cause side effects,
    which can make debugging more difficult; but it also provides
    fodder for post-mortem debugging.  However, the collector is not
    meant to be configurable, but to capture everything it can and let
    the formatters be configurable.  Maybe this would have to be a
    configuration value, or maybe it could be indicated by another
    magical variable (which would probably mean 'show all local
    variables below this frame')
    """
    implements( IHTTPLiveDebug )

    frame_index = {}    # { <identification-code> : ( globals, locals ) ... }:
    """Each frame has its own globals() and locals() context. To support
    browser based debugging, expressions need to be evaluated under these
    context."""

    #---- IHTTPLiveDebug method APIs

    def render( self, request, etype, value, tb ):
        """:meth:`pluggdapps.web.interfaces.IHTTPLiveDebug.render` interface 
        method."""
        response = request.response
        c = self.collectException( request, etype, value, tb )
        weba = self.pa.findapp( appname='pluggdapps.webadmin' )
        c['url_jquery'] = \
            weba.pathfor( request, 'staticfiles', path='jquery-1.8.3.min.js')
        c['url_css'] = \
            weba.pathfor( request, 'staticfiles', path='errorpage.css' )
        c['url_palogo150'] = \
            weba.pathfor( request, 'staticfiles', path='palogo.150.png' )

        html = ''
        if self['html'] and self['template'] :
            # Must be enable in the configuration and a template_file available
            html= response.render( request, c, file=self['template'] )
        return html

    #---- Local methods

    def getRevision(self, globals):
        if self['show_revision'] == False : return None
        rev = globals.get('__revision__', globals.get('__version__', None))
        if rev is not None:
            try   : rev = str(rev).strip()
            except: rev = '???'
        return rev

    def collectFrame( self, request, tb, extra_data ):
        """Collect a dictionary of information about a traceback frame."""
        if isinstance( tb, tuple ) :
            filename, lineno = tb
            name, globals_, locals_ = '', {}, {}
            tbid = None
        else :
            fr = tb.tb_frame
            code = fr.f_code
            filename, lineno = code.co_filename, tb.tb_lineno
            name, globals_, locals_ = code.co_name, fr.f_globals, fr.f_locals
            tbid = id(tb)

        if not isinstance( locals_, dict ) :
            # Something weird about this frame; it's not a real dict
            name = globals_.get('__name__', 'unknown')
            msg = "Frame %s has an invalid locals(): %r" % (name, locals_)
            self.pa.logwarn( msg )
            locals_ = {}

        try :
            linetext = open( filename ).readlines()[lineno-1]
        except :
            linetext = ''

        data = {
            'modname'   : globals_.get('__name__', None),
            'filename'  : filename,
            'lineno'    : lineno,
            'linetext'  : linetext,
            'revision'  : self.getRevision(globals_),
            'name'      : name,
            'tbid'      : tbid,
            # Following are populated further done.
            'traceback_info' : '',
            'traceback_hide' : None,
            'traceback_decorator' : None,
            'url_eval' : '',
        }

        tbi = locals_.get( '__traceback_info__', None )
        if tbi is not None :
            data['traceback_info'] = str(tbi)

        for name in ( '__traceback_hide__', '__traceback_decorator__' ) :
            value = locals_.get(name, globals_.get(name, None))
            data.update({ name[2:-2] : value })

        frameid = md5( str(data).encode('utf-8') ).hexdigest()
        self.frame_index[ frameid ] = ( globals_, locals_ ) 
        if request :
            weba = self.pa.findapp( appname='pluggdapps.webadmin' )
            data['url_eval'] = \
                weba.urlfor( request, 'framedebug', frameid=frameid )
        return data

    def collectException( self, request, etype, value, tb, limit=None ):
        """``collectException( request, *sys.exc_info() )`` will return an
        instance of :class:`CollectedException`. Attibutes of this object can
        be used to render traceback.
    
        Use like::

          try:
              blah blah
          except:
              exc_data = plugin.collectException(*sys.exc_info())
        """
        # The next line provides a way to detect recursion.
        __exception_formatter__ = 1
        limit = limit or self['limit'] or getattr(sys, 'tracebacklimit', None)
        frames, ident_data, extra_data = [], [], {}

        # Collect all the frames in sys.exc_info's trace-back.
        n, tbs = 0, []
        while tb is not None and (limit is None or n < limit):
            if tb.tb_frame.f_locals.get('__exception_formatter__'):
                # Stop recursion. @@: should make a fake ExceptionFrame
                frames.append( '(Recursive formatException() stopped)\n' )
                break
            ef = ExceptionFrame( **self.collectFrame(request, tb, extra_data))
            if bool(ef.traceback_hide) == False and ef.filename :
                frames.append( ef )
                tbs.append( tb )
            n += 1
            tb = tb.tb_next

        if hasattr( value, 'filename' ) :
            tb = (value.filename, value.lineno)
        elif value.__traceback__ not in tbs :
            tb = value.__traceback__
        else :
            tb = None
        
        if tb :
            ef = ExceptionFrame( **self.collectFrame(request, tb, extra_data))
            if bool(ef.traceback_hide) == False and ef.filename :
                frames.append( ef )

        decorators = []
        for frame in frames :
            decorators.append( frame.traceback_decorator )
            ident_data.extend([ frame.modname or '?', frame.name or '?' ])

        ident_data.append( str(etype) )
        ident = hash_identifier( 
                    ' '.join(ident_data), length=5, upper=True, prefix='E-' )

        for decorator in filter( None, decorators ) :
            frames = decorator( frames )

        kwargs = {
            'frames' : frames,
            'exception_formatted':
                '\n'.join( traceback.format_exception_only(etype,value) ),
            'exception_value' : str(value),
            'exception_type' : etype.__name__,
            'identification_code' : ident,
            'date' : h.http_fromdate( time.time() ),
            'extra_data' : extra_data,
        }

        result = CollectedException( **kwargs )
        if etype is ImportError :
            extra_data[('important', 'sys.path')] = [sys.path]

        return result

    #---- ISettings interface methods

    @classmethod
    def default_settings( cls ):
        """:meth:`pluggdapps.plugin.ISettings.default_settings` interface 
        method."""
        return _default_settings

    @classmethod
    def normalize_settings( cls, sett ):
        """:meth:`pluggdapps.plugin.ISettings.normalize_settings` interface 
        method."""
        sett['limit']  = h.asint( sett['limit'] )
        sett['show_revision']  = h.asbool( sett['show_revision'] )
        sett['html']  = h.asbool( sett['html'] )
        return sett

_default_settings = h.ConfigDict()
_default_settings.__doc__ = (
    "Pluggdapps can be configured, via webapp-plugin, to catch exceptions "
    "and debug them via browser. This plugin can be configured for each "
    "application."
)

_default_settings['html'] = {
    'default'  : True,
    'types'    : (bool,),
    'help'     : "Format exception in html and return back an interactive "
                 "debug page as response."
}
_default_settings['template'] = {
    'default'  : 'pluggdapps:webadmin/templates/errorpage.ttl',
    'types'    : (str,),
    'help'     : "Template file to render the error page. Refer to the plugin "
                 "to know more about the context available to the template."
}
_default_settings['limit'] = {
    'default'  : 200,
    'types'    : (int,),
    'help'     : "Maximum number of trace back frames to display in the debug "
                 "page."
}
_default_settings['show_revision'] = {
    'default'  : False,
    'types'    : (bool,),
    'help'     : "Show revision information from frame."""
}
_default_settings['xmlhttp_key'] = {
    'default'  : '_',
    'types'    : (str,),
    'help'     : "When this key is in the request GET variables (not POST!), "
                 "expect that this is an XMLHttpRequest, and the response "
                 "will be more minimal; it shall not be a complete HTML page."
}


class CollectedException( dict ):
    """This is the result of collection the exception; it contains copies
    of data of interest.
    """

    frames = []
    """A list of frames (ExceptionFrame instances), innermost last."""

    exception_type = None
    """The *string* representation of the type of the exception
    (@@: should we give the # actual class? -- we can't keep the
    actual exception around, but the class should be safe)
    Something like 'ValueError'."""

    exception_formatted = None
    """The result of traceback.format_exception_only; this looks
    like a normal traceback you'd see in the interactive interpreter."""

    exception_value = None
    """The string representation of the exception, from ``str(e)``."""

    identification_code = None
    """An identifier which should more-or-less classify this particular
    exception, including where in the code it happened."""

    date = None
    """Date string (in HTTP format) adjusted to GMT."""

    extra_data = {}
    """A dictionary of supplemental data."""


class ExceptionFrame( h.Bunch ):
    """This represents one frame of the exception.  Each frame is a
    context in the call stack, typically represented by a line
    number and module name in the traceback.
    """

    modname = None
    """The name of the module; can be None, especially when the code
    isn't associated with a module."""

    filename = None
    """The filename (@@: when no filename, is it None or '?'?)."""

    lineno = None
    """Line number."""

    linetext = None
    """Text of line that took part in the exception."""

    revision = None
    """The value of __revision__ or __version__ -- but only if
    show_revision = True (by defaut it is false).  (@@: Why not
    collect this?)."""

    name = None
    """The name of the function with the error (@@: None or '?' when
    unknown?)."""

    traceback_info = None
    """The str() of any __traceback_info__ value found."""

    traceback_hide = False
    """The value of __traceback_hide__."""

    traceback_decorator = None
    """The value of __traceback_decorator__."""

    tbid = None
    """The id() of the traceback scope, can be used to reference the
    scope for use elsewhere."""

    def get_source_line( self, context=0 ):
        """Return the source of the current line of this frame.  You
        probably want to .strip() it as well, as it is likely to have
        leading whitespace.

        If context is given, then that many lines on either side will
        also be returned.  E.g., context=1 will give 3 lines.
        """
        if not self.filename or not self.lineno : return None
        lines = [
          linecache.getline( self.filename, lineno )
          for lineno in range( self.lineno-context, self.lineno+context+1 ) ]
        return ''.join(lines)

#----------

"""Creates a human-readable identifier, using numbers and digits,
avoiding ambiguous numbers and letters.  hash_identifier can be used
to create compact representations that are unique for a certain string
(or concatenation of strings)."""

good_characters = "23456789abcdefghjkmnpqrtuvwxyz"
base = len(good_characters)

def make_identifier( number ):
    """Encodes a number as an identifier."""
    number = int( number )
    if number < 0:
        msg = "You cannot make identifiers out of negative numbers: %r"%number
        raise ValueError(msg)

    result = []
    while number :
        next = number % base
        result.append(good_characters[next])
        # Note, this depends on integer rounding of results:
        number = number // base
    return ''.join(result)

def hash_identifier( s, length, pad=True, hasher=md5, prefix='',
                     group=None, upper=False ):
    """Hashes the string (with the given hashing module), then turns that
    hash into an identifier of the given length (using modulo to
    reduce the length of the identifier).  If ``pad`` is False, then
    the minimum-length identifier will be used; otherwise the
    identifier will be padded with 0's as necessary.

    ``prefix`` will be added last, and does not count towards the
    target length.  ``group`` will group the characters with ``-`` in
    the given lengths, and also does not count towards the target
    length.  E.g., ``group=4`` will cause a identifier like
    ``a5f3-hgk3-asdf``.  Grouping occurs before the prefix.
    """
    if not callable(hasher):
        # Accept sha/md5 modules as well as callables
        hasher = hasher.new
    if length > 26 and hasher is md5:
        msg = ( "md5 cannot create hashes longer than 26 characters in "
                "length (you gave %s)" ) % length
        raise ValueError(msg)
    digest = hasher( s.encode('utf-8') ).digest()
    modulo = base ** length
    number = 0
    for c in list(digest) :
        number = (number * 256 + c) % modulo
    ident = make_identifier(number)
    if pad:
        ident = good_characters[0]*(length-len(ident)) + ident
    if group:
        parts = []
        while ident:
            parts.insert(0, ident[-group:])
            ident = ident[:-group]
        ident = '-'.join(parts)
    if upper:
        ident = ident.upper()
    return prefix + ident


