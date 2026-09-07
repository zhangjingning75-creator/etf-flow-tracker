import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

OUTPUT_FILE = "yield.json"
API_KEY = os.environ.get("FRED_API_KEY", "")
SERIES_ID = "DGS10"  # 10年期美债收益率，FRED官方序列代码
URL = (
    f"https://api.stlouisfed.org/fred/series/observations"
    f"?series_id={SERIES_ID}&api_key={API_KEY}&file_type=json&sort_order=desc&limit=200"
)


def main():
    if not API_KEY:
        print("没有配置 FRED_API_KEY，跳过本次更新。请在仓库 Settings → Secrets 里添加这个密钥。")
        sys.exit(0)

    try:
        req = urllib.request.Request(URL, headers={"User-Agent": "personal-yield-tracker/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"抓取失败，跳过本次更新，保留原有数据：{e}")
        sys.exit(0)

    observations = payload.get("observations", [])
    rows = []
    for obs in observations:
        if obs.get("value") in (".", None, ""):
            continue  # FRED用 "." 表示当天没有数据（比如假日）
        try:
            rows.append({"date": obs["date"], "yield": float(obs["value"])})
        except (KeyError, ValueError):
            continue

    if len(rows) < 5:
        print("识别到的有效数据太少，跳过本次更新以免污染数据。")
        sys.exit(0)

    rows.sort(key=lambda r: r["date"])

    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            existing = json.load(f)
        existing_rows = {r["date"]: r["yield"] for r in existing.get("rows", [])}
    except (FileNotFoundError, json.JSONDecodeError):
        existing_rows = {}

    new_map = {r["date"]: r["yield"] for r in rows}
    merged = {**existing_rows, **new_map}
    final_rows = [{"date": d, "yield": v} for d, v in sorted(merged.items())]

    output = {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC") + "（自动更新，来源：FRED）",
        "rows": final_rows[-400:],
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"更新成功，共 {len(output['rows'])} 条记录，最新一条：{final_rows[-1]}")


if __name__ == "__main__":
    main()
