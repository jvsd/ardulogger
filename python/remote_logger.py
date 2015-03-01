import struct
import json
import socket
import zmq
import serial
import time
import numpy as np
import datetime as datetime

cont = zmq.Context()
sock = cont.socket(zmq.SUB)
sock.connect('tcp://192.168.0.150:5050')
sock.setsockopt(zmq.SUBSCRIBE,'')
log_file = open('ardupilot.log','a')

while(True):
	msg = sock.recv_json()
	json.dump(msg,log_file)
	log_file.write("\n")
