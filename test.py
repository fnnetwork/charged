import requests

ROTATING_PROXY = "http://hknlieja-rotate:ox0xi8w7ukfj@p.webshare.io:80"  # Your proxy

def test_rotation():
    session = requests.Session()
    session.proxies = {"http": ROTATING_PROXY, "https": ROTATING_PROXY}
    for i in range(3):
        try:
            response = session.get("https://api.ipify.org?format=json", timeout=10)
            ip = response.json()['ip']
            print(f"Request {i+1} IP: {ip}")
            response = session.get("https://go.mc.edu/register/form?cmd=payment", timeout=10)
            print(f"Request {i+1} Status: {response.status_code}, Response: {response.text[:100]}")
        except Exception as e:
            print(f"Request {i+1} failed: {str(e)}")
        time.sleep(2)

test_rotation()