"""Fetch verified portable Windows services into the ignored project runtime.

No service, system installation, or registry changes are made. Java 21 must
already be available (the local JetBrains runtime is suitable).
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import tarfile
from urllib.request import urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".runtime"
DOWNLOADS = RUNTIME / "downloads"


def download(url: str, target: Path) -> None:
    if target.exists():
        return
    with urlopen(url, timeout=60) as response, target.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)


def mongodb() -> None:
    with urlopen("https://downloads.mongodb.org/current.json", timeout=30) as response:
        versions = json.load(response)["versions"]
    release = next(v for v in versions if v["version"].startswith("8.0."))
    archive = next(d["archive"] for d in release["downloads"]
                   if d.get("target") == "windows" and d.get("arch") == "x86_64")
    target = DOWNLOADS / archive["url"].rsplit("/", 1)[-1]
    download(archive["url"], target)
    if hashlib.file_digest(target.open("rb"), "sha256").hexdigest() != archive["sha256"]:
        raise RuntimeError("MongoDB archive checksum mismatch; remove the incomplete download and retry")
    with zipfile.ZipFile(target) as package:
        for member in package.infolist():
            if not (RUNTIME / member.filename).resolve().is_relative_to(RUNTIME.resolve()):
                raise RuntimeError("Archive path outside project runtime")
        package.extractall(RUNTIME)
    print(f"MongoDB {release['version']} verified and extracted", flush=True)


def kafka() -> None:
    name = "kafka_2.13-3.9.1.tgz"
    url = "https://archive.apache.org/dist/kafka/3.9.1/" + name
    target = DOWNLOADS / name
    with urlopen(url + ".sha512", timeout=30) as response:
        checksum_text = response.read().decode()
    expected = "".join(re.findall(r"\b[0-9a-fA-F]{8}\b", checksum_text))
    continuous = re.search(r"[0-9a-fA-F]{128}", checksum_text)
    if continuous:
        expected = continuous.group()
    if len(expected) != 128:
        raise RuntimeError("Could not parse Apache SHA512 checksum")
    download(url, target)
    if hashlib.file_digest(target.open("rb"), "sha512").hexdigest().lower() != expected.lower():
        raise RuntimeError("Kafka archive checksum mismatch; remove the incomplete download and retry")
    with tarfile.open(target) as package:
        package.extractall(RUNTIME, filter="data")
    print("Kafka 3.9.1 verified and extracted", flush=True)


if __name__ == "__main__":
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        for result in pool.map(lambda fn: fn(), [mongodb, kafka]):
            pass
