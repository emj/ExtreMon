#!/usr/bin/python3
import socket,zmq,sys

class CollectdAdapter:
    def __init__(self,listen_addr,listen_port,cauldron,hwm=128):
        self.insocket=socket.socket(socket.AF_INET,socket.SOCK_DGRAM,socket.IPPROTO_UDP)
        self.insocket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        self.insocket.bind((listen_addr,int(listen_port)))
        self.context=zmq.Context()
        self.outsocket=self.context.socket(zmq.PUSH)
        self.outsocket.setsockopt(zmq.HWM,int(hwm))
        self.outsocket.connect(cauldron)

    def adapt(self):
        while True:
            self.outsocket.send(self.insocket.recv(16384))

if __name__=='__main__':
    try:
        CollectdAdapter(**dict([arg.split('=') for arg in sys.argv[1:]])).adapt()
    except Exception as ex:
        print(repr(ex))
        print
        print("Usage  : collectd_adapter.py listen_addr=<listen_addr> listen_port=<listen_port> cauldron=<cauldron_endpoint> hwm=<push_hwm>]")
        print("Example: collectd_adapter.py listen_addr=127.0.0.1 listen_port=1248 cauldron=tcp://127.0.0.1:2000")
        print("Example: collectd_adapter.py listen_addr=127.0.0.1 listen_port=1248 cauldron=tcp://127.0.0.1:2000 hwm=128")
