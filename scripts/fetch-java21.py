"""Download a checksum-verified Eclipse Temurin JDK into this project only."""
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen
import zipfile

root = Path(__file__).resolve().parents[1]
runtime = root / ".runtime"
url = "https://api.github.com/repos/adoptium/temurin21-binaries/releases/latest"
with urlopen(Request(url, headers={"User-Agent": "ScholarshipMapCourseProject"}), timeout=30) as response:
    assets = json.load(response)["assets"]
package = next(asset for asset in assets if asset["name"].startswith("OpenJDK21U-jdk_x64_windows_hotspot_")
               and asset["name"].endswith(".zip"))
expected = package.get("digest", "").removeprefix("sha256:")
if len(expected) != 64:
    checksum = next(asset for asset in assets if asset["name"] == package["name"] + ".sha256.txt")
    with urlopen(checksum["browser_download_url"], timeout=30) as response:
        expected = response.read().decode().split()[0]
archive = runtime / "downloads" / package["name"]
archive.parent.mkdir(parents=True, exist_ok=True)
if not archive.exists():
    with urlopen(package["browser_download_url"], timeout=60) as response, archive.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
with archive.open("rb") as source:
    if hashlib.file_digest(source, "sha256").hexdigest() != expected:
        raise RuntimeError("JDK checksum mismatch; remove the incomplete archive and retry")
with zipfile.ZipFile(archive) as zipped:
    for member in zipped.infolist():
        if not (runtime / member.filename).resolve().is_relative_to(runtime.resolve()):
            raise RuntimeError("Archive path outside project runtime")
    top = zipped.namelist()[0].split("/")[0]
    zipped.extractall(runtime)
java_home = runtime / top
(runtime / "java-home.txt").write_text(str(java_home), encoding="utf8")
print("Verified Java 21:", java_home, flush=True)
