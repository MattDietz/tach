from tach import config


def patch(config_path):
    """Patch application based on configuration."""

    # Load the configuration
    cfg = config.Config(config_path)

    # Install all the metric gatherers
    cfg.install()

    # Return the configuration
    return cfg
