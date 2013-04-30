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
        app_helper = None
        setup_module = None
        # Process configuration
        if config.has_section('global'):
            app_helper = config.get('global', 'app_helper')
            setup_module = config.get('global', 'setup_module')
            config.remove_section('global')

        if setup_module:
            # import this first to do env setup
            mod = __import__(setup_module)
            print "Environment setup module: %s" % mod
            
        for sec in config.sections():
            if sec == 'notifier' or sec.startswith('notifier:'):
                # Make a notifier
                notifier = Notifier(self, sec, config.items(sec))

                # Add it to the recognized notifiers
                self.notifiers.setdefault(notifier.label, notifier)

                # If it's a default notifier, add it as such
                if notifier.default:
                    self.notifiers.setdefault(None, notifier)
            else:
                # Make a method
                method = Method(self, sec, config.items(sec),
                                app_helper=app_helper)

                # Add it to the recognized methods
                self.methods.setdefault(method.label, method)

        # Do we have a default notifier?
        self.notifiers.setdefault(None, Notifier(self, 'notifier', []))

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

        self.label = label.partition(':')[-1]
        if not self.label:
            # No label makes this the default
            self.default = True

        # Process configuration
        for option, value in items:
            if option == 'driver':
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

    def __init__(self, config, label, items, **kwargs):
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
        self._app_cache = None
        self._metric_cache = None
        self._app_helper = kwargs.get('app_helper')

        # Other important configuration values
        required = set(['module', 'method', 'metric'])
        attrs = set(['notifier', 'app']) | required

        # if there's a global helper set, we don't require a local one
        if not self._app_helper:
            attrs.add('app_helper')

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

            # Add app to required if necessary
            if option == 'app' and not self._app_helper:
                required.add('app_helper')

        # Make sure we got the essential configuration
        if required:
            raise Exception("Missing configuration options for %s: %s" %
                            (label, ', '.join(required)))

        # Grab the method we're operating on
        method_cls = utils.import_class_or_module(self._module)
        if inspect.ismodule(method_cls):
            that_method = raw_method = getattr(method_cls, self._method)
            kind = 'function'
        else:
            that_method, raw_method, kind = _get_method(method_cls,
                                                        self._method)
        self._method_cache = that_method

        # We need to wrap the replacement if it's a static or class
        # method
        if kind == 'static method':
            meth_wrap = staticmethod
        elif kind == 'class method':
            meth_wrap = classmethod
        else:
            meth_wrap = lambda f: f

        # Wrap the method to perform statistics collection
        @functools.wraps(that_method)
        def wrapper(*args, **kwargs):
            # Deal with class method calling conventions
            if kind == 'class method':
                args = args[1:]

            # Handle app translation
            label = None
            if self._app:
                args, kwargs, label = self.app(*args, **kwargs)

            # Run the method, bracketing with statistics collection
            # and notification
            if self.metric.bump_transaction_id:
                self.notifier.bump_transaction_id()
            value = self.metric.start()
            result = that_method(*args, **kwargs)
            self.notifier(self.metric(value), self.metric.vtype,
                          label or self.label)

            return result

        # Save some introspecting data
        wrapper.tach_descriptor = self
        wrapper.tach_function = that_method

        # Save what we need
        self._method_cls = method_cls
        self._method_wrapper = meth_wrap(wrapper)
        self._method_orig = raw_method

        setattr(self._method_cls, self._method, self._method_wrapper)

    def detach(self):
        setattr(self._method_cls, self._method, self._method_orig)

    def __getitem__(self, key):
        """Allow access to additional configuration."""

        return self.additional[key]

    @property
    def method(self):
        """Return the actual method."""

        return self._method_cache

    @property
    def app(self):
        """Return the application transformer."""

        # Don't crash if we don't have an app set
        if not self._app or not self._app_helper:
            return None

        if not self._app_cache:
            app_cls = utils.import_class_or_module(self._app_helper)
            self._app_cache = getattr(app_cls, self._app)

        return self._app_cache

    @property
    def metric(self):
        """Return an initialized statistic object."""

        if not self._metric_cache:
            # Select an appropriate statistic
            cls = utils.import_class_or_module(self._metric)
            self._metric_cache = cls(self.additional)

        return self._metric_cache

    @property
    def notifier(self):
        """Return the notifier driver."""

        return self.config.notifier(self._notifier)
