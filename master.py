#!/usr/bin/python3
import pyinotify,zmq,sys,re,traceback,time
from subprocess import Popen,PIPE
from threading import Thread
from queue import Queue,Empty

class Sub2Pipe(Thread):
    def __init__(self,context,sub_endpoint,pipe,in_filter,out_filter=None,name=None):
        Thread.__init__(self,name=name)
        self.daemon=True
        self.context=context
        self.sub_endpoint=sub_endpoint
        self.pipe=pipe
        self.allow_in_cache={}
        self.buffer=[]
        self.in_filter=re.compile(in_filter)

        if out_filter:
            self.out_filter=re.compile(out_filter) 
        else:
            self.out_filter=None

    def run(self):
        sub_socket=self.context.socket(zmq.SUB)
        sub_socket.connect(self.sub_endpoint)
        sub_socket.setsockopt_unicode(zmq.SUBSCRIBE,'')
        self.running=True
        while self.running:
            try:
                data=sub_socket.recv()
                if len(data):
                    del self.buffer[:]
                    for line in str(data,'UTF-8').split('\n'):
                        if len(line):
                            try:
                                (label,value)=line.split('=')
                                if label and value:
                                    try:
                                        allow_in=self.allow_in_cache[label]
                                    except KeyError:
                                        allow_in=((self.in_filter.match(label)!=None) and ((self.out_filter==None or not (self.out_filter.match(label)))))
                                        self.allow_in_cache[label]=allow_in
                                    if allow_in:
                                        self.buffer.append(line)
                            except ValueError:
                                print("failed to parse line [{0}]".format(line),file=sys.stderr)
                    
                    self.pipe.write(bytes('\n'.join(self.buffer),'utf-8'))
                    self.pipe.write(bytes('\n','utf-8'))
                else:
                    print("Input Plugin Ended")
                    self.running=False
            except Exception as ex:
                traceback.print_exc(file=sys.stderr)
                self.running=False


class QueuePusher(Thread):
    def __init__(self,context,prefix,push_endpoint,push_hwm=128,shuttle_size_threshold=32768,shuttle_age_threshold=.1,name=None):
        Thread.__init__(self,name=name)
        self.daemon=True
        self.context=context
        self.prefix=prefix
        self.push_endpoint=push_endpoint
        self.push_hwm=int(push_hwm)
        self.shuttle_size_threshold=int(shuttle_size_threshold)
        self.shuttle_age_threshold=float(shuttle_age_threshold)
        self.name=name
        self.outq=Queue()
        self.buffer=bytearray()
        self.clear_buffer(time.time())

    def clear_buffer(self,now):
        del self.buffer[:]
        self.buffer_expiry=now+self.shuttle_age_threshold

    def flush_buffer(self,now):
        self.buffer.extend(bytes('%s.%s.qsize=%d\n' % (self.prefix,self.name,self.outq.qsize()),'UTF-8'))
        self.push_socket.send(self.buffer)
        self.clear_buffer(now)

    def run(self):
        self.push_socket=self.context.socket(zmq.PUSH)
        self.push_socket.setsockopt(zmq.HWM,self.push_hwm)
        self.push_socket.connect(self.push_endpoint)
        self.running=True
        while self.running:
            try:
                self.buffer.extend(self.outq.get(timeout=self.shuttle_age_threshold))
            except Empty:
                pass
            now=time.time()
            if(now>=self.buffer_expiry):
                self.flush_buffer(now)
                continue
            if(len(self.buffer)>=self.shuttle_size_threshold):
                self.flush_buffer(now)
                continue

    def tx(self,data):
        self.outq.put(data)


class Pipe2Push(Thread):
    def __init__(self,context,prefix,pipe,push_endpoint,out_filter='.*',name=None):
        Thread.__init__(self,name=name)
        self.daemon=True
        self.context=context
        self.pipe=pipe
        self.push_endpoint=push_endpoint
        self.pusher=QueuePusher(context,prefix,push_endpoint,name=name)
        self.out_filter=re.compile(out_filter)
        self.allow_out_cache={}

    def run(self):
        self.pusher.start()
        self.running=True
        while self.running:
            data=self.pipe.readline(256)
            if len(data)==0:
                print("EOF from Plugin. Ending Pipe2Push Thread")
                self.running=False
            else:
                line=str(data,'utf-8')
                (label,value)=line.rstrip().split('=')
                if label and value:
                    try:
                        allow_out=self.allow_out_cache[label]
                    except KeyError:
                        allow_out=(self.out_filter.match(label)!=None)
                        self.allow_out_cache[label]=allow_out
                    if allow_out:
                        self.pusher.tx(bytes(line,'utf-8'))


class ContributorProcess(Thread):
    def __init__(self,path,context,prefix,config,cauldron_sub,cauldron_push):
        Thread.__init__(self,name='ContributorProcess %s' % (path))
        self.deamon=True
        self.path=path
        self.context=context
        self.prefix=prefix
        self.config=config
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

                if 'out.filter' in self.config:
                    stdout_to_cauldron=Pipe2Push(self.context,self.prefix,self.process.stdout,self.cauldron_push,out_filter=self.config.get('out.filter'),name='%s -> cauldron' % (self.path))
                    stdout_to_cauldron.start()

                if 'in.filter' in self.config:
                    cauldron_to_stdin=Sub2Pipe(self.context,self.cauldron_sub,self.process.stdin,in_filter=self.config.get('in.filter'),out_filter=self.config.get('out.filter'),name='cauldron -> %s' % (self.path))
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
                traceback.print_exc(file=sys.stderr)
                self.running=False

    def stop(self):
        print("stop called on %s" % (self.path))
        if self.running and self.process:
            print("stopping %s" % (self.path))
            self.process.terminate()
            self.running=False

class CauldronMaster(pyinotify.ProcessEvent):
    def __init__(self,plugin_dir,prefix):
        self.plugin_dir=plugin_dir
        self.prefix=prefix
        self.wm=pyinotify.WatchManager()
        self.notifier=pyinotify.Notifier(self.wm,self)
        self.watch=self.wm.add_watch(plugin_dir,pyinotify.IN_DELETE|pyinotify.IN_CLOSE_WRITE,rec=True)
        self.boiling={}
        self.context=zmq.Context()
        self.config_matcher=re.compile('^#\\s*x3\.([a-z0-9.]+)\\s*=\\s*(.*)\\s*$')

    def get_config(self,path):
        conf={}
        try:
            with open(path,'r') as plugin_file:
                magic_bytes=plugin_file.read(2)
                if magic_bytes=='#!':
                    plugin_file.seek(0)
                    for line in plugin_file:
                        config_match=self.config_matcher.match(line)
                        if config_match:
                            conf[config_match.group(1)]=config_match.group(2)
        except Exception as ex:
            traceback.print_exc(file=sys.stderr)
        return conf


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
        process=ContributorProcess(path,self.context,prefix=self.prefix,config=self.get_config(path),cauldron_sub='tcp://127.0.0.1:3000',cauldron_push='tcp://127.0.0.1:2000')
        self.boiling[path]=process
        process.start()
		
if __name__=='__main__':
    master=CauldronMaster('/home/frank','be.apsu')
    master.stir_forever()
