import socket
import shelve
import sys, os
import traceback
from time import sleep
from pickle import dumps, loads
try:                from imp       import reload
except ImportError: from importlib import reload
sys.path = [os.curdir] + sys.path
import groupserver_settings as conf
del sys.path[0]

users = {}
if conf.Save_users_in_file:
    users.update(shelve.open('Users'))

def getusrname(user):
    return str(users[user].get('nick', user))

def fromusr(user, message, direct=False):
    if not direct: ret = getusrname(user)
    else: ret = user
    return ret + ':\n\t' + message.replace('\n', '\n\t').strip()

def send(user, message):
    sockobj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sockobj.connect(user)
    sockobj.send(dumps((conf.Port, message)))
    sockobj.close()

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
    elif cmd == 'updatesettings' and checkmaster(args): reload(conf)
    elif cmd == 'masterhelp' and checkmaster(args): return
    elif cmd == 'destroy' and checkmaster(args):
        end()
        sys.exit()
    else: send(addr, fromusr(conf.Host_username, 'Invalid command %s' % repr(cmd), direct=True))

def end():
    print('quitting group server...')
    if conf.Save_users_in_file:
        shelve.open('Users').update(users)
        usershelve = shelve.open('Users')
        for user in users:
            usershelve[user] = users[user]
            print('succesfully saved the data', repr(users[user]), 'for the user', getusrname(user))
#from atexit import register
#register(end)

while True:
    try:
        while True:
            sockobj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sockobj.bind(('', conf.Port))
            sockobj.listen(0)
            conn, addr = sockobj.accept()
            data = bytes()
            while True:
                recv = conn.recv(1024)
                if not recv: break
                data += recv
            message = list(loads(data))
            addr = (addr[0], message[0])
            if not addr in users: users[addr] = {}
            if message[1].startswith('!'):
                intercept(addr, *message[1].split(' ', 1))
                print('command', repr(message[1]), 'sent by', addr)
            else:
                message[1] = fromusr(addr, message[1])
                for user in users:
                    send(user, message[1])
                    if user == addr: print('message sent by', getusrname(user))
            sleep(conf.Time_between_messages + 0.2)
    except BaseException as exc:
        #print('Error in server:\nTraceback (most recent call last):\n%s\n%s' %
        #    (traceback.print_exc, exc.__class__.__name__))
        traceback.print_exc()