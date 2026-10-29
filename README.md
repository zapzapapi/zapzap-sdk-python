# ZapZap API - Python SDK

Official Python SDK for the [ZapZap API](https://zapzapapi.com), a multi-tenant
WhatsApp platform. Manage instances, connect numbers and send WhatsApp messages
from Python.

- Base URL: `https://api.zapzapapi.com/api/v1`
- Authentication: `x-api-key` + `x-api-secret` headers
- Full reference: https://api.zapzapapi.com/llms.txt

## Installation

```bash
pip install zapzapapi
```

Requires Python 3.8+ and [`requests`](https://pypi.org/project/requests/).

## Authentication

Get your API key and secret from the ZapZap panel at
https://app.zapzapapi.com (Settings). Never hardcode them: load them from
environment variables or a secrets manager.

```python
import os
from zapzapapi import ZapZapClient

client = ZapZapClient(
    api_key=os.environ["ZAPZAP_API_KEY"],
    api_secret=os.environ["ZAPZAP_API_SECRET"],
)
```

## Quickstart

```python
# Account
account = client.account.get()
print(account["balance"])

# Instances
instances = client.instances.list()
created = client.instances.create("my-instance", metadata={"clientId": "123"})
instance_id = created["instance"]["id"]

qr = client.instances.qrcode(instance_id)   # scan with your phone
client.instances.update(instance_id, webhook_url="https://example.com/webhook")

# Webhook
client.webhook.set(instance_id, "https://example.com/webhook", events="messages,status")
print(client.webhook.get(instance_id))

# Messaging (bound to one instance)
wa = client.instance(instance_id)
wa.status()
wa.send_text("5511999999999", "Hello from Python!")
wa.send_media("5511999999999", type="image", file="https://example.com/photo.jpg", text="Look!")
wa.react("5511999999999", id="5511991515364:2A6E2F02CE4125FDBA1B", emoji="👍")

# Groups
wa.group.list()
wa.group.create("My Group", ["5511999999999", "5511888888888"])
```

## Error handling

Any non-2xx response or transport failure raises `ZapZapError`:

```python
from zapzapapi import ZapZapError

try:
    client.instances.create("bad name!")
except ZapZapError as err:
    print(err.status_code)  # e.g. 402 (insufficient balance), 409 (name exists)
    print(err.message)      # message from the API body when available
    print(err.response)     # parsed response body
```

## API surface

| Area | Method | Endpoint |
|------|--------|----------|
| Account | `client.account.get()` | `GET /account` |
| Instances | `client.instances.list()` | `GET /instances` |
| Instances | `client.instances.cost()` | `GET /instances/cost` |
| Instances | `client.instances.create(name, system_name=None, metadata=None)` | `POST /instances` |
| Instances | `client.instances.get(id)` | `GET /instances/{id}` |
| Instances | `client.instances.update(id, webhook_url=None, metadata=None)` | `PUT /instances/{id}` |
| Instances | `client.instances.delete(id)` | `DELETE /instances/{id}` |
| Instances | `client.instances.qrcode(id)` | `GET /instances/{id}/qrcode` |
| Webhook | `client.webhook.get(id)` | `GET /instances/{id}/webhook` |
| Webhook | `client.webhook.set(id, webhook_url, events=None, exclude_messages=None)` | `PUT /instances/{id}/webhook` |
| Webhook | `client.webhook.test(id, url=None)` | `POST /instances/{id}/webhook/test` |
| Messaging | `client.instance(id).send_text(number, text, ...)` | `POST /{id}/send/text` |
| Messaging | `client.instance(id).send_media(number, type, file, ...)` | `POST /{id}/send/media` |
| Messaging | `client.instance(id).send_menu(number, **options)` | `POST /{id}/send/menu` |
| Messaging | `client.instance(id).react(number, id, emoji)` | `POST /{id}/message/react` |
| Status | `client.instance(id).status()` | `GET /{id}/instance/status` |
| Groups | `client.instance(id).group.*` | `POST /{id}/group/*` |

## License

MIT (c) GM Solutions Hub LTDA.
