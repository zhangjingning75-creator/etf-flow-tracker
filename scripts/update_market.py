import json
import sys
import urllib.request
from datetime import datetime, timezone

OUTPUT_FILE = "market.json"
HEADERS = {"User-Agent": "personal-market-tracker/1.0 (+contact: personal use)"}


def fetch_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_ohlc(coin_id):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc?vs_currency=usd&days=90"
    raw = fetch_json(url)
    rows = []
    for ts, o, h, l, c in raw:
        date_str = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        rows.append({"date": date_str, "o": o, "h": h, "l": l, "c": c})
    rows.sort(key=lambda r: r["date"])
    return rows


def fetch_fear_greed():
    url = "https://api.alternative.me/fng/?limit=90&format=json"
    raw = fetch_json(url)
    rows = []
    for item in raw.get("data", []):
        date_str = datetime.fromtimestamp(int(item["timestamp"]), tz=timezone.utc).strftime("%Y-%m-%d")
        rows.append({
            "date": date_str,
            "value": int(item["value"]),
            "label": item.get("value_classification", ""),
        })
    rows.sort(key=lambda r: r["date"])
    return rows


def main():
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            output = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        output = {"updated_at": None, "btc": [], "eth": [], "fear_greed": []}

    ok_any = False

    try:
        output["btc"] = fetch_ohlc("bitcoin")
        ok_any = True
    except Exception as e:
        print(f"比特币价格抓取失败，保留原数据：{e}")

    try:
        output["eth"] = fetch_ohlc("ethereum")
        ok_any = True
    except Exception as e:
        print(f"以太坊价格抓取失败，保留原数据：{e}")

    try:
        output["fear_greed"] = fetch_fear_greed()
        ok_any = True
    except Exception as e:
        print(f"恐慌贪婪指数抓取失败，保留原数据：{e}")

    if not ok_any:
        print("三个数据源全部失败，本次不写入文件。")
        sys.exit(0)

    output["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"更新完成：BTC {len(output['btc'])}条，ETH {len(output['eth'])}条，恐慌贪婪指数 {len(output['fear_greed'])}条")


if __name__ == "__main__":
    main()
