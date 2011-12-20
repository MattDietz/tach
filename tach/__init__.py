from ConfigParser import SafeConfigParser

from tach import patcher

def load_config(config_path):
    config = SafeConfigParser()
    config.read(config_path)
    to_decorate = []
    other_config = None
    for sec in config.sections():
        if not sec == 'graphite.config' and not sec == 'statsd.config':
            method_dict = {'module': config.get(sec, 'module'),
                           'method': config.get(sec, 'method'),
                           'metric': config.get(sec, 'metric')}
            if config.has_option(sec, 'app'):
                method_dict['app'] = config.get(sec, 'app')
                method_dict['app_path'] = config.get(sec, 'app_path')
            method_dict['metric_label'] = sec
            to_decorate.append(method_dict)
    if config.has_section('graphite.config'):
        other_config = {'carbon_host': config.get('graphite.config',
                                                  'carbon_host'),
                        'carbon_port': config.getint('graphite.config',
                                                     'carbon_port')}
    if config.has_section('statsd.config'):
        other_config = {'statsd_host': config.get('statsd.config',
                                                  'statsd_host'),
                        'statsd_port': config.getint('statsd.config',
                                                     'statsd_port')}
    return to_decorate, other_config

def patch(config_path):
    to_decorate, other_config = load_config(config_path)
    for method_config in to_decorate:
        patcher.decorate_method(method_config, other_config)
