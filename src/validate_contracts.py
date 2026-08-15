"""階段 1：資料契約驗證。

**只驗證，不轉換，不寫入任何檔案。** 契約不過即擋，不得「先跑跑看」。

刻意使用標準函式庫 `csv` 而非 pandas：pandas 的 dtype 自動推斷會把千分位逗號、
空字串、前導零這類問題悄悄吸收掉，而本階段的目的正是把它們暴露出來。

用法：
    .\\.venv\\Scripts\\python.exe src\\validate_contracts.py
退出碼：0 = 全部通過；1 = 任一項不符——後續階段一律不執行，也不修補資料。
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"

F_7164 = RAW / "ncc_7164_寬頻上網帳號數.csv"
F_27953 = RAW / "ncc_27953_有線寬頻用戶數.csv"

# ---------------------------------------------------------------------------
# 契約：以 2026-08-08 的檔案快照釘住。欄位若變動，驗證即失敗——這正是契約的用途。
# 來源：開工前實測並存檔的 Ground Truth 自檢基準
# ---------------------------------------------------------------------------

COLS_7164 = [
    "年月",
    "ADSL_固網（有線）寬頻帳號數",
    "FTTX_固網（有線）寬頻帳號數",
    "Cable_Modem固網（有線）寬頻帳號數",
    "Leased_Line_固網（有線）寬頻帳號數",
    "小計_固網（有線）寬頻帳號數",
    "行動寬頻_無線寬頻帳號數",
    "PWLAN_無線寬頻帳號數",
    "小計_無線寬頻帳號數",
    "合計_寬頻帳號數",
    "Data+Voice_實際行動寬頻上網帳號數",
    "Data only_實際行動寬頻上網帳號數",
    "合計_實際行動寬頻上網帳號數",
]

COLS_27953 = [
    "年度",
    "月份",
    "有線寬頻帳號-ADSL",
    "有線寬頻帳號-FTTX",
    "有線寬頻帳號-Cable Modem",
    "有線寬頻帳號-固接專線",
    "無線寬頻帳號-PWLAN",
    "總計",
]

EXPECTED = {
    "7164": {"rows": 88, "first": (2019, 1), "last": (2026, 4), "live": True},
    "27953": {"rows": 164, "first": (2007, 1), "last": (2020, 8), "live": False},
}

# `--allow-growth`：給月更新管線用。
# 7164 仍在更新，把列數與結束月釘死等於**新月份一到就被自己的契約擋下**。
# 放寬的只有「列數 ≥ 快照」與「結束月 ≥ 快照」這兩項；
# 結構性檢查（欄位、數值、算術、連續性、起始月）**一律維持嚴格**。
# 27953 已停更，不論如何都用嚴格比對——它若長出新月份才是真的出事了。
ALLOW_GROWTH = "--allow-growth" in sys.argv

# 小計算術的加總項（陷阱 2：兩份的總計定義不同，絕不可互相比對）
SUM_7164 = {
    "total": "小計_固網（有線）寬頻帳號數",
    "parts": [
        "ADSL_固網（有線）寬頻帳號數",
        "FTTX_固網（有線）寬頻帳號數",
        "Cable_Modem固網（有線）寬頻帳號數",
        "Leased_Line_固網（有線）寬頻帳號數",
    ],
}
SUM_27953 = {
    "total": "總計",
    "parts": [
        "有線寬頻帳號-ADSL",
        "有線寬頻帳號-FTTX",
        "有線寬頻帳號-Cable Modem",
        "有線寬頻帳號-固接專線",
        "無線寬頻帳號-PWLAN",  # ← 27953 的總計「含」PWLAN，7164 的小計固網「不含」
    ],
}

TOLERANCE = 0.001  # 0.1%，預先登記

results: list[tuple[str, bool, str]] = []


def check(name: str, passed: bool, detail: str = "") -> None:
    results.append((name, passed, detail))


def parse_int(raw: str, where: str) -> int:
    """陷阱 1：部分數值帶千分位逗號，且不是每一列都有。naive int() 會炸。"""
    cleaned = raw.replace(",", "").strip()
    if not cleaned:
        raise ValueError(f"{where}：空值")
    if not cleaned.isdigit():  # isdigit() 同時擋掉負號與小數點
        raise ValueError(f"{where}：'{raw}' 去逗號後非非負整數")
    return int(cleaned)


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """陷阱 5、6：用 DictReader（勿用 split(',')），encoding 用 utf-8-sig 吃掉 BOM。"""
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        return list(reader.fieldnames or []), list(reader)


def roc_to_ad(roc_year: int) -> int:
    """陷阱 3：西元 = 民國 + 1911。"""
    return roc_year + 1911


def check_file(tag: str, path: Path, expected_cols: list[str],
               sum_spec: dict, period_of) -> None:
    print(f"\n{'=' * 70}\n  {tag}  {path.name}\n{'=' * 70}")

    if not path.exists():
        check(f"[{tag}] 檔案存在", False, f"找不到 {path}")
        return
    check(f"[{tag}] 檔案存在", True, str(path.relative_to(ROOT)))

    cols, rows = read_csv(path)

    # --- 檢查 1：欄位清單 ---------------------------------------------------
    ok = cols == expected_cols
    detail = "與契約完全相符" if ok else (
        f"缺少={set(expected_cols) - set(cols)} 多出={set(cols) - set(expected_cols)}"
    )
    check(f"[{tag}] 欄位清單", ok, detail)
    if not ok:
        return  # 欄位不符則後續檢查無意義

    # --- 檢查 2：資料列數 ---------------------------------------------------
    exp_rows = EXPECTED[tag]["rows"]
    growth = ALLOW_GROWTH and EXPECTED[tag]["live"]
    check(f"[{tag}] 資料列數", len(rows) >= exp_rows if growth else len(rows) == exp_rows,
          f"實際 {len(rows)} 列 / 契約 {'≥ ' if growth else ''}{exp_rows} 列"
          + (f"（新增 {len(rows) - exp_rows} 個月）" if growth and len(rows) > exp_rows else ""))

    # --- 檢查 3：數值可解析（去逗號後為非負整數）----------------------------
    numeric_cols = [c for c in expected_cols if c not in ("年月", "年度", "月份")]
    bad: list[str] = []
    comma_rows = 0
    for i, row in enumerate(rows, start=2):  # 2 = 扣掉表頭的實際檔案行號
        had_comma = False
        for c in numeric_cols:
            if "," in row[c]:
                had_comma = True
            try:
                parse_int(row[c], f"第 {i} 行 欄位「{c}」")
            except ValueError as e:
                bad.append(str(e))
        if had_comma:
            comma_rows += 1
    check(f"[{tag}] 數值可解析（非負整數）", not bad,
          f"{len(rows)} 列 × {len(numeric_cols)} 欄全數通過"
          f"；其中 {comma_rows} 列含千分位逗號"
          if not bad else f"{len(bad)} 筆失敗，前 3 筆：{bad[:3]}")

    # --- 檢查 4：小計算術 ---------------------------------------------------
    # 刻意把「完全相等」與「容差內」分開統計：若只回報合併後的通過數，
    # 容差內的案例會被藏起來，而本專案的失敗模式正是「數字錯的漂亮報表」。
    exact = 0
    within_tol: list[str] = []
    mismatches: list[str] = []
    for i, row in enumerate(rows, start=2):
        total = parse_int(row[sum_spec["total"]], "")
        parts = sum(parse_int(row[c], "") for c in sum_spec["parts"])
        if total == parts:
            exact += 1
        elif total and abs(total - parts) / total <= TOLERANCE:
            within_tol.append(f"第 {i} 行：{total} vs {parts}（差 {total - parts}）")
        else:
            mismatches.append(f"第 {i} 行：{total} ≠ {parts}（差 {total - parts}）")

    n = len(rows)
    formula = " + ".join(c.split("-")[-1].split("_")[0] for c in sum_spec["parts"])
    detail = f"完全相等 {exact}/{n}，容差內 {len(within_tol)}，不符 {len(mismatches)}（{sum_spec['total']} = {formula}）"
    if within_tol:
        detail += f"；⚠️ 容差內案例：{within_tol[:3]}"
    if mismatches:
        detail += f"；❌ 不符：{mismatches[:3]}"
    check(f"[{tag}] 小計算術", not mismatches, detail)

    # --- 檢查 5：月份連續性（無缺月、無重複）--------------------------------
    periods = [period_of(row) for row in rows]
    uniq = sorted(set(periods))
    dup_ok = len(uniq) == len(periods)
    dups = [p for p in set(periods) if periods.count(p) > 1] if not dup_ok else []
    check(f"[{tag}] 無重複月份", dup_ok,
          f"{len(periods)} 期全為唯一" if dup_ok else f"重複：{dups[:5]}")

    gaps: list[str] = []
    for prev, cur in zip(uniq, uniq[1:]):
        y, m = prev
        nxt = (y + 1, 1) if m == 12 else (y, m + 1)
        if cur != nxt:
            gaps.append(f"{prev[0]}-{prev[1]:02d} → {cur[0]}-{cur[1]:02d}")
    check(f"[{tag}] 無缺月", not gaps,
          f"{len(uniq)} 期連續" if not gaps else f"斷點 {len(gaps)} 處：{gaps[:5]}")

    # --- 檢查 6：期間範圍 ---------------------------------------------------
    exp_first, exp_last = EXPECTED[tag]["first"], EXPECTED[tag]["last"]
    # 起始月一律嚴格：它若變動，代表上游改了歷史，那是必須擋下的事。
    ok = uniq[0] == exp_first and (uniq[-1] >= exp_last if growth else uniq[-1] == exp_last)
    check(f"[{tag}] 期間範圍", ok,
          f"{uniq[0][0]}-{uniq[0][1]:02d} ~ {uniq[-1][0]}-{uniq[-1][1]:02d}"
          f"（契約 {exp_first[0]}-{exp_first[1]:02d} ~ "
          f"{'≥ ' if growth else ''}{exp_last[0]}-{exp_last[1]:02d}）")

    # --- 附帶資訊：排序方向（不列入通過與否，僅記錄）------------------------
    direction = "升序" if periods == sorted(periods) else (
        "降序" if periods == sorted(periods, reverse=True) else "未排序")
    print(f"  · 檔案原始排序方向：{direction}（陷阱 4：兩份方向相反，讀入後須統一升序）")


def period_7164(row: dict[str, str]) -> tuple[int, int]:
    roc, month = row["年月"].split("/")
    return roc_to_ad(int(roc)), int(month)


def period_27953(row: dict[str, str]) -> tuple[int, int]:
    return roc_to_ad(int(row["年度"])), int(row["月份"])


def main() -> int:
    print("階段 1：資料契約驗證（只驗證、不轉換、不寫入）")
    print("依據：預先登記的契約表——欄位、列數、型別、算術、連續性、期間")

    check_file("7164", F_7164, COLS_7164, SUM_7164, period_7164)
    check_file("27953", F_27953, COLS_27953, SUM_27953, period_27953)

    print(f"\n{'=' * 70}\n  驗證結果\n{'=' * 70}")
    for name, passed, detail in results:
        print(f"  {'✅ PASS' if passed else '❌ FAIL'}  {name:<34} {detail}")

    failed = [r for r in results if not r[1]]
    print(f"\n  合計 {len(results)} 項，通過 {len(results) - len(failed)}，失敗 {len(failed)}")
    if failed:
        print("\n  ❌ 契約未通過 → 停止，不進入分析層，也不修補資料。")
        return 1
    print("\n  ✅ 契約全數通過 → 可進入階段 2（接合校驗）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
