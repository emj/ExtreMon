#!/usr/bin/python3
from os import listdir,path
from time import sleep
import pyinotify, hashlib,re

""" PrintingDirWatcher is a way to observe how a DirManager works,
    and an example on how to write a DirWatcher """

class PrintingDirWatcher(object):
    def __init__(self):
        self.current=set()

    def printcurrent(self):
        for name in self.current:
            print("[%s]" % (name),end=" ")
        print()

    def process_FileCreated(self,name):
        print("%s created" % (name)) 
        self.current.add(name)
        self.printcurrent()

    def process_FileChanged(self,name):
        print("%s changed" % (name)) 

    def process_FileDeleted(self,name):
        print("%s deleted" % (name)) 
        self.current.remove(name)
        self.printcurrent()


""" DirManager takes a path in the filesystem and a DirWatcher,
    uses PyIntotify to capture events on that path, and calls
    the DirWatcher with a somewhat higher-level interface.
    Note that while starting up, files already present will 
    cause "Created" notifications, for consistency """

class DirManager(pyinotify.ProcessEvent):
    def __init__(self,path,watcher,ignore=None):
        self.path=path
        self.wm=pyinotify.WatchManager()
        self.notifier=pyinotify.ThreadedNotifier(self.wm,self)
        self.watcher=watcher
        self.files={}

        self.ignore=[]
        if ignore:
            for regex in ignore:
                self.ignore.append(re.compile(regex, re.UNICODE)) 

        self.watch=self.wm.add_watch(   path,
                                        pyinotify.IN_DELETE|
                                        pyinotify.IN_CLOSE_WRITE|
                                        pyinotify.IN_MOVED_FROM|
                                        pyinotify.IN_MOVED_TO,
                                        rec=True)

        for existing in listdir(path):
            if not self.isIgnored(existing):
                self.addFile(existing)

    def start(self):
        self.notifier.start()

    def stop(self):
        self.notifier.stop()

# ----------------------------------------------------------

    def addFile(self,name):
        self.files[name]=self.md5(name)
        self.watcher.process_FileCreated(name)

    def removeFile(self,name):
        try:
            del self.files[name]
            self.watcher.process_FileDeleted(name)
        except KeyError:
            pass

# ----------------------------------------------------------

    def isIgnored(self,name):
        if not self.ignore:
            return False
        for ignore in self.ignore:
            if ignore.search(name):
                return True
        return False

# ------- called by Notifier -------------------------------

    def process_IN_DELETE(self, event):
        if self.isIgnored(event.name):
            return
        self.removeFile(event.name)

    def process_IN_CLOSE_WRITE(self,event):
        if self.isIgnored(event.name):
            return
        if event.name in self.files:
            newmd5=self.md5(event.name)
            if newmd5!=self.files[event.name]:
                self.watcher.process_FileChanged(event.name)
                self.files[event.name]=newmd5
        else:
            self.addFile(event.name)

    def process_IN_MOVED_FROM(self, event):
        if self.isIgnored(event.name):
            return
        self.removeFile(event.name)

    def process_IN_MOVED_TO(self, event):
        if self.isIgnored(event.name):
            return
        self.addFile(event.name)

# -------------------------------------------------------------

    def md5(self,name):
        try:
            md5=hashlib.md5()
            with open(path.join(self.path,name),"rb") as theFile:
                while True:
                    data=theFile.read(8192)
                    if data:
                        md5.update(data)
                    else:
                        break
            return md5.digest()
        except IOError:
            return None

# -------------------------------------------------------------

if __name__=='__main__':
    master=DirManager('/opt/extremon/plugins',PrintingDirWatcher(),ignore=[r'^\.',r'\.x?swp$',r'~'])
    master.start()
    sleep(30)
    master.stop()

