# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

import os, fcntl, signal, sys, time, threading, imp, signal
from   os.path  import abspath

from   pluggdapps.plugin        import implements, ISettings, Singleton
from   pluggdapps.interfaces    import ICommand, IHTTPServer
import pluggdapps.utils         as h

class Serve( Singleton ):
    """Sub-command for starting native web server. Configuring this plugin
    does not control the web server, instead refer to the corresponding web
    server plugin. By default it uses :class:`HTTPEPollServer`, a single
    threaded / single process epoll based server.

    For automatic server restart, when a module or configuration file is
    modified, pass ``-m`` switch to main script and ``-r`` switch to this
    sub-command. Typically used in development mode,
    
    .. code-block:: bash
        :linenos:

        $ pa -w -m -c <master.ini> serve -r

    .. code-block:: text

        fork ---> child ------> poll-thread
          |        |      |
          *--------*      |
           monitor        *---> pluggdapps-thread

    """

    implements( ICommand )

    description = "Start epoll based http server."
    cmd = 'serve'

    def __init__( self, *args, **kwargs ):
        self.module_mtimes = {}

    #---- ICommand API methods

    def subparser( self, parser, subparsers ):
        """:meth:`pluggdapps.interfaces.ICommand.subparser` interface 
        method."""
        self.subparser = subparsers.add_parser( 
                                self.cmd, description=self.description )
        self.subparser.set_defaults( handler=self.handle )
        self.subparser.add_argument( "-r", dest="mreload",
                                     action="store_true", default=False,
                                     help="Monitor and reload modules" )
        return parser

    def handle( self, args ):
        """:meth:`pluggdapps.interfaces.ICommand.handle` interface method."""
        self.fork_and_monitor( args ) if args.monitor else self.gemini( args )

    #---- Local function.

    def gemini( self, args ):
        """Start a poll thread and then start pluggdapps platform."""
        server = self.qp( 'pluggdapps.IHTTPServer', self['IHTTPServer'] )
        if args.mreload :
            # Launch a thread to poll and then start serving http
            t = threading.Thread( target=self.pollthread, 
                                  name='Reloader', args=(args, server) )
            t.setDaemon(True)
            t.start()

        time.sleep(0.5) # To allow the poll-thread to execute first.
        self.pa.start() # Start pluggdapps
        server.start()  # Blocking call

        # use os._exit() here and not sys.exit() since within a
        # thread sys.exit() just closes the given thread and
        # won't kill the process; note os._exit does not call
        # any atexit callbacks, nor does it do finally blocks,
        # flush open files, etc.  In otherwords, it is rude.
        os._exit(3)

    def fork_and_monitor( self, args ):
        """Fork a child process with same command line arguments except the
        ``-m`` switch. Monitor and reload the child process until normal
        exit."""
        while True :
            self.pa.logdebug( "Forking monitor ..." )
            pid = os.fork()
            if pid == 0 :   # child process
                cmdargs = sys.argv[:]
                cmdargs.remove( '-m' )
                cmdargs.append( os.environ )
                h.reseed_random()
                os.execlpe( sys.argv[0], *cmdargs )

            else :          # parent 
                try :
                    pid, status = os.wait()
                    if status & 0xFF00 != 0x300 :
                        sys.exit( status )
                except KeyboardInterrupt :
                    sys.exit(0)

    def pollthread( self, args, server ):
        """Thread (daemon) to monitor for changing files."""
        self.pa.logdebug( "Periodic poll started for module reloader ..." )
        while True:
            if self.pollthread_checkfiles( args ) == True :
                server.stop()
                break
            time.sleep( self['reload.poll_interval'] )

    def pollthread_checkfiles( self, args ):
        """Check whether any of the module files have modified after loading
        this platform. If so, return True else False."""
        from pluggdapps import papackages
        modfiles = {}
        for mod in sys.modules.values() :
            if hasattr( mod, '__file__' ) :
                modfiles.setdefault( getattr(mod, '__file__'), mod )
        
        inifiles = self.inifiles() if self['reload.config'] else []
        files = list(modfiles.keys()) + self.ttlfiles() + inifiles

        for filename in files :
            stat = os.stat(filename)
            mtime = stat.st_mtime if stat else 0

            if filename.endswith( '.pyc' ) and os.path.exists( filename[:-1] ):
                mtime = max(os.stat(filename[:-1]).st_mtime, mtime)
            elif filename.endswith('$py.class') and \
                    os.path.exists(filename[:-9] + '.py'):
                mtime = max(os.stat(filename[:-9] + '.py').st_mtime, mtime)

            if filename not in self.module_mtimes :
                self.module_mtimes[filename] = mtime
            elif self.module_mtimes[filename] < mtime:
                self.pa.logdebug( "%r changed, reloading ...\n" % filename )
                return True
        return False

    def inifiles( self ):
        """Return a list of .ini files that are related to this
        environment."""
        if self.pa.inifile :
            inifiles = [ abspath(self.pa.inifile) ]
            inifiles.extend( map( lambda x : x[2], self.pa.webapps.keys() ))
        else :
            inifiles = []
        return inifiles

    def ttlfiles( self ):
        """Return a list of ttlfile related to this environment."""
        from pluggdapps import papackages
        ttlfiles = h.flatten(
            [ list( map( h.abspath_from_asset_spec, n.get('ttlplugins', []) ))
              for nm, n in papackages.items() ]
        )
        return ttlfiles + self.pa._monitoredfiles

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
        sett['reload.config'] = h.asbool( sett['reload.config'] )
        sett['reload.poll_interval'] = h.asint( sett['reload.poll_interval'] )
        return sett


    #---- An alternate implementation for linux platforms. But incomplete !!
    #---- Only directories can be watched and sub-directories had to be walked
    #---- and added programmatically.

    def _watch_handler( signum, frame ):
        # log.info("file changed; reloading...")

        # use os._exit() here and not sys.exit() since within a thread 
        # sys.exit() just closes the given thread and won't kill the process;
        # note os._exit does not call any atexit callbacks, nor does it do 
        # finally blocks, flush open files, etc.  In otherwords, it is rude.
        os._exit(3)

    def _watch_files( self, args ):
        if 'darwin' in sys.platform :
            log.info("Not supported on `darwin`")
            os.exit(64)
        else :
            _watch_flag = fcntl.DN_MODIFY | fcntl.DN_CREATE | fcntl.DN_MULTISHOT

        filenames = [args.config] if args.config else []
        filenames.extend(
            getattr( mod, '__file__', None) for mod in sys.modules.values()
        )
        filenames = filter( None, filenames )
        for filename in filenames :
            fd = os.open( filename, os.O_RDONLY )
            fcntl.fcntl( fd, fcntl.F_SETSIG, 0 )
            fcntl.fcntl( fd, fcntl.F_NOTIFY, self._watch_flag )

def SIGINT_handler( signal, frame ):
    print( 'You pressed Ctrl+C!' )
    sys.exit(0)


_default_settings = h.ConfigDict()
_default_settings.__doc__ = Serve.__doc__

_default_settings['IHTTPServer'] = {
    'default' : 'pluggdapps.HTTPEPollServer',
    'types'   : (str,),
    'help'    : "Plugin name implementing :class:`IHTTPServer`. This is the "
                "actual web server that will be started by the sub-command. "
                "Can be modified only in the .ini file.",
    'webconfig' : False,
}
_default_settings['reload.config'] = {
    'default' : True,
    'types'   : (bool,),
    'help'    : "Relevant when the sub-command is invoked with monitor and "
                "reload switch. Specifies whether the server should be "
                "restarted when a configuration file (.ini) is changed."
}
_default_settings['reload.poll_interval'] = {
    'default' : 1,
    'types'   : (int,),
    'help'    : "Relevant when the sub-command is invoked with monitor and "
                "reload switch. Number of seconds to poll for file "
                "modifications. When a file is modified, server is restarted."
}

