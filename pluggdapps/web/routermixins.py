import re

import pluggdapps.utils             as h
from   pluggdapps.const             import URLSEP
from   pluggdapps.plugin            import interface
from   pluggdapps.web.webinterfaces import IHTTPRouter
from   pluggdapps.web.views         import HTTPNotFound

re_patt = re.compile( r'([^{]+)?'
                      r'(\{([a-z][a-z0-9]*)(,(?:[^"\\]|\\.)*)?\})?'
                      r'(.+)?' )
          # prefix, _, name, regex, sufx

class BaseMixin( object ):

    def __init__( self, *args, **kwargs ):
        self.segment = None
        self.defaultview = HTTPNotFound
        self.traversals = {}
        self.views = {}

    def onboot( self ):
        pass

    def genpath( self, request, name, *traverse, **matchdict ) :
        if traverse :
            if self.traversals == {} :
                e = 'Traversals are not defined for this router, %r' % self
                h.Error( e )
            for segment, router in self.traversals.items() :
                if segment != traverse[0] : continue
                if traverse[1:] :
                    path = router.genpath( request, traverse[1:] )
                    return URLSEP + traverse[0] + URLSEP + path
            else :
                e = 'Cannot make path for %r %r %r' % (name,traverse,matchdict)
                raise h.Error( e )
        else :
            if self.views == {} :
                e = 'View patters are not defined for this router, %r' % self
                h.Error( e )
            if 'remains' in matchdict :
                matchdict['remains'] = URLSEP.join( matchdict['remains'] )
            tmpl = self.views[name]['path_template']
            return tmpl.format( **matchdict )


    def fetchview( self, request, c ):
        view = self.lookup_traversal( request, c )
        if view == None :
            view = self.lookup_view( request, c )
        return view


class MatchMixin( BaseMixin ):
    """Provide necessary method to handle url routing pattern matching."""

    def onboot( self ):
        super().onboot()

    def lookup_view( self, request, c ):
        for name, view in self.views :
            regc = view['compiled_pattern']
            m = regc.match( request.resolve_path )

            if m == None : continue

            request.matchrouter = self
            request.matchdict = m.groupdict()
            suffix = request.matchdict.get( h.ROUTE_PATH_SUFFIX, None )
            if suffix :
                suffix = suffix.split( URLSEP )
                request.matchdict[ h.ROUTE_PATH_SUFFIX ] = suffix
            request.view_name = name
            cb = view['view_callable']
            if isinstance( cb, str ):
                v = query_plugin( self.webapp, IController, cb )
            elif callable(cb) :
                v = cb
            else:
                raise h.Error( 'Callable not resolved for %r', name )
            return v
        return None

    def add_view( self, name, **kwargs ):
        self.views[name] = view = {}
        pattern = kwargs['pattern']
        view['resource'] = kwargs.get( 'resource', None )
        view['xhr'] = kwargs.get( 'xhr', None )
        view['method'] = kwargs.get( 'method', None )
        view['path_info'] = kwargs.get( 'path_info', None )
        view['params'] = kwargs.get( 'params', None )
        view['headers'] = kwargs.get( 'headers', None )
        view['accept'] = kwargs.get( 'accept', None )
        view['view_callable'] = kwargs.get( 'view_callable', None )
        view['attr'] = kwargs.get( 'attr', None )
        view['permission'] = kwargs.get( 'permission', None )
        view['pattern'] = pattern

        regex, tmpl, redict = self.compile_url( pattern )
        view['compiled_pattern'] = re.compile( regex )
        view['path_template'] = tmpl
        view['match_segments'] = redict

    def compile_url( self, pattern ):
        """`pattern` is URL routing pattern.

        This method compiles the pattern in three different ways and returns
        them as a tuple of (regex, tmpl, redict)

        `regex`,
            A regular expression string that can be used to match incoming
            request-url to resolve view-callable.
        `tmpl`,
            A template formating string that can be used to generate URLs by
            apps.
        `redict`,
            A dictionary of variable components in path segment and optional
            regular expression that must match its value. This can be used for
            validation during URL generation.
        """
        regex, tmpl, redict = r'^', '', {}
        segs = pattern.split( URLSEP )
        while segs :
            seg = segs.pop(0)
            if not seg : continue
            regex, tmpl = (regex + URLSEP), (tmpl + URLSEP)
            prefx, _, name, reg, sufx = re_patt.match( seg ).groups()
            if name[0] == '*' :
                rempath = URLSEP.join( [seg] + segs )
                prefx, _, name, reg, sufx = re_patt.match( rempath ).groups()
                segs = []
            reg = reg[1:]

            regex += prefx if prefx else r''
            if name and reg and sufx :
                regex += r'(?P<%s>%s(?=%s))%s' % (name, reg, sufx, sufx)
            elif name and reg :
                regex += r'(?P<%s>%s)' % (name, reg)
            elif name and sufx :
                regex += r'(?P<%s>.+(?=%s))%s' % (name, sufx, sufx)
            elif name :
                regex += r'(?p<%s>.+)' % (name,)
            elif sufx :
                regex += sufx
            tmpl += prefx if prefx else ''
            tmpl += '{' + name + '}' if name else ''
            tmpl += sufx if sufx else ''
            redict[ name ] = reg
        regex += '$'
        return regex, tmpl, redict

