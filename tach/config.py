import ConfigParser
import inspect
import functools

from tach import metrics
from tach import notifiers
from tach import utils


class Config(object):
    """Represent a tach configuration."""

    def __init__(self, config_path):
        """Initialize a tach configuration.

        Reads the configuration from the config_path.
        """

        # Initialize a few things
        self.methods = {}
        self.notifiers = {}

        # Parse the configuration file
        config = ConfigParser.SafeConfigParser()
        config.read(config_path)

        # Process configuration
        for sec in config.sections():
            if (sec in ('graphite.config', 'statsd.config') or
                sec.startswith('notifier:')):
                # Make a notifier
                notifier = Notifier(self, sec, config.items(sec))

                # Add it to the recognized notifiers
                self.notifiers.setdefault(notifier.label, notifier)

                # If it's a default notifier, add it as such
                self.notifiers.setdefault(None, notifier)
            else:
                # Make a method
                method = Method(self, sec, config.items(sec))

                # Add it to the recognized methods
                self.methods.setdefault(method.label, method)

        # Do we have a default notifier?
        self.notifiers.setdefault(None, Notifier(self, '', []))

    def notifier(self, name):
        """Retrieve a notifier driver given its name."""

        # Look up the notifier
        notifier = self.notifiers.get(name, self.notifiers.get(None))

        # Return the driver
        return notifier.driver

    def _methods(self, methods):
        """Return a list of method objects given their names."""

        # If we were given none, assume all
        if not methods:
            return self.methods.values()
        else:
            return [self.methods[meth] for meth in methods
                    if meth in self.methods]

    def install(self, *methods):
        """Install the given metric gatherers."""

        # Call their install methods
        for meth in self._methods(methods):
            meth.install()

    def uninstall(self, *methods):
        """Uninstall the given metric gatherers."""

        # Call their uninstall methods
        for meth in self._methods(methods):
            meth.uninstall()


class Notifier(object):
    """Represent a notifier."""

    def __init__(self, config, label, items):
        """Initialize a method wrapped with metric collection.

        :param config: The global configuration.
        :param label: The label to use to identify the notifier.
        :param items: A list of key, value pairs giving the
                      configuration for setting up the notifier.
        """

        self.config = config
        self.default = False
        self._driver = None
        self._driver_cache = None
        self.additional = {}

        # Parse the label for backwards compatibility
        if label == 'graphite.config':
            # Graphite driver
            self.default = True
            self.label = 'graphite'
            self._driver = notifiers.GraphiteNotifier
            self._driver_cache = self._driver(self,
                                              'carbon_host', 'carbon_port')
        elif label == 'statsd.config':
            # StatsD driver
            self.default = True
            self.label = 'statsd'
            self._driver = notifiers.StatsDNotifier
            self._driver_cache = self._driver(self,
                                              'statsd_host', 'statsd_port')
        else:
            # New-style configuration
            self.label = label.partition(':')[-1]
            if not label:
                # No label makes this the default
                self.default = True

        # Process configuration
        for option, value in items:
            if option == 'driver':
                # Get the driver, but only if we don't have one
                if not self._driver:
                    self._driver = utils.import_class_or_module(value)

            # Other options go into additional
            else:
                self.additional[option] = value

        # Default driver to the print notifier
        if not self._driver:
            self._driver = notifiers.PrintNotifier

    def __getitem__(self, key):
        """Allow access to additional configuration."""

        return self.additional[key]

    @property
    def driver(self):
        """Return an initialized notifier driver."""

        if not self._driver_cache:
            self._driver_cache = self._driver(self)

        return self._driver_cache


def _get_method(cls, name):
    """Introspect a class for a method and its kind.

    This is copied from the heart of inspect.classify_class_attrs(),
    with the difference that we're only concerned about a single
    attribute of the class.
    """

    mro = inspect.getmro(cls)

    # Try to get it from the class dict
    if name in cls.__dict__:
        raw_obj = cls.__dict__[name]
    else:
        raw_obj = getattr(cls, name)

    # Figure out where it came from
    homecls = getattr(raw_obj, "__objclass__", None)
    if homecls is None:
        # Search the dicts
        for base in mro:
            if name in base.__dict__:
                homecls = base
                break

    # Get the object again, in order to get it from the __dict__
    # instead of via getattr (if possible)
    if homecls is not None and name in homecls.__dict__:
        raw_obj = homecls.__dict__[name]

    # Also get via getattr
    obj = getattr(cls, name)

    # Classify the object
    if isinstance(raw_obj, staticmethod) or name == '__new__':
        kind = "static method"
    elif isinstance(raw_obj, classmethod):
        kind = "class method"
    elif isinstance(raw_obj, property):
        kind = "property"
    elif inspect.ismethod(obj) or inspect.ismethoddescriptor(obj):
        kind = "method"
    else:
        kind = "data"

    # Return the object and its kind
    return obj, raw_obj, kind


class Method(object):
    """Represent a method wrapped with metric collection."""

    def __init__(self, config, label, items):
        """Initialize a method wrapped with metric collection.

        :param config: The global configuration; needed for the
                       notifier.
        :param label: The label to use when reporting the collected
                      statistic.
        :param items: A list of key, value pairs giving the
                      configuration for setting up the method wrapper.
        """

        self.config = config
        self.label = label
        self._method_cache = None
        self._app_cache = None
        self._metric_cache = None

        # Other important configuration values
        attrs = set(['module', 'method', 'metric', 'notifier',
                     'app', 'app_path'])
        required = set(['module', 'method', 'metric'])
        for attr in attrs:
            setattr(self, '_' + attr, None)
        self.additional = {}

        # Process configuration
        for option, value in items:
            if option in attrs:
                setattr(self, '_' + option, value)
                required.discard(option)
            else:
                self.additional[option] = value

            # Add app or app_path to required if necessary
            if option == 'app' and not self._app_path:
                required.add('app_path')
            elif option == 'app_path' and not self._app:
                required.add('app')

        # Make sure we got the essential configuration
        if required:
            raise Exception("Missing configuration options for %s: %s" %
                            (sec, ', '.join(required)))

        # Grab the method we're operating on
        method_cls = utils.import_class_or_module(self._module)
        if inspect.ismodule(method_cls):
            method = raw_method = getattr(method_cls, self._method)
            kind = 'function'
        else:
            method, raw_method, kind = _get_method(method_cls, self._method)
        self._method_cache = method

        # We need to wrap the replacement if its a static or class
        # method
        if kind == 'static method':
            meth_wrap = staticmethod
        elif kind == 'class method':
            meth_wrap = classmethod
        else:
            meth_wrap = lambda f: f

        # Wrap the method to perform statistics collection
        @functools.wraps(method)
        def wrapper(*args, **kwargs):
            # Handle app translation
            label = None
            if self.app:
                args, kwargs, label = self.app(*args, **kwargs)

            # Run the method, bracketing with statistics collection
            # and notification
            value = self.metric.start()
            result = method(*args, **kwargs)
            self.notifier(self.metric(value), label or self.label)

            return result

        # Save some introspecting data
        wrapper.tach_descriptor = self
        wrapper.tach_function = method

        # Save what we need
        self._method_cls = method_cls
        self._method_wrapper = meth_wrap(wrapper)
        self._method_orig = raw_method

    def __getitem__(self, key):
        """Allow access to additional configuration."""

        return self.additional[key]

    def install(self):
        """Install the metric collector."""

        setattr(self._method_cls, self._method, self._method_wrapper)

    def uninstall(self):
        """Uninstall the metric collector."""

        setattr(self._method_cls, self._method, self._method_orig)

    @property
    def method(self):
        """Return the actual method."""

        return self._method_cache

    @property
    def app(self):
        """Return the application transformer."""

        if not self._app_cache:
            app_cls = utils.import_class_or_module(self._app_path)
            self._app_cache = getattr(app_cls, self._app)

        return self._app_cache

    @property
    def metric(self):
        """Return an initialized statistic object."""

        if not self._metric_cache:
            if self._metric in ('timer', 'graphite', 'statsd_timer'):
                # These all handled execution times
                self._metric_cache = metrics.ExecTime({})
            elif self._metric == 'statsd_incr':
                # This was an increment operation
                self._metric_cache = metrics.Increment(dict(increment=1))
            elif self._metric == 'statsd_decr':
                # This was a decrement operation
                self._metric_cache = metrics.Increment(dict(increment=-1))
            else:
                # New-style config; select an appropriate statistic
                cls = utils.import_class_or_module(self._metric)
                self._metric_cache = cls(self.additional)

        return self._metric_cache

    @property
    def notifier(self):
        """Return the notifier driver."""

        return self.config.notifier(self._notifier)
