import ConfigParser
import inspect
import StringIO

from tach import config
from tach import metrics
from tach import notifiers

import tests
from tests import fake_module


class FakeConfig(object):
    _notifier = None

    def notifier(self, name):
        if not self._notifier:
            self._notifier = FakeNotifier(self)
        return self._notifier


class FakeNotifier(notifiers.BaseNotifier):
    def __init__(self, config):
        super(FakeNotifier, self).__init__(config)

        self.sent_msgs = []

    def default(self, value, label):
        return 'default/%r/%r' % (value, label)

    def send(self, body):
        self.sent_msgs.append(body)


class FakeMetric(metrics.Metric):
    vtype = 'fake'

    def __init__(self, config):
        super(FakeMetric, self).__init__(config)

        self.config = config

    def start(self):
        return "started"

    def __call__(self, value):
        return "%s/ended" % value


class FakeClass(object):
    def instance_method(self, *args, **kwargs):
        return 'method', dict(args=args, kwargs=kwargs)

    @classmethod
    def class_method(cls, *args, **kwargs):
        return 'class', dict(args=args, kwargs=kwargs)

    @staticmethod
    def static_method(*args, **kwargs):
        return 'static', dict(args=args, kwargs=kwargs)


class FakeHelper(object):
    @staticmethod
    def fake_helper(*args, **kwargs):
        # Swap args and kwargs
        new_kwargs = dict(zip('abcdefghijklmnopqrstuvwxyz', args))
        new_args = [kwargs[k] for k in sorted(kwargs)]
        return new_args, new_kwargs, 'fake_label'


class FakeSubConfig(object):
    def __init__(self, cfg, label, items, **kwargs):
        self.config = cfg
        self.items = dict(items)

        if label.startswith('notifier'):
            self.label = label.partition(':')[-1]
            self.default = not self.label

            # Set up a driver
            self.driver = self.items.get('driver', '__default__')
        else:
            self.label = label


class TestConfig(tests.TestCase):
    config = {
        'init_config': """
[notifier]
param1=this is a test
param2=this is also a test

[notifier:foobar]
spam=I am a fubared notifier

[foo.bar]
desc=a typical method

[bar.foo]
desc=a not so typical method

[third]
desc=a third method, just to make things interesting.
""",
        'notifier_config': """
[notifier]
driver=default_driver

[notifier:foo]
driver=foo_driver
""",
        'blank_config': "",
        }

    def setUp(self):
        super(TestConfig, self).setUp()

        def fake_read(cp, filenames):
            if isinstance(filenames, basestring):
                filenames = [filenames]
            read_ok = []
            for filename in filenames:
                if filename not in self.config:
                    continue
                fp = StringIO.StringIO(self.config[filename])
                cp._read(fp, filename)
                fp.close()
                read_ok.append(filename)
            return read_ok

        self.stubs.Set(ConfigParser.SafeConfigParser, 'read', fake_read)

        self.stubs.Set(config, 'Notifier', FakeSubConfig)
        self.stubs.Set(config, 'Method', FakeSubConfig)

    def test_init(self):
        cfg = config.Config('init_config')

        # Check that we set up the correct notifiers dict entries
        self.assertEqual(len(cfg.notifiers), 3)
        self.assertIn(None, cfg.notifiers)
        self.assertIn('', cfg.notifiers)
        self.assertEqual(cfg.notifiers[None], cfg.notifiers[''])
        self.assertIn('foobar', cfg.notifiers)

        # Check that we fed the notifiers the right arguments
        self.assertEqual(cfg.notifiers[None].config, cfg)
        self.assertEqual(cfg.notifiers[None].label, '')
        self.assertEqual(cfg.notifiers[None].items, dict(
                param1='this is a test',
                param2='this is also a test'))
        self.assertEqual(cfg.notifiers['foobar'].config, cfg)
        self.assertEqual(cfg.notifiers['foobar'].label, 'foobar')
        self.assertEqual(cfg.notifiers['foobar'].items, dict(
                spam='I am a fubared notifier'))

        # Check that we set up the correct method dict entries
        self.assertEqual(len(cfg.methods), 3)
        self.assertIn('foo.bar', cfg.methods)
        self.assertIn('bar.foo', cfg.methods)
        self.assertIn('third', cfg.methods)

        # Check that we fed the methods the right arguments
        self.assertEqual(cfg.methods['foo.bar'].config, cfg)
        self.assertEqual(cfg.methods['foo.bar'].label, 'foo.bar')
        self.assertEqual(cfg.methods['foo.bar'].items, dict(
                desc='a typical method'))
        self.assertEqual(cfg.methods['bar.foo'].config, cfg)
        self.assertEqual(cfg.methods['bar.foo'].label, 'bar.foo')
        self.assertEqual(cfg.methods['bar.foo'].items, dict(
                desc='a not so typical method'))
        self.assertEqual(cfg.methods['third'].config, cfg)
        self.assertEqual(cfg.methods['third'].label, 'third')
        self.assertEqual(cfg.methods['third'].items, dict(
                desc='a third method, just to make things interesting.'))

    def test_init_nodefault_notifier(self):
        cfg = config.Config('blank_config')

        self.assertEqual(len(cfg.notifiers), 1)
        self.assertIn(None, cfg.notifiers)

        self.assertEqual(cfg.notifiers[None].config, cfg)
        self.assertEqual(cfg.notifiers[None].label, '')
        self.assertEqual(cfg.notifiers[None].items, {})

    def test_notifier(self):
        cfg = config.Config('notifier_config')
        result = cfg.notifier('foo')

        self.assertEqual(result, 'foo_driver')

    def test_notifier_default(self):
        cfg = config.Config('notifier_config')
        result = cfg.notifier('bar')

        self.assertEqual(result, 'default_driver')

    def test_notifier_nodefault(self):
        cfg = config.Config('blank_config')
        result = cfg.notifier('bar')

        self.assertEqual(result, '__default__')

    def test_all_methods(self):
        cfg = config.Config('init_config')
        result = sorted([meth.label for meth in cfg._methods(())])

        self.assertEqual(result, ['bar.foo', 'foo.bar', 'third'])

    def test_methods_slice(self):
        cfg = config.Config('init_config')
        result = sorted([meth.label for meth in
                         cfg._methods(('foo.bar', 'bar.foo'))])

        self.assertEqual(result, ['bar.foo', 'foo.bar'])


class TestNotifier(tests.TestCase):
    imports = {'FakeNotifier': FakeNotifier}

    def test_basic(self):
        notifier = config.Notifier('config', 'notifier:basic', [
                ('driver', 'FakeNotifier'),
                ('foo', 'bar')])

        self.assertEqual(notifier.config, 'config')
        self.assertEqual(notifier.default, False)
        self.assertEqual(notifier._driver, FakeNotifier)
        self.assertEqual(notifier._driver_cache, None)
        self.assertEqual(notifier.additional, {'foo': 'bar'})
        self.assertEqual(notifier.label, 'basic')

    def test_empty_label(self):
        notifier = config.Notifier('config', 'notifier:', [
                ('driver', 'FakeNotifier'),
                ('foo', 'bar')])

        self.assertEqual(notifier.config, 'config')
        self.assertEqual(notifier.default, True)
        self.assertEqual(notifier._driver, FakeNotifier)
        self.assertEqual(notifier._driver_cache, None)
        self.assertEqual(notifier.additional, {'foo': 'bar'})
        self.assertEqual(notifier.label, '')

    def test_missing_label(self):
        notifier = config.Notifier('config', 'notifier', [
                ('driver', 'FakeNotifier'),
                ('foo', 'bar')])

        self.assertEqual(notifier.config, 'config')
        self.assertEqual(notifier.default, True)
        self.assertEqual(notifier._driver, FakeNotifier)
        self.assertEqual(notifier._driver_cache, None)
        self.assertEqual(notifier.additional, {'foo': 'bar'})
        self.assertEqual(notifier.label, '')

    def test_missing_driver(self):
        notifier = config.Notifier('config', 'notifier', [
                ('foo', 'bar')])

        self.assertEqual(notifier.config, 'config')
        self.assertEqual(notifier.default, True)
        self.assertEqual(notifier._driver, notifiers.PrintNotifier)
        self.assertEqual(notifier._driver_cache, None)
        self.assertEqual(notifier.additional, {'foo': 'bar'})
        self.assertEqual(notifier.label, '')

    def test_additional_config(self):
        notifier = config.Notifier(None, 'notifier', [
                ('foo', 'bar')])

        self.assertEqual(notifier['foo'], 'bar')
        with self.assertRaises(KeyError):
            _foo = notifier['bar']

    def test_get_driver(self):
        notifier = config.Notifier(None, 'notifier', [
                ('driver', 'FakeNotifier')])

        self.assertIsInstance(notifier.driver, FakeNotifier)
        self.assertEqual(notifier.driver.config, notifier)


class TestGetMethod(tests.TestCase):
    def test_instance_method(self):
        obj, raw_obj, kind = config._get_method(FakeClass, 'instance_method')

        self.assertEqual(obj, FakeClass.instance_method)
        self.assertEqual(raw_obj, FakeClass.__dict__['instance_method'])
        self.assertEqual(kind, 'method')

    def test_class_method(self):
        obj, raw_obj, kind = config._get_method(FakeClass, 'class_method')

        self.assertEqual(obj, FakeClass.class_method)
        self.assertEqual(raw_obj, FakeClass.__dict__['class_method'])
        self.assertEqual(kind, 'class method')

    def test_static_method(self):
        obj, raw_obj, kind = config._get_method(FakeClass, 'static_method')

        self.assertEqual(obj, FakeClass.static_method)
        self.assertEqual(raw_obj, FakeClass.__dict__['static_method'])
        self.assertEqual(kind, 'static method')


class TestMethod(tests.TestCase):
    imports = {
        'FakeMetric': FakeMetric,
        'FakeHelper': FakeHelper,
        'FakeClass': FakeClass,
        'fake_module': fake_module,
        }

    def setUp(self):
        super(TestMethod, self).setUp()
        self.method = None

    def tearDown(self):
        super(TestMethod, self).tearDown()
        if self.method:
            self.method.detach()

    def test_missing_module(self):
        regexp = 'Missing configuration options for label: module'
        with self.assertRaisesRegexp(Exception, regexp):
            self.method = config.Method(None, 'label', [
                    ('method', 'instance_method'),
                    ('metric', 'FakeMetric')])

    def test_missing_method(self):
        regexp = 'Missing configuration options for label: method'
        with self.assertRaisesRegexp(Exception, regexp):
            self.method = config.Method(None, 'label', [
                    ('module', 'FakeClass'),
                    ('metric', 'FakeMetric')])

    def test_missing_metric(self):
        regexp = 'Missing configuration options for label: metric'
        with self.assertRaisesRegexp(Exception, regexp):
            self.method = config.Method(None, 'label', [
                    ('module', 'FakeClass'),
                    ('method', 'instance_method')])

    def test_init(self):
        # We have to grab these here, because we can't look for them
        # after they've been monkey-patched.
        original = FakeClass.__dict__['instance_method']
        original_method = FakeClass.instance_method

        method = self.method = config.Method('config', 'label', [
                ('module', 'FakeClass'),
                ('method', 'instance_method'),
                ('metric', 'FakeMetric'),
                ('notifier', 'notifier'),
                ('app_helper', 'FakeHelper'),
                ('app', 'fake_helper'),
                ('foo', 'bar')])
        self.assertEqual(method.config, 'config')
        self.assertEqual(method.label, 'label')
        self.assertEqual(method._app_cache, None)
        self.assertEqual(method._metric_cache, None)
        self.assertEqual(method.additional, {'foo': 'bar'})
        self.assertEqual(method._module, 'FakeClass')
        self.assertEqual(method._method, 'instance_method')
        self.assertEqual(method._metric, 'FakeMetric')
        self.assertEqual(method._notifier, 'notifier')
        self.assertEqual(method._app_helper, 'FakeHelper')
        self.assertEqual(method._app, 'fake_helper')
        self.assertEqual(method._method_cls, FakeClass)
        self.assertTrue(inspect.isfunction(method._method_wrapper))
        self.assertEqual(method._method_orig, original)
        self.assertEqual(method._method_wrapper.tach_descriptor, method)
        self.assertEqual(method._method_wrapper.tach_function,
                         original_method)

    def test_init_class(self):
        method = self.method = config.Method(None, 'label', [
                ('module', 'FakeClass'),
                ('method', 'class_method'),
                ('metric', 'FakeMetric')])

        self.assertEqual(method._method_cls, FakeClass)
        self.assertIsInstance(method._method_wrapper, classmethod)

        method.detach()
        self.assertEqual(method._method_orig,
                         FakeClass.__dict__['class_method'])

    def test_init_static(self):
        method = self.method = config.Method(None, 'label', [
                ('module', 'FakeClass'),
                ('method', 'static_method'),
                ('metric', 'FakeMetric')])

        self.assertEqual(method._method_cls, FakeClass)
        self.assertIsInstance(method._method_wrapper, staticmethod)

        method.detach()
        self.assertEqual(method._method_orig, 
                                    FakeClass.__dict__['static_method'])

    def test_init_function(self):
        method = self.method = config.Method(None, 'label', [
                ('module', 'fake_module'),
                ('method', 'function'),
                ('metric', 'FakeMetric')])

        self.assertEqual(method._method_cls, fake_module)
        self.assertTrue(inspect.isfunction(method._method_wrapper))

        method.detach()
        self.assertEqual(method._method_orig, fake_module.function)

    def test_additional_config(self):
        method = self.method = config.Method(None, 'label', [
                ('module', 'FakeClass'),
                ('method', 'instance_method'),
                ('metric', 'FakeMetric'),
                ('foo', 'bar')])

        self.assertEqual(method['foo'], 'bar')
        with self.assertRaises(KeyError):
            _foo = method['bar']

    def test_wrapper_basic(self):
        method = self.method = config.Method(FakeConfig(), 'label', [
                ('module', 'fake_module'),
                ('method', 'function'),
                ('metric', 'FakeMetric')])

        # We know that method._method_wrapper is the wrapper function,
        # so we can call it with impunity
        result = method._method_wrapper(1, 2, 3, a=4, b=5, c=6)

        self.assertEqual(result, ('function', dict(
                    args=(1, 2, 3),
                    kwargs=dict(a=4, b=5, c=6))))
        self.assertEqual(method.notifier.sent_msgs,
                         ["default/'started/ended'/'label'"])

    def test_wrapper_helper(self):
        method = self.method = config.Method(FakeConfig(), 'label', [
                ('module', 'fake_module'),
                ('method', 'function'),
                ('metric', 'FakeMetric'),
                ('app_helper', 'FakeHelper'),
                ('app', 'fake_helper')])

        # We know that method._method_wrapper is the wrapper function,
        # so we can call it with impunity
        result = method._method_wrapper(1, 2, 3, a=4, b=5, c=6)

        self.assertEqual(result, ('function', dict(
                    args=(4, 5, 6),
                    kwargs=dict(a=1, b=2, c=3))))
        self.assertEqual(method.notifier.sent_msgs,
                         ["default/'started/ended'/'fake_label'"])

    def test_get_app(self):
        method = self.method = config.Method(None, 'label', [
                ('module', 'FakeClass'),
                ('method', 'instance_method'),
                ('metric', 'FakeMetric'),
                ('app_helper', 'FakeHelper'),
                ('app', 'fake_helper')])

        self.assertEqual(method.app, FakeHelper.fake_helper)

    def test_get_no_app(self):
        method = self.method = config.Method(None, 'label', [
                ('module', 'FakeClass'),
                ('method', 'instance_method'),
                ('metric', 'FakeMetric')])

        self.assertEqual(method.app, None)

    def test_get_metric(self):
        method = self.method = config.Method(None, 'label', [
                ('module', 'FakeClass'),
                ('method', 'instance_method'),
                ('metric', 'FakeMetric')])

        self.assertIsInstance(method.metric, FakeMetric)

    def test_get_notifier(self):
        method = self.method = config.Method(FakeConfig(), 'label', [
                ('module', 'FakeClass'),
                ('method', 'instance_method'),
                ('metric', 'FakeMetric')])

        self.assertIsInstance(method.notifier, FakeNotifier)
