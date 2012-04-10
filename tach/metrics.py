import logging
import time

from tach import utils


LOG = logging.getLogger(__name__)


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
        self._bump_transaction_id = int(
                                    config.get('bump_transaction_id', 0)) > 0

    @property
    def bump_transaction_id(self):
        return self._bump_transaction_id

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
        super(DebugMetric, self).__init__(config)

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
        LOG.debug("DebugMetric: Starting metric %r: %r" %
                  (self.metric_name, value))

        return value

    def __call__(self, value):
        """Finish collecting the metric and return the value."""

        # Collect the ending statistic from the underlying metric
        end_value = self.metric(value)

        # Output debugging information
        LOG.debug("DebugMetric: Ending metric %r: %r/%r" %
                  (self.metric_name, value, end_value))

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
    """Collect increment/decrement metrics.

    Use the "increment" configuration option to specify the increment.
    If not specified, it defaults to "1".
    """

    vtype = 'increment'

    def __init__(self, config):
        """Initialize the metric from the configuration."""
        super(Increment, self).__init__(config)
        self.increment = int(config.get('increment', 1))

    def __call__(self, value):
        """Finish collecting the metric and return the value."""

        return self.increment
