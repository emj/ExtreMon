#!/usr/bin/python3
import zmq

context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect ("tcp://127.0.0.1:3000")
socket.setsockopt_unicode(zmq.SUBSCRIBE, '')
while True:
	print(str(socket.recv(),'utf-8'))

