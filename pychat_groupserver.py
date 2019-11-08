import socket
import shelve
import sys, os
import traceback
import time
import gzip
from time import sleep
from pickle import dumps, loads, dump, load
try:                from imp       import reload
except ImportError: from importlib import reload
from argparse import ArgumentParser
sys.path = [os.curdir] + sys.path
import groupserver_settings as conf
del sys.path[0]

arghandle = ArgumentParser()
arghandle.add_argument('-p', '--port', dest='Port', type=int, default=conf.Port,
    help='The port for PyChat to use')
arghandle.add_argument('-t', '--time', dest='Time_between_messages', type=int, metavar='Time', default=conf.Time_between_messages,
    help='The amount of time between when users can send messages (in seconds)')
arghandle.add_argument('-s', '--save', dest='Save_users_in_file', type=bool, metavar='True|False', default=conf.Save_users_in_file,
    help='The port for PyChat to use')
for (key, item) in vars(arghandle.parse_args()).items():
    data = 'conf.' + key + ' = ' + repr(item)
    print(data)
    exec(data)

users = {}
if conf.Save_users_in_file:
    print('loading users...')
    try: users = load(open('users.pkl', 'rb'))
    except:
        print('failed to load users')
        users = {}
    else:
        print('users loaded')

def getusrname(user):
    return str(users[user].get('nick', user))

def fromusr(user, message, direct=False):
    if not direct: ret = getusrname(user)
    else: ret = user
    return ret + (':\n\t' + message.replace('\n', '\n\t').strip() if message else '') + '\n'

from threading import Thread, Lock
mutex = Lock()
def _send(user, message, thread):
    if not isinstance(message, list): message = [message]
    sockobj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    for i in range(15):
        try:
            sockobj.connect(user)
            sockobj.send(dumps([conf.Port] + message))
            sockobj.close()
        except (ConnectionRefusedError, TimeoutError):
            try:
                if i >= 14: users[user]['err'] += 1
            except KeyError: users[user]['err'] = 1
        else:
            users[user]['err'] = 0
            break
    if users[user]['err'] > 15: del users[user]
    mutex.acquire()
    print('thread 0x%04x has exited' % thread.ident, file=sys.stderr)
    mutex.release()
def send(user, message):
    thread = Thread(target=_send)
    thread._args = (user, message, thread)
    thread.start()

def checkmaster(pswd):
    if pswd == conf.Master_password:
        send(addr, fromusr(conf.Host_username, conf.__doc__, direct=True))
        return True
    else:
        send(addr, fromusr(conf.Host_username, conf.Access_denied_message, direct=True))
        return False

def usrlist():
    ret = ''
    for (ukey, uitem) in users.items():
        data = ''
        for (dkey, ditem) in uitem.items():
            data += repr(dkey) + ' => ' + repr(ditem) + '\n'
        ret += fromusr(ukey, data)
    return fromusr(conf.Host_username, ret, direct=True)

def intercept(addr, cmd, args=''):
    cmd = cmd.lower()[1:]
    if cmd == 'nick': users[addr]['nick'] = args
    elif cmd == 'leave':
        send(addr, fromusr(conf.Host_username, conf.Goodbye_message, direct=True))
        del users[addr]
    elif cmd == 'help':
        send(addr, fromusr(conf.Host_username, conf.Help_message, direct=True))
    elif cmd == 'join':
        send(addr, fromusr(conf.Host_username, conf.Join_message, direct=True))
    elif cmd == 'usrlist':
        send(addr, usrlist())
    elif cmd == 'updatesettings' and checkmaster(args): reload(conf)
    elif cmd == 'masterhelp' and checkmaster(args): return
    elif cmd == 'destroy' and checkmaster(args):
        end()
        sys.exit()
    else: send(addr, fromusr(conf.Host_username, 'Invalid command %s' % repr(cmd), direct=True))

def end():
    print('quitting group server...')
    if conf.Save_users_in_file:
        print('saving users...')
        dump(users, open('users.pkl', 'wb'))
        print('saved users')
from atexit import register
register(end)

sockobj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sockobj.bind(('', conf.Port))
sockobj.listen(conf.Message_backwash)
while True:
    try:
        while True:
            conn, addr = sockobj.accept()
            data = bytes()
            while True:
                recv = conn.recv(1024)
                if not recv: break
                data += recv
            message = loads(data)
            message = list(message)
            addr = (addr[0], message[0])
            if not addr in users: users[addr] = {'err': 0}
            if message[1].startswith('/'):
                intercept(addr, *message[1].split(' ', 1))
                mutex.acquire()
                print('command', repr(message[1]), 'sent by', addr)
                mutex.release()
            else:
                message[1] = fromusr(addr, message[1])
                if (len(message) > 3) and (len(message[3]) > (conf.Max_attachment_size * 1048576)):
                    message[3] = gzip.compress((conf.Placeholder_attachment_text
                        % dict(max=conf.Max_attachment_size, size=len(message[3]) / 1048576))
                        .encode())
                    message[2] = conf.Placeholder_attachment_filename
                for user in users:
                    send(user, message[1:])
                    mutex.acquire()
                    if user == addr: print('message sent by', getusrname(user))
                    mutex.release()
            sleep(conf.Time_between_messages)
    except Exception as exc:
        #print('Error in server:\nTraceback (most recent call last):\n%s\n%s' %
        #    (traceback.print_exc, exc.__class__.__name__))
        traceback.print_exc()