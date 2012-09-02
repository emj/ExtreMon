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
from extremon	import	CauldronLabelFilter

class LabelCleanupFilter(CauldronLabelFilter):

	def __init__(self):
		self.ip_address_pattern=re.compile(r"(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)")
		self.ip_address_subst=r'\1-\2-\3-\4'
		CauldronLabelFilter.__init__(self,in_addr=('224.0.0.1',1248),out_addr=('224.0.0.1',1249))
		print("LabelCleanupFilter Starting..")

	def filter_label(self,label):
		print("new label [%s]" % (label))
		new_label=re.sub('[^a-z0-9._/;:-]+','',label.lower())
		new_label=self.ip_address_pattern.sub(self.ip_address_subst,new_label)
		return new_label

if __name__=='__main__':
	LabelCleanupFilter().filter_forever()
	
