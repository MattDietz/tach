import time
import socket

def _time(method, config, *args, **kwargs):
    t1 = time.time()
    result = method(*args, **kwargs)
    print "---- Execution time: %s" % str(time.time() - t1)
    return result

def _graphite(method, config, *args, **kwargs):
    t1 = time.time()
    result = method(*args, **kwargs)
    now = time.time()
    delta = now - t1

    sock = socket()
    carbon_connection = (config['carbon_host'], config['carbon_port'])
    try:
        sock.connect(carbon_connection)
    except sock.error, e:
        print "Error connecting to graphite server on %s:%s" %
                    carbon_connection
    lines.append("hurr.durr %s %d" % (delta, now))
    message = '\n'.join(lines) + '\n' #all lines must end in a newline
    sock.sendall(message)
    return result
