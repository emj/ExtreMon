#!/usr/bin/python3
import sys,time

class X3In(object):

  def __init__(self):
    shuttle={}
    try:
      for line in sys.stdin:
        if len(line)==1:
          if len(shuttle)>0:
            self.receive(shuttle)
          shuttle.clear()
        else:
          try:
            (label,value)=line.rstrip().split('=')
            shuttle[label]=value
          except ValueError:
            print("invalid record [%s]\n" % (line),file=sys.stderr)
    except IOError:
      sys.exit(0)

  def receive(self,shuttle):
    raise TypeError("X3 Plugins Should Implement the "
                    "receive(self,shuttle) method")


class X3Out(object):

  def __init__(self,max_shuttle_size=512,max_shuttle_age=.5):
    self.max_shuttle_size=max_shuttle_size                            
    self.max_shuttle_age=max_shuttle_age
    self.shuttle=set()
    self.shuttle_age=time.time()

  def contribute(self,label,_value):
    value=str(_value)
    if '=' in label or '=' in value:
      raise ValueError('"=" Is Illegal in X3Mon Labels And Values')
    self.shuttle.add('%s=%s' % (label,value))
    if len(self.shuttle)>=self.max_shuttle_size or \
       time.time()>=(self.shuttle_age+self.max_shuttle_age):
      try:
        print('%s\n' % ('\n'.join(self.shuttle)))
        sys.stdout.flush()
      except IOError:
        sys.exit(0)
      self.shuttle.clear()

class X3IO(X3In,X3Out):
  def __init__(self,max_shuttle_size=512,max_shuttle_age=.5):
      X3Out.__init__(self,max_shuttle_size=max_shuttle_size,
                          max_shuttle_age=max_shuttle_age)
      X3In.__init__(self)
