"""把 Ground Truth 與已知陷阱編碼成測試。

**刻意不依賴 PostgreSQL**——這些測的是解析與接合邏輯，跑起來不需要 Docker，
CI 才掛得上。落庫與指標的正確性由 `load_postgres.py --verify`（逐列 md5）
與 `compute_metrics.py` 的自檢負責，那兩層需要資料庫。

Ground Truth 於開工前實測並存檔（2026-08-02），本檔把它編碼成回歸測試。
**測試失敗代表解析錯了，不是改測試的理由。**
"""

from __future__ import annotations

import statistics
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from sources import (  # noqa: E402
    CAMP,
    COMPARABLE,
    SPLICE_CUTOVER,
    _to_int,
    load_7164,
    load_27953,
    overlap_periods,
    spliced,
)


# ── 陷阱 1：千分位逗號 ─────────────────────────────────────────────────
@pytest.mark.parametrize("raw,want", [
    ("346,192", 346192),
    ("200356", 200356),
    ("1,234,567", 1234567),
    (" 1276 ", 1276),
    ("0", 0),
])
def test_thousands_separator(raw, want):
    assert _to_int(raw) == want


def test_comma_rows_are_exactly_the_two_known_ones():
    """逗號只出現在 109/1 與 109/2——而這兩個月正好落在接合校驗的重疊窗內。

    naive int() 會剛好炸在校驗窗裡，所以這件事值得釘住。
    """
    import csv
    from sources import F_7164
    with F_7164.open(encoding="utf-8-sig", newline="") as fh:
        hits = {r["年月"] for r in csv.DictReader(fh)
                if any("," in v for v in r.values())}
    assert hits == {"109/1", "109/2"}


# ── 陷阱 3：民國年 ─────────────────────────────────────────────────────
def test_roc_year_conversion():
    p = {r.period for r in load_7164()}
    assert (2026, 4) in p          # 115/4
    assert (2019, 1) in p          # 108/1
    assert (2025, 4) not in {(y, m) for y, m in p if y == 115}


# ── 陷阱 4：兩份排序方向相反，讀入後須統一升序 ─────────────────────────
@pytest.mark.parametrize("loader", [load_7164, load_27953])
def test_ascending_after_load(loader):
    periods = [r.period for r in loader()]
    assert periods == sorted(periods)


# ── Ground Truth：列數與期間 ───────────────────────────────────────────
def _span_months(first, last):
    return (last[0] - first[0]) * 12 + (last[1] - first[1]) + 1


def test_frozen_source_is_exact():
    """27953 已停更——它的一切都該是精確值。長出新月份才是真的出事了。"""
    p = sorted({r.period for r in load_27953()})
    assert len(p) == 164
    assert p[0] == (2007, 1) and p[-1] == (2020, 8)


def test_live_source_holds_its_invariants():
    """7164 仍在更新，所以**測不變量而不是測快照**。

    釘死 88 列的版本在 2026-05 到達的當天就會紅——那不是抓到 bug，
    是測試自己過期。真正該守的是：起點不動、期數與跨距一致、只會往前長。
    """
    p = sorted({r.period for r in load_7164()})
    assert p[0] == (2019, 1), "起始月變動代表上游改了歷史，必須擋下"
    assert p[-1] >= (2026, 4), "最新月份不該倒退"
    assert len(p) == _span_months(p[0], p[-1]), "期數與跨距不符＝有缺月或重複"


@pytest.mark.parametrize("loader", [load_7164, load_27953])
def test_no_missing_or_duplicate_months(loader):
    periods = sorted({r.period for r in loader()})
    assert len(periods) == len({r.period for r in loader()})
    for prev, cur in zip(periods, periods[1:]):
        y, m = prev
        assert cur == ((y + 1, 1) if m == 12 else (y, m + 1))


# ── 陣營歸類預先登記、寫死，不得更改 ───────────────────────────────────
def test_camp_mapping_is_frozen():
    assert CAMP == {
        "ADSL": "TELCO",
        "FTTX": "TELCO",
        "CABLE_MODEM": "CABLE",
        "LEASED_LINE": "EXCLUDED",
        "PWLAN": "EXCLUDED",
    }


def test_comparable_columns_exclude_totals():
    """陷阱 2：27953 的總計含 PWLAN、7164 的小計固網不含，**絕不可比對總計欄**。"""
    assert set(COMPARABLE) == {"ADSL", "FTTX", "CABLE_MODEM"}
    assert not any("總計" in c or "小計" in c for c in COMPARABLE)


# ── Ground Truth：接合校驗 ─────────────────────────────────────────────
def test_overlap_is_20_periods():
    p = overlap_periods()
    assert len(p) == 20
    assert p[0] == (2019, 1) and p[-1] == (2020, 8)


def test_overlap_difference_is_exactly_zero():
    """20 期 × 3 欄 = 60 筆，全部完全相等，中位數與最大值皆 0.0000%。"""
    a = {(r.year, r.month, r.tech_code): r.accounts for r in load_7164()}
    b = {(r.year, r.month, r.tech_code): r.accounts for r in load_27953()}
    pct = [abs(a[k] - b[k]) / a[k] * 100
           for p in overlap_periods() for tech in COMPARABLE
           if (k := (*p, tech)) and a[k]]
    assert len(pct) == 60
    assert statistics.median(pct) == 0.0
    assert max(pct) == 0.0


def test_splice_takes_7164_over_the_overlap():
    """預先登記：重疊期一律採 7164，**不混用**。"""
    out = spliced()
    for r in out:
        if r.period >= SPLICE_CUTOVER:
            assert r.source == "ncc_7164"
        else:
            assert r.source == "ncc_27953"
    periods = sorted({r.period for r in out})
    assert periods[0] == (2007, 1)
    assert len(out) == len(periods) * 5          # 每期恰好 5 種技術別
    assert len(periods) == _span_months(periods[0], periods[-1])


# ── Ground Truth：核心發現 ─────────────────────────────────────────────
def _camp_totals(period):
    tot = {"TELCO": 0, "CABLE": 0}
    for r in spliced():
        if r.period == period and CAMP[r.tech_code] in tot:
            tot[CAMP[r.tech_code]] += r.accounts
    return tot


@pytest.mark.parametrize("period,telco,cable,share", [
    ((2019, 1), 4_296_061, 1_403_819, 75.37),
    ((2026, 4), 4_872_796, 2_469_678, 66.36),
])
def test_ground_truth_snapshots(period, telco, cable, share):
    t = _camp_totals(period)
    assert t["TELCO"] == telco
    assert t["CABLE"] == cable
    assert round(t["TELCO"] / (t["TELCO"] + t["CABLE"]) * 100, 2) == share


def test_headline_is_minus_9_01_pp():
    """**這個數字是整個專案的核心發現。** 算出別的，先查解析，不要改測試。"""
    def share(p):
        t = _camp_totals(p)
        return t["TELCO"] / (t["TELCO"] + t["CABLE"]) * 100
    assert round(share((2026, 4)) - share((2019, 1)), 2) == -9.01


# ── 小計算術（零容差）─────────────────────────────────────────────────
def test_subtotal_arithmetic_is_exact():
    import csv
    from sources import F_7164, F_27953
    cases = [
        (F_7164, "小計_固網（有線）寬頻帳號數",
         ["ADSL_固網（有線）寬頻帳號數", "FTTX_固網（有線）寬頻帳號數",
          "Cable_Modem固網（有線）寬頻帳號數", "Leased_Line_固網（有線）寬頻帳號數"]),
        (F_27953, "總計",
         ["有線寬頻帳號-ADSL", "有線寬頻帳號-FTTX", "有線寬頻帳號-Cable Modem",
          "有線寬頻帳號-固接專線", "無線寬頻帳號-PWLAN"]),
    ]
    # 不釘列數——那由上面兩個 span 測試負責。這裡要的是「**每一列**都零容差相等」，
    # 不論檔案長到幾列。
    for path, total_col, parts in cases:
        with path.open(encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
        exact = sum(1 for r in rows
                    if _to_int(r[total_col]) == sum(_to_int(r[c]) for c in parts))
        assert exact == len(rows), f"{path.name}: 只有 {exact}/{len(rows)} 完全相等"
