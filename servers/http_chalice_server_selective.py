#!/usr/bin/env python3

#
#	ExtreMon Project
#	Copyright (C) 2009-2013 Frank Marien
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

import 						sys, re, sre_constants
from http.server	import 	HTTPServer,BaseHTTPRequestHandler
from socketserver	import 	ThreadingMixIn
from queue 				import 	Queue,Full
from socket 			import 	error
from extremon			import 	CauldronReceiver,ChaliceServer
from threading		import 	Thread


class HTTPSelectiveChaliceRequestHandler(BaseHTTPRequestHandler):
	server_version = "Extremon/0.1"

	def valid_selector(self,path):
		return re.match('^[a-z0-9_:;/*-]*$',path)

	def regexify(self,path):
		pathelems=self.path[1:].split('/')
		if len(pathelems)==0:
			return '.*'
		for i in range(0,len(pathelems)):
			print(pathelems[i])
			if pathelems[i]=='*':
				pathelems[i]='([a-z0-9_:;-]+)'
			elif pathelems[i]=='**':
				pathelems[i]='([a-z0-9_:;.-]+)'
		return '^%s' % ('\.'.join(pathelems))

	def assemble_shuttle(self,data):
		for line in str(data,'UTF-8').splitlines():
			if len(line)>0:
				(label,value)=line.split('=')
				if label and value:
					try:
						select=self.select_cache[label]
					except KeyError:
						select=(self.regex.match(label)!=None)
						self.select_cache[label]=select
					if select:
						self.shuttle.add('%s=%s' % (label,value))

	def do_GET(self):
		self.shuttle=set()
		self.select_cache={}
		if self.path and self.valid_selector(self.path):
			try:
				regex=self.regexify(self.path)
				if regex:
					print(regex)
					self.regex=re.compile(regex)
			except sre_constants.error:
				self.send_error(400,'Invalid Selector')
				return
		else:
			self.send_error(400,'Invalid Character In Request')
			return

		try:
			self.send_response(200)
			self.send_header("Content-type", "text/plain")
			self.send_header("Access-Control-Allow-Origin", "*")
			self.end_headers()
			self.running=True
			self.outq=Queue(maxsize=1000)
			self.server.add_consumer(self)
			while self.running:
				try:
					data=self.outq.get()
					self.shuttle.clear()
					self.assemble_shuttle(data)
					if len(self.shuttle)>0:
						self.wfile.write(bytes(	'%s\n\n' % ('\n'.join(self.shuttle)),
																		'UTF-8'))
					self.outq.task_done()
				except error:
					self.running=False
		finally:
			self.server.remove_consumer(self)

	def write(self,data):
		try:
			self.outq.put(data,block=False)
		except Full:
			pass

class HTTPSelectiveChaliceServer(ThreadingMixIn,ChaliceServer,HTTPServer):
	def __init__(self,listen,prefix):
		HTTPServer.__init__(self,listen,HTTPSelectiveChaliceRequestHandler)
		ChaliceServer.__init__(self,prefix)

class HTTPSelectiveChaliceDispatcher(Thread):
	def __init__(self,mcast_addr,listen,prefix):
		Thread.__init__(self)
		self.daemon=True
		self.server=HTTPSelectiveChaliceServer(listen,prefix)
		self.receiver=CauldronReceiver(mcast_addr=mcast_addr,handler=self);
		self.server.start()
		self.start()
		self.server.serve_forever()

	def run(self):
		self.receiver.receive_forever()

	def handle_shuttle(self,data):
		if len(data):
			self.server.write(data)

if __name__=='__main__':
	if len(sys.argv)==2:
		listen_addr=''
		listen_port=17817
	elif len(sys.argv)==4:
		listen_addr=sys.argv[2]
		listen_port=int(sys.argv[3])
	else:
		print("Usage: http_server.py <prefix> [<listen_addr> <listen_port>]")
		sys.exit(-1)
	prefix=sys.argv[1]
	HTTPSelectiveChaliceDispatcher(	mcast_addr=('224.0.0.1',1249),
																	listen=(listen_addr,listen_port),
																	prefix=prefix)

