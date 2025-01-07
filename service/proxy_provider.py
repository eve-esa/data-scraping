import random
import requests
from bs4 import BeautifulSoup

from helper.singleton import singleton


@singleton
class ProxyProvider:
    def __init__(self):
        # Get a free proxy list from proxylist.geonode.com and free-proxy-list.net
        self._proxies = []

        # from proxylist.geonode.com
        try:
            response = requests.get(
                "https://proxylist.geonode.com/api/proxy-list?limit=100&page=1&sort_by=lastChecked&sort_type=desc&protocols=http%2Chttps&anonymityLevel=elite&anonymityLevel=anonymous")
            data = response.json()
            for proxy in data["data"]:
                if proxy["protocols"][0] in ["http", "https"]:
                    self._proxies.append(f"{proxy['protocols'][0]}://{proxy['ip']}:{proxy['port']}")
        except:
            pass

        # from free-proxy-list.net
        try:
            response = requests.get("https://free-proxy-list.net/")
            soup = BeautifulSoup(response.text, "html.parser")
            for row in soup.find("table").find_all("tr")[1:]:
                cols = row.find_all("td")
                if len(cols) > 6:
                    ip = cols[0].text
                    port = cols[1].text
                    https = cols[6].text
                    if https == "yes":
                        self._proxies.append(f"https://{ip}:{port}")
        except:
            pass

    def find_proxy(self) -> str | None:
        """
        Find a working proxy from the list of proxies

        Returns:
            str | None: A working proxy or None if no working proxy is found
        """
        # Select a random working proxy
        working_proxy = None
        while self._proxies and not working_proxy:
            test_proxy = random.choice(self._proxies)

            # Test if the proxy is working by sending a request to google.com
            try:
                response = requests.get(
                    "https://www.google.com",
                    proxies={"http": test_proxy, "https": test_proxy},
                    timeout=10,
                    verify=False
                )
                if response.status_code != 200:
                    raise Exception("Invalid response")

                working_proxy = test_proxy
            except:
                self._proxies.remove(test_proxy)

        return working_proxy
