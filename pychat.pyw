from socket import socket, AF_INET, SOCK_STREAM
#import threading
from pickle import dumps, loads
import sys
from argparse import ArgumentParser
import queue
from tkinter import *
from tkinter.scrolledtext import ScrolledText
from tkinter.filedialog   import askopenfilename, asksaveasfile
from tkinter.messagebox   import showerror
import time
from time import sleep
import gzip
import os
try: import win10toast
except ImportError: win10toast = None
else: win10toast = win10toast.ToastNotifier()
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
            data += recv
        print('recieved', data[:1024])
        port, *data = loads(data)
        win.title('PyChat - user: %s - message from: %s' % (thisport, (addr[0], port)))
        #if win10toast: win10toast.show_toast('PyChat', data[0].split('\n')[0])
        lbl['state'] = NORMAL
        lbl.window_create(END, window=
            Label(lbl, text="message recieved\nfrom %s\nat %s"
            % ((addr[0], port), time.strftime('%I:%M %p')),
            relief=SUNKEN, borderwidth=5))
        lbl.insert(END, '\n')
        if len(data) > 2:
            def save():
                ungz = gzip.decompress(data[2])
                fi = asksaveasfile('wb', initialfile=data[1])
                if fi: fi.write(ungz)
            lbl.window_create(END, window=
                Button(lbl, text=data[1], command=save, borderwidth=5))
            lbl.insert(END, '\n')
        lbl.insert(END, data[0])
        lbl.insert(END, '\n\n\n')
        lbl.see(END)
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
        data = [thisport, txt.get('1.0','end-1c')]
        value = attached.get()
        if value:
            size = os.path.getsize(value)
            print('attachment size =', size)
            if size < 100000000:
                data += [os.path.split(value)[1]]
                try:
                    fi = open(value, 'rb').read()
                    data += [gzip.compress(fi)]
                    attached.set('')
                except:
                    showerror('PyChat', '%s occured while attaching your attachment.\n(The message was:\n%s\n)' % sys.exc_info()[:2])
            else:
                showerror('PyChat', "Sorry file %s's size is greater than 100MB (it's size is %sMB)"
                    % (os.path.split(value)[1], size // 1000000))
        data = dumps(data)
        sockobj.send(data)
        print('sent    ', data[:1024])
    else:
        print('error sending')
        showerror('PyChat', 'An error occured while sending your message.')
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
    attached = StringVar()
    attachlbl = Label(frm, textvariable=attached)
    attachlbl.pack(side=LEFT)
    def attach():
        toattach = askopenfilename()
        currattach = attached.get()
        attached.set(toattach or currattach)
    Button(frm, text='Attach', command=attach).pack(side=LEFT)
    Button(frm, text='Remove Attachment', command=(lambda: attached.set(''))).pack(side=LEFT)
    lbl.pack(expand=YES, fill=BOTH)
    frm.pack(expand=YES, fill=X, side=BOTTOM)
    txt.pack(expand=YES, fill=BOTH)
    menu = Menu(win)
    filemenu = Menu(menu)
    def clear():
        lbl['state'] = NORMAL
        lbl.delete('1.0', 'end-1c')
        lbl['state'] = DISABLED
    filemenu.add_command(label='Clear', command=clear)
    menu.add_cascade(menu=filemenu, label='File')
    win.config(menu=menu)
    state = False
    recievechat()
    win.mainloop()