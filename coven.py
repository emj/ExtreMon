#!/usr/bin/python3 -u
from time import sleep
from dirmanager import DirManager
from os import path
from subprocess import Popen,PIPE
from threading import Thread
import re,traceback,sys,signal
from extremon import CauldronReceiver,CauldronSender
import cProfile

# ------------------------------------------------------------------------

class CauldronToWitch(Thread):
  def __init__(self,cauldronAddr,witch,inFilter,outFilter=None):
    Thread.__init__(self)
    self.daemon=True
    self.cauldronAddr=cauldronAddr
    self.witch=witch
    self.allowCache={}
    self.buffer=[]
    self.inFilter=re.compile(inFilter)

    if outFilter:
      self.outFilter=re.compile(outFilter) 
    else:
      self.outFilter=None

  def run(self):
    self.running=True
    self.cauldron=CauldronReceiver(self.cauldronAddr,self)
    while self.running:
      self.cauldron.receive_shuttle()

  def handle_shuttle(self,shuttle):
    if not self.running:
      return
    self.buffer=[]
    for (label,value) in shuttle:
      try:
        allow=self.allowCache[label]
      except KeyError:
        allow= (( self.inFilter.search(label)!=None) and
               (( self.outFilter==None or not
                ( self.outFilter.search(label)))))
        self.allowCache[label]=allow
      if allow:
        self.buffer.append("%s=%s" % (label,value))

    try:
      self.witch.write(bytes('\n'.join(self.buffer),'utf-8'))
      self.witch.write(bytes('\n','utf-8'))
    except IOError:
      self.stop()

  def stop(self):
    self.running=False
    self.witch.close()

# ------------------------------------------------------------------------

class WitchToCauldron(Thread):
  def __init__(self,cauldronAddr,witch,outFilter):
    Thread.__init__(self)
    self.daemon=True
    self.cauldronAddr=cauldronAddr
    self.witch=witch
    self.allowCache={}
    self.buffer=[]
    self.outFilter=re.compile(outFilter)

  def run(self):
    self.running=True
    self.cauldron=CauldronSender(self.cauldronAddr)
    while self.running:
      data=self.witch.readline(256)
      if len(data)==0:
        print("EOF from Plugin. Ending WitchToCauldron Thread")
        self.running=False
      else:
        line=str(data,'utf-8')
        if len(line)>1:
          try:
            (label,value)=line.rstrip().split('=')
            if label and value:
              try:
                allow=self.allowCache[label]
              except KeyError:
                allow=(self.outFilter.search(label)!=None)
                self.allowCache[label]=allow
              if allow:
                self.cauldron.put(label,value)
          except ValueError:
            print("Can't Parse [%s]" % (line))
  
  def stop(self):
    self.running=False
    self.witch.close()

# ------------------------------------------------------------------------

class Witch(Thread):
  def __init__(self,name,path,prefix,config,cauldronAddr):
    Thread.__init__(self,name='%s' % (name))
    self.deamon=True
    self.process=None
    self.c2p=None
    self.p2c=None
    self.running=False
    self.name=name
    self.path=path
    self.prefix=prefix
    self.config=config
    self.cauldronAddr=cauldronAddr
    self.isInput=(self.config.get('in.filter')!=None)
    self.isOutput=(self.config.get('out.filter')!=None)

    if self.isInput:
      if self.isOutput:
        print("%s: in(%s)/out(%s)" % (self.name,
                                      self.config.get('in.filter'),
                                      self.config.get('out.filter')))
      else:
        print("%s: in(%s)" % (self.name,self.config.get('in.filter')))
    else:
       print("%s: out(%s)" % (self.name,self.config.get('out.filter')))

  def run(self):
    print("%s: Starting.." % (self.name))
    self.running=True
    try:
      self.process=Popen( self.path,
                          bufsize=0,
                          stdin=  PIPE if self.isInput else None,
                          stdout= PIPE if self.isOutput else None,
                          stderr= PIPE)

      print("%s Started" % (self.name))

      if 'in.filter' in self.config:
        self.c2p=CauldronToWitch(self.cauldronAddr,
                                 self.process.stdin,
                                 inFilter=self.config.get('in.filter'),
                                 outFilter=self.config.get('out.filter'))
        self.c2p.start()

      if 'out.filter' in self.config:
        self.p2c=WitchToCauldron(self.cauldronAddr,
                                 self.process.stdout,
                                 outFilter=self.config.get('out.filter'))
        self.p2c.start()

      while self.running:
        data=self.process.stderr.read()
        if len(data)>0:
          for error_line in str(data,'UTF-8').split('\n'):
            print("%s: %s" % (self.name,error_line))
          sys.stderr.flush()
        else:
          print("%s: Saw EOF On STDERR" % (self.name))
          self.running=False
    except Exception as ex:
      traceback.print_exc()
      self.running=False

  def stop(self):
    print("%s: Asked To Stop" % (self.name))
    self.running=False
    if self.p2c:
      self.p2c.stop()
    if self.c2p:
      self.c2p.stop()

# ------------------------------------------------------------------------

class Coven(object):
  def __init__( self,path,prefix,cauldronAddr,
                ignore=[r'^\.',r'\.x?swp$',r'~']):
    self.path=path
    self.prefix=prefix
    self.cauldronAddr=cauldronAddr
    self.witches={}
    self.confRE=re.compile('^#\\s*x3\.([a-z0-9.]+)\\s*=\\s*(.*)\\s*$')
    self.dirManager=DirManager(self.path,self,ignore=ignore)
    self.cauldron=CauldronSender(self.cauldronAddr)

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
          config_match=self.confRE.match(line)
          if config_match:
            conf[config_match.group(1)]=config_match.group(2)
    except Exception as ex:
      traceback.print_exc()
      return None
    return conf

  def practice(self):
    try:
      self.dirManager.start()
      while True:
        sleep(1)
    except KeyboardInterrupt:
      print("Coven stopping..")
      self.dirManager.stop()
      for partingWitch in self.witches.values():
        partingWitch.stop()
      

# ------------------------------------------------------------------------

  def process_FileCreated(self,name):
    print("%s arrives" % (name)) 
    config=self.getConfig(name)
    if config:
      self.witches[name]=Witch( name,
                                self.getOSPath(name),
                                self.prefix,
                                config,
                                self.cauldronAddr)
      self.witches[name].start()

  def process_FileDeleted(self,name):
    print("%s leaves" % (name)) 
    try:
      self.witches[name].stop()
      del self.witches[name]
    except KeyError:
      pass

  def process_FileChanged(self,name):
    self.process_FileDeleted(name)
    self.process_FileCreated(name)
  
# ------------------------------------------------------------------------

if __name__=='__main__':
  signal.signal(signal.SIGCHLD, signal.SIG_IGN)
  coven=Coven('/opt/extremon/plugins','be.apsu',('224.0.0.1',1249))
  coven.practice()
