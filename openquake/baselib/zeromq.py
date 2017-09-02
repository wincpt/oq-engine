import multiprocessing
import threading
import re
import zmq
try:
    from setproctitle import setproctitle
except ImportError:
    def setproctitle(title):
        "Do nothing"
from openquake.baselib.parallel import safely_call

REQ = zmq.REQ
REP = zmq.REP
PUSH = zmq.PUSH
PULL = zmq.PULL
ROUTER = zmq.ROUTER
DEALER = zmq.DEALER
PUB = zmq.PUB
SUB = zmq.SUB
POLLIN = zmq.POLLIN
POLLOUT = zmq.POLLOUT


class _Context(zmq.Context):
    """
    A zmq Context subclass with methods .bind and .connect
    """
    def bind(self, end_point, socket_type, **kw):
        identity = kw.pop('identity') if 'identity' in kw else None
        socket = self.socket(socket_type, **kw)
        if identity:
            socket.identity = identity
        try:
            socket.bind(end_point)
        except Exception as exc:  # invalid end_point
            socket.close()
            raise exc.__class__('%s: %s' % (exc, end_point))
        return socket

    def bind_to_random_port(self, end_point, socket_type):
        # the end_point must end in :<min_port>-<max_port>
        p1, p2 = re.search(r':(\d+)-(\d+)$', end_point).groups()
        end_point = end_point.rsplit(':', 1)[0]  # strip port range
        socket = self.socket(socket_type)
        port = socket.bind_to_random_port(end_point, int(p1), int(p2))
        backurl = '%s:%d' % (end_point, port)
        return backurl, socket

    def connect(self, end_point, socket_type, **kw):
        identity = kw.pop('identity') if 'identity' in kw else None
        socket = self.socket(socket_type, **kw)
        if identity:
            socket.identity = identity
        try:
            socket.connect(end_point)
        except Exception as exc:  # invalid end_point
            socket.close()
            raise exc.__class__('%s: %s' % (exc, end_point))
        return socket

# NB: using a global context is probably good: http://250bpm.com/blog:23
context = _Context()


class Process(multiprocessing.Process):
    """
    Process with a zmq socket
    """
    def __init__(self, func, *args, **kw):
        def newfunc(*args, **kw):
            # the only reason it is not .instance() is that there may be a
            # stale Context instance already initialized, from the docs
            with context:
                func(*args, **kw)
        super(Process, self).__init__(target=newfunc, args=args, kwargs=kw)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, etype, exc, tb):
        self.join()


class Thread(threading.Thread):
    """
    Thread with a zmq socket
    """
    def __init__(self, func, *args, **kw):
        def newfunc(*args, **kw):
            try:
                func(*args, **kw)
            except zmq.ContextTerminated:  # CTRL-C was given
                pass
        super(Thread, self).__init__(target=newfunc, args=args, kwargs=kw)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, etype, exc, tb):
        self.join()


def streamer(frontend_url, backend_url):
    """
    A streamer routing messages from the frontend to the backend
    """
    with context.bind(frontend_url, PULL) as frontend, \
            context.bind(backend_url, PUSH) as backend:
        zmq.proxy(frontend, backend)


class Responder(object):
    def __init__(self, backend_url, socket_type):
        self.backend_url = backend_url
        self.socket_type = socket_type

    def __enter__(self):
        self.socket = context.connect(self.backend_url, self.socket_type)
        return self

    def __exit__(self, *args):
        self.socket.close()
        del self.socket

    def __call__(self, res):
        self.socket.send_pyobj(res)

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.backend_url)


def starmap(frontend_url, backend_url, func, allargs):
    """
    starmap a function over an iterator of arguments by using a zmq socket
    """
    backurl, receiver = context.bind_to_random_port(backend_url, PULL)
    sender = context.connect(frontend_url, PUSH)
    with sender:
        n = 0
        for args in allargs:
            args[-1].backurl = backurl
            sender.send_pyobj((func, args))
            n += 1
        yield n
    with receiver:
        for _ in range(n):
            yield receiver.recv_pyobj()


def workerpool(url, func=None):
    """
    A worker reading tuples and returning results to the backend via a zmq
    socket.

    :param url: URL where to connect
    :param func: if None, expects message to be pairs (cmd, args) else args
    """
    title = 'oq-worker ' + url
    pool = multiprocessing.Pool(ncores, setproctitle, (title,))
    receiver = context.connect(url, PULL)
    while True:
        if func is None:  # retrieve the cmd from the message
            cmd, args = receiver.recv_pyobj()
        else:  # use the provided func as cmd
            cmd, args = func, receiver.recv_pyobj()
        if cmd == 'stop':
            print('Received stop command')
            pool.terminate()
            break
        # NB: the starmap attached .backurl to the monitor argument
        resp = Responder(args[-1].backurl, PUSH)
        pool.apply_async(safely_call, (cmd, args, resp))
        # NB: passing a responder to safely_call, since passing a callback to
        # apply_async fails randomly with BrokenPipeErrors


if __name__ == '__main__':  # run workers
    import sys
    try:
        url, _ncores = sys.argv[1:]
        ncores = int(_ncores)
    except ValueError:
        url = sys.argv[1]
        ncores = multiprocessing.cpu_count()
    with context:
        workerpool(url)
