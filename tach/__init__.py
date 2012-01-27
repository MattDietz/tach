from tach import config


def patch(config_path):
    """Patch application based on configuration."""

    # Simply loading the configuration will do the trick
    return config.Config(config_path)
