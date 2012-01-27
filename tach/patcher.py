import functools
import time

from tach import statistics
from tach import utils


def get_statistic(metric, config):
    """Get an instance implementing the statistic."""

    if metric in ('timer', 'graphite', 'statsd_timer'):
        # These all handled execution times
        return statistics.ExecTime({})
    elif metric == 'statsd_incr':
        # This was an increment operation
        return statistics.Increment(dict(increment=1))
    elif metric == 'statsd_decr':
        # This was a decrement operation
        return statistics.Increment(dict(increment=-1))
    else:
        # New-style config; select appropriate statistic
        cls = utils.import_class_or_module(metric)
        return cls(config)


def _decorate(method, metric, notifier, config, additional,
              metric_label, app=None):
    """Decorate a method and collect the desired statistics."""

    # Get the statistics object
    statistic = get_statistic(metric, additional)

    @functools.wraps(method)
    def _decorated(*args, **kwargs):
        # Handle app translation
        label = None
        if app:
            args, kwargs, label = app(*args, **kwargs)

        # Run a method, bracketing with stastics collection and
        # notification
        statistic.start()
        result = method(*args, **kwargs)
        notifier(statistic(), label or metric_label, config)

        return result

    return _decorated


def decorate_method(method_config, other_config):
    """Decorate a method specified by configuration."""

    # Grab all the data we need
    app_method = None
    module = method_config['module']
    func = method_config['method']
    metric = method_config['metric']
    notifier = other_config['notifier']
    metric_label = method_config['metric_label']
    app = method_config.get('app')
    if app:
        app_path = method_config.get('app_path')
        app_kls = utils.import_class_or_module(app_path)
        app_method = getattr(app_kls, app)
    additional = method_config.get('additional', {})

    # Find the method and decorate it
    kls = utils.import_class_or_module(module)
    method = _decorate(getattr(kls, func), metric, notifier, other_config,
                       additional, metric_label, app=app_method)
    setattr(kls, func, method)


