# Tach

## Example instrumentation:

### For the API, created in tach-api.conf

    [notifier:statsd]
    driver = tach.notifiers.StatsDNotifier
    host = <Your statsd host>
    port = <Your statsd port, probably 8125>

    [nova.api.openstack.api]
    module = nova.api.openstack.wsgi.Resource
    method = _process_stack
    metric = tach.metrics.ExecTime
    notifier = statsd
    app_path = tach_helper
    app = process_stack

### For compute, created in tach-compute.conf

    [notifier:statsd]
    driver = tach.notifiers.StatsDNotifier
    host = <your statsd host>
    port = <your statsd port, probably 8125>

    [nova.compute.queue_receive]
    module = nova.rpc.amqp.ProxyCallback
    method = _process_data
    metric = tach.metrics.ExecTime
    notifier = statsd
    app_path = tach_helper
    app = queue_receive

### For network, created in tach-network.conf

    [notifier:statsd]
    driver = tach.notifiers.StatsDNotifier
    host = <your statsd host>
    port = <your statsd port, probably 8125>

    [nova.compute.queue_receive]
    module = nova.rpc.amqp.ProxyCallback
    method = _process_data
    metric = tach.metrics.ExecTime
    notifier = statsd
    app_path = tach_helper
    app = network_queue_receive

### For sheduler, created in tach-scheduler.conf

    [notifier:statsd]
    driver = tach.notifiers.StatsDNotifier
    host = <your statsd host>
    port = <your statsd port, probably 8125>

    [nova.scheduler.queue_receive]
    module = nova.rpc.amqp.ProxyCallback
    method = _process_data
    metric = tach.metrics.ExecTime
    notifier = statsd
    app_path = tach_helper
    app = scheduler_queue_receive

### Set up the helper script, created in tach_helper.py

This is where things get a little messy, but that's the catch with trying to instrument something you don't want to modify directly...

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

### Finally, launch the above

    # Assumes you're in the nova dir already
    tach tach-api.conf ./bin/nova-api
    tach tach-compute.conf ./bin/nova-compute
    tach tach-scheduler.conf ./bin/nova-scheduler
    tach tach-network.conf ./bin/nova-network
