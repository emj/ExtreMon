#!/usr/bin/python3
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
  

