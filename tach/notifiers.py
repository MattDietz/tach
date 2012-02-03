import logging
import socket
import time

from tach import utils


LOG = logging.getLogger(__name__)


class BaseNotifier(object):
    """Base notifier class."""

    def __init__(self, config):
        """Initialize a notifier.

        Saves the configuration for later use.
        """

        self.config = config

    def format(self, value, vtype, label):
        """Format the value.

        Subclasses must implement methods for metric types.
        """

        # Get the value formatter for the value type
        meth = getattr(self, vtype, None)
        if not meth:
            meth = getattr(self, 'default', None)
            if not meth:
                return

        # Format the value into a body
        return meth(value, label)

    def __call__(self, value, vtype, label):
        """Causes the metric to be formatted and sent.

        Subclasses must implement methods for metric types and the
        send() method.
        """

        # Send the message
        self.send(self.format(value, vtype, label))


class PrintNotifier(BaseNotifier):
    """Simple print notifier."""

    def send(self, body):
        """Send to standard output."""

        # Basic do-nothing notifier
        print "---- %s" % body

    def exec_time(self, value, label):
        """Format execution time."""

        return "Execution time %s: %s" % (label, value)

    def increment(self, value, label):
        """Format increment/decrement."""

        return "Increment %s: %s" % (label, value)

    def default(self, value, label):
        """Format default string."""

        return "Metric %s: %s" % (label, value)


class DebugNotifier(BaseNotifier):
    """Debug notifier.

    Use the "real_driver" configuration option to specify the notifier
    to wrap.
    """

    def __init__(self, config):
        """Initialize the notifier from the configuration."""

        # First, figure out the real notifier
        self.driver_name = config['real_driver']

        # Get the class and instantiate it
        cls = utils.import_class_or_module(self.driver_name)
        self.driver = cls(config)

    def __call__(self, value, vtype, label):
        """Causes the metric to be formatted and sent."""

        # Format the value
        body = self.driver.format(value, vtype, label)

        # Output debugging information
        LOG.debug("DebugNotifier: Notifying %r of message %r" %
                  (self.driver_name, body))
        LOG.debug("DebugNotifier: Raw value of type %r: %r" % (vtype, value))
        LOG.debug("DebugNotifier: Statistic label: %r" % label)

        return self.driver.send(body)


class SocketNotifier(BaseNotifier):
    """Base class for notifiers using sockets."""

    def __init__(self, config, hostattr='host', portattr='port'):
        """Initialize a SocketNotifier.

        The legacy configuration for the Graphite and StatsD notifiers
        requires alternate configuration keys than the defaults.  The
        defaults can be overridden by specifying hostattr and
        portattr.
        """

        super(SocketNotifier, self).__init__(config)
        self.host = config[hostattr]
        self.port = int(config[portattr])

        # Save the socket
        self._sock = None

    def send(self, body):
        """Send to a service specified by host and port."""

        # Since we're keeping the socket open for a long time, we try
        # the send twice, reopening the socket in between rounds, if
        # sending fails the first time.
        for rnd in range(2):
            # Get the socket
            sock = self.sock
            if not sock:
                return

            # Send the body
            try:
                sock.sendall(body)
            except socket.error as e:
                if rnd:
                    print "Error writing to server: %s" % e

                # Try reopening the socket next time
                del self.sock
            else:
                # Body successfully sent
                break

    @property
    def sock(self):
        """Retrieve a socket for the server.

        Creates the socket, if necessary.
        """

        if not self._sock:
            # TCP or UDP?
            if getattr(self, 'sock_type', 'tcp') == 'udp':
                sock_type = socket.SOCK_DGRAM
            else:
                sock_type = socket.SOCK_STREAM

            # Obtain the socket
            sock = socket.socket(socket.AF_INET, sock_type)

            # Connect the socket
            try:
                sock.connect((self.host, self.port))
            except socket.error as e:
                print ("Error connecting to server %s port %s: %s" %
                       (self.host, self.port, e))
                return None

            # Save the created socket
            self._sock = sock

        return self._sock

    @sock.deleter
    def sock(self):
        """Reset server socket.

        Close the existing socket and clear the cache.  Causes the
        socket to be recreated next time self.sock is accessed.
        """

        if self._sock:
            # Close the existing socket
            try:
                self._sock.close()
            except Exception:
                # Might already be closed; we don't care
                pass

            # Clear the cache
            self._sock = None


class GraphiteNotifier(SocketNotifier):
    """Simple Graphite notifier."""

    def default(self, value, label):
        """Format metric submission."""

        return "%s %s %d\n" % (label, value, int(time.time()))


class StatsDNotifier(SocketNotifier):
    """Simple statsd notifier."""

    sock_type = 'udp'

    def exec_time(self, value, label):
        """Format execution time."""

        return "%s:%s|ms" % (label, value * 1000.0)

    def increment(self, value, label):
        """Format increment/decrement."""

        return "%s:%s|c" % (label, value)
