# Dirt simple usage with Nova:
    # create this in a config file

    [notifier:graphite]
    driver = tach.notifiers.GraphiteNotifier
    host = <host>
    port = <port>

    [nova.compute.queue_receive]
    module = nova.rpc.impl_kombu.ProxyCallback
    method = __call__
    metric = tach.metrics.ExecTime
    notifier = graphite
    app_path = tach_helper
    app = queue_receive

    # create this in a file called tach_helper.py in the same directory as the conf
    def queue_receive(*args, **kwargs):
        method = args[1].get('method')
        return args, kwargs, "nova.compute.queue_receive.%s" % method

    # Call this
    tach tach.conf ./bin/nova-compute
