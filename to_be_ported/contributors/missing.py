#!/usr/bin/python3

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

import time
from extremon import CauldronContributor

STATE_OK=0
STATE_WARNING=1
STATE_ALERT=2
STATE_MISSING=3
STATE_TACKLED=4

class Missing(CauldronContributor):
	def __init__(self,mcast_addr,max_missing,max_delay):
		CauldronContributor.__init__(self,mcast_addr=mcast_addr);
		self.running=False
		self.last_seen={}
		self.max_missing=max_missing
		self.max_delay=max_delay
		self.last_sent=time.time()

	def handle_shuttle(self,shuttle):
		CauldronContributor.handle_shuttle(self,shuttle)
		now=time.time()
		if(now-self.last_sent) > self.max_delay:
			self.put_missing(now)	
			self.last_sent=now

	def contribute(self,label,value):
		if label.endswith('state') and value!=str(STATE_MISSING):
			self.last_seen[label]=time.time()

	def put_missing(self,now):
		for (label,last_seen_at) in self.last_seen.items():
			if (now-last_seen_at) > self.max_missing:
				self.put(label,STATE_MISSING)
				print("MISSING %s for %d seconds" % (label,(now-last_seen_at)))
	
if __name__=='__main__':
	Missing(mcast_addr=('224.0.0.1',1249),max_missing=10,max_delay=1).contribute_forever()
	

