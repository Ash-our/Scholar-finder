import time
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx

USER_AGENT = "ScholarshipMapCourseProject/0.1"


class PublicClient:
    def __init__(self, hosts, delay=1.0):
        self.hosts = set(hosts)
        self.delay = delay
        self.last_request = {}
        self.robots = {}
        self.client = httpx.Client(timeout=25, headers={"User-Agent": USER_AGENT}, follow_redirects=False)

    def _request(self, url):
        for _ in range(5):
            host = urlsplit(url).hostname
            if host not in self.hosts or urlsplit(url).scheme != "https":
                raise ValueError("Collection URL is outside the configured public source")
            elapsed = time.monotonic() - self.last_request.get(host, 0)
            time.sleep(max(0, self.delay - elapsed))
            self.last_request[host] = time.monotonic()
            response = self.client.get(url)
            if response.is_redirect:
                url = urljoin(url, response.headers["location"])
                continue
            return response
        raise ValueError("Too many source redirects")

    def get(self, url):
        origin = f"https://{urlsplit(url).netloc}"
        if origin not in self.robots:
            response = self._request(origin + "/robots.txt")
            if response.status_code not in {200, 404}:
                response.raise_for_status()
            rules = RobotFileParser()
            rules.parse(response.text.splitlines() if response.status_code == 200 else [])
            self.robots[origin] = rules
            self.delay = max(self.delay, rules.crawl_delay(USER_AGENT) or 0)
        if not self.robots[origin].can_fetch(USER_AGENT, url):
            raise PermissionError("The source's robots policy disallows this path")
        error = None
        for attempt in range(3):
            try:
                response = self._request(url)
                response.raise_for_status()
                if len(response.content) > 3_000_000:
                    raise ValueError("Source page exceeds the collection size limit")
                return response.text
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                error = exc
                if attempt < 2:
                    time.sleep(2 ** attempt)
        raise error

    def close(self):
        self.client.close()
