import time

from tach import metrics

import tests



class TestBase(tests.TestCase):
    def test_transaction_id_default(self):
        metric = metrics.Metric({})
        self.assertFalse(metric.bump_transaction_id)

    def test_transaction_id_true(self):
        metric = metrics.Metric(dict(bump_transaction_id=1))
        self.assertTrue(metric.bump_transaction_id)

    def test_transaction_id_false(self):
        metric = metrics.Metric(dict(bump_transaction_id=0))
        self.assertFalse(metric.bump_transaction_id)


class TestExecTime(tests.TestCase):
    def test_function(self):
        metric = metrics.ExecTime({})
        value = metric.start()
        time.sleep(0.5)
        result = metric(value)

        self.assertAlmostEqual(result, 0.5, delta=0.1)


class TestIncrement(tests.TestCase):
    def test_increment(self):
        metric = metrics.Increment({})
        value = metric.start()
        result = metric(value)

        self.assertEqual(result, 1)

    def test_decrement(self):
        metric = metrics.Increment({'increment': '-1'})
        value = metric.start()
        result = metric(value)

        self.assertEqual(result, -1)

    def test_arbitrary(self):
        metric = metrics.Increment({'increment': '5000'})
        value = metric.start()
        result = metric(value)

        self.assertEqual(result, 5000)


class MetricTest(metrics.Metric):
    vtype = 'test'

    def start(self):
        return 'started'

    def __call__(self, value):
        return 'result'


class TestDebug(tests.LoggingTestCase):
    imports = {'MetricTest': MetricTest}

    def test_initialize(self):
        metric = metrics.DebugMetric({'real_metric': 'MetricTest'})

        self.assertEqual(metric.metric_name, 'MetricTest')
        self.assertIsInstance(metric.metric, MetricTest)
        self.assertEqual(metric.vtype, MetricTest.vtype)

    def test_start(self):
        metric = metrics.DebugMetric({'real_metric': 'MetricTest'})
        value = metric.start()

        self.assertEqual(value, 'started')
        self.assertEqual(self.logmsg[0], "DebugMetric: Starting metric "
                         "'MetricTest': 'started'")

    def test_finish(self):
        metric = metrics.DebugMetric({'real_metric': 'MetricTest'})
        result = metric('testing')

        self.assertEqual(result, 'result')
        self.assertEqual(self.logmsg[0], "DebugMetric: Ending metric "
                         "'MetricTest': 'testing'/'result'")
