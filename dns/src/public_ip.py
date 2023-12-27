import requests


def get_public_ip() -> str:
    ip_url = "https://ifconfig.me"
    public_ip = requests.request("GET", ip_url)
    if public_ip.ok:
        return public_ip.text
