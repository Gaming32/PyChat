import sys
import socket, _thread, time
from frozendict import frozendict

def _conv_kwargs(func, args, kwargs):
    kwpos = func.__code__.co_varnames[:func.__code__.co_argcount]
    for (ix, item) in enumerate(args):
        kwargs[kwpos[ix]] = item
    return kwargs

class SubSocketWrapper:
    def __init__(self):
        self.sockets = {}
    def socket(self, *args, **kwargs):
        kwargs = frozendict(_conv_kwargs(socket.socket.__init__, args, kwargs))
        if not kwargs in self.sockets:
            sock = SubSocket(self, kwargs)
            self.sockets[kwargs] = sock
        else:
            sock = self.sockets[kwargs]
        return sock

def _sub_socket_ref_check(subsocket):
    saved = sys.getrefcount(subsocket)
    while True:
        refcount = sys.getrefcount(subsocket)
        if refcount < saved:
            subsocket.close()
        saved = refcount
        # print(sys.getrefcount(subsocket), end='\r')
        time.sleep(1)

class SubSocket:
    def __init__(self, parent, kwargs):
        self.kwargs = kwargs
        self.parent = parent
        self.kept_socket = socket.socket(**kwargs)
        self.socket = self.kept_socket
        _thread.start_new_thread(_sub_socket_ref_check, (self,))
    def __getattr__(self, attr):
        return getattr(self.socket, attr)
    def close(self):
        self.socket = None
    def connect(self, addr):
        if self.socket is None:
            self.socket = self.kept_socket
        self.socket.connect(addr)