import datetime

from tach import utils


def _decorate(method, metric):
    def _datetime(*args, **kwargs):
        t1 = datetime.datetime.utcnow()
        result = method(*args, **kwargs)
        print "---- Execution time: %s" % str(datetime.datetime.utcnow() - t1)
        return result
    
    metric_method = None
    if metric == 'datetime':
        metric_method = _datetime

    metric_method.__name__ = method.__name__
    metric_method.__doc__ = method.__doc__
    return metric_method

def decorate_method(klass_path, method_name, metric):
    kls = utils.import_class(klass_path) 
    method = _decorate(getattr(kls, method_name), metric)
    setattr(kls, method_name, method)


