#!/usr/bin/python3
import zmq,time

context = zmq.Context()
socket = context.socket(zmq.PUSH)
socket.setsockopt(zmq.HWM, 100)
socket.connect ("tcp://127.0.0.1:2000")
while True:
	socket.send(bytes('be.apsu.test.two=2000','utf-8'));
	time.sleep(.01)

