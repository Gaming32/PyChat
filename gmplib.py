import sys, socket, struct, io, time, _thread, queue
import PIL, PIL.Image
class SizeError(OverflowError): pass
class NoData(BaseException): pass

__version__ = '1.0.0 (no docs)'
__author__ = 'Gaming32'
__credits__ = '\n'.join(['theglossy1'])
__email__ = 'gaming32i64@gmail.com'
__status__ = 'Prototype'

def _checksize(component, length, maxlength):
    if length > maxlength:
            raise SizeError('%s exceeds size limit (%i > %i)' % (component, length, maxlength))

def _convert(data, component, compname, maxsize, maxlength, encoding, mylen=None):
    if mylen is None:
        mylen = len(component)
    _checksize(compname, mylen, maxlength)
    dat = mylen.to_bytes(maxsize, 'big')
    if encoding is not None:
        dat += component.encode(encoding)
    else:
        dat += component
    data += dat
    return data

_HASMESSAGE = 0b10000000
_HASATTACHMENT = 0b01000000

def assemble_message(message=None, attachment=None, attachment_filename=None, extra=[], maxsize=3, encoding='utf-8', chunksize=1024) -> bytes:
    """This function turns your message and its attachment into binary compatible with gmp.
    
    Parameters
    ----------
    message : str, optional
    attachment : buffer object, optional
    attachment_filename : str, optional
        the filename of the attachment to send with the message, defaults to attachment.name,
        otherwise attachment.fileno(), otherwise 'unknown_filename'
    extra : list, optional
        a list of extra data to send with the message (e.g. sending server data in a chat server
        program)
    maxsize : int, optional
        the number of bytes used to signify the size of your message parts; to find out the maximum
        size of your message parts in bytes, use this formula (where x is maxsize): 256 ** x - 1
    encoding : str, optional
        the encoding to use for text parts of the message (including the attachment if it is a
        form of StringIO)
    chunksize : int, optional
        the number of bytes to copy from the attachment to the raw message at one time
    
    Returns
    -------
    bytes
        your assembled message"""
    ismsg = bool(message)    * _HASMESSAGE
    isatt = bool(attachment) * _HASATTACHMENT
    header = ismsg | isatt | maxsize
    data = bytes((header,))
    realmax = 256 ** maxsize - 1
    if message:
        data = _convert(data, message, 'message', maxsize, realmax, encoding)
    if attachment:
        if attachment_filename is not None: pass
        elif hasattr(attachment, 'name'):
            attachment_filename = attachment.name
        elif hasattr(attachment, 'fileno'):
            try:
                attachment_filename = attachment.fileno()
            except OSError:
                attachment_filename = 'unknown_filename'
        else:
            attachment_filename = 'unknown_filename'
        attachment_filename = str(attachment_filename)
        data = _convert(data, attachment_filename, 'attachment filename', maxsize, realmax, encoding)
        doenc = False
        if hasattr(attachment, 'newlines'):
            doenc = True
        curlen = 0
        attdat = b''
        while True:
            newdat = attachment.read(chunksize)
            if doenc:
                newdat = newdat.encode(encoding)
                newdat = newdat.replace('\n', attachment.newlines)
            if not newdat: break
            curlen += len(newdat)
            _checksize('attachment', curlen, realmax)
            attdat += newdat
        data = _convert(data, attdat, 'attachment', maxsize, realmax, None)
    for item in extra:
        if isinstance(item, str):
            data = _convert(data, item, 'extra string item', maxsize, realmax, encoding)
        else:
            data = _convert(data, item, 'extra binary item', maxsize, realmax, None)
    return data

def disassamble_message(data, encoding='utf-8', chunksize=1024) -> (str, io.BytesIO):
    """"""
    data = io.BytesIO(data)
    header = data.read(1)[0]
    maxlen = int(bin(header)[4:], base=2)
    if header & _HASMESSAGE:
        length = int.from_bytes(data.read(maxlen), 'big')
        i = 0
        message = ''
        while i < length:
            newdata = data.read(min(chunksize, length))
            i += len(newdata)
            message += newdata.decode(encoding)
    else: message = None
    if header & _HASATTACHMENT:
        length = int.from_bytes(data.read(maxlen), 'big')
        i = 0
        attachment_filename = ''
        while i < length:
            newdata = data.read(min(chunksize, length))
            i += len(newdata)
            attachment_filename += newdata.decode(encoding)
        length = int.from_bytes(data.read(maxlen), 'big')
        i = 0
        attachment_data = b''
        while i < length:
            newdata = data.read(min(chunksize, length))
            i += len(newdata)
            attachment_data += newdata
        attachment = io.BytesIO(attachment_data)
        attachment.name = attachment_filename
    else: attachment = None
    extra = []
    length = data.read(maxlen)
    while length != b'':
        length = int.from_bytes(length, 'big')
        i = 0
        extradat = b''
        while i < length:
            newdata = data.read(min(chunksize, length))
            i += len(newdata)
            extradat += newdata
        extra.append(extradat)
        length = data.read(maxlen)
    return message, attachment, extra

class Connection:
    def __init__(self, sock, tup, doconnect, gmp):
        self.sock = sock
        self.tuple = tup
        self.lasttalk = -1
        self.usrname = '?' * 32
        self.picture = PIL.Image.new('RGBA', (64, 64))
        self.gmp = gmp
        if self.tuple not in gmp.connections:
            gmp.connections[self.tuple] = self
        self._connected = False
        if doconnect:
            self.connect()
    def connect(self):
        if not self._connected:
            self.sock.connect(self.tuple)
            self._connected = True
    def isready(self):
        self.sock.setblocking(False)
        try: data = self.sock.recv(4)
        except BlockingIOError:
            self.sock.setblocking(True)
            return False
        else:
            self.sock.setblocking(True)
            return data
    def _neg_send(self):
        self.sock.send(struct.pack('>f', self.lasttalk))
    def _neg_recv(self):
        return struct.unpack('>f', self.sock.recv(4))
    def negotioate(self, metothem):
        self.sock.setblocking(True)
        try: self._negotioate(metothem)
        except ConnectionError:
            self._connected = False
            raise
    def _negotioate(self, metothem):
        if metothem:
            self._neg_send()
            lasttalk = self.lasttalk
            hastalked = not lasttalk < self.gmp.lastupdate # True if talked recently
            self.sock.send(struct.pack('>?', hastalked))
            if not hastalked:
                ulen = int.from_bytes(self.sock.recv(1), 'big')
                self.usrname = self.sock.recv(ulen).decode(self.gmp.encoding)
                data = b''
                leng = 0
                while leng < 16384:
                    data += self.sock.recv(1)
                    leng += 1
                self.picture = PIL.Image.frombytes('RGBA', (64, 64), data)
                data = self.gmp.usrname.encode(self.gmp.encoding)
                self.sock.send(len(data).to_bytes(1, 'big'))
                self.sock.send(data)
                self.sock.send(self.gmp.picture.tobytes())
        else:
            lasttalk = self._neg_recv()
            hastalked = struct.unpack('>?', self.sock.recv(1))[0]
            if not hastalked:
                data = self.gmp.usrname.encode(self.gmp.encoding)
                self.sock.send(len(data).to_bytes(1, 'big'))
                self.sock.send(data)
                self.sock.send(self.gmp.picture.tobytes())
                ulen = int.from_bytes(self.sock.recv(1), 'big')
                self.usrname = self.sock.recv(ulen).decode(self.gmp.encoding)
                data = b''
                leng = 0
                while leng < 16384:
                    data += self.sock.recv(1)
                    leng += 1
                self.picture = PIL.Image.frombytes('RGBA', (64, 64), data)
    def send_message(self, *args, **kwargs):
        message = assemble_message(*args, **kwargs)
        self.sock.send(message)
    def recv_message(self, chunksize=1024):
        data = self.isready()
        if not data: raise NoData
        self.sock.setblocking(False)
        while True:
            try: newdata = self.sock.recv(chunksize)
            except BlockingIOError: break
            else:
                if not len(newdata): break
                data += newdata
        return data

class _Message_Metaclass(type):
    def __getattr__(self, attr):
        # if attr == 'default_connections':
        #     return self.__init__.__defaults__[2]
        # else: return object.__getattribute__(self, attr)
        return object.__getattribute__(self, attr)
class Message(metaclass=_Message_Metaclass):
    def __init__(self, gmp, ip:str='127.0.0.1', port:int=1245):
        connections = gmp.connections
        tup = (ip, port)
        if tup in connections and not connections[tup].sock._closed:
            self.connection = connections[tup]
        else:
            sockobj = socket.socket()
            self.connection = Connection(sockobj, tup, False, gmp)
            connections[tup] = self.connection
    def new_negotioate(self):
        self.connection.connect()
        self.connection.negotioate(True)
    def open_negotioate(self):
        self.connection.connect()
        self.connection.negotioate(False)
    def send(self, *args, **kwargs):
        self.new_negotioate()
        self.connection.send_message(*args, **kwargs)
    def recv(self, chunksize=1024):
        self.open_negotioate()
        return self.connection.recv_message(chunksize)

class GMP:
    def __init__(self, usrname, picture=PIL.Image.new('RGBA', (64, 64)), encoding='utf-8', chunksize=1024):
        self.lastupdate = time.time()
        self.connections = {}
        self.encoding = encoding
        self.chunksize = chunksize
        self._usrname = usrname
        self._picture = picture.resize((64, 64)).convert('RGBA')
        self.recv_callbacks = []
        self._recving = False
        self.messages_recved = queue.Queue()
        self.register_recv_callback(self._recv_callback)
    def _recv_callback(self, message):
        self.messages_recved.put(message)
    @property
    def usrname(self):
        return self._usrname
    @usrname.setter
    def usrname(self, usrname):
        self._usrname = usrname
        self.lastupdate = time.time()
    @property
    def picture(self):
        return self._picture
    @picture.setter
    def picture(self, picture=PIL.Image.new('RGBA', (64, 64))):
        self._picture = picture.resize((64, 64)).convert('RGBA')
        self.lastupdate = time.time()
    def send_message(self, ip='127.0.0.1', port=1245, *args, **kwargs):
        message = Message(self, ip, port)
        message.send(*args, encoding=self.encoding, chunksize=self.chunksize, **kwargs)
    def recv_message(self):
        for connection in self.connections.values():
            message = Message(self, *connection.tuple)
            try: data = message.recv(self.chunksize)
            except NoData: continue
            else: return disassamble_message(data, self.encoding, self.chunksize)
    def register_recv_callback(self, func):
        self.recv_callbacks.append(func)
    def recv_messages(self, pause=0.01):
        self._recving = True
        _thread.start_new_thread(self._recv_messages, (pause,))
    def stop_recv_messages(self):
        self._recving = False
    def _recv_messages(self, pause=0.01):
        while self._recving:
            message = self.recv_message()
            for callback in self.recv_callbacks:
                callback(message)
    def get_address_from_usrname(self, username, forceconnected=True):
        for (tup, connection) in self.connections.items():
            if connection.usrname == username:
                if (not forceconnected) or connection._connected:
                    return tup
        raise KeyError('no%s user named %r found' % (' connected'*forceconnected, username))
    def wait_new_user(self, addr=('', 1245), backlog=None):
        if hasattr(self, 'socket'):
            sockobj = self.socket
        else:
            sockobj = socket.socket()
            sockobj.bind(addr)
            if backlog is not None:
                sockobj.listen(backlog)
            else:
                sockobj.listen()
            self.socket = sockobj
        conn, addr = sockobj.accept()
        connobj = Connection(conn, addr, False, self)
        connobj._connected = True
        return connobj
    def connect(self, addr=('localhost', 1245), forceconnect=False):
        sockobj = socket.socket()
        connobj = Connection(sockobj, addr, forceconnect, self)
        return connobj

if __name__ == '__main__':
    # rawmessage = assemble_message('Hello World!', open('groupserver.tar', 'rb'), extra=['55', b'\x55\x55'])
    # # rawmessage = assemble_message('Hello World!', maxsize=255)
    # print(rawmessage)
    # message, attachment, extra = disassamble_message(rawmessage)
    # print(message)
    # print(attachment)
    # if not attachment is None:
    #     print(attachment.getvalue()[:64], '...')
    #     print(attachment.name)
    # import pprint
    # pprint.pprint(extra)
    # print(_float_to_hex(1/3))
    # newgmp = GMP()
    # newmsg = Message(newgmp)
    # print(Message.default_connections)
    if len(sys.argv) > 1:
        gmp = GMP('Gaming32', PIL.Image.open(r"E:\Downloads\Gaming 32 - Copy - Copy.png"))
        sockobj = socket.socket()
        sockobj.bind(('', 1492))
        sockobj.listen(0)
        print('Gaming32 accepting connection on port 1492...')
        conn, addr = sockobj.accept()
        print('connection accepted from', addr)
        connobj = Connection(conn, addr, False, gmp)
        connobj._connected = True
        # connobj.negotioate(True)
        # time.sleep(10)
        time.sleep(1)
        c = 0
        def callback(message):
            global c
            print(message)
            time.sleep(1)
            c += 1
            gmp.send_message(*gmp.get_connection_from_usrname('local'), str(c))
        gmp.register_recv_callback(callback)
        gmp.recv_messages()
        time.sleep(30)
    else:
        gmp = GMP('local', PIL.Image.open(r"C:\Users\josia\Pictures\DAT DAT.png"))
        sockobj = socket.socket()
        print('local connecting...')
        connobj = Connection(sockobj, ('localhost', 1492), True, gmp)
        # connobj.negotioate(False)
        # gmp.send_message('localhost', 1492, message='Hello World!')
        c = 1
        gmp.send_message('localhost', 1492, '0')
        def callback(message):
            global c
            print(message)
            time.sleep(1)
            c += 1
            gmp.send_message(*gmp.get_connection_from_usrname('Gaming32'), str(c))
        gmp.register_recv_callback(callback)
        gmp.recv_messages()
        time.sleep(30)