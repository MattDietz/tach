from ConfigParser import SafeConfigParser

from tach import patcher

def _load_config(config_path):
    config = SafeConfigParser()
    config.read(config_path)
    to_decorate = []
    other_config = None
    for sec in config.sections():
        if sec.startswith('measured.'):
            module = config.get(sec, 'module')
            method = config.get(sec, 'method')
            metric = config.get(sec, 'metric')
            to_decorate.append((module, method, metric))
    if config.has_section('graphite.config'):
        other_config = {'carbon_host': config.get('graphite.config',
                                                  'carbon_host'),
                        'carbon_port': config.getint('graphite.config',
                                               'carbon_port')}
    return to_decorate, other_config

def patch(config_path):
    to_decorate, other_config = _load_config(config_path)
    for k, m, e in to_decorate:
        patcher.decorate_method(k, m, e, other_config)
