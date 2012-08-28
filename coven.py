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
    self.accu=set()
    self.inFilter=re.compile(inFilter)
    self.log=log

    if outFilter:
      self.outFilter=re.compile(outFilter) 
    else:
      self.outFilter=None
  
  def run(self):
    self.running=True
    self.log("running")
    self.cauldron=CauldronReceiver(self.cauldronAddr,self)
    while self.running:
      self.cauldron.receive_shuttle()
    self.plugin.close()

  def handle_shuttle(self,shuttle):
    if not self.running:
      return
    for (label,value) in shuttle:
      try:
        allow=self.allowCache[label]
      except KeyError:
        allow= (( self.inFilter.search(label)!=None) and
               (( self.outFilter==None or not
                ( self.outFilter.search(label)))))
        self.allowCache[label]=allow
      if allow:
        self.accu.add("%s=%s" % (label,value))

    if len(self.accu)>0:
      try:
        self.plugin.write(bytes('%s\n' %
                          ('\n\n'.join(self.accu)),'utf-8'))
        self.accu.clear()
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
    self.log("running")
    self.cauldron=CauldronSender(self.cauldronAddr)
    for recordBytes in self.plugin:
      if len(recordBytes)>1:
        try:
          record=str(recordBytes,'UTF-8')
          (label,value)=record.rstrip().split('=')
          try:
            allow=self.allowCache[label]
          except KeyError:
            allow=(self.outFilter.search(label)!=None)
            self.allowCache[label]=allow
          if allow:
            self.cauldron.put(label,value)
          else:
            self.log("Label [%s] does not match filter (%s)" %
                     (label,self.outFilterExpr),
                      syslog.LOG_WARNING)
        except ValueError:
          self.log("Can't Parse [%s] [%s]" % (
              str(recordBytes,'utf-8').rstrip(),
              ''.join(['%02x' % (thebyte) for thebyte in recordBytes])))

     
  def stop(self):
    pass

# ------------------------------------------------------------------------

class Plugin(Thread):
  def __init__(self,name,path,prefix,config,cauldronAddr,log):
    Thread.__init__(self,name=name)
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
        self.in_log(self.config.get('in.filter'))
        self.out_log(self.config.get('out.filter'))
      else:
        self.in_log(self.config.get('in.filter'))
    else:
      self.out_log(self.config.get('out.filter'))

  def run(self):
    self.log("starting..",priority=syslog.LOG_INFO,component=self.name)
    self.running=True
    newEnvironment=dict(environ)
    for (label,value) in self.config.items():
      newEnvironment["X3MON_%s" % (label.upper().replace('.','_'))]=value

    self.process=Popen(['x3:%s' % (self.name)],
                        bufsize=1,
                        executable=self.path,
                        cwd=path.dirname(self.path),
                        stdin=  PIPE if self.isInput else None,
                        stdout= PIPE if self.isOutput else None,
                        stderr= PIPE,
                        env=newEnvironment,
                        start_new_session=True)

    ''' if input plugin, connect C2P thread to handle stdin '''    
    if 'in.filter' in self.config:
      self.c2p=CauldronToPlugin(self.name,self.cauldronAddr,
                               self.process.stdin,
                               inFilter=self.config.get('in.filter'),
                               log=self.in_log,
                               outFilter=self.config.get('out.filter'))
      self.c2p.start()

    ''' if output plugin, connect P2C thread to handle stdout '''
    if 'out.filter' in self.config:
      self.p2c=PluginToCauldron(self.name,self.cauldronAddr,
                               self.process.stdout,
                               log=self.out_log,
                               outFilter=self.config.get('out.filter'))
    self.p2c.start()

    ''' in this thread, read stderr, and log output '''
    for line in self.process.stderr:
      self.log(str(line.rstrip(),'utf-8'),component=self.name)
    self.log("EOF on stderr",component=self.name)

    # reaching here implies self.process.stderr is EOF
    # this ends run()

  def in_log(self,message,priority=syslog.LOG_INFO):
    self.log( '[in] %s' % (message),
              priority=priority,
              component=self.name)

  def out_log(self,message,priority=syslog.LOG_INFO):
    self.log( '[out] %s' % (message),
              priority=priority,
              component=self.name)

  def stop(self):
    self.log("Asked To Stop",component=self.name)
    if self.p2c:
      self.p2c.stop()
    if self.c2p:
      self.c2p.stop()
    self.log("Stopped",component=self.name,priority=syslog.LOG_INFO)

# ------------------------------------------------------------------------

class Coven(object):
  def __init__( self,path,prefix,cauldronAddr,
                ignore=[r'^\.',r'\.x?swp$',r'~',r'^__',r'__$',r'\.jar$']):
    syslog.openlog(ident="X3Coven",facility=syslog.LOG_DAEMON)
    self.path=path
    self.prefix=prefix
    self.cauldronAddr=cauldronAddr
    self.plugins={}
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
  
  def log(self,message,component=None,priority=syslog.LOG_DEBUG):
    syslog.syslog(priority,message if component==None 
                                else '[%s] %s' % (component,message))
  def practice(self):
    try:
      self.dirManager.start()
    except KeyboardInterrupt:
      self.log("Stopping..")
      self.dirManager.stop()
      for partingPlugin in self.plugins.values():
        partingPlugin.stop()
      self.log("Stopped..",priority=syslog.LOG_INFO)

# ------------------------------------------------------------------------

  def startPlugin(self,name):
    self.log("Starting %s" % (name)) 
    config=self.getConfig(name)
    if config:
      try:
        self.plugins[name]=Plugin(name, self.getOSPath(name),
                                 self.prefix, config, self.cauldronAddr,
                                 self.log)
        self.plugins[name].start()
        self.log("Started %s" % (name),priority=syslog.LOG_INFO)
      except:
        self.log("Failed To Start %s" % (name),priority=syslog.LOG_ERR)
    else:
      self.log("Not an X3 Plugin: %s" % (name),
               priority=syslog.LOG_WARNING)

  def stopPlugin(self,name):
    self.log("Stopping %s" % (name))
    try:
      self.plugins[name].stop()
      del self.plugins[name]
      self.log("Stopped %s" % (name),priority=syslog.LOG_INFO) 
    except:
      self.log("Failed To Stop %s" % (name),priority=syslog.LOG_ERR) 

# ------------------------------------------------------------------------

  def process_FileCreated(self,name):
    self.startPlugin(name)

  def process_FileDeleted(self,name):
    self.stopPlugin(name)

  def process_FileChanged(self,name):
    self.log("Restarting %s" % (name),priority=syslog.LOG_INFO) 
    self.stopPlugin(name)
    self.startPlugin(name)
  
# ------------------------------------------------------------------------

if __name__=='__main__':
  signal.signal(signal.SIGCHLD, signal.SIG_IGN)
  environ['PYTHONPATH']=sys.path[0]
  coven=Coven('/opt/extremon/plugins','be.apsu',('224.0.0.1',1249))
  coven.practice()
