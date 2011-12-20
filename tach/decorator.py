import time
import socket

def _connect_and_send(host, port, body):
    sock.sendall(body)

def timer(value, metric, config):
    print "---- Execution time: %s" % value

def graphite(value, metric_label, config):
    sock = socket.socket()
    now = int(time.time())
    body = "%s %s %d\n" % (metric_label, value, now)
    try:
        sock.connect((config['carbon_host'],
                      config['carbon_port']))
        sock.sendall(body)
    except socket.error, e:
        print "Error connecting to graphite server %s" % e

def statsd_timer(value, metric_label, config):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    body = "%s:%s|ms" % (metric_label, value*1000.0)
    try:
        sock.connect((config['statsd_host'],
                      config['statsd_port']))
        sock.sendall(body)
    except socket.error, e:
        print "Error connecting to statsd server %s" % e
