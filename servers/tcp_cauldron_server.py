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

import 						sys
from socketserver 	import 	ThreadingTCPServer,BaseRequestHandler
from queue 			import 	Queue,Full
from socket 		import 	error
from extremon		import 	CauldronReceiver,CauldronServer


class TCPCauldronRequestHandler(BaseRequestHandler):
	def setup(self):
		self.outq=Queue()
		self.running=True
		self.server.add_consumer(self)
	
	def handle(self):
		while self.running:
			try:
				self.request.sendall(self.outq.get())
				self.outq.task_done()
			except error:
				self.running=False

	def finish(self):
		self.server.remove_consumer(self)

	def write(self,data):
		try:
			self.outq.put(data,block=False)
		except Full:
			pass


class TCPCauldronServer(CauldronServer,ThreadingTCPServer):
	def __init__(self,listen,prefix):
		self.allow_reuse_address=True
		ThreadingTCPServer.__init__(self,listen, TCPCauldronRequestHandler)
		CauldronServer.__init__(self, prefix)


class TCPCauldronDispatcher:
	def __init__(self,mcast_addr,listen,prefix):
		self.server=TCPCauldronServer(listen,prefix)
		self.client=CauldronReceiver(mcast_addr=mcast_addr,handler=self);
		self.server.start()
		self.client.start()
		self.server.serve_forever()

	def handle(self,data):
		if len(data):
			self.server.write(data)

if __name__=='__main__':

	if len(sys.argv)==2:
		listen_addr=''
		listen_port=17617
	elif len(sys.argv)==4:
		listen_addr=sys.argv[2]
		listen_port=int(sys.argv[3])
	else:
		print("Usage: tcp_server.py <prefix> [<listen_addr> <listen_port>]")
		sys.exit(-1)

	prefix=sys.argv[1]

	TCPCauldronDispatcher(mcast_addr=('224.0.0.1',1248),listen=(listen_addr,listen_port),prefix=prefix)
