"""月更新管線：抓取 → 契約驗證 → 缺月偵測 → 冪等 upsert → 重生看板。

流程：抓取 → 契約驗證 → 缺月偵測 → 冪等 upsert → 重生看板 → append 執行紀錄。

**兩件規格沒寫、但實跑才知道的事**（2026-08-08 實測，勿照規格字面實作）：

1. 規格寫的 `data.gov.tw/api/v2/rest/dataset/7164` **只回中繼資料，不是 CSV**。
   真正的檔案在中繼資料的 `distribution[0].resourceDownloadUrl`，**必須兩段式取用**。
2. **`data.gov.tw` 會擋 Python 的預設 User-Agent**——`urllib` 直打得到 403。
   必須帶瀏覽器 UA。照抄 urllib 範例會整支掛掉。

**缺月偵測**：政府資料更新有延遲。最新月份若未前進，記 log 後正常結束（退出碼 0），
**不視為錯誤**——月更新排程不該因為上游還沒發布就整天噴警報。

**契約不過就停**：不寫入資料庫、不動既有快照、退出碼 1。

用法：
    .\\.venv\\Scripts\\python.exe src\\update_monthly.py            # 正常執行
    .\\.venv\\Scripts\\python.exe src\\update_monthly.py --dry-run  # 只抓取與驗證，不寫入
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
RAW = ROOT / "data" / "raw"
LOGS = ROOT / "logs"
RUN_LOG = LOGS / "update-runs.log"

DATASET_ID = "7164"
SNAPSHOT = RAW / "ncc_7164_寬頻上網帳號數.csv"
META_URL = f"https://data.gov.tw/api/v2/rest/dataset/{DATASET_ID}"

# 陷阱 2：data.gov.tw 擋預設的 Python UA
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
TIMEOUT = 60

PY = sys.executable


def log(line: str) -> None:
    print(line)
    LOGS.mkdir(exist_ok=True)
    with RUN_LOG.open("a", encoding="utf-8") as fh:
        fh.write(f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}  {line}\n")


def encode_url(url: str) -> str:
    """把 URL 裡的非 ASCII 字元百分比編碼。

    **第三個規格沒寫的坑**：中繼資料回傳的 `resourceDownloadUrl` 內含**中文字元**
    （`filedisplay=寬頻上網帳號數.csv`），而 HTTP 請求行只能是 ASCII——
    直接丟給 urllib 會 `UnicodeEncodeError`，錯誤訊息還指向 http.client 內部，
    第一眼看不出是 URL 的問題。
    """
    p = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((
        p.scheme, p.netloc,
        urllib.parse.quote(p.path, safe="/%"),
        urllib.parse.quote(p.query, safe="=&%"),
        p.fragment,
    ))


def get(url: str) -> bytes:
    req = urllib.request.Request(encode_url(url), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read()


def latest_period(path: Path) -> tuple[int, int]:
    """讀出檔案裡最新的年月（民國轉西元）。"""
    with path.open(encoding="utf-8-sig", newline="") as fh:
        periods = []
        for row in csv.DictReader(fh):
            roc, month = row["年月"].split("/")
            periods.append((int(roc) + 1911, int(month)))
    return max(periods)


def run(script: str, *args: str) -> int:
    return subprocess.run([PY, str(SRC / script), *args], cwd=ROOT).returncode


def main() -> int:
    dry = "--dry-run" in sys.argv
    log(f"=== 月更新開始{'（dry-run）' if dry else ''} ===")

    # ── 1. 兩段式取用 ────────────────────────────────────────────────
    meta = json.loads(get(META_URL))["result"]
    dist = meta["distribution"][0]
    url = dist["resourceDownloadUrl"]
    log(f"中繼資料 OK：{meta['title']}　上游更新於 {meta.get('modifiedDate')}")
    log(f"檔案位址（取自 distribution[0]）：{url[:96]}…")

    staged = Path(tempfile.mkdtemp(prefix="ncc_")) / SNAPSHOT.name
    staged.write_bytes(get(url))
    log(f"已下載到暫存：{staged.stat().st_size:,} bytes")

    # ── 2. 缺月偵測（在驗證之前，因為沒前進就沒必要往下跑）────────────
    cur = latest_period(SNAPSHOT)
    new = latest_period(staged)
    log(f"最新月份：本地 {cur[0]}-{cur[1]:02d}　上游 {new[0]}-{new[1]:02d}")

    if new <= cur:
        log("上游尚未發布新月份 → 正常結束，不視為錯誤（政府資料更新有延遲）")
        log("=== 月更新結束（無變更）===\n")
        return 0

    # ── 3. 契約驗證（先在暫存檔上驗，過了才動既有快照）────────────────
    backup = staged.with_suffix(".snapshot.bak")
    shutil.copy2(SNAPSHOT, backup)
    shutil.copy2(staged, SNAPSHOT)
    log("契約驗證（--allow-growth：僅放寬列數與結束月，結構檢查維持嚴格）…")
    rc = run("validate_contracts.py", "--allow-growth")
    if rc != 0:
        shutil.copy2(backup, SNAPSHOT)          # 還原，絕不留下半套狀態
        log("❌ 契約未通過 → 已還原既有快照，未寫入資料庫。退出碼 1")
        return 1
    log("✅ 契約通過")

    rc = run("splice_check.py")
    if rc != 0:
        shutil.copy2(backup, SNAPSHOT)
        log("❌ 接合校驗未通過 → 已還原既有快照，未寫入資料庫。退出碼 1")
        return 1
    log("✅ 接合校驗通過")

    if dry:
        shutil.copy2(backup, SNAPSHOT)
        log("dry-run：已還原快照，未寫入資料庫、未重生看板")
        log("=== 月更新結束（dry-run）===\n")
        return 0

    # ── 4. 冪等 upsert ＋ 重生看板 ───────────────────────────────────
    if run("load_postgres.py", "--verify") != 0:
        log("❌ 落庫或冪等驗證失敗。退出碼 1")
        return 1
    log("✅ 落庫完成，冪等驗證通過")

    if run("compute_metrics.py") != 0:
        log("❌ 指標自檢失敗。退出碼 1")
        return 1
    log("✅ 指標自檢通過")

    if run("build_dashboard.py") != 0:
        log("❌ 看板重生失敗。退出碼 1")
        return 1

    log(f"✅ 看板已重生（資料截止 {new[0]}-{new[1]:02d}）")
    log(f"=== 月更新完成：{cur[0]}-{cur[1]:02d} → {new[0]}-{new[1]:02d} ===\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
