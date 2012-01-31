import time


class Metric(object):
    """Base class for all metrics.

    Subclasses must implement __call__(); it should take as an
    argument the return value of the start() method (by default,
    None); stop the collection; and return the final metric value.
    """

    def __init__(self, config):
        """Initialize the metric from the configuration."""

        # By default, do nothing
        pass

    def start(self):
        """Start collecting the metric."""

        # By default, do nothing
        pass


class ExecTime(Metric):
    """Collect execution time metrics."""

    type = 'exec_time'

    def start(self):
        """Start collecting the metric."""

        return time.time()

    def __call__(self, value):
        """Finish collecting the metric and return the value."""

        return time.time() - value


class Increment(Metric):
    """Collect increment/decrement metrics."""

    type = 'increment'

    def __init__(self, config):
        """Initialize the metric from the configuration."""

        self.increment = config.get('increment', 1)

    def __call__(self, value):
        """Finish collecting the metric and return the value."""

        return self.increment
