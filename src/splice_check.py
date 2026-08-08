"""階段 2：接合校驗。

依規格第四節（已於看資料前存進 `logs/decisions.log`）：
    重疊期兩序列的月度差異中位數 > 5% → **放棄接合**，只呈現 7164（2019-01 起）。
**閾值 5% 已寫死，不得因看到結果而調整。**

只比對 ADSL／FTTX／Cable Modem 三欄。**絕不比對兩份的總計欄**——
27953 的總計含 PWLAN，7164 的小計固網不含（prompt 第二節陷阱 2）。

用法：
    .\\.venv\\Scripts\\python.exe src\\splice_check.py
退出碼：0 = 接合通過；1 = 依規則放棄接合。
"""

from __future__ import annotations

import statistics
import sys

from sources import (
    COMPARABLE,
    SPLICE_CUTOVER,
    TECH_NAME,
    load_7164,
    load_27953,
    overlap_periods,
    spliced,
)

THRESHOLD_PCT = 5.0  # 規格第四節，寫死


def index(records) -> dict[tuple[int, int, str], int]:
    return {(r.year, r.month, r.tech_code): r.accounts for r in records}


def main() -> int:
    print("階段 2：接合校驗")
    print("依據：docs/10-project-spec.md 第四節、5.2；閾值 5% 已預先登記，不得調整\n")

    a = index(load_7164())      # 主序列
    b = index(load_27953())     # 補早期
    periods = overlap_periods()

    print(f"重疊期：{periods[0][0]}-{periods[0][1]:02d} ~ "
          f"{periods[-1][0]}-{periods[-1][1]:02d}，共 {len(periods)} 期")
    print(f"比對欄位：{', '.join(COMPARABLE)}（**不比對總計欄**，兩份定義不同）")
    print(f"比對筆數：{len(periods)} 期 × {len(COMPARABLE)} 欄 = "
          f"{len(periods) * len(COMPARABLE)} 筆\n")

    # 差異定義：以 7164（主序列）為分母。此為規格未寫明、實作者自行選定的
    # 判準，理由：接合規則指定 7164 為主，分母取主序列語義一致。已記入 decision-trail。
    rows: list[tuple[str, str, int, int, int, float]] = []
    for period in periods:
        for tech in COMPARABLE:
            key = (*period, tech)
            v_a, v_b = a[key], b[key]
            delta = v_a - v_b
            pct = abs(delta) / v_a * 100 if v_a else (0.0 if delta == 0 else float("inf"))
            rows.append((f"{period[0]}-{period[1]:02d}", tech, v_a, v_b, delta, pct))

    all_pct = [r[5] for r in rows]
    median_pct, max_pct = statistics.median(all_pct), max(all_pct)
    exact = sum(1 for r in rows if r[4] == 0)

    # --- 逐月逐欄明細 -------------------------------------------------------
    print(f"{'年月':<9}{'技術別':<14}{'7164':>12}{'27953':>12}{'差':>8}{'差異%':>10}")
    print("-" * 66)
    for ym, tech, v_a, v_b, delta, pct in rows:
        print(f"{ym:<9}{TECH_NAME[tech]:<14}{v_a:>12,}{v_b:>12,}{delta:>8,}{pct:>9.4f}%")

    # --- 各技術別統計 -------------------------------------------------------
    print(f"\n{'技術別':<14}{'中位數':>12}{'最大':>12}{'完全相等':>12}")
    print("-" * 50)
    for tech in COMPARABLE:
        sub = [r[5] for r in rows if r[1] == tech]
        eq = sum(1 for r in rows if r[1] == tech and r[4] == 0)
        print(f"{TECH_NAME[tech]:<14}{statistics.median(sub):>11.4f}%"
              f"{max(sub):>11.4f}%{eq:>8}/{len(sub)}")

    # --- 判定 ---------------------------------------------------------------
    print(f"\n{'=' * 66}\n  判定\n{'=' * 66}")
    print(f"  差異中位數：{median_pct:.4f}%")
    print(f"  差異最大值：{max_pct:.4f}%")
    print(f"  完全相等：{exact}/{len(rows)} 筆")
    print(f"  預先登記閾值：中位數 > {THRESHOLD_PCT}% → 放棄接合")

    if median_pct > THRESHOLD_PCT:
        print(f"\n  ❌ {median_pct:.4f}% > {THRESHOLD_PCT}% → **放棄接合**。")
        print("     只呈現 7164（2019-01 起），看板標明「早期資料因來源不一致未納入」。")
        return 1

    print(f"\n  ✅ {median_pct:.4f}% ≤ {THRESHOLD_PCT}% → **接合通過**。")

    # 規格 5.2（2026-08-06 外部審查）：0.0000% 的詮釋已預先寫死。
    if max_pct == 0.0:
        print("\n  ⚠️ 措辭規則（規格 5.2，預先寫死，不得改寫）：")
        print("     20 期三欄完全一致，**更可能代表兩個資料集出自同一個上游（NCC 報表）**，")
        print("     而非兩個獨立來源互相驗證。")
        print("     → 一律表述為「**同源確認，可安全接合**」。")
        print("     → **不得**寫成「交叉驗證」或「兩來源互證」——懂的人會挑，而且挑得對。")

    out = spliced()
    ps = sorted({r.period for r in out})
    print(f"\n  接合後序列：{ps[0][0]}-{ps[0][1]:02d} ~ {ps[-1][0]}-{ps[-1][1]:02d}"
          f"，{len(ps)} 期，{len(out)} 筆")
    print(f"  切點：{SPLICE_CUTOVER[0]}-{SPLICE_CUTOVER[1]:02d} 起用 7164，之前用 27953"
          f"（重疊 {len(periods)} 期一律採 7164，**不混用**）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
