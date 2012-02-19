#!/usr/bin/python3

from threading 	import Thread
from queue 		import Queue
import zmq,time,socket,struct

class Sender(Thread):
	def __init__(self,push_addr):
		Thread.__init__(self,name='sender')
		self.daemon=True
		self.context=zmq.Context()
		self.push_addr=push_addr
		self.outq=Queue()

	def run(self):
		socket=self.context.socket(zmq.PUSH)
		socket.setsockopt(zmq.HWM, 100)
		socket.connect(self.push_addr)
		while True:
			socket.send(self.outq.get());

class Injector:
	def __init__(self,mcast_addr,push_addr):
		self.sender=Sender(push_addr)
		(mcast_group,mcast_port)=mcast_addr
		self.socket=socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
		self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.socket.bind(('', mcast_port))
		self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, struct.pack("4sl", socket.inet_aton(mcast_group), socket.INADDR_ANY))

	def run(self):
		self.sender.start()
		self.running=True
		while self.running:
			self.sender.outq.put(self.socket.recv(16384))

if __name__=='__main__':
	injector=Injector(mcast_addr=('224.0.0.1',1249),push_addr='tcp://127.0.0.1:2000')
	injector.run()
