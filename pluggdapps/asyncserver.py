"""An I/O event loop for non-blocking sockets.

In addition to I/O events, the `IOLoop` can also schedule time-based events.
`IOLoop.add_timeout` is a non-blocking alternative to `time.sleep`.
"""

from __future__ import absolute_import, division, with_statement

import datetime, errno, heapq, time, collections
import os, sys, re, fcntl, logging, traceback, ssl
import select, signal, thread, threading, socket

from   utils    import timedelta_to_seconds

def set_close_exec( *fds ):
    for fd in fds :
        flags = fcntl.fcntl( fd, fcntl.F_GETFD )
        fcntl.fcntl( fd, fcntl.F_SETFD, flags | fcntl.FD_CLOEXEC )

def set_nonblocking( *fds ):
    for fd in fds :
        flags = fcntl.fcntl( fd, fcntl.F_GETFL )
        fcntl.fcntl( fd, fcntl.F_SETFL, flags | os.O_NONBLOCK )

class Waker( object ):
    def __init__(self):
        r, w = os.pipe()
        set_nonblocking(r, w)
        set_close_exec(r, w)
        self.reader = os.fdopen(r, "rb", 0)
        self.writer = os.fdopen(w, "wb", 0)

    def fileno(self):
        return self.reader.fileno()

    def wake(self):
        try           : self.writer.write(b"x"))
        except IOError: pass

    def consume(self):
        try           : while self.reader.read() : pass
        except IOError: pass

    def close(self):
        self.reader.close()
        self.writer.close()

# Constants from the epoll module
_EPOLLIN = 0x001
_EPOLLPRI = 0x002
_EPOLLOUT = 0x004
_EPOLLERR = 0x008
_EPOLLHUP = 0x010
_EPOLLRDHUP = 0x2000
_EPOLLONESHOT = (1 << 30)
_EPOLLET = (1 << 31)

class IOLoop(object):
    """A level-triggered I/O loop. A faster version of poll(2)."""

    # IOLoop events mapped to epoll events
    NONE = 0
    READ = _EPOLLIN
    WRITE = _EPOLLOUT
    ERROR = _EPOLLERR | _EPOLLHUP

    default_settings = {}

    def __init__( self, poll, settings={} ):
        # I/O Even poller
        self._poll = poll = poll or select.poll
        set_close_exec( poll.fileno() ) if hasattr( poll, 'fileno') else None
        self.settings = {}
        self.settings.update( self.default_settings )
        self.settings.update( settings )
        # Book-keeping
        self._handlers = {}   # map of descriptors and callback handlers
        self._events = {}     # map of descriptors and events unblocking them
        self._callbacks = []  # list of callbacks to call for each iteration
        self._callback_lock = threading.Lock() # synchronize _callback_lock
        self._timeouts = []   # list of _Timeout objects
        self._running = False # boolean whether ioloop is running
        self._stopped = False # stop() was called, and start() must exit
        self._thread_ident = None
        self._blocking_signal_threshold = None
        # Create a pipe that we send bogus data to when we want to wake
        # the I/O loop when it is idle
        self._waker = Waker()
        self.add_handler(
                self._waker.fileno(), 
                lambda fd, events: self._waker.consume(),
                self.READ )

    def close( self ):
        """Closes the IOLoop, freeing any resources used.

        An IOLoop must be completely stopped before it can be closed.  This
        means that `IOLoop.stop()` must be called *and* `IOLoop.start()` must
        be allowed to return before attempting to call `IOLoop.close()`.
        Therefore the call to `close` will usually appear just after
        the call to `start` rather than near the call to `stop`.
        """
        self.remove_handler( self._waker.fileno() )
        self.close_handlers()
        self._waker.close()
        self._poll.close()

    def close_handlers( self ):
        [ os.close(fd) for fd in self._handlers.keys()[:] ]

    def add_handler(self, fd, handler, events):
        """Registers the given handler to receive the given events for fd."""
        self._handlers[fd] = handler
        self._poll.register( fd, events | self.ERROR )

    def update_handler( self, fd, events ):
        """Changes the events we listen for fd."""
        self._poll.modify( fd, events | self.ERROR )

    def remove_handler( self, fd ):
        """Stop listening for events on fd."""
        self._handlers.pop( fd, None )
        self._events.pop( fd, None )
        self._poll.unregister( fd )

    def set_blocking_signal_threshold( self, seconds, action ):
        """Sends a signal if the ioloop is blocked for more than s seconds.

        Pass seconds=None to disable.  Requires python 2.6 on a unixy
        platform.

        The action parameter is a python signal handler.  Read the
        documentation for the python 'signal' module for more information.
        If action is None, the process will be killed if it is blocked for
        too long.
        """
        self._blocking_signal_threshold = seconds
        action = action if action is not None else signal.SIG_DFL
        signal.signal(signal.SIGALRM, action) if seconds is not None else None

    def set_blocking_log_threshold( self, seconds ):
        """Logs a stack trace if the ioloop is blocked for more than s seconds.
        Equivalent to set_blocking_signal_threshold(seconds, self.log_stack)
        """
        self.set_blocking_signal_threshold( seconds, self.log_stack )

    def log_stack( self, signal, frame ):
        """Signal handler to log the stack trace of the current thread.

        For use with set_blocking_signal_threshold.
        """
        fframe = ''.join(traceback.format_stack(frame))
        logging.warning( "IOLoop blocked for %f seconds in\n%s",
                         self._blocking_signal_threshold, fframe )

    def start( self ):
        """Starts the I/O loop.

        The loop will run until one of the I/O handlers calls stop(), which
        will make the loop stop after the current event iteration completes.
        """
        if self._stopped:
            self._stopped = False
            return

        self._thread_ident = thread.get_ident()
        self._running = True
        while True:
            poll_timeout = 3600.0

            # Prevent IO event starvation by delaying new callbacks
            # to the next iteration of the event loop.
            with self._callback_lock:
                callbacks = self._callbacks
                self._callbacks = []
            map( self._run_callback, callbacks )

            if self._timeouts :
                now = time.time()
                while self._timeouts :
                    if self._timeouts[0].callback is None : # timeout cancelled
                        heapq.heappop( self._timeouts )
                    elif self._timeouts[0].deadline <= now :
                        timeout = heapq.heappop( self._timeouts )
                        self._run_callback( timeout.callback )
                    else :
                        seconds = self._timeouts[0].deadline - now
                        poll_timeout = min( seconds, poll_timeout )
                        break

            if self._callbacks:
                # If any callbacks or timeouts called add_callback,
                # we don't want to wait in poll() before we run them.
                poll_timeout = 0.0

            
            if self._running == False : break   # <--- Exit IOLoop

            if self._blocking_signal_threshold is not None :
                # clear alarm so it doesn't fire while poll is waiting for
                # events.
                signal.setitimer( signal.ITIMER_REAL, 0, 0 )

            try:
                event_pairs = self._poll.poll( poll_timeout )
            except Exception, e:
                # Depending on python version and IOLoop implementation,
                # different exception types may be thrown and there are
                # two ways EINTR might be signaled:
                # * e.errno == errno.EINTR
                # * e.args is like (errno.EINTR, 'Interrupted system call')
                if (getattr(e, 'errno', None) == errno.EINTR or
                    (isinstance(getattr(e, 'args', None), tuple) and
                     len(e.args) == 2 and e.args[0] == errno.EINTR)):
                    continue
                else:
                    raise

            if self._blocking_signal_threshold is not None :
                signal.setitimer(
                    signal.ITIMER_REAL, self._blocking_signal_threshold, 0 )

            # Pop one fd at a time from the set of pending fds and run
            # its handler. Since that handler may perform actions on
            # other file descriptors, there may be reentrant calls to
            # this IOLoop that update self._events
            self._events.update( event_pairs )
            while self._events:
                fd, events = self._events.popitem()
                try:
                    self._handlers[fd]( fd, events )
                except (OSError, IOError), e :
                    if e.args[0] == errno.EPIPE:
                        # Happens when the client closes the connection
                        pass
                    else:
                        logging.error( "Exception in I/O handler for fd %s",
                                       fd, exc_info=True )
                except Exception:
                    logging.error( "Exception in I/O handler for fd %s",
                                   fd, exc_info=True )

        # Exit this IOLoop and reset the stopped flag so another start/stop 
        # pair can be issued
        self._stopped = False
        if self._blocking_signal_threshold is not None :
            signal.setitimer( signal.ITIMER_REAL, 0, 0 )

    def stop( self ):
        """Stop the loop after the current event loop iteration is complete.
        If the event loop is not currently running, the next call to start()
        will return immediately.

        To use asynchronous methods from otherwise-synchronous code (such as
        unit tests), you can start and stop the event loop like this::

          ioloop = IOLoop()
          async_method(ioloop=ioloop, callback=ioloop.stop)
          ioloop.start()

        ioloop.start() will return after async_method has run its callback,
        whether that callback was invoked before or after ioloop.start.

        Note that even after `stop` has been called, the IOLoop is not
        completely stopped until `IOLoop.start` has also returned.
        """
        self._running = False
        self._stopped = True
        self._waker.wake()

    def running( self ):
        """Returns true if this IOLoop is currently running."""
        return self._running

    def add_timeout( self, deadline, callback ):
        """Calls the given callback at the time deadline from the I/O loop.

        Returns a handle that may be passed to remove_timeout to cancel.

        ``deadline`` may be a number denoting a unix timestamp (as returned
        by ``time.time()`` or a ``datetime.timedelta`` object for a deadline
        relative to the current time.

        Note that it is not safe to call `add_timeout` from other threads.
        Instead, you must use `add_callback` to transfer control to the
        IOLoop's thread, and then call `add_timeout` from there.
        """
        timeout = _Timeout( deadline, callback )
        heapq.heappush( self._timeouts, timeout )
        return timeout

    def remove_timeout( self, timeout ):
        """Cancels a pending timeout.

        The argument is a handle as returned by add_timeout.
        """
        # Removing from a heap is complicated, so just leave the defunct
        # timeout object in the queue (see discussion in
        # http://docs.python.org/library/heapq.html).
        # If this turns out to be a problem, we could add a garbage
        # collection pass whenever there are too many dead timeouts.
        timeout.callback = None
        return None

    def add_callback( self, callback ):
        """Calls the given callback on the next I/O loop iteration.

        It is safe to call this method from any thread at any time.
        Note that this is the *only* method in IOLoop that makes this
        guarantee; all other interaction with the IOLoop must be done
        from that IOLoop's thread.  add_callback() may be used to transfer
        control from other threads to the IOLoop's thread.
        """
        with self._callback_lock:
            list_empty = not self._callbacks
            self._callbacks.append( callback )
        if list_empty and thread.get_ident() != self._thread_ident:
            # If we're in the IOLoop's thread, we know it's not currently
            # polling.  If we're not, and we added the first callback to an
            # empty list, we may need to wake it up (it may wake up on its
            # own, but an occasional extra wake is harmless).  Waking
            # up a polling IOLoop is relatively expensive, so we try to
            # avoid it when we can.
            self._waker.wake()

    def _run_callback(self, callback):
        try:
            callback()
        except Exception:
            self.handle_callback_exception(callback)

    def handle_callback_exception(self, callback):
        """This method is called whenever a callback run by the IOLoop
        throws an exception.

        By default simply logs the exception as an error.  Subclasses
        may override this method to customize reporting of exceptions.

        The exception itself is not passed explicitly, but is available
        in sys.exc_info.
        """
        logging.error("Exception in callback %r", callback, exc_info=True)


class _Timeout( object ):
    """An IOLoop timeout, a UNIX timestamp and a callback"""

    # Reduce memory overhead when there are lots of pending callbacks
    __slots__ = ['deadline', 'callback']

    def __init__( self, deadline, callback ):
        if isinstance(deadline, (int, long, float)):
            self.deadline = deadline
        elif isinstance( deadline, datetime.timedelta ):
            self.deadline = time.time() + _Timeout.timedelta_to_seconds(deadline)
        else:
            raise TypeError("Unsupported deadline %r" % deadline)
        self.callback = callback

    # Comparison methods to sort by deadline, with object id as a tiebreaker
    # to guarantee a consistent ordering.  The heapq module uses __le__
    # in python2.5, and __lt__ in 2.6+ (sort() and most other comparisons
    # use __lt__).
    def __lt__(self, other):
        return ((self.deadline, id(self)) < (other.deadline, id(other)))

    def __le__(self, other):
        return ((self.deadline, id(self)) <= (other.deadline, id(other)))


class PeriodicCallback(object):
    """Schedules the given callback to be called periodically.

    The callback is called every callback_time milliseconds.

    `start` must be called after the PeriodicCallback is created.
    """
    def __init__( self, callback, callback_time, io_loop ):
        self.callback = callback
        self.callback_time = callback_time
        self.io_loop = io_loop
        self._running = False   # Whether periodic timeout is active or not
        self._timeout = None    # _Timeout instance subscribed to ioloop

    def start(self):
        """Starts the timer."""
        self._running = True
        self._next_timeout = time.time()
        self._schedule_next()

    def stop(self):
        """Stops the timer."""
        self._running = False
        if self._timeout != None :
            self._timeout = self.io_loop.remove_timeout(self._timeout)

    def _run(self):
        if not self._running: return

        try:
            self.callback()
        except Exception:
            logging.error("Error in periodic callback", exc_info=True)
        self._schedule_next()

    def _schedule_next(self):
        if not self._running: return

        while self._next_timeout <= time.time() :
            self._next_timeout += self.callback_time / 1000.0
        self._timeout = self.io_loop.add_timeout(self._next_timeout, self._run)


class IOStream( object ):
    r"""A utility class to write to and read from a non-blocking socket.

    We support a non-blocking ``write()`` and a family of ``read_*()`` methods.
    All of the methods take callbacks (since writing and reading are
    non-blocking and asynchronous).

    The socket parameter may either be connected or unconnected.  For
    server operations the socket is the result of calling socket.accept().
    For client operations the socket is created with socket.socket(),
    and may either be connected before passing it to the IOStream or
    connected with IOStream.connect.
    """
    default_settings = {
        'max_buffer_size' : 104857600,
        'read_chunk_size' : 4096,
    }

    def __init__( self, socket, io_loop, settings={} ):
        self.socket = socket
        self.socket.setblocking(False)
        self.io_loop = io_loop
        self.settings = {}
        self.settings.update( self.default_settings )
        self.settings.update( settings )
        self._state = None
        self._pending_callbacks = 0
        # Connection state-vars
        self._connect_callback = None
        self._connecting = False
        self._close_callback = None
        # Read state-vars
        self._read_callback = None
        self._streaming_callback = None
        self._read_buffer = collections.deque()
        self._read_buffer_size = 0
        self._read_delimiter = None
        self._read_regex = None
        self._read_bytes = None
        self._read_until_close = False
        # Write state-vars
        self._write_buffer = collections.deque()
        self._write_buffer_frozen = False
        self._write_callback = None

    def connect( self, address, callback=None ):
        """Connects the socket to a remote address without blocking.

        May only be called if the socket passed to the constructor was
        not previously connected.  The address parameter is in the
        same format as for socket.connect, i.e. a (host, port) tuple.
        If callback is specified, it will be called when the
        connection is completed.

        Note that it is safe to call IOStream.write while the
        connection is pending, in which case the data will be written
        as soon as the connection is ready.  Calling IOStream read
        methods before the socket is connected works on some platforms
        but is non-portable.
        """
        self._connecting = True
        try:
            self.socket.connect(address)
        except socket.error, e:
            # In non-blocking mode we expect connect() to raise an
            # exception with EINPROGRESS or EWOULDBLOCK.
            #
            # On freebsd, other errors such as ECONNREFUSED may be
            # returned immediately when attempting to connect to
            # localhost, so handle them the same way as an error
            # reported later in _handle_connect.
            if e.args[0] not in (errno.EINPROGRESS, errno.EWOULDBLOCK):
                logging.warning( "Connect error on fd %d: %s",
                                 self.socket.fileno(), e )
                self.close()
                return
        self._connect_callback = callback
        self._add_io_state(self.io_loop.WRITE)

    def read_until_regex(self, regex, callback):
        """Call callback when we read the given regex pattern."""
        self._set_read_callback(callback)
        self._read_regex = re.compile(regex)
        self._try_inline_read()

    def read_until(self, delimiter, callback):
        """Call callback when we read the given delimiter."""
        self._set_read_callback(callback)
        self._read_delimiter = delimiter
        self._try_inline_read()

    def read_bytes(self, num_bytes, callback, streaming_callback=None):
        """Call callback when we read the given number of bytes.

        If a ``streaming_callback`` is given, it will be called with chunks
        of data as they become available, and the argument to the final
        ``callback`` will be empty.
        """
        self._set_read_callback(callback)
        assert isinstance(num_bytes, (int, long))
        self._read_bytes = num_bytes
        self._streaming_callback = streaming_callback
        self._try_inline_read()

    def read_until_close(self, callback, streaming_callback=None):
        """Reads all data from the socket until it is closed.

        If a ``streaming_callback`` is given, it will be called with chunks
        of data as they become available, and the argument to the final
        ``callback`` will be empty.

        Subject to ``max_buffer_size`` limit from `IOStream` constructor if
        a ``streaming_callback`` is not used.
        """
        self._set_read_callback(callback)
        if self.closed():
            self._run_callback(callback, self._consume(self._read_buffer_size))
            self._read_callback = None
            return
        self._read_until_close = True
        self._streaming_callback = streaming_callback
        self._add_io_state(self.io_loop.READ)

    def write(self, data, callback=None):
        """Write the given data to this stream.

        If callback is given, we call it when all of the buffered write
        data has been successfully written to the stream. If there was
        previously buffered write data and an old write callback, that
        callback is simply overwritten with this new callback.
        """
        assert isinstance(data, bytes)
        self._check_closed()
        if data:
            # We use bool(_write_buffer) as a proxy for write_buffer_size>0,
            # so never put empty strings in the buffer.
            self._write_buffer.append(data)
        self._write_callback = callback
        self._handle_write()
        if self._write_buffer:
            self._add_io_state(self.io_loop.WRITE)
        self._maybe_add_error_listener()

    def set_close_callback(self, callback):
        """Call the given callback when the stream is closed."""
        self._close_callback = callback

    def close(self):
        """Close this stream."""
        if self.socket is not None:
            if self._read_until_close:
                callback = self._read_callback
                self._read_callback = None
                self._read_until_close = False
                self._run_callback(callback,
                                   self._consume(self._read_buffer_size))
            if self._state is not None:
                self.io_loop.remove_handler(self.socket.fileno())
                self._state = None
            self.socket.close()
            self.socket = None
        self._maybe_run_close_callback()

    def _maybe_run_close_callback(self):
        if (self.socket is None and self._close_callback and
            self._pending_callbacks == 0):
            # if there are pending callbacks, don't run the close callback
            # until they're done (see _maybe_add_error_handler)
            cb = self._close_callback
            self._close_callback = None
            self._run_callback(cb)

    def reading(self):
        """Returns true if we are currently reading from the stream."""
        return self._read_callback is not None

    def writing(self):
        """Returns true if we are currently writing to the stream."""
        return bool(self._write_buffer)

    def closed(self):
        """Returns true if the stream has been closed."""
        return self.socket is None

    def _handle_events(self, fd, events):
        if not self.socket:
            logging.warning("Got events for closed stream %d", fd)
            return
        try:
            if events & self.io_loop.READ:
                self._handle_read()
            if not self.socket:
                return
            if events & self.io_loop.WRITE:
                if self._connecting:
                    self._handle_connect()
                self._handle_write()
            if not self.socket:
                return
            if events & self.io_loop.ERROR:
                # We may have queued up a user callback in _handle_read or
                # _handle_write, so don't close the IOStream until those
                # callbacks have had a chance to run.
                self.io_loop.add_callback(self.close)
                return
            state = self.io_loop.ERROR
            if self.reading():
                state |= self.io_loop.READ
            if self.writing():
                state |= self.io_loop.WRITE
            if state == self.io_loop.ERROR:
                state |= self.io_loop.READ
            if state != self._state:
                assert self._state is not None, \
                    "shouldn't happen: _handle_events without self._state"
                self._state = state
                self.io_loop.update_handler(self.socket.fileno(), self._state)
        except Exception:
            logging.error("Uncaught exception, closing connection.",
                          exc_info=True)
            self.close()
            raise

    def _run_callback(self, callback, *args):
        def wrapper():
            self._pending_callbacks -= 1
            try:
                callback(*args)
            except Exception:
                logging.error("Uncaught exception, closing connection.",
                              exc_info=True)
                # Close the socket on an uncaught exception from a user callback
                # (It would eventually get closed when the socket object is
                # gc'd, but we don't want to rely on gc happening before we
                # run out of file descriptors)
                self.close()
                # Re-raise the exception so that IOLoop.handle_callback_exception
                # can see it and log the error
                raise
            self._maybe_add_error_listener()
        # We schedule callbacks to be run on the next IOLoop iteration
        # rather than running them directly for several reasons:
        # * Prevents unbounded stack growth when a callback calls an
        #   IOLoop operation that immediately runs another callback
        # * Provides a predictable execution context for e.g.
        #   non-reentrant mutexes
        # * Ensures that the try/except in wrapper() is run outside
        #   of the application's StackContexts
        self._pending_callbacks += 1
        self.io_loop.add_callback( wrapper )

    def _handle_read(self):
        try:
            try:
                # Pretend to have a pending callback so that an EOF in
                # _read_to_buffer doesn't trigger an immediate close
                # callback.  At the end of this method we'll either
                # estabilsh a real pending callback via
                # _read_from_buffer or run the close callback.
                #
                # We need two try statements here so that
                # pending_callbacks is decremented before the `except`
                # clause below (which calls `close` and does need to
                # trigger the callback)
                self._pending_callbacks += 1
                while True:
                    # Read from the socket until we get EWOULDBLOCK or equivalent.
                    # SSL sockets do some internal buffering, and if the data is
                    # sitting in the SSL object's buffer select() and friends
                    # can't see it; the only way to find out if it's there is to
                    # try to read it.
                    if self._read_to_buffer() == 0:
                        break
            finally:
                self._pending_callbacks -= 1
        except Exception:
            logging.warning("error on read", exc_info=True)
            self.close()
            return
        if self._read_from_buffer():
            return
        else:
            self._maybe_run_close_callback()


    def _set_read_callback(self, callback):
        assert not self._read_callback, "Already reading"
        self._read_callback = callback

    def _try_inline_read(self):
        """Attempt to complete the current read operation from buffered data.

        If the read can be completed without blocking, schedules the
        read callback on the next IOLoop iteration; otherwise starts
        listening for reads on the socket.
        """
        # See if we've already got the data from a previous read
        if self._read_from_buffer():
            return
        self._check_closed()
        while True:
            if self._read_to_buffer() == 0:
                break
            self._check_closed()
        if self._read_from_buffer():
            return
        self._add_io_state(self.io_loop.READ)

    def _read_from_socket(self):
        """Attempts to read from the socket.

        Returns the data read or None if there is nothing to read.
        May be overridden in subclasses.
        """
        try:
            chunk = self.socket.recv(self.read_chunk_size)
        except socket.error, e:
            if e.args[0] in (errno.EWOULDBLOCK, errno.EAGAIN):
                return None
            else:
                raise
        if not chunk:
            self.close()
            return None
        return chunk

    def _read_to_buffer(self):
        """Reads from the socket and appends the result to the read buffer.

        Returns the number of bytes read.  Returns 0 if there is nothing
        to read (i.e. the read returns EWOULDBLOCK or equivalent).  On
        error closes the socket and raises an exception.
        """
        try:
            chunk = self._read_from_socket()
        except socket.error, e:
            # ssl.SSLError is a subclass of socket.error
            logging.warning("Read error on %d: %s",
                            self.socket.fileno(), e)
            self.close()
            raise
        if chunk is None:
            return 0
        self._read_buffer.append(chunk)
        self._read_buffer_size += len(chunk)
        if self._read_buffer_size >= self.max_buffer_size:
            logging.error("Reached maximum read buffer size")
            self.close()
            raise IOError("Reached maximum read buffer size")
        return len(chunk)

    def _read_from_buffer(self):
        """Attempts to complete the currently-pending read from the buffer.

        Returns True if the read was completed.
        """
        if self._streaming_callback is not None and self._read_buffer_size:
            bytes_to_consume = self._read_buffer_size
            if self._read_bytes is not None:
                bytes_to_consume = min(self._read_bytes, bytes_to_consume)
                self._read_bytes -= bytes_to_consume
            self._run_callback(self._streaming_callback,
                               self._consume(bytes_to_consume))
        if self._read_bytes is not None and self._read_buffer_size >= self._read_bytes:
            num_bytes = self._read_bytes
            callback = self._read_callback
            self._read_callback = None
            self._streaming_callback = None
            self._read_bytes = None
            self._run_callback(callback, self._consume(num_bytes))
            return True
        elif self._read_delimiter is not None:
            # Multi-byte delimiters (e.g. '\r\n') may straddle two
            # chunks in the read buffer, so we can't easily find them
            # without collapsing the buffer.  However, since protocols
            # using delimited reads (as opposed to reads of a known
            # length) tend to be "line" oriented, the delimiter is likely
            # to be in the first few chunks.  Merge the buffer gradually
            # since large merges are relatively expensive and get undone in
            # consume().
            if self._read_buffer:
                while True:
                    loc = self._read_buffer[0].find(self._read_delimiter)
                    if loc != -1:
                        callback = self._read_callback
                        delimiter_len = len(self._read_delimiter)
                        self._read_callback = None
                        self._streaming_callback = None
                        self._read_delimiter = None
                        self._run_callback(callback,
                                           self._consume(loc + delimiter_len))
                        return True
                    if len(self._read_buffer) == 1:
                        break
                    _double_prefix(self._read_buffer)
        elif self._read_regex is not None:
            if self._read_buffer:
                while True:
                    m = self._read_regex.search(self._read_buffer[0])
                    if m is not None:
                        callback = self._read_callback
                        self._read_callback = None
                        self._streaming_callback = None
                        self._read_regex = None
                        self._run_callback(callback, self._consume(m.end()))
                        return True
                    if len(self._read_buffer) == 1:
                        break
                    _double_prefix(self._read_buffer)
        return False

    def _handle_connect(self):
        err = self.socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
        if err != 0:
            # IOLoop implementations may vary: some of them return
            # an error state before the socket becomes writable, so
            # in that case a connection failure would be handled by the
            # error path in _handle_events instead of here.
            logging.warning("Connect error on fd %d: %s",
                            self.socket.fileno(), errno.errorcode[err])
            self.close()
            return
        if self._connect_callback is not None:
            callback = self._connect_callback
            self._connect_callback = None
            self._run_callback(callback)
        self._connecting = False

    def _handle_write(self):
        while self._write_buffer:
            try:
                if not self._write_buffer_frozen:
                    # On windows, socket.send blows up if given a
                    # write buffer that's too large, instead of just
                    # returning the number of bytes it was able to
                    # process.  Therefore we must not call socket.send
                    # with more than 128KB at a time.
                    _merge_prefix(self._write_buffer, 128 * 1024)
                num_bytes = self.socket.send(self._write_buffer[0])
                if num_bytes == 0:
                    # With OpenSSL, if we couldn't write the entire buffer,
                    # the very same string object must be used on the
                    # next call to send.  Therefore we suppress
                    # merging the write buffer after an incomplete send.
                    # A cleaner solution would be to set
                    # SSL_MODE_ACCEPT_MOVING_WRITE_BUFFER, but this is
                    # not yet accessible from python
                    # (http://bugs.python.org/issue8240)
                    self._write_buffer_frozen = True
                    break
                self._write_buffer_frozen = False
                _merge_prefix(self._write_buffer, num_bytes)
                self._write_buffer.popleft()
            except socket.error, e:
                if e.args[0] in (errno.EWOULDBLOCK, errno.EAGAIN):
                    self._write_buffer_frozen = True
                    break
                else:
                    logging.warning("Write error on %d: %s",
                                    self.socket.fileno(), e)
                    self.close()
                    return
        if not self._write_buffer and self._write_callback:
            callback = self._write_callback
            self._write_callback = None
            self._run_callback(callback)

    def _consume(self, loc):
        if loc == 0:
            return b""
        _merge_prefix(self._read_buffer, loc)
        self._read_buffer_size -= loc
        return self._read_buffer.popleft()

    def _check_closed(self):
        if not self.socket:
            raise IOError("Stream is closed")

    def _maybe_add_error_listener(self):
        if self._state is None and self._pending_callbacks == 0:
            if self.socket is None:
                self._maybe_run_close_callback()
            else:
                self._add_io_state(ioloop.IOLoop.READ)

    def _add_io_state(self, state):
        """Adds `state` (IOLoop.{READ,WRITE} flags) to our event handler.

        Implementation notes: Reads and writes have a fast path and a
        slow path.  The fast path reads synchronously from socket
        buffers, while the slow path uses `_add_io_state` to schedule
        an IOLoop callback.  Note that in both cases, the callback is
        run asynchronously with `_run_callback`.

        To detect closed connections, we must have called
        `_add_io_state` at some point, but we want to delay this as
        much as possible so we don't have to set an `IOLoop.ERROR`
        listener that will be overwritten by the next slow-path
        operation.  As long as there are callbacks scheduled for
        fast-path ops, those callbacks may do more reads.
        If a sequence of fast-path ops do not end in a slow-path op,
        (e.g. for an @asynchronous long-poll request), we must add
        the error handler.  This is done in `_run_callback` and `write`
        (since the write callback is optional so we can have a
        fast-path write with no `_run_callback`)
        """
        if self.socket is None:
            # connection has been closed, so there can be no future events
            return
        if self._state is None:
            self._state = ioloop.IOLoop.ERROR | state
            self.io_loop.add_handler( 
                self.socket.fileno(), self._handle_events, self._state )
        elif not self._state & state:
            self._state = self._state | state
            self.io_loop.update_handler( self.socket.fileno(), self._state )


class SSLIOStream(IOStream):
    """A utility class to write to and read from a non-blocking SSL socket.

    If the socket passed to the constructor is already connected,
    it should be wrapped with::

        ssl.wrap_socket(sock, do_handshake_on_connect=False, **kwargs)

    before constructing the SSLIOStream.  Unconnected sockets will be
    wrapped when IOStream.connect is finished.
    """
    def __init__(self, *args, **kwargs):
        """Creates an SSLIOStream.

        If a dictionary is provided as keyword argument ssl_options,
        it will be used as additional keyword arguments to ssl.wrap_socket.
        """
        self._ssl_options = kwargs.pop('ssl_options', {})
        super(SSLIOStream, self).__init__(*args, **kwargs)
        self._ssl_accepting = True
        self._handshake_reading = False
        self._handshake_writing = False

    def reading(self):
        return self._handshake_reading or super(SSLIOStream, self).reading()

    def writing(self):
        return self._handshake_writing or super(SSLIOStream, self).writing()

    def _do_ssl_handshake(self):
        # Based on code from test_ssl.py in the python stdlib
        try:
            self._handshake_reading = False
            self._handshake_writing = False
            self.socket.do_handshake()
        except ssl.SSLError, err:
            if err.args[0] == ssl.SSL_ERROR_WANT_READ:
                self._handshake_reading = True
                return
            elif err.args[0] == ssl.SSL_ERROR_WANT_WRITE:
                self._handshake_writing = True
                return
            elif err.args[0] in (ssl.SSL_ERROR_EOF,
                                 ssl.SSL_ERROR_ZERO_RETURN):
                return self.close()
            elif err.args[0] == ssl.SSL_ERROR_SSL:
                logging.warning("SSL Error on %d: %s", self.socket.fileno(), err)
                return self.close()
            raise
        except socket.error, err:
            if err.args[0] == errno.ECONNABORTED:
                return self.close()
        else:
            self._ssl_accepting = False
            super(SSLIOStream, self)._handle_connect()

    def _handle_read(self):
        if self._ssl_accepting:
            self._do_ssl_handshake()
            return
        super(SSLIOStream, self)._handle_read()

    def _handle_write(self):
        if self._ssl_accepting:
            self._do_ssl_handshake()
            return
        super(SSLIOStream, self)._handle_write()

    def _handle_connect(self):
        self.socket = ssl.wrap_socket(self.socket,
                                      do_handshake_on_connect=False,
                                      **self._ssl_options)
        # Don't call the superclass's _handle_connect (which is responsible
        # for telling the application that the connection is complete)
        # until we've completed the SSL handshake (so certificates are
        # available, etc).

    def _read_from_socket(self):
        if self._ssl_accepting:
            # If the handshake hasn't finished yet, there can't be anything
            # to read (attempting to read may or may not raise an exception
            # depending on the SSL version)
            return None
        try:
            # SSLSocket objects have both a read() and recv() method,
            # while regular sockets only have recv().
            # The recv() method blocks (at least in python 2.6) if it is
            # called when there is nothing to read, so we have to use
            # read() instead.
            chunk = self.socket.read(self.read_chunk_size)
        except ssl.SSLError, e:
            # SSLError is a subclass of socket.error, so this except
            # block must come first.
            if e.args[0] == ssl.SSL_ERROR_WANT_READ:
                return None
            else:
                raise
        except socket.error, e:
            if e.args[0] in (errno.EWOULDBLOCK, errno.EAGAIN):
                return None
            else:
                raise
        if not chunk:
            self.close()
            return None
        return chunk

def _double_prefix(deque):
    """Grow by doubling, but don't split the second chunk just because the
    first one is small.
    """
    new_len = max(len(deque[0]) * 2,
                  (len(deque[0]) + len(deque[1])))
    _merge_prefix(deque, new_len)


def _merge_prefix(deque, size):
    """Replace the first entries in a deque of strings with a single
    string of up to size bytes.

    >>> d = collections.deque(['abc', 'de', 'fghi', 'j'])
    >>> _merge_prefix(d, 5); print d
    deque(['abcde', 'fghi', 'j'])

    Strings will be split as necessary to reach the desired size.
    >>> _merge_prefix(d, 7); print d
    deque(['abcdefg', 'hi', 'j'])

    >>> _merge_prefix(d, 3); print d
    deque(['abc', 'defg', 'hi', 'j'])

    >>> _merge_prefix(d, 100); print d
    deque(['abcdefghij'])
    """
    if len(deque) == 1 and len(deque[0]) <= size:
        return
    prefix = []
    remaining = size
    while deque and remaining > 0:
        chunk = deque.popleft()
        if len(chunk) > remaining:
            deque.appendleft(chunk[remaining:])
            chunk = chunk[:remaining]
        prefix.append(chunk)
        remaining -= len(chunk)
    # This data structure normally just contains byte strings, but
    # the unittest gets messy if it doesn't use the default str() type,
    # so do the merge based on the type of data that's actually present.
    if prefix:
        deque.appendleft(type(prefix[0])().join(prefix))
    if not deque:
        deque.appendleft(b"")


def doctests():
    import doctest
    return doctest.DocTestSuite()
