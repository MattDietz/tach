import ConfigParser
import inspect
import StringIO

from tach import config
from tach import metrics
from tach import notifiers

import tests
from tests import fake_module


class FakeConfig(object):
    def notifier(self, name):
        return FakeNotifier(None)


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
    def instance_method(self):
        pass

    @classmethod
    def class_method(cls):
        pass

    @staticmethod
    def static_method():
        pass


class FakeHelper(object):
    @staticmethod
    def fake_helper(*args, **kwargs):
        return args, kwargs, 'fake_label'


class ConfigTestCase(tests.TestCase):
    config = {}
    notifier_class = None
    method_class = None

    def setUp(self):
        super(ConfigTestCase, self).setUp()

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

        if self.notifier_class:
            self.stubs.Set(config, 'Notifier', self.notifier_class)
        if self.method_class:
            self.stubs.Set(config, 'Method', self.method_class)


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

    def test_missing_module(self):
        regexp = 'Missing configuration options for label: module'
        with self.assertRaisesRegexp(Exception, regexp):
            method = config.Method(None, 'label', [
                    ('method', 'instance_method'),
                    ('metric', 'FakeMetric')])

    def test_missing_method(self):
        regexp = 'Missing configuration options for label: method'
        with self.assertRaisesRegexp(Exception, regexp):
            method = config.Method(None, 'label', [
                    ('module', 'FakeClass'),
                    ('metric', 'FakeMetric')])

    def test_missing_metric(self):
        regexp = 'Missing configuration options for label: metric'
        with self.assertRaisesRegexp(Exception, regexp):
            method = config.Method(None, 'label', [
                    ('module', 'FakeClass'),
                    ('method', 'instance_method')])

    def test_init(self):
        method = config.Method('config', 'label', [
                ('module', 'FakeClass'),
                ('method', 'instance_method'),
                ('metric', 'FakeMetric'),
                ('notifier', 'notifier'),
                ('app_path', 'FakeHelper'),
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
        self.assertEqual(method._app_path, 'FakeHelper')
        self.assertEqual(method._app, 'fake_helper')
        self.assertEqual(method._method_cls, FakeClass)
        self.assertTrue(inspect.isfunction(method._method_wrapper))
        self.assertEqual(method._method_orig,
                         FakeClass.__dict__['instance_method'])
        self.assertEqual(method._method_wrapper.tach_descriptor, method)
        self.assertEqual(method._method_wrapper.tach_function,
                         FakeClass.instance_method)

    def test_init_class(self):
        method = config.Method(None, 'label', [
                ('module', 'FakeClass'),
                ('method', 'class_method'),
                ('metric', 'FakeMetric')])

        self.assertEqual(method._method_cls, FakeClass)
        self.assertIsInstance(method._method_wrapper, classmethod)
        self.assertEqual(method._method_orig,
                         FakeClass.__dict__['class_method'])

    def test_init_static(self):
        method = config.Method(None, 'label', [
                ('module', 'FakeClass'),
                ('method', 'static_method'),
                ('metric', 'FakeMetric')])

        self.assertEqual(method._method_cls, FakeClass)
        self.assertIsInstance(method._method_wrapper, staticmethod)
        self.assertEqual(method._method_orig,
                         FakeClass.__dict__['static_method'])

    def test_init_static(self):
        method = config.Method(None, 'label', [
                ('module', 'FakeClass'),
                ('method', 'static_method'),
                ('metric', 'FakeMetric')])

        self.assertEqual(method._method_cls, FakeClass)
        self.assertIsInstance(method._method_wrapper, staticmethod)
        self.assertEqual(method._method_orig,
                         FakeClass.__dict__['static_method'])

    def test_init_function(self):
        method = config.Method(None, 'label', [
                ('module', 'fake_module'),
                ('method', 'function'),
                ('metric', 'FakeMetric')])

        self.assertEqual(method._method_cls, fake_module)
        self.assertTrue(inspect.isfunction(method._method_wrapper))
        self.assertEqual(method._method_orig, fake_module.function)
