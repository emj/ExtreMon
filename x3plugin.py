#!/usr/bin/python3
import sys,time

class X3In(object):
  def __init__(self):
    self.inshuttle={}
    try:
      for line in sys.stdin:
        if len(line)==1:
          if len(self.inshuttle)>0:
            self.receive(self.inshuttle)
          self.inshuttle.clear()
        else:
          try:
            (label,value)=line.rstrip().split('=')
            self.record(label,value)
          except ValueError:
            print("invalid record [%s]\n" % (line),file=sys.stderr)
    except IOError:
      sys.exit(0)

  def record(self,label,value):
    self.inshuttle[label]=value

  def receive(self,inshuttle):
    raise TypeError("X3 Plugins Should Implement the "
                    "receive(self,shuttle) method")

  def log(self,message):
    print(message,file=sys.stderr)
    sys.stderr.flush()

class X3CachingIn(X3In):
  def __init__(self):
    self.cached={}
    X3In.__init__(self)

  def record(self,label,value):
    X3In.record(self,label,value)
    self.cached[label]=value


class X3Out(object):
  def __init__(self,max_shuttle_size=512,max_shuttle_age=.5):
    self.max_shuttle_size=max_shuttle_size                            
    self.max_shuttle_age=max_shuttle_age
    self.outshuttle=set()
    self.outshuttle_age=time.time()

  def contribute(self,label,_value):
    value=str(_value)
    if '=' in label or '=' in value:
      raise ValueError('"=" Is Illegal in X3Mon Labels And Values')
    self.outshuttle.add('%s=%s' % (label,value))
    if len(self.outshuttle)>=self.max_shuttle_size or \
       time.time()>=(self.outshuttle_age+self.max_shuttle_age):
      try:
        print('%s\n' % ('\n'.join(self.outshuttle)))
        sys.stdout.flush()
      except IOError:
        sys.exit(0)
      self.outshuttle.clear()

  def log(self,message):
    print(message,file=sys.stderr)
    sys.stderr.flush()

class X3IO(X3In,X3Out):
  def __init__(self,max_shuttle_size=512,max_shuttle_age=.5):
      X3Out.__init__(self,max_shuttle_size=max_shuttle_size,
                          max_shuttle_age=max_shuttle_age)
      X3In.__init__(self)

class X3IOC(X3CachingIn,X3Out):
  def __init__(self,max_shuttle_size=512,max_shuttle_age=.5):
      X3Out.__init__(self,max_shuttle_size=max_shuttle_size,
                          max_shuttle_age=max_shuttle_age)
      X3CachingIn.__init__(self)
