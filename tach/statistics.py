import time


class Statistic(object):
    """Base class for all statistics.

    Subclasses must implement __call__(); it should take no arguments,
    stop the collection, and return the final statistic value.
    """

    def __init__(self, config):
        """Initialize the statistic from the configuration."""

        # By default, do nothing
        pass

    def start(self):
        """Start collecting the statistic."""

        # By default, do nothing
        pass


class ExecTime(Statistic):
    """Collect execution time statistics."""

    type = 'exec_time'

    def start(self):
        """Start collecting the statistic."""

        self.start_time = time.time()

    def __call__(self):
        """Finish collecting the statistic and return the value."""

        return time.time() - self.start_time


class Increment(Statistic):
    """Collect increment/decrement statistics."""

    type = 'increment'

    def __init__(self, config):
        """Initialize the statistic from the configuration."""

        self.increment = config.get('increment', 1)

    def __call__(self):
        """Finish collecting the statistic and return the value."""

        return self.increment
