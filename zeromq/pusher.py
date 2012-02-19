#!/usr/bin/python3
import zmq,time

context = zmq.Context()
socket = context.socket(zmq.PUSH)
socket.setsockopt(zmq.HWM, 100)
socket.connect ("tcp://127.0.0.1:2000")
sequence=0

shuttle=''
for i in range(0,128):
	shuttle+='be.apsu.test=42\n'

while True:
	socket.send(bytes('%sbe.apsu.test=%d' % (shuttle,sequence),'utf-8'));
	sequence+=1
	time.sleep(0.001)

