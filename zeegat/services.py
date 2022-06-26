import asyncio
import inspect
import logging
from typing import Dict

from ocpp.exceptions import InternalError, NotSupportedError, OCPPError

from zeegat.frame import Frame

from zeegat.interfaces import IntoResponse, Service


logging.basicConfig(level=logging.INFO)
l = logging.getLogger(__name__)


class log:
    """A :class:`Service` that logs request and responses to stdout."""

    def __init__(self, service: Service):
        self._service = service

    async def call(self, frame: Frame) -> IntoResponse:
        response = await self._service.call(frame)
        l.info("%s - %s", frame.as_bytes(), response)
        return response


class timeout:
    """A :class:`Service` that returns a :class:`CallError` containing
    InternalError if inner service doesn't respond in time.

    """

    def __init__(self, interval_in_s: int, service: Service):
        self._interval = interval_in_s
        self._service = service

    async def call(self, frame: Frame) -> IntoResponse:
        try:
            future = await asyncio.wait_for(self._service.call(frame), self._interval)
        except asyncio.TimeoutError:
            raise InternalError(
                details={
                    "cause": f"Handler for action {frame.as_call().action} timed out."
                }
            )

        return future


class route:
    """A :class:`Service` that routes requests :class:`Service`."""

    def __init__(self, action: str, service: Service):
        self._routes: Dict[str, Service] = {}
        self.route(action, service)

    def route(self, action: str, service: Service):
        if action in self._routes:
            raise Exception(
                f"Can't register handler for action {action}: already a handler registered."
            )

        if not isinstance(service, Service):
            service = handler(service)

        self._routes[action] = service
        return self

    async def call(self, frame: Frame) -> IntoResponse:
        try:
            try:
                service = self._routes[frame.as_call().action]
            except KeyError:
                raise NotSupportedError(
                    details={
                        "cause": f"No handler for {frame.as_call().action} registered."
                    }
                )
            else:
                return await service.call(frame)
        except OCPPError as e:
            return frame.as_call().create_call_error(e)


class handler:
    """The :class:`handler` turns an arbitrary async function into a :class:`Service`.
    :class:`handler` analyzes the function's signature and inject dependencies.

    Types used in the function signature must implement `from_frame()`.

    Consider the following example

        async def on_heart_beat(call: Call):
            ...


        handler(on_heart_beat)


    When :meth:`handler.frame(frame: Frame)` is called, this method passes the
    `frame` argument down to :meth:`Call.from_frame()`. The response value is
    passed down to the function :func:`on_heart_beat()`.

    """

    def __init__(self, handler):
        self._handler = _inject_dependencies(handler)

    async def call(self, frame: Frame) -> IntoResponse:
        return await self._handler(frame)


def _inject_dependencies(fn, **kwargs):
    """Inject dependencies in `fn`

    This function returns a callable that takes a single argument of type
    `Frame`.

    """
    _kwargs = {}
    for (argument, type_hint) in inspect.signature(fn).parameters.items():
        try:
            _kwargs[argument] = kwargs[argument]
            continue
        except KeyError:
            pass

        if type_hint.annotation == inspect.Signature.empty:
            raise MissingTypeHintError(fn, argument)

        try:
            concrete_type = fn.__globals__[type_hint.annotation]
        except KeyError as e:
            # This `KeyError` is raised when `inject_dependencies()` is
            # called on it's own result.
            #
            #   inject_dependencies(inject_dependencies(fn))
            #
            # I don't fully understand what happens, but the type `Frame` is
            # not available in the scope of `fn`. As we have this class in our
            # scope, we can ignore it.
            if type_hint.annotation != Frame:
                raise Exception("type not in scope") from e

            concrete_type = Frame

        try:
            _kwargs[argument] = concrete_type.from_frame
        except AttributeError:
            raise UnsupportedTypeError(fn, argument, concrete_type)

    def from_frame(frame: Frame):
        for (argument, callable) in _kwargs.items():
            _kwargs[argument] = callable(frame)

        return fn(**_kwargs)

    from_frame.__deps = True
    return from_frame


def inject(**kwargs):
    """Decorator injecting arbitrary data in handlers.

    import sqlite3

    def get_database():
        return sqlite3.connect(":memory:")


    @inject(db=get_database)
    async def on_authorize(call: Call, db: sqlite3.Connection):
        ...

    """

    def decorator(fn):
        return _inject_dependencies(fn, **kwargs)

    return decorator


class InvalidSignatureError(Exception):
    pass


class MissingTypeHintError(InvalidSignatureError):
    def __init__(self, fn, argument: str):
        self.fn = fn
        self.argument = argument

    def __str__(self):
        return f"Argument '{self.argument}' of callable '{self.fn.__module__}.{self.fn.__name__}()' is lacking a type hint."


class UnsupportedTypeError(InvalidSignatureError):
    def __init__(self, fn, argument: str, concrete_type):
        self.fn = fn
        self.argument = argument
        self.concrete_type = concrete_type

    def __str__(self):
        return f"Argument '{self.argument}' of callable '{self.fn.__module__}.{self.fn.__name__}()' has an incorrect type hint. It's of type {self.concrete_type}, but that type doesn't implement a `from_frame()` method."
