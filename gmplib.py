import sys, socket, struct, io, time
import PIL, PIL.Image
class SizeError(OverflowError): pass

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
        if doconnect:
            self.connect()
    def connect(self):
        self.sock.connect(self.tuple)
    def isready(self):
        data = self.sock.recv(4)
        if not data: return False
        else: return data
    def _neg_send(self):
        self.sock.send(struct.pack('>f', self.lasttalk))
    def _neg_recv(self):
        return struct.unpack('>f', self.sock.recv(4))
    def negotioate(self, metothem):
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
                while leng < 16383:
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
                self.sock.send(len(data).to_bytes(1, 'big'))
                self.sock.send(data)
                self.sock.send(self.gmp.picture.tobytes())
                ulen = int.from_bytes(self.sock.recv(1), 'big')
                self.usrname = self.sock.recv(ulen).decode(self.gmp.encoding)
                data = b''
                leng = 0
                while leng < 16383:
                    data += self.sock.recv(1)
                    leng += 1
                self.picture = PIL.Image.frombytes('RGBA', (64, 64), data)

class _Message_Metaclass(type):
    def __getattr__(self, attr):
        if attr == 'default_connections':
            return self.__init__.__defaults__[2]
        else: return object.__getattribute__(self, attr)
class Message(metaclass=_Message_Metaclass):
    """This class is under construction."""
    def __init__(self, gmp, ip:str='127.0.0.1', port:int=1245):
        connections = gmp.connections
        tup = (ip, port)
        if tup in connections and not connections[tup].sock._closed:
            self.connection = connections[tup]
        else:
            sockobj = socket.socket()
            self.connection = Connection(sockobj, tup, False, gmp)
            connections[tup] = self.connection
        self.connection = Connection(sockobj, tup, False, gmp)
    def new_negotioate(self):
        self.connection.connect()
        self.connection.negotioate(True)
    def open_negotioate(self):
        self.connection.connect()
        self.connection.negotioate(False)

class GMP:
    def __init__(self, usrname, picture=PIL.Image.new('RGBA', (64, 64)), encoding='utf-8'):
        self.lastupdate = time.time()
        self.connections = {}
        self.encoding = encoding
        self.usrname = usrname
        self.picture = picture.resize((64, 64)).convert('RGBA')

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
    gmp = GMP('Gaming32', PIL.Image.open(r"E:\Downloads\Gaming 32 - Copy - Copy.png"))
    sockobj = socket.socket()
    sockobj.bind(('', 1492))
    sockobj.listen(0)
    print('Gaming32 accepting connection on port 1492...')
    conn, addr = sockobj.accept()
    print('connection accepted from', addr)
    connobj = Connection(conn, addr, False, gmp)
    connobj.negotioate(True)