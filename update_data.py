import json
import sys
import urllib.request
from datetime import datetime, timezone

SOURCE_URL = "https://www.tftc.io/bitcoin-etf-flows/data.json"
OUTPUT_FILE = "data.json"

DATE_KEYS = ["date", "day", "d"]
FLOW_KEYS = ["total", "net", "flow", "value", "netFlow", "total_flow"]


def find_key(record, candidates):
    for k in candidates:
        if k in record:
            return k
    return None


def extract_rows(payload):
    candidate_lists = []
    if isinstance(payload, list):
        candidate_lists.append(payload)
    elif isinstance(payload, dict):
        for key in ["rows", "daily", "data", "flows", "days", "history"]:
            if key in payload and isinstance(payload[key], list):
                candidate_lists.append(payload[key])

    for lst in candidate_lists:
        if not lst or not isinstance(lst[0], dict):
            continue
        date_key = find_key(lst[0], DATE_KEYS)
        flow_key = find_key(lst[0], FLOW_KEYS)
        if not date_key or not flow_key:
            continue
        rows = []
        for item in lst:
            try:
                date_val = str(item[date_key])[:10]
                flow_val = float(item[flow_key])
                rows.append({"date": date_val, "flow": round(flow_val, 1)})
            except (KeyError, ValueError, TypeError):
                continue
        if len(rows) >= 10:
            rows.sort(key=lambda r: r["date"])
            return rows
    return None


def main():
    try:
        req = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "personal-etf-tracker/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"抓取失败，跳过本次更新，保留原有 data.json 内容：{e}")
        sys.exit(0)

    rows = extract_rows(payload)
    if not rows:
        print("没能从数据源里认出日期和净流入字段，源数据结构可能变了，跳过本次更新。")
        sys.exit(0)

    output = {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "rows": rows[-180:],
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"更新成功，共 {len(output['rows'])} 条记录，最新一条：{output['rows'][-1]}")


if __name__ == "__main__":
    main()
