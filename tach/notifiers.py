import socket
import time


class BaseNotifier(object):
    """Base notifier class."""

    def __call__(self, value, metric, config):
        """Causes the metric to be formatted and sent.

        Subclasses must implement methods for statistic types and the
        send() method.
        """

        # Get the value formatter for the value type
        meth = getattr(self, value.type, None)
        if not meth:
            return

        # Format the value into a body
        body = meth(value, metric, config)

        # Send the message
        self.send(body, config)


class PrintNotifier(BaseNotifier):
    """Simple print notifier."""

    def send(self, body, config):
        """Send to standard output."""

        # Basic do-nothing notifier
        print "---- %s" % body

    def exec_time(self, value, metric, config):
        """Format execution time."""

        return "Execution time %s: %s" % (metric, value)

    def increment(self, value, metric, config):
        """Format increment/decrement."""

        return "Increment %s: %s" % (metric, value)


class SocketNotifier(BaseNotifier):
    """Base class for notifiers using sockets."""

    def send(self, body, config):
        """Send to a service specified by host and port.

        Subclasses must implement the get_params() method.
        """

        # Get the host and port
        host, port = self.get_params(config)

        # TCP or UDP?
        if getattr(self, 'sock_type', 'tcp') == 'udp':
            sock_type = socket.SOCK_DGRAM
        else:
            sock_type = socket.SOCK_STREAM

        # Get the socket
        sock = socket.socket(socket.AF_INET, sock_type)

        # Send the body
        try:
            sock.connect((host, port))
            sock.sendall(body)
        except socket.error as e:
            print "Error connecting to server: %s" % e
        finally:
            # Note: Not caching; this would be easy to add
            sock.close()


class GraphiteNotifier(SocketNotifier):
    """Simple Graphite notifier."""

    def get_params(self, config):
        """Retrieve Graphite host and port from configuration."""

        return config['carbon_host'], config['carbon_port']

    def exec_time(self, value, metric, config):
        """Format execution time."""

        return "%s %s %d\n" % (metric, value, int(time.time()))

    def increment(self, value, metric, config):
        """Format increment/decrement."""

        return "%s %s %d\n" % (metric, value, int(time.time()))


class StatsDNotifier(SocketNotifier):
    """Simple statsd notifier."""

    sock_type = 'udp'

    def get_params(self, config):
        """Retrieve statsd host and port from configuration."""

        return config['statsd_host'], config['statsd_port']

    def exec_time(self, value, metric, config):
        """Format execution time."""

        return "%s:%s|ms" % (metric, value * 1000.0)

    def increment(self, value, metric, config):
        """Format increment/decrement."""

        return "%s:%s|c" % (metric, value)
