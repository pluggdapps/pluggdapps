# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 Netscale Computing

import logging, os, fcntl, signal, sys, time, threading, traceback

from pluggdapps.const import ROOTAPP
from pluggdapps.config import ConfigDict
from pluggdapps.core import implements, pluginname
from pluggdapps.plugin import Singleton, query_plugin, ISettings
from pluggdapps.interfaces import ICommand
import pluggdapps.utils as h

# TODO :
#   * Should we explicitly check for multi-process server and avoid reloading
#   strategy ?
#   * While restarting, should we also consider pa.boot() method ?


log = logging.getLogger( __name__ )

_default_settings = ConfigDict()
_default_settings.__doc__ = (
    "Configuration for serve sub-command." )

_default_settings['reload'] = {
    'default' : False,
    'types'   : (bool,),
    'help'    : "Whether to monitor for changes to module files and watched "
                "files, and restart the server."
}
_default_settings['reload.config'] = {
    'default' : True,
    'types'   : (bool,),
    'help'    : "Via web configuration is supported by pluggdapps. This "
                "parameter specifies whether the server should be restarted "
                "when a configuration parameter is changed."
}
_default_settings['reload.poll_interval'] = {
    'default' : 1,
    'types'   : (int,),
    'help'    : "Number seconds to poll for watched file's modification "
                "timestamp. When a file is modified server is restarted."
}

class Serve( Singleton ):
    implements( ICommand )

    description = "Start http server."

    def __init__( self, *args, **kwargs ):
        self.module_mtimes = {}

    def subparser( self, parser, subparsers ):
        name = pluginname( self )
        self.subparser = subparsers.add_parser( 
                                name, description=self.description )
        self.subparser.set_defaults( handler=self.handle )
        self._arguments( self.subparser )

    def handle( self, args ):
        if args.monitor :
            self.gemini( args )
        else :
            self.serve( args )

    def serve( self, args ):
        self.app.pa.serve()
        self.app.pa.shutdown()

    def gemini( self, args ):
        """If reload is enabled, then create a thread to poll for changing
        files, based on mtime, and serve http requests. When a file gets
        changed, return with a predefined exit code so that waiting process
        will restart the gemini server again."""
        # Launch a thread to poll and then start serving http
        t = threading.Thread( target=self.pollthread, 
                              name='Reloader', args=(args,) )
        t.setDaemon(True)
        t.start()
        self.serve( args )

    def pollthread( self, args ):
        log.info( "Periodic poll started" )
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
        filenames = [args.config] if args.config else []
        filenames.extend( 
            getattr( mod, '__file__', None ) for mod in sys.modules.values()
        )
        filenames = filter( None, filenames )
        for filename in filenames:
            stat = os.stat(filename)
            if stat:
                mtime = stat.st_mtime
            else:
                mtime = 0

            if filename.endswith( '.pyc' ) and os.path.exists( filename[:-1] ):
                mtime = max(os.stat(filename[:-1]).st_mtime, mtime)
            elif filename.endswith('$py.class') and \
                    os.path.exists(filename[:-9] + '.py'):
                mtime = max(os.stat(filename[:-9] + '.py').st_mtime, mtime)

            if filename not in self.module_mtimes :
                self.module_mtimes[filename] = mtime
            elif self.module_mtimes[filename] < mtime:
                log.info( "Detected a change in %r ..." % filename )
                return True
        return False

    def _arguments( self, parser ):
        return parser


    #---- An alternate implementation for linux platforms. But incomplete !!
    #---- Only directories can be watched and sub-directories had to be walked
    #---- and added programmatically.

    def fork_and_monitor( self, args ):
        """Install the reloading monitor."""
        while True :
            pid = os.fork()
            if pid == 0 :   # child process
                h.reseed_random()
                signal.signal( signal.SIGIO, self._watch_handler )
                self._watch_files( args )
                self.serve( args )
            else :          # parent 
                pid, status = os.wait()
                if status != 3 :
                    sys.exit(status)

    def _watch_handler( signum, frame ):
        log.info("file changed; reloading...")
        # use os._exit() here and not sys.exit() since within a thread 
        # sys.exit() just closes the given thread and won't kill the process;
        # note os._exit does not call any atexit callbacks, nor does it do 
        # finally blocks, flush open files, etc.  In otherwords, it is rude.
        os._exit(3)

    watch_flag = fcntl.DN_MODIFY | fcntl.DN_CREATE | fcntl.DN_MULTISHOT
    def _watch_files( self, args ):
        filenames = [args.config] if args.config else []
        filenames.extend(
            getattr( mod, '__file__', None) for mod in sys.modules.values()
        )
        filenames = filter( None, filenames )
        for filename in filenames :
            fd = os.open( filename, os.O_RDONLY )
            fcntl.fcntl( fd, fcntl.F_SETSIG, 0 )
            fcntl.fcntl( fd, fcntl.F_NOTIFY, self.watch_flag )


    #---- ISettings interface methods

    @classmethod
    def default_settings( cls ):
        return _default_settings

    @classmethod
    def normalize_settings( cls, sett ):
        sett['reload'] = h.asbool( sett['reload'] )
        sett['reload.config'] = h.asbool( sett['reload.config'] )
        sett['reload.poll_interval'] = h.asbool( sett['reload.poll_interval'] )
        return sett

