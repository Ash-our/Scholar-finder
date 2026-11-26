"""Download an official portable Cloudflare binary and verify its GitHub digest."""
from hashlib import sha256
import json
from pathlib import Path

import httpx

ROOT=Path(__file__).resolve().parents[1]


def main():
    response=httpx.get("https://api.github.com/repos/cloudflare/cloudflared/releases/latest",timeout=30)
    response.raise_for_status();release=response.json()
    asset=next(item for item in release["assets"] if item["name"]=="cloudflared-windows-amd64.exe")
    expected=asset.get("digest","")
    if not expected.startswith("sha256:"):
        raise RuntimeError("Official release does not provide a SHA-256 digest; manual verification required")
    folder=ROOT/".runtime"/"cloudflared";folder.mkdir(parents=True,exist_ok=True)
    target=folder/asset["name"]
    if not target.exists() or "sha256:"+sha256(target.read_bytes()).hexdigest()!=expected:
        binary=httpx.get(asset["browser_download_url"],follow_redirects=True,timeout=120)
        binary.raise_for_status()
        if "sha256:"+sha256(binary.content).hexdigest()!=expected:
            raise RuntimeError("Cloudflare binary checksum mismatch")
        target.write_bytes(binary.content)
    (folder/"provenance.json").write_text(json.dumps({"version":release["tag_name"],"url":asset["browser_download_url"],"digest":expected},indent=2)+"\n","utf8")
    print("Verified official cloudflared "+release["tag_name"])


if __name__=="__main__":main()
