#!/usr/bin/python3 
from dirmanager   import DirManager
from os           import path,environ
from subprocess   import Popen,PIPE
from threading    import Thread
from queue        import Queue,Empty
from extremon     import CauldronReceiver,CauldronSender
import re,traceback,sys,signal,syslog

# ------------------------------------------------------------------------

class CauldronToPlugin(Thread):
  def __init__(self,name,cauldronAddr,plugin,inFilter,log,outFilter=None):
    Thread.__init__(self,name="%s (in)" % (name))
    self.daemon=True
    self.cauldronAddr=cauldronAddr
    self.plugin=plugin
    self.allowCache={}
    self.buffer=[]
    self.inFilter=re.compile(inFilter)
    self.log=log

    if outFilter:
      self.outFilter=re.compile(outFilter) 
    else:
      self.outFilter=None

  def run(self):
    self.running=True
    self.cauldron=CauldronReceiver(self.cauldronAddr,self)
    while self.running:
      self.cauldron.receive_shuttle()
    self.plugin.close()

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

    if len(self.buffer)>0:
      self.buffer.extend(['','']);
      try:
        self.plugin.write(bytes('\n'.join(self.buffer),'utf-8'))
      except IOError:
        self.running=False

  def stop(self):
    self.running=False

# ------------------------------------------------------------------------

class PluginToCauldron(Thread):
  def __init__(self,name,cauldronAddr,plugin,log,outFilter):
    Thread.__init__(self,name="%s (out)" % (name))
    self.daemon=True
    self.cauldronAddr=cauldronAddr
    self.plugin=plugin
    self.allowCache={}
    self.buffer=[]
    self.outFilterExpr=outFilter
    self.outFilter=re.compile(outFilter)
    self.log=log

  def run(self):
    self.running=True
    self.cauldron=CauldronSender(self.cauldronAddr)
    while self.running:
      data=self.plugin.readline(16384)
      if len(data)==0:
        self.log("%s: EOF From Plugin" % (self.name))
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
              else:
                self.log("%s: label [%s] does not match filter (%s)" %
                         (self.name,label,self.outFilterExpr),
                         syslog.LOG_WARNING)
          except ValueError:
            self.log("%s: Can't Parse [%s]" % (self.name,line))
    self.plugin.close()
  
  def stop(self):
    self.running=False

# ------------------------------------------------------------------------

class Plugin(Thread):
  def __init__(self,name,path,prefix,config,cauldronAddr,log):
    Thread.__init__(self,name='%s' % (name))
    self.deamon=True
    self.process=None
    self.c2p=None
    self.p2c=None
    self.running=False
    self.path=path
    self.prefix=prefix
    self.config=config
    self.log=log
    self.cauldronAddr=cauldronAddr
    self.isInput=(self.config.get('in.filter')!=None)
    self.isOutput=(self.config.get('out.filter')!=None)
    if self.isInput:
      if self.isOutput:
        self.log("%s: in(%s)/out(%s)" % (self.name,
                                      self.config.get('in.filter'),
                                      self.config.get('out.filter')))
      else:
        self.log("%s: in(%s)" % (self.name,self.config.get('in.filter')))
    else:
       self.log("%s: out(%s)" % (self.name,self.config.get('out.filter')))

  def run(self):
    self.log("%s: Starting.." % (self.name),priority=syslog.LOG_INFO)
    self.running=True
    try:
      self.process=Popen(['x3:%s' % (self.name)],
                          bufsize=0,
                          executable=self.path,
                          stdin=  PIPE if self.isInput else None,
                          stdout= PIPE if self.isOutput else None,
                          stderr= PIPE,
                          start_new_session=True)

      if 'in.filter' in self.config:
        self.c2p=CauldronToPlugin(self.name,self.cauldronAddr,
                                 self.process.stdin,
                                 inFilter=self.config.get('in.filter'),
                                 log=self.log,
                                 outFilter=self.config.get('out.filter'))
        self.c2p.start()

      if 'out.filter' in self.config:
        self.p2c=PluginToCauldron(self.name,self.cauldronAddr,
                                 self.process.stdout,
                                 log=self.log,
                                 outFilter=self.config.get('out.filter'))
        self.p2c.start()

      while self.running:
        data=self.process.stderr.read()
        if len(data)>0:
          lines=['%s reports:' % (self.name)]
          for error_line in str(data,'UTF-8').split('\n'):
            lines.append(" | %s" % (error_line))
          lines.append("")
          self.log(lines)
        else:
          self.log("%s: EOF On stderr" % (self.name))
          self.running=False
    except Exception as ex:
      self.running=False
      

  def stop(self):
    self.log("%s: Asked To Stop" % (self.name))
    self.running=False
    if self.p2c:
      self.p2c.stop()
    if self.c2p:
      self.c2p.stop()
    self.log("%s: Stopped" % (self.name),priority=syslog.LOG_INFO)

# ------------------------------------------------------------------------

class Coven(object):
  def __init__( self,path,prefix,cauldronAddr,
                ignore=[r'^\.',r'\.x?swp$',r'~',r'^__',r'__$']):
    syslog.openlog(ident="X3Coven",facility=syslog.LOG_DAEMON)
    self.path=path
    self.prefix=prefix
    self.cauldronAddr=cauldronAddr
    self.plugins={}
    self.logq=Queue()
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
    pluginPath=self.getOSPath(name)    
    if not self.isShebangExecutable(pluginPath):
      return None
    conf={}
    try:
      with open(pluginPath,'r') as plugin_file:
        for line in plugin_file:
          config_match=self.confRE.match(line)
          if config_match:
            conf[config_match.group(1)]=config_match.group(2)
    except:
      return None
    return conf
  
  def log(self,message,priority=syslog.LOG_DEBUG):
    self.logq.put((priority,message))

  def deQueueLogQueue(self,block=True):
    try:
      while True:
        (priority,message)=self.logq.get(block=block)
        if type(message)==str:
          syslog.syslog(priority,message)
        elif type(message)==list:
          for line in message:
            syslog.syslog(priority,line)
        self.logq.task_done()
    except Empty:
      pass

  def practice(self):
    try:
      self.dirManager.start()
      self.deQueueLogQueue(block=True)
    except KeyboardInterrupt:
      self.log("Coven stopping..")
      self.dirManager.stop()
      for partingPlugin in self.plugins.values():
        partingPlugin.stop()
      self.deQueueLogQueue(block=False) 
      self.log("Coven stopped..",priority=syslog.LOG_INFO)

# ------------------------------------------------------------------------

  def startPlugin(self,name):
    self.log("Starting [%s]" % (name)) 
    config=self.getConfig(name)
    if config:
      try:
        self.plugins[name]=Plugin(name, self.getOSPath(name),
                                 self.prefix, config, self.cauldronAddr,
                                 self.log)
        self.plugins[name].start()
        self.log("%s Started" % (name),priority=syslog.LOG_INFO)
      except:
        self.log("%s Failed To Start" % (name),priority=syslog.LOG_ERR)
    else:
      self.log("%s Is Not an X3 Plugin" % (name),
               priority=syslog.LOG_WARNING)

  def stopPlugin(self,name):
    self.log("Stopping [%s]" % (name))
    try:
      self.plugins[name].stop()
      del self.plugins[name]
      self.log("%s Stopped" % (name),priority=syslog.LOG_INFO) 
    except:
      self.log("%s Failed To Stop" % (name),priority=syslog.LOG_ERR) 

# ------------------------------------------------------------------------

  def process_FileCreated(self,name):
    self.startPlugin(name)

  def process_FileDeleted(self,name):
    self.stopPlugin(name)

  def process_FileChanged(self,name):
    self.log("Restarting [%s]" % (name),priority=syslog.LOG_INFO) 
    self.stopPlugin(name)
    self.startPlugin(name)
  
# ------------------------------------------------------------------------

if __name__=='__main__':
  signal.signal(signal.SIGCHLD, signal.SIG_IGN)
  environ['PYTHONPATH']=sys.path[0]
  coven=Coven('/opt/extremon/plugins','be.apsu',('224.0.0.1',1249))
  coven.practice()
