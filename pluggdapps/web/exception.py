# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

# Originally zExceptions.ExceptionFormatter from Zope, subsequently from
# paste

"""An exception collector that finds traceback information plus supplements."""

import sys, traceback, linecache, cgi, time
from   hashlib              import md5

import pluggdapps.utils         as h
from   pluggdapps.plugin        import Plugin, implements
from   pluggdapps.web.interfaces import IHTTPWebDebug

frame_index = {}    # { <identification-code> : ( globals, locals ) ... }:
"""Each frame has its own globals() and locals() context. To support browser
based debugging, expressions need to be evaluated under these context."""

_default_settings = h.ConfigDict()
_default_settings.__doc__ = \
    "Configuration settings for traceback collector."

_default_settings['limit'] = {
    'default'  : 200,
    'types'    : (int,),
    'help'     : "Limit of trace back frames."
}
_default_settings['show_revision'] = {
    'default'  : False,
    'types'    : (bool,),
    'help'     : "Show revision information from frame."""
}
_default_settings['error_message'] = {
    'default'  : '',
    'types'    : (str,),
    'help'     : "When debug mode is off, the error message to show to users."
}
_default_settings['xmlhttp_key'] = {
    'default'  : '_',
    'types'    : (str,),
    'help'     : "When this key is in the request GET "
                 "variables (not POST!), expect that this is an "
                 "XMLHttpRequest, and the response should be more minimal; it "
                 "should not be a complete HTML page."
}
_default_settings['html'] = {
    'default'  : True,
    'types'    : (bool,),
    'help'     : "Render formatted exception in html."
}


class CatchAndDebug( Plugin ):
    """Produces a data structure that can be used by formatters to
    display exception reports.

    Magic variables:

    If you define one of these variables in your local scope, you can
    add information to tracebacks that happen in that context.  This
    allows applications to add all sorts of extra information about
    the context of the error, including URLs, environmental variables,
    users, hostnames, etc.  These are the variables we look for:

    ``__traceback_supplement__``:
        You can define this locally or globally (unlike all the other
        variables, which must be defined locally).

        ``__traceback_supplement__`` is a tuple of ``(factory, arg1,
        arg2...)``.  When there is an exception, ``factory(arg1, arg2,
        ...)`` is called, and the resulting object is inspected for
        supplemental information.

    ``__traceback_info__``:
        This information is added to the traceback, usually fairly
        literally.

    ``__traceback_hide__``:
        If set and true, this indicates that the frame should be
        hidden from abbreviated tracebacks.  This way you can hide
        some of the complexity of the larger framework and let the
        user focus on their own errors.

        By setting it to ``'before'``, all frames before this one will
        be thrown away.  By setting it to ``'after'`` then all frames
        after this will be thrown away until ``'reset'`` is found.  In
        each case the frame where it is set is included, unless you
        append ``'_and_this'`` to the value (e.g.,
        ``'before_and_this'``).

        Note that formatters will ignore this entirely if the frame
        that contains the error wouldn't normally be shown according
        to these rules.

    ``__traceback_reporter__``:
        This should be a reporter object (see the reporter module),
        or a list/tuple of reporter objects.  All reporters found this
        way will be given the exception, innermost first.

    ``__traceback_decorator__``:
        This object (defined in a local or global scope) will get the
        result of this function (the CollectedException defined
        below).  It may modify this object in place, or return an
        entirely new object.  This gives the object the ability to
        manipulate the traceback arbitrarily.

    The actually interpretation of these values is largely up to the
    reporters and formatters.
    
    ``collectException(*sys.exc_info())`` will return an instance of 
    :class:`CollectedException`. Attibutes of this object can be used to
    render traceback.
    
    The list of frames goes innermost first.  Each frame has these
    attributes; some values may be None if they could not be
    determined. Each frame is an instance of :class:`ExceptionFrame`.

    ``__traceback_supplement__`` is thrown away, but a fixed
    set of attributes are captured; each of these attributes is
    optional. These are used to create an object with attributes of the same
    names.
    
    If ``__traceback_supplement__`` contains the optional attribute,
    ``getInfo``, a function/method that takes no arguments and returns a
    string describing any extra information is saved under attribute ``info``.
        
    If ``__traceback_supplement__`` contains the optional attribute 
    ``extraData``, a function/method that takes no arguments, and returns 
    a dictionary and saved under attribute ``extra``. The contents of this
    dictionary will not be displayed in the context of the traceback, but
    globally for the exception.  Results will be grouped by the keys in the
    dictionaries (which also serve as titles).  The keys can also be tuples of
    (importance, title); in this case the importance should be ``important``
    (shows up at top), ``normal`` (shows up somewhere; unspecified),
    ``supplemental`` (shows up at bottom), or ``extra`` (shows up hidden or
    not at all).

    ``__traceback_supplement__`` implementations should be careful to
    produce values that are relatively static and unlikely to cause
    further errors in the reporting system -- any complex
    introspection should go in ``getInfo()`` and should ultimately
    return a string. Refer to :class:`SupplementaryData` for details.

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
    implements( IHTTPWebDebug )

    #---- IHTTPWebDebug method APIs

    def handle_exc( self, request, etype, value, tb ):
        response = request.response
        c = self.collectException( request, etype, value, tb )
        app_webadmin = self.pa.findapp( appname='webadmin' )
        c['url_jquery'] = app_webadmin.pathfor(
                            request, 'staticfiles', path='jquery-1.8.3.min.js')
        if self['html'] :
            html= response.render(
                    request, c, 
                    file='pluggdapps:webadmin/templates/errorpage.ttl' )
        else :
            html = ''
        return html

    #---- Local methods

    def getRevision(self, globals):
        if self['show_revision'] == False : return None
        rev = globals.get('__revision__', globals.get('__version__', None))
        if rev is not None:
            try   : rev = str(rev).strip()
            except: rev = '???'
        return rev

    def collectSupplement( self, supplement, tb ):
        result = { name : getattr(supplement, name, None)
                   for name in ('object', 'source_url', 'line', 'column',
                                'expression', 'warnings') }
        result['info'] = getattr(supplement, 'getInfo', lambda x : None)()
        result['extra'] = getattr(supplement, 'extraData', lambda x : None)()
        return SupplementaryData( **result )

    def collectFrame( self, request, tb, extra_data ):
        frame = tb.tb_frame
        code, globals, locals, = frame.f_code, frame.f_globals, frame.f_locals
        name = code.co_name
        if not isinstance( locals, dict ) :
            # Something weird about this frame; it's not a real dict
            name = globals.get('__name__', 'unknown')
            self.pa.logwarn(
                "Frame %s has an invalid locals(): %r" % (name, locals))
            locals = {}
        data = {
            'modname'   : globals.get('__name__', None),
            'filename'  : code.co_filename,
            'lineno'    : tb.tb_lineno,
            'linetext'  : open( code.co_filename ).readlines()[tb.tb_lineno-1],
            'revision'  : self.getRevision(globals),
            'name'      : name,
            'tbid'      : id(tb),
        }

        # Output a traceback supplement, if any.
        tbs = locals.get( '__traceback_supplement__', 
                          globals.get('__traceback_supplement__', None) )
        if tbs is not None:
            try:
                supp = tbs[0]( *tbs[1:] )   # factory(*args)
                data['supplement'] = self.collectSupplement(supp, tb)
                [ extra_data.setdefault(key, []).append(value)
                  for key, value in (data['supplement'].extra or {}).items() ]
            except:
                if self['debug'] :
                    data['supplement_exception'] = h.print_exc()
                # else just swallow the exception.

        try:
            tbi = locals.get( '__traceback_info__', None )
            if tbi is not None :
                data['traceback_info'] = str(tbi)
        except:
            pass

        for name in ( '__traceback_hide__', '__traceback_log__',
                      '__traceback_decorators__' ) :
            value = locals.get(name, globals.get(name, None))
            data.update({ name[2:-2] : value })

        frameid = md5( str(data).encode('utf-8') ).hexdigest()
        frame_index[ frameid ] = ( globals, locals ) 
        app_webadmin = self.pa.findapp( appname='webadmin' )
        data['url_eval'] = app_webadmin.urlfor(
                                request, 'framedebug', frameid=frameid )
        return data

    def collectException( self, request, etype, value, tb, limit=None ):
        """Collection an exception from ``sys.exc_info()``.
        
        Use like::

          try:
              blah blah
          except:
              exc_data = plugin.collectException(*sys.exc_info())
        """
        # The next line provides a way to detect recursion.
        __exception_formatter__ = 1
        limit = limit or self['limit'] or getattr(sys, 'tracebacklimit', None)
        frames, ident_data, traceback_decorators, extra_data = [], [], [], {}
        n = 0
        while tb is not None and (limit is None or n < limit):
            if tb.tb_frame.f_locals.get('__exception_formatter__'):
                # Stop recursion. @@: should make a fake ExceptionFrame
                frames.append( '(Recursive formatException() stopped)\n' )
                break
            data = self.collectFrame( request, tb, extra_data )
            frame = ExceptionFrame( **data )
            frames.append( frame )
            if frame.traceback_decorator is not None:
                traceback_decorators.append( frame.traceback_decorator )
            ident_data.append( frame.modname or '?' )
            ident_data.append( frame.name or '?' )
            tb = tb.tb_next
            n += 1

        ident_data.append( str(etype) )
        ident = hash_identifier( 
                    ' '.join(ident_data), length=5, upper=True, prefix='E-' )

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

        for decorator in traceback_decorators:
            try:
                new_result = decorator( result )
                if new_result is not None:
                    result = new_result
            except:
                pass
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

    supplement = None
    """A SupplementaryData object, if __traceback_supplement__ was found
    (and produced no errors)."""

    supplement_exception = None
    """If accessing __traceback_supplement__ causes any error, the
    plain-text traceback is stored here."""

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

class SupplementaryData( h.Bunch ):
    """The result of __traceback_supplement__.  We don't keep the
    supplement object around, for fear of GC problems and whatnot.
    (@@: Maybe I'm being too superstitious about copying only specific
    information over)
    """
    object = None
    """the name of the object being visited."""

    source_url = None
    """the original URL requested."""

    line = None
    """the line of source being executed (for interpreters, like ZPT)."""

    column = None
    """the column of source being executed."""

    expression = None
    """the expression being evaluated (also for interpreters)."""

    warnings = None
    """a list of (string) warnings to be displayed."""

    info = None
    """This is the *return value* of supplement.getInfo()."""


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

