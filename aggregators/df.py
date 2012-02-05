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

import 					re
from extremon	import	CauldronContributor

class DF(CauldronContributor):
	def __init__(self,mcast_addr):
		CauldronContributor.__init__(self,mcast_addr=mcast_addr,suffix='percentage')
		self.regex=re.compile('^(?P<prefix>[a-z0-9.-]+)\\.df\\.(?P<mountpoint>[a-z0-9-]+)\\.df_complex\\.(?P<measure>free|reserved|used)\\.value$')
		self.cache={}
		self.running=False
		print("DF Starting")

	def compute_percentages(self,params):
		try:
			prefix=params['prefix']
			mountpoint=params['mountpoint']
			free=float(self.values['%s.df.%s.df_complex.free.value' % (prefix,mountpoint)])
			reserved=float(self.values['%s.df.%s.df_complex.reserved.value' % (prefix,mountpoint)])
			used=float(self.values['%s.df.%s.df_complex.used.value' % (prefix,mountpoint)])
			total=free+reserved+used
			self.put('%s.df.%s.df_complex.free' % (prefix,mountpoint),str((free/total)*100.0))
			self.put('%s.df.%s.df_complex.reserved' % (prefix,mountpoint),str((reserved/total)*100.0))
			self.put('%s.df.%s.df_complex.used' % (prefix,mountpoint),str((used/total)*100.0))
		except KeyError:
			print("%s (%s) not complete yet" % (prefix,mountpoint))

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
				self.cache[label]=None
		if params:
			self.compute_percentages(params)
		
if __name__=='__main__':
	DF(mcast_addr=('224.0.0.1',1249)).contribute_forever()
	

