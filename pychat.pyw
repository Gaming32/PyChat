from socket import socket, AF_INET, SOCK_STREAM
#import threading
from pickle import dumps, loads
import sys
from argparse import ArgumentParser
import queue
from tkinter import *
from tkinter.scrolledtext import ScrolledText
from tkinter.simpledialog import askinteger
from time import sleep
#from shelve import open as sopen
#chats = open('contacts')
win = Tk()
thisport = (len(sys.argv) > 1 and int(sys.argv[1])) or 0
share = queue.LifoQueue(2)

def recievechat():
    global state, sockobj, thisport
    if state == False:
        sockobj = socket(AF_INET, SOCK_STREAM)
        sockobj.setblocking(0)
        sockobj.bind(('', thisport))
        thisport = sockobj.getsockname()[1]
        sockobj.listen(50)
        state = True
    while True:
        try: conn, addr = sockobj.accept()
        except BlockingIOError: break
        data = bytes()
        while True:
            recv = conn.recv(1024)
            if not recv: break
            print('recieved', recv)
            data += recv
        port, data = loads(data)
        win.title('PyChat - user: %s - message from: %s' % (thisport, (addr[0], port)))
        lbl['state'] = NORMAL
        lbl.delete('1.0', 'end-1c')
        lbl.insert('1.0', data)
        lbl['state'] = DISABLED
        break
    state = win.after(1000, recievechat)

def chat():
    global state
    while state is True: sleep(0.05)
    win.after_cancel(state)
    sockobj = socket(AF_INET, SOCK_STREAM)
    i = 0
    while sockobj.connect_ex((host.get(), int(port.get()))) == 10061 and i < 15: i += 1
    if i < 15:
        data = dumps((thisport, txt.get('1.0','end-1c')))
        sockobj.send(data)
        print('sent    ', data)
    else:
        print('error sending')
        lbl['state'] = NORMAL
        lbl.delete('1.0', 'end-1c')
        lbl.insert('1.0', 'An error occured while sending your message.')
        lbl['state'] = DISABLED
    sockobj.close()
    state = False
    recievechat()

# def display():
#     try: win.title(share.get_nowait())
#     except queue.Empty: pass
#     else: lbl['text'] = share.get()
#     win.after(1000, display)

if __name__ == "__main__":
    win.title('PyChat - user: %s' % str(thisport))
    lbl = ScrolledText(win, relief=SUNKEN, state=DISABLED,
        bg='SystemButtonFace', borderwidth=2, wrap=WORD)
    txt = ScrolledText(win, wrap=WORD)
    frm = Frame(win)
    Button(frm, text='Chat!', command=chat).pack(side=RIGHT)
    port = Entry(frm)
    port.delete(0)
    port.insert(0, '1245')
    port.pack(side=RIGHT)
    host = Entry(frm)
    host.delete(0)
    host.insert(0, 'localhost')
    host.pack(side=RIGHT)
    lbl.pack(expand=YES, fill=BOTH)
    frm.pack(expand=YES, fill=X, side=BOTTOM)
    txt.pack(expand=YES, fill=BOTH)
    state = False
    recievechat()
    win.mainloop()