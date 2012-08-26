import sys
if sys.version_info.major==2:
  if sys.version_info.minor<7:
    sys.stderr.write("ExtreMon Requires Python >=2.7")
    sys.exit(1)
  pver=2
else:
  pver=3
import time,os,re
from extremon import Loom

class X3Conf(object):
  def __init__(self):
    self.config={}
    for (label,value) in os.environ.items():
      if label.startswith('X3MON_'):
        self.config[label[6:].lower().replace('_','.')]=value

class X3Log(object):
  def log(self,message):
    sys.stderr.write('%s\n' % (message))
    sys.stderr.flush()

class X3In(X3Log,X3Conf):
  def __init__(self,cache=False,capture=False):
    X3Log.__init__(self)
    X3Conf.__init__(self)
    inshuttle={}
    if cache:
      self.cached={}
    if capture:
      self.regex=re.compile(self.config['in.filter'])
      self.captures={}

    try:
      for line in sys.stdin:
        if len(line)==1:
          if len(inshuttle)>0:
            if cache:
              self.cached.update({label:value for (label,value) in inshuttle.items()})
            if capture:
              for (label,value) in inshuttle.items():
                if label not in self.captures:
                  matches=self.regex.match(label)
                  if matches:
                    self.captures[label]=matches.groupdict()
                  else:
                    self.captures[label]=None
              self.receive((label,value,self.captures[label]) for (label,value) in inshuttle.items())
            else:
              self.receive((label,value) for (label,value) in inshuttle.items())
          inshuttle.clear()
        else:
          try:
            (label,value)=line.rstrip().split('=')
            inshuttle[label]=value
          except ValueError:
            self.log("invalid record [%s]\n" % (line))
    except IOError:
      sys.exit(0)

  def receive(self,inshuttle):
    raise TypeError("X3 Plugins Should Implement the "
                    "receive(self,shuttle) method")

class X3Out(Loom,X3Log,X3Conf):
  def __init__(self,max_shuttle_size=128,max_shuttle_age=.5):
    X3Log.__init__(self)
    X3Conf.__init__(self)
    Loom.__init__(self,launcher=self.launch,max_shuttle_size=max_shuttle_size, max_shuttle_age=max_shuttle_age)
    self.start()

  def launch(self,shuttle):
    try:
      sys.stdout.write(shuttle)
      sys.stdout.flush()
    except IOError:
      self.log("IOError writing to stdout.. exiting")
      sys.exit(0)

class X3IO(X3In,X3Out):
  def __init__(self,cache=False,capture=False,max_shuttle_size=512,max_shuttle_age=.5):
    X3Out.__init__(self,max_shuttle_size=max_shuttle_size,max_shuttle_age=max_shuttle_age)
    X3In.__init__(self,cache=cache,capture=capture)
