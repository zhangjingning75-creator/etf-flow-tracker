import html
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone

OUTPUT_FILE = "data.json"

# jina.ai reader：免费的网页渲染中转服务，会先把目标网页正常渲染好，
# 再把渲染后的文字内容返回给我们，这样能绕开"直接用程序访问被网站拦截"的问题。
PROXY_PREFIX = "https://r.jina.ai/"
SOURCES = {
    "btc_etf": "https://www.tftc.io/bitcoin-etf-flows",
    "eth_etf": "https://www.tftc.io/ethereum-etf-flows",  # 尝试同网站的以太坊页面，格式应该跟BTC一致
}

MONTHS = {
    "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
    "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
    "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12",
}

PATTERN = re.compile(
    r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*,\s*"
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+"
    r"(\d{1,2}),\s*(\d{4})\s*[·:]\s*"
    r"([+\-\u2212])\$([\d,]+(?:\.\d+)?)([MB])?"
)


def fetch_text(url):
    full_url = PROXY_PREFIX + url
    req = urllib.request.Request(full_url, headers={"User-Agent": "Mozilla/5.0 (personal-etf-tracker/1.0)"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def parse_page(text):
    text = html.unescape(text)
    rows = {}
    for m in PATTERN.finditer(text):
        month, day, year, sign, amount, unit = m.groups()
        date_str = f"{year}-{MONTHS[month]}-{int(day):02d}"
        value = float(amount.replace(",", ""))
        if unit == "B":
            value *= 1000
        if sign in ("-", "\u2212"):
            value = -value
        rows[date_str] = round(value, 1)
    return rows


def update_series(key, url, existing):
    try:
        page_text = fetch_text(url)
    except Exception as e:
        print(f"[{key}] 网页抓取失败，跳过本次更新：{e}")
        return existing, False

    scraped = parse_page(page_text)
    if len(scraped) < 5:
        print(f"[{key}] 这次只识别出 {len(scraped)} 条记录，太少了，可能页面结构变了，跳过本次更新。")
        return existing, False

    existing_map = {r["date"]: r["flow"] for r in existing}
    merged = {**existing_map, **scraped}
    rows = [{"date": d, "flow": v} for d, v in sorted(merged.items())]
    print(f"[{key}] 更新成功：本次识别到 {len(scraped)} 条，合并后共 {len(rows)} 条，最新一条：{rows[-1]}")
    return rows[-400:], True


def main():
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            output = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        output = {"updated_at": None, "btc_etf": [], "eth_etf": []}

    any_success = False
    for key, url in SOURCES.items():
        new_rows, ok = update_series(key, url, output.get(key, []))
        output[key] = new_rows
        any_success = any_success or ok

    if not any_success:
        print("本次两个数据源都没能成功识别，data.json 保持原样不变。")
        sys.exit(0)

    output["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC") + "（自动更新）"
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
