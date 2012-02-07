import tach
from tach import config

import tests


class FakeConfig(object):
    def __init__(self, path):
        self.path = path
        self.installed = False

    def install(self):
        self.installed = True


class TestPatch(tests.TestCase):
    def setUp(self):
        super(TestPatch, self).setUp()

        self.stubs.Set(config, 'Config', FakeConfig)

    def test_patch(self):
        cfg = tach.patch('foobar')

        self.assertEqual(cfg.path, 'foobar')
        self.assertEqual(cfg.installed, True)
