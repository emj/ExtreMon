#!/usr/bin/python3
import zmq
from extremon import CauldronSubscriber

class CauldronPrinter:
    def __init__(self,context,endpoint):
        self.receiver=CauldronSubscriber(context,endpoint,self)

    def recv(self,shuttle):
        print(shuttle)
        print("<<<<")

    def run(self):
        self.receiver.receive_as_strings_forever()

if __name__=='__main__':
    cf=CauldronPrinter(zmq.Context(),"tcp://127.0.0.1:3000")
    cf.run()
