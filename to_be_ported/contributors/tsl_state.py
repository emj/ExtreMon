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

import 					re
from extremon	import 	CauldronContributor

STATE_OK=0
STATE_WARNING=1
STATE_ALERT=2
STATE_MISSING=3
STATE_TACKLED=4


class TrustState(CauldronContributor):
	def __init__(self,mcast_addr):
		CauldronContributor.__init__(self,mcast_addr=mcast_addr,suffix='state')
		self.regex=re.compile('^(?P<prefix>[a-z0-9.]+\.tsl\.belgium\.be\.tslprobe)\.(?P<measure>responsetime|result)$')
		self.cache={}
		self.running=False
		print('tsl_state Starting')

	def compute_state(self,params):
		try:
			prefix=params['prefix']
			measure=params['measure']
	
			found_response_time =float(self.values['%s.responsetime' % (prefix)])
			found_result        =int(float(self.values['%s.result' % (prefix)]))

			if found_result!=0:
				self.put_with_comment(prefix,STATE_ALERT,'Invalid Result!')
				return

			if found_response_time>500:
				self.put_with_comment(prefix,STATE_ALERT,'Response Time > 500ms (But Still Valid Results)')
				return

			if found_response_time>250:
				self.put_with_comment(prefix,STATE_ALERT,'Response Time > 250ms (But Still Valid Results)')
				return
			
			self.put_with_comment(prefix,STATE_OK,'Valid Results Within 250ms')

		except KeyError:
			print("%s (%s) not complete yet" % (prefix,measure))

	def contribute(self,label,value):
		params=None
		try:
			params=self.cache[label]
		except KeyError:
			matches=self.regex.match(label)
			if matches:
				params=matches.groupdict()
				self.cache[label]=params
			else:
				# print("Negative Cache %s" % (label))
				self.cache[label]=None
		if params:
			self.compute_state(params)
		
if __name__=='__main__':
	TrustState(mcast_addr=('224.0.0.1',1249)).contribute_forever()
	
