import socket
import time

from tach import notifiers

import tests


class NotifierTest(notifiers.BaseNotifier):
    def __init__(self, config):
        super(NotifierTest, self).__init__(config)

        self.sent_msg = None

    def test(self, value, label):
        return 'test/%r/%r' % (value, label)

    def default(self, value, label):
        return 'default/%r/%r' % (value, label)

    def send(self, body):
        self.sent_msg = body


class TestBaseNotifier(tests.TestCase):
    def test_format(self):
        notifier = NotifierTest({})
        result = notifier.format('result', 'test', 'label')

        self.assertEqual(result, "test/'result'/'label'")

    def test_format_default(self):
        notifier = NotifierTest({})
        result = notifier.format('result', 'spam', 'label')

        self.assertEqual(result, "default/'result'/'label'")

    def test_call(self):
        notifier = NotifierTest({})
        notifier('result', 'test', 'label')

        self.assertEqual(notifier.sent_msg, "test/'result'/'label'")


class TestDebugNotifier(tests.LoggingTestCase):
    imports = {'NotifierTest': NotifierTest}

    def test_initialize(self):
        notifier = notifiers.DebugNotifier({'real_driver': 'NotifierTest'})

        self.assertEqual(notifier.driver_name, 'NotifierTest')
        self.assertIsInstance(notifier.driver, NotifierTest)

    def test_call(self):
        notifier = notifiers.DebugNotifier({'real_driver': 'NotifierTest'})
        notifier('result', 'test', 'label')

        self.assertEqual(self.logmsg[0],
                         "DebugNotifier: Notifying 'NotifierTest' of message "
                         "\"test/'result'/'label'\"")
        self.assertEqual(self.logmsg[1],
                         "DebugNotifier: Raw value of type 'test': 'result'")
        self.assertEqual(self.logmsg[2],
                         "DebugNotifier: Statistic label: 'label'")


class FakeSocket(object):
    throw = None

    def __init__(self, sock_type):
        self.open = True
        self.sock_type = sock_type
        self.host = None
        self.port = None
        self.buffer = []

    def connect(self, (host, port)):
        self.host = host
        self.port = port

    def close(self):
        self.open = False

    def sendall(self, body):
        if self.throw:
            raise self.throw
        self.buffer.append(body)


class UdpSocketNotifier(notifiers.SocketNotifier):
    sock_type = 'udp'


class TestSocketNotifierBase(tests.LoggingTestCase):
    def setUp(self):
        super(TestSocketNotifierBase, self).setUp()

        self.config = dict(host='test.example.com', port='12345')


class TestSocketNotifier(TestSocketNotifierBase):
    def setUp(self):
        super(TestSocketNotifier, self).setUp()

        def fake_socket(_family, sock_type):
            return FakeSocket(sock_type)

        self.stubs.Set(socket, 'socket', fake_socket)

    def test_init(self):
        notifier = notifiers.SocketNotifier(self.config)

        self.assertEqual(notifier.host, 'test.example.com')
        self.assertEqual(notifier.port, 12345)
        self.assertEqual(notifier._sock, None)

    def test_tcp_sock(self):
        notifier = notifiers.SocketNotifier(self.config)
        sock = notifier.sock

        self.assertIsInstance(sock, FakeSocket)
        self.assertEqual(sock.open, True)
        self.assertEqual(sock.sock_type, socket.SOCK_STREAM)
        self.assertEqual(sock.host, 'test.example.com')
        self.assertEqual(sock.port, 12345)
        self.assertEqual(sock.buffer, [])

    def test_udp_sock(self):
        notifier = UdpSocketNotifier(self.config)
        sock = notifier.sock

        self.assertIsInstance(sock, FakeSocket)
        self.assertEqual(sock.open, True)
        self.assertEqual(sock.sock_type, socket.SOCK_DGRAM)
        self.assertEqual(sock.host, 'test.example.com')
        self.assertEqual(sock.port, 12345)
        self.assertEqual(sock.buffer, [])

    def test_del_sock(self):
        notifier = notifiers.SocketNotifier(self.config)
        sock = notifier.sock

        self.assertIsInstance(sock, FakeSocket)
        self.assertEqual(sock, notifier._sock)

        del notifier.sock

        self.assertEqual(notifier._sock, None)

    def test_send(self):
        notifier = notifiers.SocketNotifier(self.config)
        notifier.send('this is a test')

        self.assertEqual(notifier._sock.buffer, ['this is a test'])

    def test_send_reopen(self):
        notifier = notifiers.SocketNotifier(self.config)
        sock = notifier.sock
        sock.throw = socket.error(1, 2, 3)
        notifier.send('this is a test')

        self.assertEqual(sock.open, False)
        self.assertEqual(self.logmsg, [])
        self.assertNotEqual(notifier._sock, sock)
        self.assertEqual(notifier._sock.open, True)
        self.assertEqual(notifier._sock.buffer, ['this is a test'])

    def test_send_fail(self):
        self.stubs.Set(FakeSocket, 'throw', socket.error(1, 2, 3))
        notifier = notifiers.SocketNotifier(self.config)
        notifier.send('this is a test')

        self.assertEqual(self.logmsg, [
                "SocketNotifier: Error writing to server "
                "(test.example.com, 12345): [Errno 1] 2: 3"])
        self.assertEqual(notifier._sock, None)


class TestGraphiteNotifier(TestSocketNotifierBase):
    def test_default(self):
        notifier = notifiers.GraphiteNotifier(self.config)
        cur_time = time.time()
        result = notifier.default('value', 'label')

        self.assertEqual(result[-1], '\n')
        parts = result.split()
        self.assertEqual(parts[0], 'label')
        self.assertEqual(parts[1], 'value')
        self.assertAlmostEqual(int(parts[2]), cur_time, delta=1)


class TestStatsDNotifier(TestSocketNotifierBase):
    def test_exec_time(self):
        notifier = notifiers.StatsDNotifier(self.config)
        result = notifier.exec_time(12.3456789, 'label')

        self.assertEqual(result, 'label:12345.6789|ms')

    def test_increment(self):
        notifier = notifiers.StatsDNotifier(self.config)
        result = notifier.increment(2, 'label')

        self.assertEqual(result, 'label:2|c')
