#
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

import sys
if sys.version_info.major==2:
  if sys.version_info.minor<7:
    sys.stderr.write("ExtreMon Requires Python >=2.7")
    sys.exit(1)
  pver=2
else:
  pver=3

import time,socket, struct
from numbers import Number
from threading import Thread,Lock
if pver==3:
  from queue import Queue,Empty
else:
  from Queue import Queue,Empty


############################### CAULDRON ################################

''' base for classes that contribute shuttles
    allows label-value pairs (pairs with same label replaces previous)
    to be gathered into a shuttle, which is sent by launcher()
    when max_shuttle_size or max_shuttle_age is reached '''

class Loom(Thread):
  def __init__( self,launcher=None,
                max_shuttle_size=128,
                max_shuttle_age=.5):
    Thread.__init__(self)
    self.daemon=True
    self.launcher=launcher if launcher!=None else self._default_launcher
    self.max_shuttle_size=max_shuttle_size
    self.max_shuttle_age=max_shuttle_age
    self._launch=self._launch_p3 if pver==3 else self._launch_p2
    self.inqueue=Queue()
    self.shuttle=dict()
    self.next_deadline=time.time()+max_shuttle_age

# call start() inherited from Thread to start treating shuttles
# call stop() to stop treating shuttles

  def stop(self):
    self.inqueue.put(('None',None)) # "poison" the queue
    self.inqueue.join()             # wait until all records handled

# call put(label,value) for any data to contribute

  def put(self,label,_value):
    if isinstance(_value, Number):
      value=str(round(_value,3))
    else:
      value=_value
    if '=' in label or '\n' in label or '=' in value or '\n' in value:
      raise ValueError('"=" and "\\n" Are Illegal '
                       'in X3Mon Labels And Values')
    self.inqueue.put((label,value))

# default launcher writes shuttle to stdout
  def _default_launcher(shuttle):
    sys.stdout.write(shuttle)

# internal launch (python3). don't call directly
  def _launch_p3(self,shuttle): 
    self.launcher('%s\n\n' % ('\n'.join(['%s=%s' % (label,value) 
                            for (label,value) in shuttle.items()])))

# internal launch (python2). don't call directly
  def _launch_p2(self,shuttle): 
    self.launcher('%s\n\n' % ('\n'.join(['%s=%s' % (label,value) 
                            for (label,value) in shuttle.items()])).encode('utf-8'))

# launch using python2 or 3 launcher
  def launch_and_clear(self,shuttle):
    self._launch(shuttle)
    self.shuttle.clear()
    self._reset()
    
# reset deadline
  def _reset(self): 
    self.next_deadline=time.time()+self.max_shuttle_age

# main dequeuer loop
  def run(self):
    lazy=False
    ending=False
    while True:
      try:    # if we're empty, don't bother to wake up until we aren't
        timeout=(None if lazy else self.max_shuttle_age)
        (label,value)=self.inqueue.get(block=True, timeout=timeout)
        if value==None:   # poison value indicated stop() was called
          self.inqueue.task_done()
          ending=True     # signal ending
          lazy=False      # and make sure we don't block
        else:
          if lazy:            # if we're just awakened
            self._reset()     # reset deadline to avoid sending 1 record
          self.shuttle[label]=value   # store unqueued value
          self.inqueue.task_done()    # keep tally for join()
          lazy=False                  # not empty, block only for max_age
          if (len(self.shuttle)>=self.max_shuttle_size or 
             time.time()>=self.next_deadline):  # launch if old or full
            self.launch_and_clear(self.shuttle)
      except Empty:                             # if empty
        if (len(self.shuttle)>0 and             # launch if old and 
            time.time()>=self.next_deadline):   # something to launch
          self.launch_and_clear(self.shuttle)
        if ending:                              # if stop() called
          return                                # run() ends
        lazy=True  # otherwise (normal empty), we may now block > max_age

class CauldronReceiver:

  """ subscribe to the multicast Cauldron at a certain port, handler is 
    called with shuttles boiling at that port.
  
    pass an (address,port) tuple indicating what mcast group/port you 
    want to subscribe to, and a handler instance, which should 
    implement a handle_shuttle(self, set) method, then call 
    receive_forever (which blocks): your handle_shuttle method will be 
    called with a set of (label,value) tuples for each shuttle that 
    boils at the group/port you gave.
  """

  def __init__(self,mcast_addr,handler):
    (mcast_group,mcast_port)=mcast_addr
    self.handler=handler
    self.socket=socket.socket(  socket.AF_INET,
                                socket.SOCK_DGRAM,
                                socket.IPPROTO_UDP)
    self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    self.socket.bind(('', mcast_port))
    self.socket.setsockopt( socket.IPPROTO_IP,
                            socket.IP_ADD_MEMBERSHIP,
                            struct.pack("4sl",
                            socket.inet_aton(mcast_group),
                            socket.INADDR_ANY))
    self.shuttle=set()


  def receive_shuttle(self):
    data=self.socket.recv(16384)
    for line in str(data,'UTF-8').splitlines():
      if len(line)>0:
          labelAndValue=line.split('=')
          if len(labelAndValue)==2:
            self.shuttle.add((labelAndValue[0],labelAndValue[1]))
    self.handler.handle_shuttle(set(self.shuttle))
    self.shuttle.clear()


  def receive_forever(self):
    while True:
      self.receive_shuttle()


class CauldronSender(Loom):

  """ contribute to the multicast Cauldron at a certain port, adding
    values.
  
    pass an (address,port) tuple indicating what mcast group/port you
    want to contribute to, call put(label,value) to contribute. the 
    CauldronSender will accumulate values until either max_shuttle_size
    are ready to send, or max_shuttle_age seconds have passed.
  """

  def __init__(self,mcast_addr,max_shuttle_size=128,max_shuttle_age=.5):
    self.mcast_addr=mcast_addr
    self.sock=socket.socket(  socket.AF_INET,
                              socket.SOCK_DGRAM,
                              socket.IPPROTO_UDP)
    self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL,1)
    Loom.__init__(self,launcher=self.launch,
                  max_shuttle_size=max_shuttle_size,
                  max_shuttle_age=max_shuttle_age)
    self.start()

  def launch(self,shuttle):
      self.sock.sendto(bytes(shuttle,'utf-8'),self.mcast_addr)

class CauldronLabelFilter:

  """ Base class for filtering the labels of label-value pairs boiling, 
    *between* ports in a boiling cauldron.
  
    Pass two (address,port) tuples indicating the mcast group/port to 
    listen for values, and the mcast group/port to write filtered 
    values to, call filter_forever (blocks).
  
    Subclasses should implement the filter_label() method which takes a 
    label and returns a label, after whatever filtering it applies.
    Note that the subclasses' filter_label method is only called once
    per unique label, as the CauldronLabelFilter will cache the result
    and use the cached label without calling the filter_label again.
  """
  
  def __init__( self,in_addr,out_addr,max_shuttle_size=128,
                max_shuttle_age=.1):
    self.receiver=CauldronReceiver(mcast_addr=in_addr,handler=self)
    self.sender=CauldronSender( mcast_addr=out_addr,
                                max_shuttle_size=max_shuttle_size,
                                max_shuttle_age=max_shuttle_age)
    self.cache={}
    self.receiver.receive_shuttle()

    
  def filter_forever(self):
    self.receiver.receive_forever()


  def handle_shuttle(self,shuttle):
    for (old_label,value) in shuttle:
      try:
        label=self.cache[old_label]
      except KeyError:
        label=self.filter_label(old_label)
        self.cache[old_label]=label
      self.sender.put(label,value)

  def filter_label(self,label):
    raise NotImplementedError(  "Subclasses of CauldronLabelFilter "
                                "should implement a filter_label "
                                "method")


class CauldronServer(Thread):
  """ Base class for streaming servers that serve full boiling cauldrons.
  
    values that are presented via the write method are asynchronously 
    copied to all consumers registered by calling the consumer's write 
    methods. adding and removing consumers, and writing are 
    thread-safe.  CauldronServer adds a sequence number and timestamp
    to shuttles being distributed, allowing clients to determine time
    lag and lost shuttles.
    
    CauldronServers are Threads, and must be start()ed.
    
    CauldronServers are intended to be Mixed with e.g. TCPServers,
    HTTPServers, etc..  there are examples in the servers/ directory
  """
  
  def __init__(self,prefix):
    Thread.__init__(self,name='server')
    self.daemon=True
    self.inq=Queue()
    self.consumers=set()
    self.consumers_lock=Lock()
    self.prefix=prefix
    self.shuttle=set()
    self.sequence=0

  def clear_shuttle(self):
    self.shuttle.clear()
    self.add_to_shuttle('%s.sequence' % (self.prefix),self.sequence)
    self.add_to_shuttle('%s.timestamp' % (self.prefix),time.time())

  def add_to_shuttle(self,label,value):
    self.shuttle.add('%s=%s' % (label,value))

  def run(self):
    while(True):
      data=self.inq.get()
      self.clear_shuttle()
      self.assemble_shuttle(data)
      self.scatter_shuttle()

  def assemble_shuttle(self,data):
    for (label,value) in data:
      self.add_to_shuttle(label,value)

  def scatter_shuttle(self):
    with self.consumers_lock:
      for consumer in self.consumers:
        consumer.write(   bytes('%s\n\n' % ('\n'.join(self.shuttle)),
                         'UTF-8'))
      self.sequence+=1

  def add_consumer(self,consumer):
    with self.consumers_lock:
      self.consumers.add(consumer)

  def remove_consumer(self,consumer):
    with self.consumers_lock:
      self.consumers.remove(consumer)

  def write(self,data):
    if len(data)>0:
      self.inq.put(data)  

    
class ChaliceServer(CauldronServer):
  """ Base class for streaming servers that serve one full cauldron, then 
    chalices of change
  
    This is basically a CauldronServer with a cache that distinguishes 
    repeat values from changes.  The entire cauldron is sent, in 
    shuttles all having an *.iscachedump=1 indicator, then only 
    changing values and new labels are sent. A new label appearing in
    chalices of changes will be sent alongside an indicator of 
    *.label.isnew=1
    
    ChaliceServers are intended to be Mixed with e.g. TCPServers, 
    HTTPServers, etc..  there are examples in the servers/ directory
  """
  
  def dump_cache(self,consumer):
    with self.cache_lock:
      consumer.write(bytes('%s\n' % ('\n'.join(['%s=%s' % (label,value)
             for (label,value) in self.cache.items()])),'UTF-8'))

  def __init__(self,prefix):
    CauldronServer.__init__(self,prefix)
    self.cache={}
    self.cache['%s.iscachedump' % (self.prefix)]=1
    self.cache_lock=Lock()

  def assemble_shuttle(self,data):
    with self.cache_lock:
      for (label,value) in data:
        try:
          if self.cache[label]!=value:
            self.add_to_shuttle(label,value)
            self.cache[label]=value
        except KeyError:
          self.cache[label]=value
          self.add_to_shuttle(label,value)
          self.shuttle.add('%s.isnew=1' % (label))

  def add_consumer(self,consumer):
    self.dump_cache(consumer)
    CauldronServer.add_consumer(self,consumer)


