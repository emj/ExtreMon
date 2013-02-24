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

import					time,re
from threading	import 	Lock
from extremon	import 	CauldronContributor

STATE_OK=0
STATE_WARNING=1
STATE_ALERT=2
STATE_MISSING=3
STATE_TACKLED=4


class Thresholds:
	def __init__(self,name=None,ok_text=None,warning_threshold=None,warning_text=None,alert_threshold=None,alert_text=None):
		self.name=name
		self.ok_text=ok_text
		self.warning_threshold=warning_threshold
		self.warning_text=warning_text
		self.alert_threshold=alert_threshold
		self.alert_text=alert_text

class LowThresholds(Thresholds):
	def __init__(self,name=None,ok_text=None,warning_threshold=None,warning_text=None,alert_threshold=None,alert_text=None):
		Thresholds.__init__(self,name,ok_text,warning_threshold,warning_text,alert_threshold,alert_text)

	def evaluate(self,value):
		if value < self.alert_threshold:
			return (STATE_ALERT,self.alert_text)
		elif value < self.warning_threshold:
			return (STATE_WARNING,self.warning_text)
		else:
			return (STATE_OK,self.ok_text)

class HighThresholds(Thresholds):
	def __init__(self,name=None,ok_text=None,warning_threshold=None,warning_text=None,alert_threshold=None,alert_text=None):
		Thresholds.__init__(self,name,ok_text,warning_threshold,warning_text,alert_threshold,alert_text)

	def evaluate(self,value):
		if value > self.alert_threshold:
			return (STATE_ALERT,self.alert_text)
		elif value > self.warning_threshold:
			return (STATE_WARNING,self.warning_text)
		else:
			return (STATE_OK,self.ok_text)

class Worst:
	def __init__(self,*conditions):
		self.conditions=conditions

	def add(self,term):
		self.conditions.add(term)

	def evaluate(self,value):
		worst_state=STATE_OK
		worst_text='OK'
		for condition in self.conditions:
			(state,state_text)=condition.evaluate(value)
			if state>=worst_state:
				worst_state=state
				worst_text=state_text
		return (worst_state,worst_text)


class State(CauldronContributor):
	def __init__(self,mcast_addr,patterns,max_missing):
		CauldronContributor.__init__(self,mcast_addr=mcast_addr,suffix='state');
		self.patterns=patterns
		self.running=False
		self.last_seen={}
		self.last_seen_lock=Lock()
		self.max_missing=max_missing
		self.cache={}

	def contribute(self,label,value):
		with self.last_seen_lock:
			self.last_seen[label]=time.time()
		condition_found=None

		try:
			condition_found=self.cache[label]
		except KeyError:
			for (pattern,condition) in patterns:
				if pattern.match(label):
					condition_found=condition
					break
			self.cache[label]=condition_found
			print("cached %s" % (label))

		if condition_found:
			(state,state_text)=condition_found.evaluate(float(value))
			self.put_with_comment(label,state,state_text)
		
if __name__=='__main__':
	patterns=[(re.compile("be.fedict.eid.([a-z0-9.]+).tslprobe.validityleft$"),LowThresholds(name='Validity Time Left',ok_text='Still Valid For 6 Weeks Or More',warning_threshold=3628800,warning_text='Less Than 6 Weeks Of Validity Left. Signing Ceremony Planning Required.',alert_threshold=1209600,alert_text='Valid For Less Than 2 Weeks! If No Signing Ceremony Occurred, Validity Will Expire Before Replacement!!')),
			  (re.compile("be.fedict.eid.([a-z0-9.-]+).df.([a-z-]+).df_complex.(free|reserved|used).percentage$"),LowThresholds(name='Free Disk Space',ok_text='More Than 60% Free Space',warning_threshold=60,warning_text='Less Than 60% Free Space',alert_threshold=30,alert_text='Less Than 30% Free Space!'))]
	State(mcast_addr=('224.0.0.1',1249),patterns=patterns,max_missing=10).contribute_forever()
