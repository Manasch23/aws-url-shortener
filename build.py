"""Embed the app in a small CloudFormation template for AWS CLI deployment."""

import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parent
LOCAL_HTML = 'HOME = Path(__file__).with_name("index.html").read_text(encoding="utf-8")'
API_MARKER = '<meta name="shortener-api-origin" content="">'


def build():
    template = json.loads((ROOT / "template.json").read_text(encoding="utf-8"))
    source = (ROOT / "src" / "app.py").read_text(encoding="utf-8")
    html = (ROOT / "src" / "index.html").read_text(encoding="utf-8")
    if source.count(LOCAL_HTML) != 1:
        raise ValueError("Expected one local HTML loader to replace.")

    code = source.replace(LOCAL_HTML, f"HOME = {html!r}", 1)
    compile(code, "index.py", "exec")
    template["Resources"]["Shortener"]["Properties"]["Code"]["ZipFile"] = code

    output = ROOT / ".build" / "stack.json"
    serialized = json.dumps(template, separators=(",", ":")).encode("ascii")
    if len(serialized) > 51_200:
        raise ValueError("The template exceeds CloudFormation's inline size limit.")
    output.parent.mkdir(exist_ok=True)
    output.write_bytes(serialized)
    print(f"Built {output}")


def build_pages(api_url):
    url = urlsplit(api_url)
    hostname = url.hostname or ""
    if (
        url.scheme != "https"
        or url.netloc != hostname
        or not hostname.endswith(".on.aws")
        or ".lambda-url." not in hostname
        or url.path not in {"", "/"}
        or url.query
        or url.fragment
    ):
        raise ValueError("Enter the HTTPS Lambda Function URL from the AppUrl output.")
    html = (ROOT / "src" / "index.html").read_text(encoding="utf-8")
    if html.count(API_MARKER) != 1:
        raise ValueError("Expected one API origin marker in index.html.")
    output = ROOT / "docs"
    output.mkdir(exist_ok=True)
    (output / "index.html").write_text(
        html.replace(API_MARKER, f'<meta name="shortener-api-origin" content="https://{hostname}">'),
        encoding="utf-8",
    )
    (output / ".nojekyll").touch()
    print(f"Built GitHub Pages files in {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", metavar="APP_URL", help="Build the GitHub Pages frontend.")
    args = parser.parse_args()
    if args.pages:
        build_pages(args.pages)
    else:
        build()
