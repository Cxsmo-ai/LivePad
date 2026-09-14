
import json
import os
from pathlib import Path
import sys
import urllib.request
import uuid

def get_server():
    req = urllib.request.Request("https://api.gofile.io/servers", headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
    return data["data"]["servers"][0]["name"]

def upload_file(file_path: Path):
    server = get_server()
    url = f"https://{server}.gofile.io/contents/uploadfile"
    boundary = uuid.uuid4().hex
    
    filename = file_path.name
    file_size = file_path.stat().st_size
    print(f"Uploading {filename} ({round(file_size/1024/1024, 2)} MB) to {server}...")

    header = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode("utf-8")
    footer = f"\r\n--{boundary}--\r\n".encode("utf-8")

    # Read binary
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    data = header + file_bytes + footer
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "Mozilla/5.0",
        },
    )

    with urllib.request.urlopen(req) as resp:
        res_json = json.loads(resp.read().decode())

    if res_json.get("status") == "ok":
        link = res_json["data"]["downloadPage"]
        print(f"SUCCESS: {link}")
        return link
    else:
        print("Failed:", res_json)
        return None

if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("release/LivePad-Complete.zip")
    upload_file(target)

