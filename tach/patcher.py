import datetime

from tach import decorator
from tach import utils


def _decorate(method, metric):
    metric_method = None
    decorator_name = "_%s" % metric
    metric_method = getattr(decorator, decorator_name)

    metric_method.__name__ = method.__name__
    metric_method.__doc__ = method.__doc__
    return metric_method

def decorate_method(klass_path, method_name, metric):
    kls = utils.import_class(klass_path)
    method = _decorate(getattr(kls, method_name), metric)
    setattr(kls, method_name, method)


