import imp
import os
import sys
import traceback


def import_class_or_module(klass_str):
    """Import a named class or module."""

    if os.path.isfile(klass_str):
        return imp.load_source('tach_helper_generic', klass_str)
    else:
        module, sep, klass = klass_str.rpartition('.')
        if module:
            try:
                __import__(module)
                return getattr(sys.modules[module], klass)
            except (ImportError, ValueError, AttributeError), exc:
                raise Exception("Could not load class %s\n%s" % (klass_str,
                                                traceback.format_exc(exc)))
        else:
            try:
                __import__(klass)
                return sys.modules[klass]
            except (ImportError, ValueError, AttributeError), exc:
                raise Exception("Could not load class %s\n%s" % (klass,
                                                traceback.format_exc(exc)))
