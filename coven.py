#!/usr/bin/python3 -u
from time import sleep
from dirmanager import DirManager
from os import path
from subprocess import Popen,PIPE
from threading import Thread
import re,traceback,sys,signal
from extremon import CauldronReceiver,CauldronSender
import cProfile
# --------------------------------------------------------------------------------------

class CauldronToWitch(Thread):
    def __init__(self,cauldron_addr,witch,in_filter,out_filter=None):
        Thread.__init__(self)
        self.daemon=True
        self.cauldron_addr=cauldron_addr
        self.witch=witch
        self.allow_in_cache={}
        self.buffer=[]
        self.in_filter=re.compile(in_filter)

        if out_filter:
            self.out_filter=re.compile(out_filter) 
        else:
            self.out_filter=None

    def run(self):
        self.running=True
        self.cauldron=CauldronReceiver(self.cauldron_addr,self)
        while self.running:
            self.cauldron.receive_shuttle()

    def handle_shuttle(self,shuttle):
        self.buffer=[]
        for record in shuttle:
            label=record[0]
            value=record[1]
            try:
                allow_in=self.allow_in_cache[label]
            except KeyError:
                allow_in=((self.in_filter.search(label)!=None) and ((self.out_filter==None or not (self.out_filter.search(label)))))
                self.allow_in_cache[label]=allow_in
            if allow_in:
                self.buffer.append("%s=%s" % (label,value))

        try:
            self.witch.write(bytes('\n'.join(self.buffer),'utf-8'))
            self.witch.write(bytes('\n','utf-8'))
        except IOError:
            self.stop()

    def stop(self):
        self.running=False

# --------------------------------------------------------------------------------------

class WitchToCauldron(Thread):
    def __init__(self,cauldron_addr,witch,out_filter):
        Thread.__init__(self)
        self.daemon=True
        self.cauldron_addr=cauldron_addr
        self.witch=witch
        self.allow_out_cache={}
        self.buffer=[]
        self.out_filter=re.compile(out_filter)

    def run(self):
        self.running=True
        self.cauldron=CauldronSender(self.cauldron_addr)
        while self.running:
            data=self.witch.readline(256)
            if len(data)==0:
                print("EOF from Plugin. Ending Pipe2Push Thread")
                self.running=False
            else:
                line=str(data,'utf-8')
                if len(line)>1:
                    try:
                        (label,value)=line.rstrip().split('=')
                        if label and value:
                            try:
                                allow_out=self.allow_out_cache[label]
                            except KeyError:
                                allow_out=(self.out_filter.search(label)!=None)
                                self.allow_out_cache[label]=allow_out
                            if allow_out:
                                self.cauldron.put(label,value)
                    except ValueError:
                        print("Can't Parse [%s]" % (line))
    
    def stop(self):
        self.running=False

class Witch(Thread):
    def __init__(self,path,prefix,config,cauldron_addr):
        Thread.__init__(self,name='Witch %s' % (path))
        self.deamon=True
        self.process=None
        self.c2p=None
        self.p2c=None
        self.running=False
        self.path=path
        self.prefix=prefix
        self.config=config
        self.cauldron_addr=cauldron_addr
        self.isInput=(self.config.get('in.filter')!=None)
        self.isOutput=(self.config.get('out.filter')!=None)
        print("Witch %s created, in=%s out=%s" % (self.path,self.isInput,self.isOutput))

    def run(self):
        print("Witch starting %s" % (self.path))
        self.running=True
        try:
            self.process=Popen(self.path,bufsize=0,stdin=(PIPE if self.isInput else None),stdout=(PIPE if self.isOutput else None),stderr=PIPE,)
            print("Witch %s casting" % (self.path))

            if 'in.filter' in self.config:
                self.c2p=CauldronToWitch(self.cauldron_addr,self.process.stdin,in_filter=self.config.get('in.filter'),out_filter=self.config.get('out.filter'))
                self.c2p.start()

            if 'out.filter' in self.config:
                self.p2c=WitchToCauldron(self.cauldron_addr,self.process.stdout,out_filter=self.config.get('out.filter'))
                self.p2c.start()

            while self.running:
                data=self.process.stderr.read()
                if len(data)>0:
                    for error_line in str(data,'UTF-8').split('\n'):
                        print("%s: %s" % (self.path,error_line),file=sys.stderr)
                    sys.stderr.flush()
                else:
                    print("EOF on stderr",file=sys.stderr)
                    self.stop()
        except Exception as ex:
            traceback.print_exc(file=sys.stderr)
            self.stop()

    def stop(self):
        print("stop called on %s" % (self.path))
        if self.p2c:
            self.p2c.stop()
        if self.c2p:
            self.c2p.stop()
        if self.running and self.process!=None:
            print("stopping %s" % (self.path))
            self.process.terminate()
        self.running=False

class Coven(object):
    def __init__(self,path,prefix,cauldron_addr,ignore=[r'^\.',r'\.x?swp$',r'~']):
        self.path=path
        self.prefix=prefix
        self.cauldron_addr=cauldron_addr
        self.witches={}
        self.config_matcher=re.compile('^#\\s*x3\.([a-z0-9.]+)\\s*=\\s*(.*)\\s*$')
        self.dirmanager=DirManager(self.path,self,ignore=ignore)

# --------------------------------------------------------------------------------------

    def getOSPath(self,name):
        return path.join(self.path,name)

    def isShebangExecutable(self,path):
        try:
            with open(path,'rb') as plugin_file:
                magic_bytes=plugin_file.read(2)
                if magic_bytes==b'#!':
                    return True
        except:
            pass
        return False

    def getConfig(self,name):
        witchPath=self.getOSPath(name)      
        if not self.isShebangExecutable(witchPath):
            return None
        conf={}
        try:
            with open(witchPath,'r') as plugin_file:
                for line in plugin_file:
                    config_match=self.config_matcher.match(line)
                    if config_match:
                        conf[config_match.group(1)]=config_match.group(2)
        except Exception as ex:
            traceback.print_exc(file=sys.stderr)
            return None
        return conf

# --------------------------------------------------------------------------------------

    def start(self):
        self.dirmanager.start()

    def stop(self):
        self.dirmanager.stop()

# --------------------------------------------------------------------------------------

    def process_FileCreated(self,name):
        print("%s arrives" % (name)) 
        config=self.getConfig(name)
        if config:
            print(config,file=sys.stderr)
            self.witches[name]=Witch(self.getOSPath(name),self.prefix,config,self.cauldron_addr)
            self.witches[name].start()

    def process_FileDeleted(self,name):
        print("%s leaves" % (name)) 
        try:
            self.witches[name].stop()
        except KeyError:
            pass

    def process_FileChanged(self,name):
        self.process_FileDeleted(name)
        self.process_FileCreated(name)
		
# --------------------------------------------------------------------------------------

def foo():
    signal.signal(signal.SIGCHLD, signal.SIG_IGN)
    coven=Coven('/opt/extremon/plugins','be.apsu',('224.0.0.1',1249))
    coven.start()
    sleep(30)
    coven.stop()

# --------------------------------------------------------------------------------------

if __name__=='__main__':
    cProfile.run('foo()','coven_profile')
