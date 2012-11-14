#!/usr/bin/python3 

#   ExtreMon Project
#   Copyright (C) 2009-2012 Frank Marien
#   frank@apsu.be
#
#   This file is part of ExtreMon.
#
#   ExtreMon is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   ExtreMon is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with ExtreMon.  If not, see <http://www.gnu.org/licenses/>.
#

from dirmanager   import DirManager
from os           import path,environ
from subprocess   import Popen,PIPE
from threading    import Thread,Lock
from queue        import Queue,Empty
from extremon     import CauldronReceiver,CauldronSender
import re,traceback,sys,signal,syslog,time

# ----------------------------------------------------------------------

class Countable(object):
  def __init__(self):
    self.labels_allowed=0
    self.counters={}

  def reset_counters(self):
    for label in self.counters.keys():
      self.counters[label]=0

  def get_counters(self):
    self.counters['labels_allowed']=self.labels_allowed
    return self.counters

  def count(self,label,increment):
    try:
      self.counters[label]+=increment
    except KeyError:
      self.counters[label]=increment

class CauldronToPlugin(Thread,Countable):
  def __init__(self,name,cauldronAddr,plugin,log,
                inFilter,inValueFilter=None,
                outFilter=None,outValueFilter=None,
                loopProtected=False):

    Thread.__init__(self,name="%s (in)" % (name))
    Countable.__init__(self)
    self.daemon=True
    self.cauldronAddr=cauldronAddr
    self.plugin=plugin
    self.allowCache={}
    self.accu=set()
    self.inFilter=re.compile(inFilter)
    self.log=log
    self.loopProtected=loopProtected

    if outFilter:
      self.outFilter=re.compile(outFilter) 
    else:
      self.outFilter=None

    if inValueFilter:
      self.inValueFilter=re.compile(inValueFilter)
    else:
      self.inValueFilter=None

    if outValueFilter:
      self.outValueFilter=re.compile(outValueFilter)
    else:
      self.outValueFilter=None
  
  def run(self):
    self.running=True
    self.log("running")
    self.cauldron=CauldronReceiver(self.cauldronAddr,self)
    while self.running:
      self.cauldron.receive_shuttle()

  def handle_shuttle(self,shuttle):
    if not self.running:
      return
    for (label,value) in shuttle:
      try:
        allow=self.allowCache[label]
      except KeyError:
        self.count('new_labels_per_second',1)

        if self.loopProtected:
          allowLabel=self.inFilter.search(label)!=None 
        else:
          allowLabel=((( self.inFilter.search(label)!=None) and (((self.outFilter==None or not ( self.outFilter.search(label)!=None)))))) 

        if self.inValueFilter==None:
          allowValueIn=True
        else:
          allowValueIn=self.inValueFilter.match(value)!=None

        if self.outValueFilter==None:
          allowValueOut=True
        else:
          allowValueOut=self.outValueFilter.match(value)!=None

        allow=allowLabel and allowValueIn and allowValueOut
        self.allowCache[label]=allow
        if allow:
          self.labels_allowed+=1
      if allow:
        self.accu.add("%s=%s" % (label,value))

    if len(self.accu)>0:
      try:
        databytes=(bytes('%s\n\n' % ('\n'.join(self.accu)),'utf-8'))
        self.plugin.write(databytes)
        self.count('bytes_per_second',len(databytes))
        self.count('shuttles_per_second',1)
        self.count('records_per_second',len(self.accu))
        self.accu.clear()
      except IOError:
        self.running=False

  def stop(self):
    self.running=False


# ----------------------------------------------------------------------

class PluginToCauldron(Thread,Countable):
  def __init__(self,name,cauldronAddr,plugin,log,
               outFilter,outValueFilter=None):

    Thread.__init__(self,name="%s (out)" % (name))
    Countable.__init__(self)
    self.daemon=True
    self.cauldronAddr=cauldronAddr
    self.plugin=plugin
    self.allowCache={}
    self.buffer=[]
    self.outFilterExpr=outFilter
    self.outFilter=re.compile(outFilter)
    self.log=log

    if outValueFilter!=None:
      self.outValueFilter=re.compile(outValueFilter)
    else:
      self.outValueFilter=None

  def run(self):
    self.running=True
    self.log("running")
    self.cauldron=CauldronSender(self.cauldronAddr,max_shuttle_size=512,max_shuttle_age=.2)
    for recordBytes in self.plugin:
      if not self.running:
        return
      if len(recordBytes)>1:
        try:
          record=str(recordBytes,'UTF-8')
          (label,value)=record.rstrip().split('=')
          try:
            allow=self.allowCache[label]
          except KeyError:
            self.count('new_labels_per_second',1)
            allow=(self.outFilter.search(label)!=None)
            self.allowCache[label]=allow
            self.labels_allowed+=1
          if allow:
            self.cauldron.put(label,value)
            self.count('records_per_second',1)
            self.count('bytes_per_second',len(recordBytes))
          else:
            self.log("Label [%s] does not match filter (%s)" %
                     (label,self.outFilterExpr),
                      syslog.LOG_WARNING)
        except ValueError:
          self.log("Can't Parse [%s] [%s]" % (
              str(recordBytes,'utf-8').rstrip(),
              ''.join(['%02x' % (thebyte) for thebyte in recordBytes])))
      else:
        self.count('shuttles_per_second',1)

  def stop(self):
    self.running=False

# ----------------------------------------------------------------------

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
    self.counters={'in':{},'out':{}}

    if self.isInput:
      if self.isOutput:
        self.in_log(self.config.get('in.filter'))
        self.out_log(self.config.get('out.filter'))
      else:
        self.in_log(self.config.get('in.filter'))
    else:
      self.out_log(self.config.get('out.filter'))

    if self.config.get('loop.protected')!=None:
      self.loopProtected=(self.config.get('loop.protected')=='yes')
    else:
      self.loopProtected=False

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
                     inValueFilter=self.config.get('in.value.filter'),
                     log=self.in_log,
                     outFilter=self.config.get('out.filter'),
                     outValueFilter=self.config.get('out.value.filter'),
                     loopProtected=self.loopProtected)
      self.c2p.start()

    ''' if output plugin, connect P2C thread to handle stdout '''
    if 'out.filter' in self.config:
      self.p2c=PluginToCauldron(self.name,self.cauldronAddr,
                     self.process.stdout,
                     log=self.out_log,
                     outFilter=self.config.get('out.filter'),
                     outValueFilter=self.config.get('out.value.filter'))
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
    self.process.terminate()
    self.log("Stopped",component=self.name,priority=syslog.LOG_INFO)

  def get_counters(self):
    if self.p2c:
      self.counters['out']=self.p2c.get_counters()
    if self.c2p:
      self.counters['in']=self.c2p.get_counters()
    return self.counters

  def reset_counters(self):
    if self.p2c:
      self.p2c.reset_counters()
    if self.c2p:
      self.c2p.reset_counters()

# ----------------------------------------------------------------------

class Coven(object):
  def __init__( self,path,prefix,cauldronAddr,
      ignore=[r'^\.',r'\.x?swp$',r'~',r'^__',r'__$',r'\.jar$',r'\.db$']):
    syslog.openlog(ident="X3Coven",facility=syslog.LOG_DAEMON)
    self.path=path
    self.prefix=prefix
    self.cauldronAddr=cauldronAddr
    self.plugins={}
    self.plugins_lock=Lock()
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

  def put(self,label,value):
    self.cauldron.put('%s.coven.%s' % (self.prefix,label),value)
  
  def log(self,message,component=None,priority=syslog.LOG_DEBUG):
    syslog.syslog(priority,message if component==None 
                                else '[%s] %s' % (component,message))
  def practice(self):
    try:
      self.dirManager.start()
      while True:
        totals={}
        with self.plugins_lock:
          self.put('plugins.running',len(self.plugins))
          for plugin in self.plugins.values():
            for (values_type,values) in plugin.get_counters().items():
              try:
                total_values=totals[values_type]
              except KeyError:
                total_values={}
                totals[values_type]=total_values
              for (label,value) in values.items():
                try:
                  total_values[label]+=value
                except KeyError:
                  total_values[label]=value
                self.put('plugin.%s.%s.%s' %
                                (plugin.name,values_type,label),value)
            plugin.reset_counters()

        for (values_type,values) in totals.items():
          for (label,value) in values.items():
            self.put('plugins.total.%s.%s' % (values_type,label),value)
        time.sleep(1.0)
    except KeyboardInterrupt:
      self.log("Stopping..")
      self.dirManager.stop()
      with self.plugins_lock:
        for partingPlugin in self.plugins.values():
          partingPlugin.stop()
        for partingPlugin in self.plugins.values():
          partingPlugin.join()
      self.log("Stopped..",priority=syslog.LOG_INFO)

# ----------------------------------------------------------------------

  def startPlugin(self,name):
    self.log("Starting %s" % (name)) 
    config=self.getConfig(name)
    if config:
      try:
        with self.plugins_lock:
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
      with self.plugins_lock:
        self.plugins[name].stop()
        del self.plugins[name]
      self.log("Stopped %s" % (name),priority=syslog.LOG_INFO) 
    except:
      self.log("Failed To Stop %s" % (name),priority=syslog.LOG_ERR) 

# ----------------------------------------------------------------------

  def process_FileCreated(self,name):
    self.startPlugin(name)

  def process_FileDeleted(self,name):
    self.stopPlugin(name)

  def process_FileChanged(self,name):
    self.log("Restarting %s" % (name),priority=syslog.LOG_INFO) 
    self.stopPlugin(name)
    self.startPlugin(name)
  
# ----------------------------------------------------------------------

if __name__=='__main__':
  signal.signal(signal.SIGCHLD, signal.SIG_IGN)
  environ['PYTHONPATH']=sys.path[0]
  coven=Coven('/opt/extremon/plugins','be.fedict.eid.mon.isolde',('224.0.0.1',1249))
  coven.practice()
