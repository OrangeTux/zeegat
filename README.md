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
INFO:ocpp:optimus: send [2,"342e4b81-de57-4abe-b45c-d3b36c9d07e7","Authorize",{"idTag":"24782"}]
INFO:ocpp:optimus: receive message [3,"342e4b81-de57-4abe-b45c-d3b36c9d07e7",{"idTagInfo":{"status":"Accepted"}}]
INFO:ocpp:optimus: send [2,"718450b2-c939-4bff-a772-26a5ac2a7ed9","Heartbeat",{}]
INFO:ocpp:optimus: receive message [3,"718450b2-c939-4bff-a772-26a5ac2a7ed9",{"currentTime":"2022-06-26T16:40:40.602735"}]
INFO:ocpp:optimus: send [2,"f50172c8-618a-4c29-8f76-19407b0d038b","BootNotification",{"chargePointModel":"Optimus","chargePointVendor":"Takara"}]
INFO:ocpp:optimus: receive message [4,"f50172c8-618a-4c29-8f76-19407b0d038b","NotSupported","Request Action is recognized but not supported by the receiver",{"cause":"No handler for BootNotification registered."}]
WARNING:ocpp:Received a CALLError: <CallError - unique_id=f50172c8-618a-4c29-8f76-19407b0d038b, error_code=NotSupported, error_description=Request Action is recognized but not supported by the receiver, error_details={'cause': 'No handler for BootNotification registered.'}>'
INFO:ocpp:optimus: send [2,"8431071d-a1c2-4532-8066-28da12d83143","FirmwareStatusNotification",{"status":"Downloading"}]
INFO:ocpp:optimus: receive message [3,"8431071d-a1c2-4532-8066-28da12d83143",{}]
```

## Concepts

### Service

The `Service` interface allows to build modular components which can be
inserted in the flow of inbound call and outbound call results or call errors.

Some services provided by `zeegat` are:

    * `log` - logs every inbound call and outbound call results or call errors to stdout
    * `route` - route an inbound call to a action specific handler.

The `Service` interface consists of an asynchronous method `call()` that
receives an instance of `zeegat.messages.Frame` and returns something that
implements the interface `zeegat.interfaces.IntoResponse`.

#### route

The route `Service` is routes inbound calls to handlers executing business
logic. The next example shows how an inbound `Heartbeat` call is linked to the
`on_heart_beat()` handler. It receives 2 arguments. First, it requires an OCPP action.
The second argument is a handler that's executed. 

``` python
from datetime import datetime, timezone
from zeegat.services import route

async def on_heart_beat(frame: Frame) -> IntoResponse:
    return frame.as_call().create_call_result(
        payload={"currentTime": datetime.now(timezone.utc).isoformat()}
    )
    
app = route("Heartbeat", on_heart_beat)
```

One can register multiple handlers at `route`:

``` python
async def on_status_notification(frame: Frame) -> IntoResult:
    return frame.as_cal().create_call_result({})


app = route("Heartbeat", on_heart_beat)
        .route("Authorize", on_status_notification)
```

### log

`log` logs inbound requests and outbound response to stdout.
The only argument it receives is another `Service`. 

In the example below, `log` wraps the `route` Service.


``` python
app = log(
    route('Heartbeat', on_heart_beat)
)
```

### timeout

The `timeout` prevents the child server from taking to look.

``` python
from datetime import timedelta

app = log(
    timeout(
        timedelta(seconds=10),
        route('Heartbeat', on_heart_beat),
    )
)
```
             
## Dependency injection

### handler
In above example, the request handlers received a single argument of type
`Frame`. `zeegat` provides the `handler`. This `Service` receives an arbitrary
async function. `handler` inspects the signature of this function and creates
and inject the right type based on the type hints.

Consider this example:

``` python
async def on_heart_beat(call: Call) -> IntoResponse:
    return call().create_call_result(
        payload={"currentTime": datetime.now(timezone.utc).isoformat()}
    )

async def on_authorize(call: Call, charger_id: ChargerId) -> IntoResponse:
    if charger_id == "zeegat":
        status = "Accepted" 
    else:
        status = "Rejected"
    return call.create_call_result(payload={"idTagInfo": {"status": status}})

app = route("Heartbeat", handler(on_heart_beat))
    .route("Authorize", handler(on_authorize))
```

For every type in the function signature, `handler` will call `from_frame()`.
This static method must return an instance of that it's class.

### Injecting custom dependencies.

`handler` only works with types implementing `from_frame()`. If you want to
inject arbitrary types, you can use `@inject()`. 

Consider the following example:

``` python
import sqlite3

def get_db(_: Frame):
    return sqlite3.connect(":memory:")


@inject(db=get_db)
async def on_authorize(call: Call, db: sqlite3.Connection):
    id_tag = call.payload['idTag']
    # Now look up the id tag in the database.
    # NOTE: THIS QUERY IS VULNERABLE TO SQL INJECTIONS
    # db.cursor().execute(f"SELECT * FROM id_tags where id = '{id_tag}')
    return call.create_call_result(payload={"idTagInfo": {"status": "Accepted"}})

app = route("Authorize", handler(on_authorize))
```

## Open points

1. How to implement equivalent of [`@after()`](https://github.com/mobilityhouse/ocpp/blob/master/ocpp/routing.py#L58-L79) handler?

Assume a charger receives a `TriggerMessage` request to trigger a
`StatusNotification`. It has to provide a response first, before sending the
`StatusNotification`. The `ocpp` package provides a `@after()` decorator. `zeegat`
must provide an API to allow users executing code after a specific request has
been received.

3. How to provide (indirect) access to the websocket so `Service`s can send requests?

# License

[MIT](LICENSE)
