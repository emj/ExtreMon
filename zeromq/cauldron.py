#!/usr/bin/python3
import zmq,time,sys,traceback
from threading import Thread,Lock
from queue  import Queue,Empty

class Cauldron(Thread):
    def __init__(self,prefix,pull_endpoint,pub_endpoint,context=zmq.Context(),pull_hwm=128,pub_hwm=128,shuttle_size_threshold=32768,shuttle_age_threshold=.1):
        Thread.__init__(self,name="Cauldron Publisher")
        self.daemon=True
        self.prefix=prefix
        self.context=context
        self.pull_endpoint=pull_endpoint
        self.pull_hwm=int(pull_hwm)
        self.pub_endpoint=pub_endpoint
        self.pub_hwm=int(pub_hwm)
        self.shuttle_size_threshold=int(shuttle_size_threshold)
        self.shuttle_age_threshold=float(shuttle_age_threshold)
        self.inq=Queue()
        self.buffer=bytearray()
        self.counter=0
        self.clear_buffer(time.time())

    def clear_buffer(self,now):
        del self.buffer[:]
        self.buffer_expiry=now+self.shuttle_age_threshold

    def flush_buffer(self,now):
        self.buffer.extend(bytes('%s.cauldron.timestamp=%.2f\n%s.cauldron.counter=%d\n%s.cauldron.qsize=%d\n' % (self.prefix,now,self.prefix,self.counter,self.prefix,self.inq.qsize()),'UTF-8'))
        self.pub_socket.send(self.buffer)
        self.clear_buffer(now)
        self.counter+=1

    def bubble(self):
        self.start()
        pull_socket=self.context.socket(zmq.PULL)
        pull_socket.setsockopt(zmq.HWM,self.pull_hwm)
        pull_socket.bind(self.pull_endpoint)
        while True:
            self.inq.put(pull_socket.recv())

    def run(self):
        self.pub_socket=self.context.socket(zmq.PUB)
        self.pub_socket.setsockopt(zmq.HWM,self.pub_hwm)
        self.pub_socket.bind(self.pub_endpoint)
        self.running=True
        while self.running:
            try:
                self.buffer.extend(self.inq.get(timeout=self.shuttle_age_threshold))
            except Empty:
                print("inq empty",file=sys.stderr)

            now=time.time()
            if(now>=self.buffer_expiry):
                print("flushing because buffer too old",file=sys.stderr)
                self.flush_buffer(now)
                continue

            if(len(self.buffer)>=self.shuttle_size_threshold):
                print("flushing because buffer too full",file=sys.stderr)
                self.flush_buffer(now)
                continue


if __name__=='__main__':
    try:
        Cauldron(**dict([arg.split('=') for arg in sys.argv[1:]])).bubble()
    except Exception as ex:
        traceback.print_exc(file=sys.stderr)
        print(file=sys.stderr)
        print("Usage  : cauldron prefix=<prefix> pull_endpoint=<pull_endpoint> pub_endpoint=<pub_endpoint> [pull_hwm=<pull_hwm>] [pub_hwm=<pub_hwm>] [shuttle_size_threshold] [shuttle_age_threshold]",file=sys.stderr)
        print("Example: cauldron prefix=be.apsu.mon pull_endpoint=tcp://127.0.0.1:2000 pub_endpoint=tcp://127.0.0.1:3000",file=sys.stderr)
        print("Example: cauldron prefix=be.apsu.mon pull_endpoint=tcp://127.0.0.1:2000 pub_endpoint=tcp://127.0.0.1:3000 pull_hwm=128 pub_hwm=128 shuttle_size_threshold=32768,shuttle_age_threshold=.1",file=sys.stderr)
