# Zeegat

`zeegat` is a project to explore a new routing system for the
[ocpp](https://github.com/mobilityhouse/ocpp) package. It's using ideas from
the [Service](https://tokio.rs/blog/2021-05-14-inventing-the-service-trait)
trait of
[tower](https://docs.rs/tower-service/0.3.1/tower_service/trait.Service.html). 

## Quickstart

Make sure to have [poetry](https://python-poetry.org/docs/#installation) installed.

``` bash
$ poetry install
```

Now run the CSMS...:

``` bash
$ poetry run python zeegat/bin/csms.py
```

... and connect a charger:

``` bash
$ poetry run python zeegat/bin/charger.py
```

## Concepts

The core of `zeegat` is the `zeegat.interfaces.Service` interface. It provides the
an asynchronous method `call()` that receives an instance of `zeegat.messages.Call`
and returns something that implements the interface `zeegat.interfaces.IntoResponse`.

This last interface transform objects into a `str` that can be send over a
websocket connection.

``` python
class Service(Protocol):
    """A type that turns a `Call` into something that implements :class:`IntoResponse`."""

    async def call(self, request: Call) -> IntoResponse:
        ...


class IntoResponse(Protocol):
    def into_response(self) -> str:
        ...
```

The module `zeegat.services` provide a few classes implementing the `Service`
interface. The [zeegat/bin/csms.py](zeegat/bin/csms.py) uses these services to implement a small
CSMS.

### route

The `route()` allows to registers `Service`s and `Handler`s to
incoming messages.

### log

`log()` logs requests and responses to sdout.

### timeout

The `timeout()` service prevents other services from blocking for ever.


## Open points

1. How to inject state into handlers?
2. How to implement equivalent of [`@after()`](https://github.com/mobilityhouse/ocpp/blob/master/ocpp/routing.py#L58-L79) handler?

Assume a charger receives a `TriggerMessage` request to trigger a
`StatusNotification`. It has to provide a response first, before sending the
`StatusNotification`. The `ocpp` package provides a `@after()` decorator. `zeegat`
must provide an API to allow users executing code after a specific request has
been received.

3. How to provide (indirect) access to the websocket so `Service`s can send requests?

# License

[MIT](LICENSE)
