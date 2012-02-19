#!/usr/bin/python3

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

import 							sys
import 							pyinotify,select
from queue 				import 	Queue,Full
from socket 			import 	error
from extremon			import 	CauldronReceiver,CauldronServer
from subprocess 		import 	Popen,PIPE
from threading			import 	Thread

READ_ONLY = select.POLLIN | select.POLLPRI | select.POLLHUP | select.POLLERR



class StdOutAndErrCauldronRequestHandler(Thread):

	def __init__(self,server,path,out,err):
		Thread.__init__(self,name='StdOutAndErrCauldronRequestHandler %s' % (path))
		self.daemon=True
		self.server=server
		self.path=path
		self.out=out
		self.out_fd=self.out.fileno()
		self.err=err
	
	def run(self):
		poller = select.poll()
		poller.register(self.out,READ_ONLY)
		poller.register(self.err,READ_ONLY)
		self.running=True
		print("StdOutAndErrCauldronRequestHandler %s running" % (self.path))

		while self.running:
			events = poller.poll(1000)
			for fd, flag in events:
				if flag & (select.POLLIN | select.POLLPRI):
					if fd==self.out_fd:
						print("stdout")
					else:
						print("stderr")
				elif flag & (select.POLLHUP | select.POLLERR):
					
					

	def stop(self):
		self.running=False


class StdInCauldronRequestHandler(Thread):

	def __init__(self,server,path):
		Thread.__init__(self,name='StdInCauldronRequestHandler %s' % (path))
		self.daemon=True
		self.server=server
		self.path=path
	
	def run(self):
		self.outq=Queue(maxsize=10)

		try:
			self.process=Popen(self.path,stdin=PIPE,stdout=PIPE,stderr=PIPE)
			self.running=True
			print("StdInCauldronRequestHandler %s running" % (self.path))

			self.outputhandler=StdOutAndErrCauldronRequestHandler(self.server,self.path,self.process.stdout,self.process.stderr)
			self.outputhandler.start()
			
			self.server.add_consumer(self)
			while self.running:
				try:
					self.process.stdin.write(self.outq.get())
					self.process.stdin.flush()
					self.outq.task_done()
				except error:
					self.running=False
		finally:
			self.server.remove_consumer(self)	

	def write(self,data):
		try:
			self.outq.put(data,block=False)
		except Full:
			print("StdInCauldronRequestHandler %s Cannot Cope.. Buffer Overflow.." % (self.path))

	def stop(self):
		self.running=False
		self.process.terminate()
		self.process.wait()



class StdInCauldronServer(Thread,pyinotify.ProcessEvent):
	def __init__(self,prefix,plugin_dir):
		Thread.__init__(self,name='StdInCauldronServer')
		self.daemon=True
		self.cauldronserver=CauldronServer(prefix)
		self.plugin_dir=plugin_dir
		self.wm=pyinotify.WatchManager()
		self.notifier=pyinotify.Notifier(self.wm,self)
		self.watch=self.wm.add_watch(plugin_dir,pyinotify.IN_DELETE|pyinotify.IN_CLOSE_WRITE,rec=True)
		self.boiling={}

	def run(self):
		self.cauldronserver.start()
		self.notifier.loop()

	def process_IN_DELETE(self, event):
		print("Removing:", event.pathname)
		self.stopProcess(event.pathname)

	def process_IN_CLOSE_WRITE(self, event):
		print("Edited:", event.pathname)
		self.stopProcess(event.pathname)
		self.startProcess(event.pathname)

	def stopProcess(self,path):
		try:
			process=self.boiling[path]
			process.stop()
		except KeyError:
			pass

	def startProcess(self,path):
		process=StdInCauldronRequestHandler(self.cauldronserver,path)
		self.boiling[path]=process
		process.start()
	
	def write(self,data):
		self.cauldronserver.write(data)



class StdInCauldronDispatcher:
	def __init__(self,mcast_addr,prefix):
		self.server=StdInCauldronServer(prefix,'/home/frank/plugins')
		self.client=CauldronReceiver(mcast_addr=mcast_addr,handler=self);
		self.server.start()
		self.client.receive_forever()

	def handle_shuttle(self,data):
		if len(data):
			self.server.write(data)

if __name__=='__main__':
	if len(sys.argv)!=2:
		print("Usage: http_server.py <prefix>")
		sys.exit(-1)
	prefix=sys.argv[1]
	StdInCauldronDispatcher(mcast_addr=('224.0.0.1',1249),prefix=prefix)


