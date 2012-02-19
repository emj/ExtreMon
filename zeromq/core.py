#!/usr/bin/python3
import zmq,time
from queue 		import Queue
from threading	import Thread


class Publisher(Thread):
	def __init__(self,context,listen_on):
		Thread.__init__(self,name="Publisher")
		self.deamon=True
		self.context=context
		self.listen_on=listen_on
		self.outq=Queue(maxsize=8192)
		self.running=False

	def publish(self,data):
		self.outq.put(data)

	def run(self):
		socket=self.context.socket(zmq.PUB)
		socket.bind(self.listen_on)
		self.running=True
		self.starttime=time.time()
		self.seq=0
		while self.running:
			socket.send(self.outq.get())
			self.seq+=1
			print("shuttle")
			if self.seq % 100==0:
				print("%d shuttles/sec ; %d in queue" % (self.seq/(time.time()-self.starttime),self.outq.qsize()))
				self.starttime=time.time()

	def stop(self):
		self.running=False
		self.outq.put(None)
			

class PullerPublisher:
	def __init__(self,pull_listen_on, pub_listen_on, high_water_mark=16):
		self.context=zmq.Context()
		self.listen_on=pull_listen_on
		self.high_water_mark=high_water_mark
		self.publisher=Publisher(self.context,pub_listen_on)

	def pull_forever(self):
		self.publisher.start();
		socket=self.context.socket(zmq.PULL)
		socket.setsockopt(zmq.HWM,self.high_water_mark)
		socket.bind(self.listen_on)
		while(True):
			self.publisher.publish(socket.recv())

if __name__=='__main__':
	puller_publisher=PullerPublisher('tcp://127.0.0.1:2000','tcp://127.0.0.1:3000')
	puller_publisher.pull_forever()
