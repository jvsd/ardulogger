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
    def __init__(self,s_type,zmq_context,port,serial_port,serial_baud,udp_client,udp_port):
        self.s_type=s_type
        self.zmq_context = zmq_context
        self.server=zmq_context.socket(zmq.REP)
        self.data_server = zmq_context.socket(zmq.PUB)
        self.data_server.bind('tcp://*:'+port)
        self.server.bind('tcp://*:'+str(int(port)+1))
        self.poller = zmq.Poller()
        self.poller.register(self.server,zmq.POLLIN)
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.addr =(str(udp_client),int(udp_port))


        self.marker=zmq_context.socket(zmq.SUB)
        self.marker.setsockopt(zmq.SUBSCRIBE,'')
        self.marker.connect('tcp://192.168.0.114:4999')
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
        elif s_type == 2:
            self.subscriber = self.zmq_context.socket(zmq.SUB)
            self.subscriber.setsockopt(zmq.SUBSCRIBE,'')
            self.subscriber.connect('tcp://192.168.0.150:4002')

        self.fifo = fifo()
        self.mav = mavlink.MAVLink(self.fifo)
        self.buffer = ''
        self.log_file = open('ardupilot.log','a')

    def run(self):
        self.time = datetime.datetime.now().isoformat()
        s = dict(self.mark_poller.poll(0))
        if s:
            if s.get(self.marker) == zmq.POLLIN:
                self.mark = float(self.marker.recv())
                print "CHANGED MARKER"
        if self.s_type==0:
            temp_buffer = self.ser.read(self.ser.inWaiting())
            self.udp_sock.sendto(temp_buffer,self.addr)
            self.buffer = self.buffer + temp_buffer
        elif self.s_type==1:
            print 'waiting to recv...'
            self.buffer=self.buffer + self.sock.recv(1024)
        elif self.s_type==2:
            messages = self.subscriber.recv_multipart()
            self.time = messages[0]
            temp_buffer = messages[1]
            self.udp_sock.sendto(temp_buffer,self.addr)
            self.buffer = self.buffer + temp_buffer

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
                    print msg.get_fieldnames()
                    #self.log_data(msg)
                    msgd = msg.to_dict()
                    msgd['ctime'] = self.time
                    msgd['mark'] = self.mark
                    self.data_server.send_json(msgd)
                    print 'Mark:'+str(self.mark)
        except:
            print 'caught exception', sys.exc_info()[0]
            self.error_lines+=1


        if len(self.buffer) >= 64:
            self.buffer = self.buffer[-65:-1]
        else:
            self.buffer = ''

        #print "received: " + str(self.sent_lines) + 'In buffer: ' + str(len(self.buffer))


    def log_data(self,mavlink_msg):

        j = mavlink_msg.to_json()
        self.log_file.write(j)
        self.log_file.write("\t%f\t" % self.mark)
        self.log_file.write(self.time + "\n")



#Requires (1)scriptname (2)zmq_port (3)serial_port (4)serial_baud
if __name__=='__main__':
    if len(sys.argv) != 7:
        print 'input arguments are s_type zmq_port serial_port serial_baud udp_client udp_port'
        sys.exit()
    else:
        s_type = int(sys.argv[1])
        zmq_port = sys.argv[2]
        serial_port = sys.argv[3]
        serial_baud = sys.argv[4]
        udp_client = sys.argv[5]
        udp_port = sys.argv[6]
        
    cont = zmq.Context()
    sp = serial_publisher(s_type,cont,zmq_port,serial_port,serial_baud,udp_client,udp_port)
    while(True):
        sp.run()
