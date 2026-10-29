"""HTTP client and resource helpers for the ZapZap API."""

import requests

from .errors import ZapZapError

DEFAULT_BASE_URL = "https://api.zapzapapi.com/api/v1"


def _clean(data):
    """Drop keys whose value is None so optional fields are not sent."""
    if not isinstance(data, dict):
        return data
    return {k: v for k, v in data.items() if v is not None}


class ZapZapClient(object):
    """Client for the ZapZap public API.

    Args:
        api_key: Your ``x-api-key`` credential (from https://app.zapzapapi.com).
        api_secret: Your ``x-api-secret`` credential.
        base_url: API base URL. Defaults to the production endpoint.
        timeout: Per-request timeout in seconds (default 30).
        session: Optional pre-configured ``requests.Session``.
    """

    def __init__(
        self,
        api_key,
        api_secret,
        base_url=DEFAULT_BASE_URL,
        timeout=30,
        session=None,
    ):
        if not api_key or not api_secret:
            raise ValueError("api_key and api_secret are required")

        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = session or requests.Session()

        # Resource namespaces
        self.account = AccountResource(self)
        self.instances = InstancesResource(self)
        self.webhook = WebhookResource(self)

    # -- transport -----------------------------------------------------------

    def request(self, method, path, json=None, params=None):
        """Perform a request and return the decoded JSON body.

        Raises:
            ZapZapError: on connection failures or non-2xx responses.
        """
        url = self.base_url + path
        headers = {
            "x-api-key": self.api_key,
            "x-api-secret": self.api_secret,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        try:
            resp = self._session.request(
                method=method,
                url=url,
                json=_clean(json) if json is not None else None,
                params=_clean(params) if params is not None else None,
                headers=headers,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise ZapZapError("Request failed: {}".format(exc))

        return self._handle(resp)

    @staticmethod
    def _handle(resp):
        body = None
        try:
            body = resp.json()
        except ValueError:
            body = resp.text or None

        if not (200 <= resp.status_code < 300):
            message = "HTTP {}".format(resp.status_code)
            if isinstance(body, dict):
                message = body.get("error") or body.get("message") or message
            elif isinstance(body, str) and body:
                message = body
            raise ZapZapError(message, status_code=resp.status_code, response=body)

        return body

    # -- per-instance entry point -------------------------------------------

    def instance(self, instance_id):
        """Return a context bound to a specific instance for WhatsApp actions."""
        return InstanceContext(self, instance_id)


class AccountResource(object):
    """``/account`` endpoints."""

    def __init__(self, client):
        self._client = client

    def get(self):
        """GET /account — account data: name, email, balance, billing_day, status."""
        return self._client.request("GET", "/account")


class InstancesResource(object):
    """``/instances`` management endpoints."""

    def __init__(self, client):
        self._client = client

    def list(self):
        """GET /instances — list all WhatsApp instances of the account."""
        return self._client.request("GET", "/instances")

    def cost(self):
        """GET /instances/cost — cost to create a new instance."""
        return self._client.request("GET", "/instances/cost")

    def create(self, name, system_name=None, metadata=None):
        """POST /instances — create a new instance (debits balance).

        Args:
            name: Instance name. Only letters, numbers, ``_`` and ``-``.
            system_name: Optional display name shown on WhatsApp (``systemName``).
            metadata: Optional free-form dict echoed back in webhooks.
        """
        payload = {"name": name, "systemName": system_name, "metadata": metadata}
        return self._client.request("POST", "/instances", json=payload)

    def get(self, instance_id):
        """GET /instances/{id} — details of a single instance."""
        return self._client.request("GET", "/instances/{}".format(instance_id))

    def update(self, instance_id, webhook_url=None, metadata=None):
        """PUT /instances/{id} — update ``webhook_url`` and/or ``metadata``."""
        payload = {"webhook_url": webhook_url, "metadata": metadata}
        return self._client.request(
            "PUT", "/instances/{}".format(instance_id), json=payload
        )

    def delete(self, instance_id):
        """DELETE /instances/{id} — soft delete; generates an activation-fee waiver."""
        return self._client.request("DELETE", "/instances/{}".format(instance_id))

    def qrcode(self, instance_id):
        """GET /instances/{id}/qrcode — QR code to connect WhatsApp."""
        return self._client.request(
            "GET", "/instances/{}/qrcode".format(instance_id)
        )


class WebhookResource(object):
    """``/instances/{id}/webhook`` endpoints."""

    def __init__(self, client):
        self._client = client

    def get(self, instance_id):
        """GET /instances/{id}/webhook — the configured webhook URL."""
        return self._client.request(
            "GET", "/instances/{}/webhook".format(instance_id)
        )

    def set(self, instance_id, webhook_url, events=None, exclude_messages=None):
        """PUT /instances/{id}/webhook — set/update the webhook URL.

        Args:
            webhook_url: Public HTTPS URL that receives events.
            events: Optional events filter (e.g. ``"messages,status"``). Empty = all.
            exclude_messages: Optional bool to exclude own messages (``excludeMessages``).
        """
        payload = {
            "webhook_url": webhook_url,
            "events": events,
            "excludeMessages": exclude_messages,
        }
        return self._client.request(
            "PUT", "/instances/{}/webhook".format(instance_id), json=payload
        )

    def test(self, instance_id, url=None):
        """POST /instances/{id}/webhook/test — send a test event to the webhook."""
        return self._client.request(
            "POST",
            "/instances/{}/webhook/test".format(instance_id),
            json={"url": url},
        )


class GroupResource(object):
    """``/{instanceId}/group/*`` endpoints (WhatsApp groups)."""

    def __init__(self, ctx):
        self._ctx = ctx

    def list(self, get_participants=None):
        """POST /{id}/group/list — list groups the instance belongs to."""
        return self._ctx.post("/group/list", {"getParticipants": get_participants})

    def info(self, groupjid, get_invite_link=None):
        """POST /{id}/group/info — details of a group."""
        return self._ctx.post(
            "/group/info", {"groupjid": groupjid, "getInviteLink": get_invite_link}
        )

    def create(self, name, participants):
        """POST /{id}/group/create — create a group.

        Args:
            name: Group name.
            participants: List of numbers (with DDI).
        """
        return self._ctx.post(
            "/group/create", {"name": name, "participants": participants}
        )

    def leave(self, groupjid):
        """POST /{id}/group/leave — leave a group."""
        return self._ctx.post("/group/leave", {"groupjid": groupjid})

    def update_participants(self, groupjid, action, participants):
        """POST /{id}/group/updateParticipants — add/remove/promote/demote members.

        Args:
            action: One of ``add``, ``remove``, ``promote``, ``demote``.
            participants: List of numbers (with DDI).
        """
        return self._ctx.post(
            "/group/updateParticipants",
            {"groupjid": groupjid, "action": action, "participants": participants},
        )

    def update_name(self, groupjid, name):
        """POST /{id}/group/updateName — rename a group."""
        return self._ctx.post(
            "/group/updateName", {"groupjid": groupjid, "name": name}
        )

    def update_description(self, groupjid, description):
        """POST /{id}/group/updateDescription — set a group's description."""
        return self._ctx.post(
            "/group/updateDescription",
            {"groupjid": groupjid, "description": description},
        )

    def join(self, invitecode):
        """POST /{id}/group/join — join a group by invite code."""
        return self._ctx.post("/group/join", {"invitecode": invitecode})

    def invite_info(self, invitecode):
        """POST /{id}/group/inviteInfo — inspect a group invite."""
        return self._ctx.post("/group/inviteInfo", {"invitecode": invitecode})


class InstanceContext(object):
    """Bound helper for WhatsApp actions on a specific instance.

    All paths are proxied to ``/{instanceId}/...`` on the ZapZap API.
    """

    def __init__(self, client, instance_id):
        self._client = client
        self.instance_id = instance_id
        self.group = GroupResource(self)

    def _path(self, suffix):
        return "/{}{}".format(self.instance_id, suffix)

    def post(self, suffix, json=None):
        """POST to ``/{instanceId}{suffix}`` (low-level escape hatch)."""
        return self._client.request("POST", self._path(suffix), json=json)

    def get(self, suffix, params=None):
        """GET ``/{instanceId}{suffix}`` (low-level escape hatch)."""
        return self._client.request("GET", self._path(suffix), params=params)

    # -- messaging -----------------------------------------------------------

    def send_text(self, number, text, mentions=None, delay=None, reply_id=None):
        """POST /{id}/send/text — send a plain text message.

        Args:
            number: Destination with DDI (e.g. ``5511999999999``).
            text: Message body.
            mentions: Optional ``"all"`` or comma-separated numbers (groups only).
            delay: Optional delay in ms before sending.
            reply_id: Optional message id to reply to (``replyid``).
        """
        payload = {
            "number": number,
            "text": text,
            "mentions": mentions,
            "delay": delay,
            "replyid": reply_id,
        }
        return self.post("/send/text", payload)

    def send_media(
        self,
        number,
        type,
        file,
        text=None,
        mentions=None,
        doc_name=None,
        delay=None,
    ):
        """POST /{id}/send/media — send media from a public URL.

        Args:
            number: Destination with DDI.
            type: One of ``image``, ``video``, ``videoplay``, ``audio``, ``ptt``,
                ``myaudio``, ``ptv``, ``document``, ``sticker``.
            file: Public URL of the file.
            text: Optional caption (images and videos).
            mentions: Optional ``"all"`` or comma-separated numbers (groups only).
            doc_name: File name shown in chat (``docName``); required for ``document``.
            delay: Optional delay in ms before sending.
        """
        payload = {
            "number": number,
            "type": type,
            "file": file,
            "text": text,
            "mentions": mentions,
            "docName": doc_name,
            "delay": delay,
        }
        return self.post("/send/media", payload)

    def send_menu(self, number, **options):
        """POST /{id}/send/menu — send an interactive menu (buttons/list/poll).

        ``number`` is required; all other fields are passed through verbatim so
        the full UazAPI menu payload is supported without the SDK constraining it.
        """
        payload = dict(options)
        payload["number"] = number
        return self.post("/send/menu", payload)

    def react(self, number, id, emoji):
        """POST /{id}/message/react — react to a message with an emoji.

        Args:
            number: Contact number.
            id: Message id in ``OWNER:MSGID`` format
                (e.g. ``5511991515364:2A6E2F02CE4125FDBA1B``).
            emoji: Reaction emoji; empty string removes the reaction.
        """
        payload = {"number": number, "id": id, "emoji": emoji}
        return self.post("/message/react", payload)

    def status(self):
        """GET /{id}/instance/status — WhatsApp connection status."""
        return self.get("/instance/status")
