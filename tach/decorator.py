import time
import socket

def _time(value, metric, config):
    print "---- Execution time: %s" % value

def _graphite(value, metric_label, config):
    sock = socket.socket()
    carbon_connection = (config['carbon_host'], config['carbon_port'])
    try:
        sock.connect(carbon_connection)
    except sock.error, e:
        print "Error connecting to graphite server on %s:%s" %\
                    carbon_connection
    #When wouldn't this be true?
    now = int(time.time())
    body = "%s %s %d\n" % (metric_label, value, now)
    sock.sendall(body)
