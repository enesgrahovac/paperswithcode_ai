import json
from datetime import datetime


def handler(event, context):
    """
    A very small Lambda handler.

    • If you invoke it from the AWS console, it will reply
      “Hello, World”.
    • If you pass `{"name": "Alice"}` in the event payload,
      it will reply “Hello, Alice”.
    """
    name = event.get("name", "World")
    response = {
        "message": f"Hello, {name}!",
        "invoked_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }

    return {
        "statusCode": 200,
        "body": json.dumps(response),
        "headers": {"Content-Type": "application/json"},
    }