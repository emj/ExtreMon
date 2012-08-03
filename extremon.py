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

import time,socket, struct
from queue      import Queue
from threading  import Thread,Lock

############################### CAULDRON ############################

class CauldronReceiver:
    """ subscribe to the multicast Cauldron at a certain port, handler is called with shuttles boiling at that port.
    
        pass an (address,port) tuple indicating what mcast group/port you want to subscribe to,
        and a handler instance, which should implement a handle_shuttle(self, set) method,
        then call receive_forever (which blocks): your handle_shuttle method will be called
        with a set of (label,value) tuples for each shuttle that boils at the group/port you gave.
    """
    def __init__(self,mcast_addr,handler):
        (mcast_group,mcast_port)=mcast_addr
        self.handler=handler
        self.socket=socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('', mcast_port))
        self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, struct.pack("4sl", socket.inet_aton(mcast_group), socket.INADDR_ANY))
        self.shuttle=set()

    def receive_shuttle(self):
        data=self.socket.recv(16384)
        for line in str(data,'UTF-8').splitlines():
            if len(line)>0:
                try:
                    (label,value)=line.split('=')
                    if label and value:
                        self.shuttle.add((label,value))
                except ValueError:
                    pass
        self.handler.handle_shuttle(set(self.shuttle))
        self.shuttle.clear()

    def receive_forever(self):
        while True:
            self.receive_shuttle()


class CauldronSender:
    """ contribute to the multicast Cauldron at a certain port, adding values.
    
        pass an (address,port) tuple indicating what mcast group/port you want to contribute to,
        call put(label,value) to contribute. the CauldronSender will accumulate values until either
        max_shuttle_size are ready to send, or max_shuttle_age seconds have passed.
        
        WARNING: CauldronSender assumes a minimal boiling level where values are presented
                 at least every max_shuttle_age seconds: If e.g. you present one value,
                 and then none for minutes, that one value will not be contributed for
                 minutes even if max_shuttle_age is far lower than that.
    """
    def __init__(self,mcast_addr,max_shuttle_size=512,max_shuttle_age=.5):
        self.mcast_addr=mcast_addr
        self.sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL,1)
        self.max_shuttle_size=max_shuttle_size
        self.max_shuttle_age=max_shuttle_age
        self.shuttle=set()
        self.clear_shuttle()

    def put(self,label,value):
        _value=str(value)
        if '=' in _value:
            raise ValueError('"=" Is An Illegal Value In ExtreMon Labels And Values')
        self.shuttle.add('%s=%s' % (label,_value))
        if len(self.shuttle)>=self.max_shuttle_size or time.time()>=(self.shuttle_age+self.max_shuttle_age):
            self.sock.sendto(bytes('%s\n\n' % ('\n'.join(self.shuttle)),'UTF-8'),self.mcast_addr)
            self.clear_shuttle()

    def clear_shuttle(self):
        self.shuttle.clear()
        self.shuttle_age=time.time()


class CauldronLabelFilter:
    """ Base class for filtering the labels of label-value pairs boiling, *between* ports in a boiling cauldron.
    
        Pass two (address,port) tuples indicating the mcast group/port to listen for values, and the mcast group/port
        to write filtered values to, call filter_forever (blocks).
    
        Subclasses should implement the filter_label() method which takes a label and returns a label, after whatever
        filtering it applies. Note that the subclasses' filter_label method is only called once per unique label,
        as the CauldronLabelFilter will cache the result and use the cached label without calling the filter_label again.
    """
    def __init__(self,in_addr,out_addr,max_shuttle_size=128,max_shuttle_age=.1):
        self.receiver=CauldronReceiver(mcast_addr=in_addr,handler=self)
        self.sender=CauldronSender(mcast_addr=out_addr,max_shuttle_size=max_shuttle_size,max_shuttle_age=max_shuttle_age)
        self.cache={}

    def filter_shuttle(self):
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
        raise NotImplementedError("Subclasses of CauldronLabelFilter should implement a filter_label method")


class CauldronContributor:
    """ Base class for contributing values to a boiling cauldron, based on values already boiling
    
    Pass an (address,port) tuple indicating the mcast group/port to contribute to, and a suffix to be added
    to the label of the existing value you want to contribute to, to form your own label, call contribute_forever (blocks).
    
    Subclasses should implement the contribute(self,label,value) method, and call one of the put_ methods
    to contribute.
    """
    def __init__(self,mcast_addr,suffix=None,max_shuttle_size=128,max_shuttle_age=.1):
        self.receiver=CauldronReceiver(mcast_addr=mcast_addr,handler=self)
        self.sender=CauldronSender(mcast_addr=mcast_addr,max_shuttle_size=max_shuttle_size,max_shuttle_age=max_shuttle_age)
        self.suffix=suffix
        self.values={}
        if self.suffix:
            self.handle_shuttle=self.handle_shuttle_with_suffix
            self.put=self.put_with_suffix
        else:
            self.handle_shuttle=self.handle_shuttle_without_suffix
            self.put=self.put_without_suffix

    def contribute_shuttle(self):
        self.receiver.receive_shuttle()

    def contribute_forever(self):
        self.receiver.receive_forever()

    def handle_shuttle_with_suffix(self,shuttle):
        for (label,value) in shuttle:
            label_parts=label.split('.')
            if not label_parts[-1].startswith(self.suffix):
                try:
                    if self.values[label]!=value:
                        self.values[label]=value
                except KeyError:
                    self.values[label]=value
                self.contribute(label,value)

    def handle_shuttle_without_suffix(self,shuttle):
        for (label,value) in shuttle:
            try:
                if self.values[label]!=value:
                    self.values[label]=value
            except KeyError:
                self.values[label]=value
            self.contribute(label,value)

    def contribute(self,label,value):
        raise NotImplementedError("Subclasses of CauldronContributor should implement a contribute method")

    def put_with_suffix(self,label,value,sub=None):
        if sub:
            self.sender.put('%s.%s.%s' % (label,self.suffix,'.'.join(sub)),value)
        else:
            self.sender.put('%s.%s' % (label,self.suffix),value)

    def put_without_suffix(self,label,value):
        self.sender.put(label,value)

    def put_with_comment(self,label,state,comment):
        self.put(label=label,value=state)
        self.put(label=label,sub=['comment'],value=comment)
    
    
    
class CauldronServer(Thread):
    """ Base class for streaming servers that serve full boiling cauldrons.
    
        values that are presented via the write method are asynchronously copied to all consumers registered
        by calling the consumer's write methods. adding and removing consumers, and writing are thread-safe.
        CauldronServer adds a sequence number and timestamp to shuttles being distributed, allowing clients
        to determine time lag and lost shuttles
        
        CauldronServers are Threads, and must be start()ed.
        
        CauldronServers are intended to be Mixed with e.g. TCPServers, HTTPServers, etc..
        there are examples in the servers/ directory  
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
                consumer.write(bytes('%s\n\n' % ('\n'.join(self.shuttle)),'UTF-8'))
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

############################### CHALICE ############################        
        
class ChaliceServer(CauldronServer):
    """ Base class for streaming servers that serve one full cauldron, then chalices of change
    
        This is basically a CauldronServer with a cache that distinguishes repeat values from changes.
        The entire cauldron is sent, in shuttles all having an *.iscachedump=1 indicator,
        then only changing values and new labels are sent. A new label appearing in chalices of change will be sent alongside
        an indicator of *.label.isnew=1
        
        ChaliceServers are intended to be Mixed with e.g. TCPServers, HTTPServers, etc..
        there are examples in the servers/ directory
    """
    
    def dump_cache(self,consumer):
        with self.cache_lock:
            consumer.write(bytes('%s\n' % ('\n'.join(['%s=%s' % (label,value) for (label,value) in self.cache.items()])),'UTF-8'))

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

