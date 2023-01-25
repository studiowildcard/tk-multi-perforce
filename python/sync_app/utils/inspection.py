import traceback
import functools
import sgtk
import os

logger = sgtk.platform.get_logger(__name__)


def partialclass(cls, *args, **kwds):
    class NewCls(cls):
        __init__ = functools.partialmethod(cls.__init__, *args, **kwds)

    return NewCls


verbose = False
if os.getenv("NX_DEEP_DEBUG"):
    verbose = True


def trace(fn):
    from functools import wraps

    @wraps(fn)
    def wrapper(self, *args, **kw):
        try:
            if verbose:
                logger.debug("Function: {name} [starting...]".format(name=fn.__name__))
            catch = fn(self, *args, **kw)
            if verbose:
                logger.debug("Function: {name} [success]".format(name=fn.__name__))
            return catch
        except Exception:

            logger.error(traceback.format_exc())

    return wrapper


def method_decorator(decorator):
    def decorate(cls):
        for attr in cls.__dict__:  # there's propably a better way to do this
            if callable(getattr(cls, attr)):
                setattr(cls, attr, decorator(getattr(cls, attr)))
        return cls

    return decorate
