import base64
from functools import lru_cache
import json
import logging
import os
from pathlib import Path
import re
import secrets
from urllib.parse import urlsplit


LOGGER = logging.getLogger(__name__)
CODE = re.compile(r"[A-Za-z0-9_-]{8}")
HOME = Path(__file__).with_name("index.html").read_text(encoding="utf-8")


def response(status, body="", content_type="application/json; charset=utf-8", **headers):
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": content_type,
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
            **headers,
        },
        "body": body,
    }


def json_response(status, **data):
    return response(status, json.dumps(data))


def valid_url(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 2048:
        return False
    if not value.isascii() or any(not char.isprintable() or char.isspace() for char in value):
        return False
    if "\\" in value:
        return False
    try:
        url = urlsplit(value)
        port = url.port  # Reading the port checks that it is valid.
    except ValueError:
        return False
    return bool(
        url.scheme in {"http", "https"}
        and url.hostname
        and url.username is None
        and (port is None or port > 0)
    )


def handle(method, path, body, store):
    if method == "GET" and path == "/":
        return response(200, HOME, "text/html; charset=utf-8")

    if method == "POST" and path == "/api/links":
        if len(body) > 8192:
            return json_response(413, error="The request is too large.")
        try:
            data = json.loads(body)
        except (ValueError, TypeError):
            return json_response(400, error="Send a JSON object with a URL.")
        destination = data.get("url") if isinstance(data, dict) else None
        if not valid_url(destination):
            return json_response(400, error="Enter a valid HTTP or HTTPS URL.")
        for _ in range(5):
            code = secrets.token_urlsafe(6)
            if store.create(code, destination):
                return json_response(201, code=code, path=f"/r/{code}", visits=0)
        return json_response(503, error="Could not create a short link. Try again.")

    prefix, _, code = path.rpartition("/")
    if method == "GET" and CODE.fullmatch(code):
        if prefix == "/r":
            destination = store.visit(code)
            if destination is not None:
                return response(302, Location=destination)
        elif prefix == "/api/stats":
            visits = store.count(code)
            if visits is not None:
                return json_response(200, code=code, visits=visits)

    return json_response(404, error="This link or page could not be found.")


class DynamoLinks:
    def __init__(self, table):
        self.table = table

    def create(self, code, destination):
        try:
            self.table.put_item(
                Item={"code": code, "destination": destination, "visits": 0},
                ConditionExpression="attribute_not_exists(code)",
            )
        except self.table.meta.client.exceptions.ConditionalCheckFailedException:
            return False
        return True

    def visit(self, code):
        try:
            result = self.table.update_item(
                Key={"code": code},
                UpdateExpression="ADD visits :one",
                ExpressionAttributeValues={":one": 1},
                ConditionExpression="attribute_exists(code)",
                ReturnValues="ALL_NEW",
            )
        except self.table.meta.client.exceptions.ConditionalCheckFailedException:
            return None
        return result["Attributes"]["destination"]

    def count(self, code):
        result = self.table.get_item(Key={"code": code}, ConsistentRead=True)
        item = result.get("Item")
        return int(item["visits"]) if item else None


@lru_cache(maxsize=1)
def cloud_store():
    import boto3

    return DynamoLinks(boto3.resource("dynamodb").Table(os.environ["LINKS_TABLE"]))


def lambda_handler(event, context):
    try:
        body = event.get("body") or ""
        if event.get("isBase64Encoded"):
            body = base64.b64decode(body)
        return handle(
            event["requestContext"]["http"]["method"], event["rawPath"], body, cloud_store()
        )
    except Exception:
        LOGGER.exception("Request failed")
        return json_response(500, error="The app could not complete the request.")
