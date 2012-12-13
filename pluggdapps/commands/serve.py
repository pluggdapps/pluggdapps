# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

import os, fcntl, signal, sys, time, threading, imp, signal

from   pluggdapps.plugin        import implements, ISettings, Singleton, \
                                       pluginname
from   pluggdapps.interfaces    import ICommand, IHTTPServer
import pluggdapps.utils         as h

_default_settings = h.ConfigDict()
_default_settings.__doc__ = (
    "Configuration for serve sub-command."
)

_default_settings['IHTTPServer'] = {
    'default' : 'httpepollserver',
    'types'   : (str,),
    'help'    : "Plugin name implementing :class:`IHTTPServer`."
}
_default_settings['reload'] = {
    'default' : False,
    'types'   : (bool,),
    'help'    : "Whether to monitor for changes to module files and watched "
                "files, and restart the server."
}
_default_settings['reload.config'] = {
    'default' : True,
    'types'   : (bool,),
    'help'    : "This parameter specifies whether the server should be "
                "restarted when a configuration parameter is changed."
}
_default_settings['reload.poll_interval'] = {
    'default' : 1,
    'types'   : (int,),
    'help'    : "Number seconds to poll for watched file's modification "
                "timestamp. When a file is modified server is restarted."
}
_default_settings['reload.config'] = {
    'default' : True,
    'types'   : (bool,),
    'help'    : "This parameter specifies whether the server should be "
                "restarted when a configuration parameter is changed."
}
_default_settings['reload.poll_interval'] = {
    'default' : 1,
    'types'   : (int,),
    'help'    : "Number seconds to poll for watched file's modification "
                "timestamp. When a file is modified server is restarted."
}

class CommandServe( Singleton ):
    """Sub-command to starts a web server (using epoll) for pluggdapps."""

    implements( ICommand )

    description = "Start epoll based http server."
    cmd = 'serve'
    def __init__( self, *args, **kwargs ):
        self.module_mtimes = {}

    #---- ICommand API methods

    def subparser( self, parser, subparsers ):
        """:meth:`pluggdapps.interfaces.ICommand.subparser` interface method."""
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
        """If reload is enabled, then create a thread to poll for changing
        files, based on mtime, and serve http requests. When a file gets
        changed, return with a predefined exit code so that waiting process
        will restart the gemini server again.

        Typically used in development mode.
        """
        if args.mreload :
            # Launch a thread to poll and then start serving http
            t = threading.Thread( target=self.pollthread, 
                                  name='Reloader', args=(args,) )
            t.setDaemon(True)
            t.start()

        time.sleep(0.5) # To allow the poll-thread to execute first.
        self.pa.start() # Start pluggdapps
        server = self.query_plugin( IHTTPServer, self['IHTTPServer'] )
        server.start()  # Blocking call


    def fork_and_monitor( self, args ):
        """Install the reloading monitor."""
        while True :
            self.pa.logdebug( "Forking monitor ..." )
            pid = os.fork()
            if pid == 0 :   # child process
                cmdargs = sys.argv[:]
                cmdargs.remove( '-m' )
                cmdargs.append( os.environ )
                h.reseed_random()
                os.execlpe( sys.argv[0], *cmdargs )
                # signal.signal( signal.SIGIO, self._watch_handler )
                # self._watch_files( args )
                # self.gemini( args )
            else :          # parent 
                try :
                    pid, status = os.wait()
                    if status & 0xFF00 != 0x300 :
                        sys.exit( status )
                except KeyboardInterrupt :
                    sys.exit(0)
                    

    def pollthread( self, args ):
        """Thread (daemon) to monitor for changing files."""
        self.pa.logdebug( "Periodic poll started for module reloader ..." )
        while True:
            if self.pollthread_checkfiles( args ) == True :
                # use os._exit() here and not sys.exit() since within a
                # thread sys.exit() just closes the given thread and
                # won't kill the process; note os._exit does not call
                # any atexit callbacks, nor does it do finally blocks,
                # flush open files, etc.  In otherwords, it is rude.
                os._exit(3)
                break
            time.sleep( self['reload.poll_interval'] )

    def pollthread_checkfiles( self, args ):
        """Check whether any of the module files have modified after loading
        this platform. If so, return True else False."""
        files = [args.config] if args.config else []
        modfiles = {}
        for mod in sys.modules.values() :
            if hasattr( mod, '__file__' ) :
                modfiles.setdefault( getattr(mod, '__file__'), mod )

        for filename in list( modfiles.keys() ) + files :
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
        sett['reload'] = h.asbool( sett['reload'] )
        sett['reload.config'] = h.asbool( sett['reload.config'] )
        sett['reload.poll_interval'] = h.asbool( sett['reload.poll_interval'] )
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

    _watch_flag = fcntl.DN_MODIFY | fcntl.DN_CREATE | fcntl.DN_MULTISHOT
    def _watch_files( self, args ):
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
