#!/usr/bin/env python3

#   ExtreMon Project
#   Copyright (C) 2009-2013 Frank Marien
#   frank@apsu.be
#
#   This file is part of ExtreMon.
#
#   ExtreMon is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   ExtreMon is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with ExtreMon.  If not, see <http://www.gnu.org/licenses/>.
#

from extremon import CauldronReceiver

class CauldronDump(CauldronReceiver):
  def __init__(self,mcast_addr):
    CauldronReceiver.__init__(self,mcast_addr,self)
    self.running=False
    print("Dump Starting")

  def handle_shuttle(self,shuttle):
    print("\n".join("%s=%s" % (label,value) for (label,value) in shuttle))

if __name__=='__main__':
  CauldronDump(mcast_addr=('224.0.0.1',1249)).receive_forever()

