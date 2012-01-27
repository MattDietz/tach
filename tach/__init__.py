from ConfigParser import SafeConfigParser

from tach import notifiers
from tach import patcher


def load_config(config_path):
    """Load configuration from config_path."""

    config = SafeConfigParser()
    config.read(config_path)
    to_decorate = []
    other_config = {'notifier': notifiers.PrintNotifier()}

    # Process the config
    for sec in config.sections():
        # Handle configuration for graphite
        if sec == 'graphite.config':
            other_config.update(carbon_host=config.get('graphite.config',
                                                       'carbon_host'),
                                carbon_port=config.getint('graphite.config',
                                                          'carbon_port'),
                                notifier=notifiers.GraphiteNotifier())

        # Handle configuration for statsd
        elif sec == 'statsd.config':
            other_config.update(statsd_host=config.get('statsd.config',
                                                       'statsd_host'),
                                statsd_port=config.getint('statsd.config',
                                                          'statsd_port'),
                                notifier=notifiers.StatsDNotifier())

        # Handle configuration for watching a method
        else:
            method_dict = {'module': config.get(sec, 'module'),
                           'method': config.get(sec, 'method'),
                           'metric': config.get(sec, 'metric')}

            # Extract app translator
            if config.has_option(sec, 'app'):
                method_dict['app'] = config.get(sec, 'app')
                method_dict['app_path'] = config.get(sec, 'app_path')

            # Save the desired label
            method_dict['metric_label'] = sec

            # Extract additional specific configuration
            method_dict['additional'] = {}
            for key in config.options(sec):
                # Skip options we've already handled
                if key in method_dict:
                    continue

                method_dict['additional'][key] = config.get(sec, key)

            to_decorate.append(method_dict)

    return to_decorate, other_config


def patch(config_path):
    """Patch application based on configuration."""

    to_decorate, other_config = load_config(config_path)
    for method_config in to_decorate:
        patcher.decorate_method(method_config, other_config)
