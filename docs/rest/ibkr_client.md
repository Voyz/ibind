# IbkrClient

The `IbkrClient` class provides an interface to the [IBKR REST API][ibkr-endpoints].

It shares some basic configuration with the `IbkrWsClient`. See [IBind Configuration - Construction Parameters][ibind-configuration-construction-parameters] section for more.

Basic usage of `IbkrClient`:

```python
from ibind import IbkrClient

ibkr_client = IbkrClient()
ibkr_client.tickle()
```

See example ["rest_01_basic"][rest_01_basic] for a quick showcase of the basic REST setup.

The `IbkrClient` class is a concrete implementation of the abstract [`RestClient`][rest-client.py] class.

The `RestClient` provides a boilerplate support for common REST methods: `GET`, `POST` and `DELETE`, and handles the request/response processing of all API methods declared in the `IbkrClient`.

See [API Reference - IbkrClient][api-ibkr-client] for more.

# Mapped endpoints

Almost all endpoints defined in the [IBKR REST API][ibkr-endpoints] are mapped to `IbkrClient` methods. Currently, the endpoint sections that are still NOT mapped are:

* Alerts
* FA Allocation Management
* FYIs and Notifications

Note:

* IBKR endpoints are not documented in this documentation. Please refer to the official [IBKR REST API][ibkr-endpoints] reference for full documentation.
* Endpoints' API implementation is categorised into Python class mixins. See [API Reference - IbkrClient][api-ibkr-client] for full list of mixins and their methods.

# REST Results

Almost all methods in the `IbkrClient` return an instance of `Result` object. It is a [dataclass][dataclass] containing two fields:

* `data` - the data returned from the operation
* `request` - details of the request that resulted in this data, usually containing the URL and arguments used in the REST request to IBKR

This interface gives you additional information as to how `IbkrClient` communicated with the IBKR API. The `request` field facilitates debugging and ensuring the client library operates according to our expectations.

What this implies, is that to access the returned data of the REST API calls, you need to use the `.data` accessor:

```python
authentication_data = IbkrClient.authentication_status().data
```

There are very few methods that do not return `Result`. In all such cases it is explicitly stated in the documentation.

# Advanced API

Majority of the IBKR endpoints' mapping is implemented by performing a simple REST request. For example:

```python
class SessionMixin():
    def authentication_status(self: 'IbkrClient') -> Result:
        return self.post('iserver/auth/status')

    ...
```

In several cases, `IbkrClient` implements additional logic to allow more sophisticated interaction with the IBKR endpoints. See [Advanced REST][advanced-rest] page to learn about the advanced API concepts.

----

#### Next

Learn about the [Advanced REST][advanced-rest] concepts.


[ibkr-endpoints]: https://ibkrcampus.com/ibkr-api-page/cpapi-v1/#endpoints

[ibind-configuration-construction-parameters]: ../configuration.md#constructor-parameters

[rest-client.py]: https://github.com/Voyz/ibind/blob/master/ibind/base/rest_client.py

[ibkr-client-mixins]: https://github.com/Voyz/ibind/tree/master/ibind/client/ibkr_client_mixins

[dataclass]: https://docs.python.org/3/library/dataclasses.html

[advanced-rest]: ./advanced_rest.md

[api-ibkr-client]: ../api_reference/ibkr_client.md

[rest_01_basic]: https://github.com/Voyz/ibind/blob/master/examples/rest_01_basic.py

[rest_02_intermediate]: https://github.com/Voyz/ibind/blob/master/examples/rest_02_intermediate.py
