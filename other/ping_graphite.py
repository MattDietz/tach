import socket
import sys
import time

sys.path.insert(0, '../')

def ping_graphite(host, port, metric, value):
    sock = socket.socket()
    carbon_connection = (host, port)
    try:
        sock.connect(carbon_connection)
    except socket.error, e:
        print "Error connecting to graphite server on %s:%s" %\
                    carbon_connection
    #When wouldn't this be true?
    now = int(time.time())
    lines = []
    lines.append("%s %s %d\n" % (metric, value, now))
    body = '\n'.join(lines) + '\n'
    sock.sendall(body)

def ping(value):
    ping_graphite('173.203.110.242', 2003, 'derp.hoobahurr', value)
