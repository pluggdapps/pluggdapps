# -*- coding: utf-8 -*-

# Derived work from Facebook's tornado server.

"""Utilities for working with multiple processes."""

import os, sys, time, logging, errno

import pluggdapps.utils as h

log = logging.getLogger( __name__ )

_task_id = None

def fork_processes( num_processes, max_restarts ):
    """Starts multiple listener cum worker processes.

    If ``num_processes`` is None or <= 0, we detect the number of cores
    available on this machine and fork that number of child
    processes. If ``num_processes`` is given and > 0, we fork that
    specific number of sub-processes.

    Since we use processes and not threads, there is no shared memory
    between any server code.

    Note that multiple processes are not compatible with the autoreload
    module (or the debug=True option to `Platform`).
    When using multiple processes, no HTTPIOLoops can be created or
    referenced until after the call to ``fork_processes``.

    In each child process, ``fork_processes`` returns its *task id*, a
    number between 0 and ``num_processes``.  Processes that exit
    abnormally (due to a signal or non-zero exit status) are restarted
    with the same id (up to ``max_restarts`` times).  In the parent
    process, ``fork_processes`` returns None if all child processes
    have exited normally, but will otherwise only exit by throwing an
    exception.
    """
    global _task_id
    assert _task_id is None
    if num_processes is None or num_processes <= 0:
        num_processes = h.cpu_count()
    children = {}

    def start_child(i):
        log.info( "Starting http connection process process, taskid %s", i )
        pid = os.fork()
        if pid == 0:
            # child process
            h.reseed_random()
            global _task_id
            _task_id = i
            return i
        else:
            children[pid] = i
            return None
        
    for i in range(num_processes):
        id = start_child(i)
        if id is not None: # Return from child process
            return id
        # continue with spawning.

    num_restarts = 0
    while children :
        try:
            pid, status = os.wait()
        except OSError as e:
            if e.errno == errno.EINTR :
                continue
            raise

        if pid not in children :
            continue

        id = children.pop(pid)
        if os.WIFSIGNALED(status):
            log.warning( "child %d (pid %d) killed by signal %d, restarting",
                         id, pid, os.WTERMSIG(status) )
        elif os.WEXITSTATUS(status) != 0:
            log.warning( "child %d (pid %d) exited with status %d, restarting",
                         id, pid, os.WEXITSTATUS(status) )
        else:
            log.info( "child %d (pid %d) exited normally", id, pid )
            continue

        num_restarts += 1
        if num_restarts > max_restarts:
            raise RuntimeError("Too many child restarts, giving up")

        new_id = start_child(id)
        if new_id is not None:
            return new_id

    # All child processes exited cleanly, so exit the master process
    # instead of just returning to right after the call to
    # fork_processes (which will probably just start up another HTTPIOLoop
    # unless the caller checks the return value).
    sys.exit(0)


def task_id():
    """Returns the current task id, if any.

    Returns None if this process was not created by `fork_processes`.
    """
    global _task_id
    return _task_id
