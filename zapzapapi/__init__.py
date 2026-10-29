"""Official Python SDK for the ZapZap API (https://zapzapapi.com).

Usage::

    from zapzapapi import ZapZapClient

    client = ZapZapClient(api_key="...", api_secret="...")
    account = client.account.get()
    client.instance("instance-id").send_text("5511999999999", "Hello!")
"""

from .client import ZapZapClient, InstanceContext
from .errors import ZapZapError

__version__ = "1.0.0"
__all__ = ["ZapZapClient", "InstanceContext", "ZapZapError", "__version__"]
