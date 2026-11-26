"""Fetch matching Hadoop 3.4.1 Windows native libraries, locally and pinned.

These are third-party CI builds of Apache Hadoop source (not ASF binaries).
The source/build workflow is https://github.com/notepass/hadoop-native-win-libs.
Linux/Docker does not need these files.
"""
import hashlib
from pathlib import Path
from urllib.request import urlopen
import zipfile

root = Path(__file__).resolve().parents[1]
url = "https://github.com/notepass/hadoop-native-win-libs/releases/download/rel/release-3.4.1/hadoop-win-utils.zip"
expected = "b1bb9daab246845b552a18b73e6c639deea5de79cc8e398315857fd34a5a10c1"
archive = root / ".runtime" / "downloads" / "hadoop-3.4.1-windows.zip"
archive.parent.mkdir(parents=True, exist_ok=True)
if not archive.exists():
    with urlopen(url, timeout=60) as response, archive.open("wb") as output:
        output.write(response.read())
with archive.open("rb") as stream:
    if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
        raise RuntimeError("Hadoop native archive checksum mismatch")
target = root / ".runtime" / "hadoop" / "bin"
target.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(archive) as package:
    for name in ["hadoop.dll", "winutils.exe"]:
        entries = [entry for entry in package.namelist() if Path(entry).name == name]
        if len(entries) != 1:
            raise RuntimeError("Unexpected native archive layout")
        (target / name).write_bytes(package.read(entries[0]))
print("Verified Hadoop 3.4.1 Windows libraries:", target)
