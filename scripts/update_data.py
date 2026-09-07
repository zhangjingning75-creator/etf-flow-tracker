import html
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone

SOURCE_URL = "https://www.tftc.io/bitcoin-etf-flows"
OUTPUT_FILE = "data.json"

MONTHS = {
    "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
    "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
    "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12",
}

# 匹配形如 "Wednesday, Aug 19, 2026 · +$517.2M" 或 "Monday, Jul 13, 2026 · -$424.7M" 的文字片段
PATTERN = re.compile(
    r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*,\s*"
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+"
    r"(\d{1,2}),\s*(\d{4})\s*[·:]\s*"
    r"([+\-\u2212])\$([\d,]+(?:\.\d+)?)([MB])?"
)


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


def main():
    try:
        req = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "Mozilla/5.0 (personal-etf-tracker/1.0)"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            page_text = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"网页抓取失败，跳过本次更新，保留原有 data.json 内容：{e}")
        sys.exit(0)

    scraped = parse_page(page_text)
    if len(scraped) < 5:
        print(f"这次只从页面里识别出 {len(scraped)} 条记录，太少了，可能页面结构变了，跳过本次更新以免污染数据。")
        sys.exit(0)

    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            existing = json.load(f)
        existing_rows = {r["date"]: r["flow"] for r in existing.get("rows", [])}
    except (FileNotFoundError, json.JSONDecodeError):
        existing_rows = {}

    merged = {**existing_rows, **scraped}
    rows = [{"date": d, "flow": v} for d, v in sorted(merged.items())]

    output = {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "rows": rows[-400:],
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"更新成功：本次从网页识别到 {len(scraped)} 条，合并后共 {len(output['rows'])} 条记录，最新一条：{rows[-1]}")


if __name__ == "__main__":
    main()
