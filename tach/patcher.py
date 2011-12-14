import functools
import time

from tach import decorator
from tach import utils


def _decorate(method, metric, config, metric_label, app=None):
    decorator_name = "_%s" % metric
    metric_method = getattr(decorator, decorator_name)
    def _decorated(*args, **kwargs):
        label = None
        if app:
            args, kwargs, label = app(*args, **kwargs)
        t1 = time.time()
        result = method(*args, **kwargs)
        delta = time.time() - t1
        metric_method(delta, label or metric_label, config)
        return result

    _decorated.__name__ = method.__name__
    _decorated.__doc__ = method.__doc__
    return _decorated


def decorate_method(method_config, other_config):
    app_method = None
    module = method_config['module']
    func = method_config['method']
    metric = method_config['metric']
    metric_label = method_config['metric_label']
    app = method_config.get('app')
    if app:
        app_path = method_config.get('app_path')
        app_kls = utils.import_class_or_module(app_path)
        app_method = getattr(app_kls, app)

    kls = utils.import_class_or_module(module)
    method = _decorate(getattr(kls, func), metric, other_config,
                       metric_label, app=app_method)
    setattr(kls, func, method)


