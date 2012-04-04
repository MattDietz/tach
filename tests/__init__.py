import logging
import unittest2 as unittest

import stubout

from tach import utils


class TestCase(unittest.TestCase):
    imports = {}

    def setUp(self):
        self.stubs = stubout.StubOutForTesting()

        def fake_import(module):
            return self.imports[module]

        self.stubs.Set(utils, 'import_class_or_module', fake_import)

    def tearDown(self):
        self.stubs.UnsetAll()


class LoggingTestCase(TestCase):
    def setUp(self):
        super(LoggingTestCase, self).setUp()

        self.logmsg = []

        def log_message(logger, message):
            self.logmsg.append(message)

        self.stubs.Set(logging.Logger, 'debug', log_message)
        self.stubs.Set(logging.Logger, 'error', log_message)
