#
#	ExtreMon Project
#	Copyright (C) 2009-2012 Frank Marien
#	frank@apsu.be
#  
#	This file is part of ExtreMon.
#    
#	ExtreMon is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	ExtreMon is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with ExtreMon.  If not, see <http://www.gnu.org/licenses/>.
#

import time,socket, struct
from queue 		import Queue
from threading 	import Thread,Lock

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
				(label,value)=line.split('=')
				if label and value:
					self.shuttle.add((label,value))
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

