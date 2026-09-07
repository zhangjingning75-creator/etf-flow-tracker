import json
import urllib.request
from datetime import datetime, timezone

OUTPUT_FILE = "live.json"
URL = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd&include_24hr_change=true"


def main():
    try:
        req = urllib.request.Request(URL, headers={"User-Agent": "personal-live-price/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"实时价格抓取失败，跳过本次更新：{e}")
        return

    output = {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "btc": {
            "price": data.get("bitcoin", {}).get("usd"),
            "change_24h": data.get("bitcoin", {}).get("usd_24h_change"),
        },
        "eth": {
            "price": data.get("ethereum", {}).get("usd"),
            "change_24h": data.get("ethereum", {}).get("usd_24h_change"),
        },
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"更新成功：{output}")


if __name__ == "__main__":
    main()
