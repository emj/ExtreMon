#!/usr/bin/python3
import pyinotify,zmq,select,sys
from subprocess import Popen,PIPE
from threading import Thread


class CauldronToPipe(Thread):
    def __init__(self,context,cauldron,pipe,name=None):
        Thread.__init__(self,name=name)
        self.daemon=True
        self.context=context
        self.cauldron=cauldron
        self.pipe=pipe

    def run(self):
        sub_socket=self.context.socket(zmq.SUB)
        sub_socket.connect(self.cauldron)
        sub_socket.setsockopt_unicode(zmq.SUBSCRIBE,'')
        self.running=True
        while self.running:
            try:
                data=sub_socket.recv()
                if len(data):
                    sys.stdout.write('W')
                    sys.stdout.flush()
                    self.pipe.write(data)
                    self.pipe.write(bytes('\n','utf-8'))
                else:
                    print("EOF ON SUB SOCKET")
                    self.running=False
            except Exception as ex:
                print(ex,ex.__traceback__)
                self.running=False

class PipeToCauldron(Thread):
    def __init__(self,context,pipe,cauldron,name=None):
        Thread.__init__(self,name=name)
        self.daemon=True
        self.context=context
        self.pipe=pipe
        self.cauldron=cauldron

    def run(self):
        accu=[]
        push_socket=self.context.socket(zmq.PUSH)
        push_socket.setsockopt(zmq.HWM,128)
        push_socket.connect(self.cauldron)
        self.running=True
        while self.running:
            line=self.pipe.readline(128)
            if len(line)==1:
                sys.stdout.write('R')
                sys.stdout.flush()
                accu.append('\n')
                push_socket.send(bytes(''.join(accu),'utf-8'))
                accu=[]
            elif len(line)==0:
                print("EOF ON PUSH SOCKET")
                self.running=False
            else:
                accu.append(str(line,'utf-8'))



class ContributorProcess(Thread):
    def __init__(self,path,context,cauldron_sub,cauldron_push):
        Thread.__init__(self,name='ContributorProcess %s' % (path))
        self.deamon=True
        self.path=path
        self.context=context
        self.cauldron_sub=cauldron_sub
        self.cauldron_push=cauldron_push
        self.running=False
        print("created %s" % (self.path))

    def run(self):
        print("starting %s" % (self.path))
        self.running=True
        while self.running:
            try:
                self.process=Popen(self.path,stdin=PIPE,stdout=PIPE,stderr=PIPE)
                print("process %s running" % (self.path))
                cauldron_to_stdin=CauldronToPipe(self.context,self.cauldron_sub,  self.process.stdin,name='cauldron -> %s' % (self.path))
                stdout_to_cauldron=PipeToCauldron(self.context,self.process.stdout,self.cauldron_push,name='%s -> cauldron' % (self.path))
                stdout_to_cauldron.start()
                cauldron_to_stdin.start()
                while self.running:
                    data=self.process.stderr.read()
                    if len(data)>0:
                        for error_line in str(data,'UTF-8').split('\n'):
                            print("%s: %s" % (self.path,error_line))
                    else:
                        print("EOF ON STDERR")
                        self.running=False
            except Exception as ex:
                print(ex,ex.__traceback__)
                self.running=False

    def stop(self):
        print("stop called on %s" % (self.path))
        if self.running and self.process:
            print("stopping %s" % (self.path))
            self.process.terminate()
            self.running=False

class CauldronMaster(pyinotify.ProcessEvent):
    def __init__(self,plugin_dir):
        self.plugin_dir=plugin_dir
        self.wm=pyinotify.WatchManager()
        self.notifier=pyinotify.Notifier(self.wm,self)
        self.watch=self.wm.add_watch(plugin_dir,pyinotify.IN_DELETE|pyinotify.IN_CLOSE_WRITE,rec=True)
        self.boiling={}
        self.context=zmq.Context()

    def stir_forever(self):
        self.notifier.loop()

    def process_IN_DELETE(self, event):
        print("Removing:", event.pathname)
#       self.stopProcess(event.pathname)

    def process_IN_CLOSE_WRITE(self, event):
        print("Edited:", event.pathname)
        self.stopProcess(event.pathname)
        self.startProcess(event.pathname)

    def stopProcess(self,path):
        try:
            process=self.boiling[path]
            process.stop()
        except KeyError:
            pass
		
    def startProcess(self,path):
        process=ContributorProcess(path,self.context,'tcp://127.0.0.1:3000','tcp://127.0.0.1:2000')
        self.boiling[path]=process
        process.start()
		
if __name__=='__main__':
    master=CauldronMaster('/home/frank')
    master.stir_forever()
