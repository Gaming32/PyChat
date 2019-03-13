from socket import socket, AF_INET, SOCK_STREAM
#import threading
from pickle import dumps, loads, dump, load
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
try: import PIL.Image, PIL.ImageTk
except ImportError: PIL = None
import mimetypes
import io
#from shelve import open as sopen
#chats = open('contacts')
win = Tk()
try: setdict = load(open('settings.pkl', 'rb'))
except FileNotFoundError: setdict = {}
try: thisport = setdict['port']
except KeyError: thisport = 0
thisport = (len(sys.argv) > 1 and int(sys.argv[1])) or thisport
share = queue.LifoQueue(2)

btnimg = []
def recievechat():
    global state, sockobj, thisport
    if state == False:
        sockobj = socket(AF_INET, SOCK_STREAM)
        sockobj.bind(('', thisport))
        thisport = sockobj.getsockname()[1]
        sockobj.listen(50)
        state = True
    while True:
        sockobj.setblocking(0)
        try: conn, addr = sockobj.accept()
        except BlockingIOError: break
        data = bytes()
        sockobj.setblocking(1)
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
            attbtn = Button(lbl, command=save, borderwidth=5)
            ftype = mimetypes.guess_type(data[1])
            if ftype[0] and not ftype[1] and ftype[0].startswith('image') and PIL:
                img = PIL.Image.open(io.BytesIO(gzip.decompress(data[2])))
                img.thumbnail((250, 250))
                global btnimg
                btnimg.append(PIL.ImageTk.PhotoImage(img))
                attbtn['image'] = btnimg[-1]
            else:
                attbtn['text'] = data[1]
            lbl.window_create(END, window=attbtn)
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
        txt.delete('1.0', END)
        print('sent    ', data[:1024])
    else:
        print('error sending')
        showerror('PyChat', 'An error occured while sending your message.')
    sockobj.close()
    state = False
    recievechat()

biglen = 15
def makeFormRow(parent, label, width=None, default='', browse=False, extend=False):
    global biglen
    if not width: width = biglen
    width = max(width, len(label))
    if width > biglen: biglen = width
    var = StringVar()
    var.set(default)
    row = Frame(parent)
    lab = Label(row, text=label, relief=RIDGE, width=width)
    ent = Entry(row, relief=SUNKEN, textvariable=var)
    row.pack(fill=X)                                  # uses packed row frames
    lab.pack(side=LEFT)                               # and fixed-width labels
    ent.pack(side=LEFT, expand=YES, fill=X)           # or use grid(row, col)
    if browse:
        btn = Button(row, text='browse...')
        btn.pack(side=RIGHT)
        if not extend:
            btn.config(command=
                 lambda: var.set(askopenfilename() or var.get()) )
        else:
            btn.config(command=
                 lambda: var.set(var.get() + ' ' + askopenfilename()) )
    return var
def options():
    global setdict
    try: setdict
    except NameError:
        try: setdict = load(open('settings.pkl', 'rb'))
        except FileNotFoundError: setdict = {}
    def onFrameConfigure(canvas):
        '''Reset the scroll region to encompass the inner frame'''
        canvas.configure(scrollregion=canvas.bbox(ALL))
    #def onCanvasConfigure(canvas):
    #    canvas.itemconfig(frmwin, width=canvas['width'])
    def save():
        global setdict
        nonlocal vardict
        setdict = {key: item[1](item[0].get()) for (key, item) in vardict.items()}
        dump(setdict, open('settings.pkl', 'wb'))
        optwin.destroy()
    optwin = Toplevel()
    optwin.title('PyChat Options')
    scrollfrm = Frame(optwin)
    canvas = Canvas(scrollfrm, borderwidth=0)
    frame = Frame(canvas)
    vsb = Scrollbar(scrollfrm, orient=VERTICAL, command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)
    vsb.pack(side=RIGHT, fill=Y)
    canvas.pack(side=LEFT, fill=BOTH, expand=True)
    frmwin = canvas.create_window((0, 0), window=frame, anchor=NW, width=canvas['width'])
    frame .bind("<Configure>", lambda event, canvas=canvas: onFrameConfigure(canvas))
    #canvas.bind("<Configure>", lambda event, canvas=canvas: onCanvasConfigure(canvas))
    scrollfrm.pack(side=TOP, expand=YES, fill=BOTH)
    vardict = dict(
        port = (makeFormRow(frame, 'Server Port', default=thisport), int)
    )
    enterfrm = Frame(frame)
    Button(enterfrm, text='Ok',     command=save)          .pack(side=RIGHT)
    Button(enterfrm, text='Cancel', command=optwin.destroy).pack(side=RIGHT)
    enterfrm.pack(side=TOP, expand=YES, fill=X)

# def display():
#     try: win.title(share.get_nowait())
#     except queue.Empty: pass
#     else: lbl['text'] = share.get()
#     win.after(1000, display)

if __name__ == "__main__":
    win.title('PyChat - user: %s' % str(thisport))
    lbl = ScrolledText(win, relief=SUNKEN, state=DISABLED,
        bg='SystemButtonFace', borderwidth=2, wrap=WORD)
    def entsend(event):
        if event.state == 8:
            txt.delete('end-1c')
            chat()
    win.bind('<Return>', entsend)
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
    filemenu.add_command(label='Clear',   command=clear)
    filemenu.add_command(label='Options', command=options)
    filemenu.add_separator()
    filemenu.add_command(label='Quit', command=win.quit)
    menu.add_cascade(menu=filemenu, label='File')
    win.config(menu=menu)
    state = False
    recievechat()
    win.mainloop()