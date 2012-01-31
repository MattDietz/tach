import time


class Metric(object):
    """Base class for all metrics.

    Subclasses must implement __call__(); it should take as an
    argument the return value of the start() method (by default,
    None); stop the collection; and return the final metric value.
    Subclasses must also set the `vtype` class attribute, to identify
    the type of the result; this will be used by notifiers to format
    the value correctly.
    """

    def __init__(self, config):
        """Initialize the metric from the configuration."""

        # By default, do nothing
        pass

    def start(self):
        """Start collecting the metric."""

        # By default, do nothing
        pass


class DebugMetric(Metric):
    """Debugging metric.

    Use the "real_metric" configuration option to specify the metric
    to wrap.
    """

    def __init__(self, config):
        """Initialize the metric from the configuration."""

        # First, figure out the real metric
        self.metric_name = config['real_metric']

        # Get the class and instantiate it
        cls = utils.import_class_or_module(self.metric_name)
        self.metric = cls(config)
        self.vtype = self.metric.vtype

    def start(self):
        """Start collecting the metric."""

        # Collect the starting statistic from the underlying metric
        value = self.metric.start()

        # Output debugging information
        print "*" * 80
        print "Debug: Starting metric %r: %r" % (self.metric_name, value)
        print "*" * 80

        return value

    def __call__(self, value):
        """Finish collecting the metric and return the value."""

        # Collect the ending statistic from the underlying metric
        end_value = self.metric(value)

        # Output debugging information
        print "*" * 80
        print "Debug: Ending metric %r: %r/%r" % (self.metric_name, value,
                                                  end_value)
        print "*" * 80

        return end_value


class ExecTime(Metric):
    """Collect execution time metrics."""

    vtype = 'exec_time'

    def start(self):
        """Start collecting the metric."""

        return time.time()

    def __call__(self, value):
        """Finish collecting the metric and return the value."""

        return time.time() - value


class Increment(Metric):
    """Collect increment/decrement metrics."""

    vtype = 'increment'

    def __init__(self, config):
        """Initialize the metric from the configuration."""

        self.increment = config.get('increment', 1)

    def __call__(self, value):
        """Finish collecting the metric and return the value."""

        return self.increment
