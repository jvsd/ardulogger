#export PYTHONPATH=/Users/jamesd/Dropbox/Developer/virtualenv/mavlink/mavlink
#

import sys, os

from pymavlink import mavlinkv10 as mavlink
import struct
import socket
import zmq
import serial
import time
import numpy as np
import datetime as datetime


class fifo(object):
    def __init__(self):
        self.buf = []
    def write(self, data):
        self.buf += data
        return len(data)
    def read(self):
        return self.buf.pop(0)

class serial_publisher(object):
    def __init__(self,s_type,zmq_context,port,serial_port,serial_baud):
        self.s_type=s_type
        self.zmq_context = zmq_context
        self.server=zmq_context.socket(zmq.REP)
        self.data_server = zmq_context.socket(zmq.PUB)
        self.data_server.bind('tcp://*:'+port)
        self.server.bind('tcp://*:'+str(int(port)+1))
        self.poller = zmq.Poller()
        self.poller.register(self.server,zmq.POLLIN)

        self.marker=zmq_context.socket(zmq.SUB)
        self.marker.setsockopt(zmq.SUBSCRIBE,'')
        self.marker.connect('tcp://localhost:5001')
        self.mark_poller = zmq.Poller()
        self.mark_poller.register(self.marker,zmq.POLLIN)
        self.mark = 0.0
	self.error_lines = 0
	self.sent_lines = 0
        self.time = 0

        
        if s_type == 0: # Serial port
            self.ser = serial.Serial(
                    port = serial_port,
                    baudrate = serial_baud,
                    timeout=0,
                    xonxoff=False,
                    rtscts=False,
                    dsrdtr=False
                )
        elif s_type == 1:
            self.sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            self.sock.connect(("192.168.0.113",2000))
        self.fifo = fifo()
        self.mav = mavlink.MAVLink(self.fifo)
        self.buffer = ''
        self.log_file = open('ardupilot.log','a')

    def run(self):
        self.time = datetime.datetime.now().isoformat()
        if self.s_type==0:
            self.buffer=self.buffer + self.ser.read(self.ser.inWaiting())
        elif self.s_type==1:
            print 'waiting to recv...'
            self.buffer=self.buffer + self.sock.recv(1024)

        if len(self.buffer) > 0 and self.sent_lines < 10:
            print self.buffer
        try:
            messages = self.mav.parse_buffer(self.buffer)
            if messages:
                for msg in messages:
                    socks = dict(self.poller.poll(0))
                    if socks:
                        if socks.get(self.server) == zmq.POLLIN:
                            self.server.recv()
                            self.server.send(msg.to_json())

                    self.sent_lines+=1
                    self.log_data(msg)
                    self.data_server.send(msg.to_json())
                    print msg.get_fieldnames()
        except:
            self.error_lines+=1


        if len(self.buffer) >= 64:
            self.buffer = self.buffer[-65:-1]
        else:
            self.buffer = ''

        print "received: " + self.sent_lines + 'In buffer: ' + str(len(self.buffer))


    def log_data(self,mavlink_msg):
        s = dict(self.mark_poller.poll(0))
        if s:
            if s.get(self.marker) == zmq.POLLIN:
                self.mark = float(self.marker.recv())

        j = mavlink_msg.to_json()
        self.log_file.write(j)
        self.log_file.write("\t%f\t" % self.mark)
        self.log_file.write(self.time + "\n")



#Requires (1)scriptname (2)zmq_port (3)serial_port (4)serial_baud
if __name__=='__main__':
    if len(sys.argv) != 5:
        print 'input arguments are s_type zmq_port serial_port serial_baud'
        sys.exit()
    else:
        s_type = int(sys.argv[1])
        zmq_port = sys.argv[2]
        serial_port = sys.argv[3]
        serial_baud = sys.argv[4]
        
    cont = zmq.Context()
    sp = serial_publisher(s_type,cont,zmq_port,serial_port,serial_baud)
    while(True):
        sp.run()
