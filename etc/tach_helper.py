# create this in a file called tach_helper.py in the same directory as the conf
def queue_receive(*args, **kwargs):
    method = args[2]
    return args, kwargs, "nova.compute.%s" % method

def network_queue_receive(*args, **kwargs):
    method = args[2]
    return args, kwargs, "nova.network.%s" % method

def scheduler_queue_receive(*args, **kwargs):
    method = args[2]
    return args, kwargs, "nova.scheduler.%s" % method

def process_stack(*args, **kwargs):
    resource = args[0]
    req = args[1].__dict__
    method = ".%s" % req['environ']['REQUEST_METHOD']
    path = '.'.join(req['environ']['PATH_INFO'].split('/')[:3])
    action = ".%s" % req['environ']['wsgiorg.routing_args'][1]['action']
    if action:
        key = 'nova.api%s%s%s' % (path, action, method)
    else:
        key = 'nova.api%s%s%s' % (path, method)
    return args, kwargs, key

