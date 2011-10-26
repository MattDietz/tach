import datetime
import functools

from tach import decorator
from tach import utils


def _decorate(method, metric, config):
    metric_method = None
    decorator_name = "_%s" % metric
    metric_method = getattr(decorator, decorator_name)
    args = {'method': method,
            'config': config}
    metric_method = functools.partial(metric_method, **args)
    metric_method.__name__ = method.__name__
    metric_method.__doc__ = method.__doc__
    return metric_method

def decorate_method(klass_path, method_name, metric, config):
    kls = utils.import_class(klass_path)
    method = _decorate(getattr(kls, method_name), metric, config)
    setattr(kls, method_name, method)


