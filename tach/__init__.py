from ConfigParser import SafeConfigParser

from tach import patcher

def _load_config(config_path):
    config = SafeConfigParser()
    config.read(config_path)
    to_decorate = []
    for sec in config.sections():
        module = config.get(sec, 'module')
        method = config.get(sec, 'method')
        metric = config.get(sec, 'metric')
        to_decorate.append((module, method, metric))
    return to_decorate

def patch(config_path):
    for k, m, e in _load_config(config_path):
        patcher.decorate_method(k, m, e)
