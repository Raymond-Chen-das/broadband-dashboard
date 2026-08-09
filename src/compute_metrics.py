"""階段 4：指標計算（依規格第四節預先登記，不得增補）。

**只算這些**：
  主要——兩陣營月度帳號數、月度淨增量（月差分）
  次要——陣營占比、12 個月移動平均、累積淨增

**明確禁止**：任何回歸、任何 p 值、任何因果效果估計。
事件時點（2022-05 MSO 價格戰、2026-03-18 中華電信降價）**僅供視覺標記，不估計效果**。

計算全部在 PostgreSQL 內以視窗函數完成，Python 只負責取結果與自檢——
資料庫是用來算的，不是載完就擺著當佐證。

用法：
    .\\.venv\\Scripts\\python.exe src\\compute_metrics.py
退出碼：0 = 自檢通過；1 = 與 Ground Truth 不符（先查解析，不要改設計）。
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

from db import connect

# Ground Truth（logs/decisions.log 第 1.2 節）
GT = {
    "2019-01": dict(telco=4_296_061, cable=1_403_819, share=75.37),
    "2026-04": dict(telco=4_872_796, cable=2_469_678, share=66.36),
}
GT_DELTA_PP = -9.01

SQL = """
WITH camp_monthly AS (
    SELECT f.year_month,
           SUM(f.accounts) FILTER (WHERE d.camp = 'TELCO') AS telco,
           SUM(f.accounts) FILTER (WHERE d.camp = 'CABLE') AS cable
    FROM fact_subscriptions_monthly f
    JOIN dim_technology d USING (tech_code)
    WHERE d.camp IN ('TELCO', 'CABLE')          -- EXCLUDED 不進陣營計算（規格第四節）
    GROUP BY f.year_month
),
base AS (
    SELECT year_month, telco, cable,
           telco + cable                                   AS total,
           ROW_NUMBER() OVER (ORDER BY year_month)         AS rn,
           telco - LAG(telco) OVER (ORDER BY year_month)   AS telco_net,
           cable - LAG(cable) OVER (ORDER BY year_month)   AS cable_net
    FROM camp_monthly
)
SELECT to_char(year_month, 'YYYY-MM')                        AS ym,
       telco, cable, total,
       ROUND(telco::numeric / total * 100, 4)                AS telco_share,
       telco_net, cable_net,
       -- 12 個月移動平均：不足 12 期不給值，避免頭部被短窗拉出假趨勢
       CASE WHEN rn >= 12 THEN ROUND(AVG(telco) OVER w12, 1) END AS telco_ma12,
       CASE WHEN rn >= 12 THEN ROUND(AVG(cable) OVER w12, 1) END AS cable_ma12,
       SUM(telco_net) OVER (ORDER BY year_month)             AS telco_cum_net,
       SUM(cable_net) OVER (ORDER BY year_month)             AS cable_cum_net
FROM base
WINDOW w12 AS (ORDER BY year_month ROWS BETWEEN 11 PRECEDING AND CURRENT ROW)
ORDER BY year_month
"""


@dataclass(frozen=True)
class Row:
    ym: str
    telco: int
    cable: int
    total: int
    telco_share: float
    telco_net: int | None
    cable_net: int | None
    telco_ma12: float | None
    cable_ma12: float | None
    telco_cum_net: int | None
    cable_cum_net: int | None


def fetch_metrics(conn=None) -> list[Row]:
    own = conn is None
    conn = conn or connect()
    try:
        with conn.cursor() as cur:
            cur.execute(SQL)
            out = []
            for r in cur.fetchall():
                out.append(Row(
                    ym=r[0], telco=int(r[1]), cable=int(r[2]), total=int(r[3]),
                    telco_share=float(r[4]),
                    telco_net=None if r[5] is None else int(r[5]),
                    cable_net=None if r[6] is None else int(r[6]),
                    telco_ma12=None if r[7] is None else float(r[7]),
                    cable_ma12=None if r[8] is None else float(r[8]),
                    telco_cum_net=None if r[9] is None else int(r[9]),
                    cable_cum_net=None if r[10] is None else int(r[10]),
                ))
            return out
    finally:
        if own:
            conn.close()


def main() -> int:
    rows = fetch_metrics()
    by_ym = {r.ym: r for r in rows}
    print(f"階段 4：指標計算　（{len(rows)} 期，{rows[0].ym} ~ {rows[-1].ym}）")
    print("計算位置：PostgreSQL 視窗函數；Python 只取結果與自檢\n")

    # ── 自檢：必須重現 Ground Truth ─────────────────────────────────────
    print("Ground Truth 自檢：")
    ok = True
    for ym, want in GT.items():
        got = by_ym[ym]
        checks = [
            ("電信帳號數", got.telco, want["telco"], got.telco == want["telco"]),
            ("Cable 帳號數", got.cable, want["cable"], got.cable == want["cable"]),
            ("電信占比", round(got.telco_share, 2), want["share"],
             abs(got.telco_share - want["share"]) < 0.005),
        ]
        for label, g, w, passed in checks:
            ok &= passed
            g_s = f"{g:,}" if isinstance(g, int) else f"{g:.2f}%"
            w_s = f"{w:,}" if isinstance(w, int) else f"{w:.2f}%"
            print(f"  {'✅' if passed else '❌'} {ym} {label:<12} 算出 {g_s:>12}   契約 {w_s:>12}")

    delta = by_ym["2026-04"].telco_share - by_ym["2019-01"].telco_share
    d_ok = abs(delta - GT_DELTA_PP) < 0.005
    ok &= d_ok
    print(f"  {'✅' if d_ok else '❌'} 七年變化      算出 {delta:>11.2f} pp   契約 {GT_DELTA_PP:>11.2f} pp")

    if not ok:
        print("\n❌ 自檢未通過 → 先查解析，不要改設計。")
        return 1
    print("\n✅ 自檢通過。")

    # ── 預先登記的指標，逐項出樣 ────────────────────────────────────────
    print(f"\n{'=' * 78}\n  預先登記的指標（固定清單，未增補）\n{'=' * 78}")
    print(f"\n【主要】兩陣營月度帳號數　最後 3 期：")
    print(f"  {'年月':<9}{'電信':>12}{'Cable':>12}{'合計':>13}")
    for r in rows[-3:]:
        print(f"  {r.ym:<9}{r.telco:>12,}{r.cable:>12,}{r.total:>13,}")

    print(f"\n【主要】月度淨增量　最後 3 期：")
    print(f"  {'年月':<9}{'電信淨增':>12}{'Cable 淨增':>13}")
    for r in rows[-3:]:
        print(f"  {r.ym:<9}{r.telco_net:>12,}{r.cable_net:>13,}")

    print(f"\n【次要】陣營占比 / 12 個月移動平均 / 累積淨增　最後 3 期：")
    print(f"  {'年月':<9}{'電信占比':>10}{'電信MA12':>14}{'Cable MA12':>14}"
          f"{'電信累積淨增':>15}{'Cable累積淨增':>15}")
    for r in rows[-3:]:
        print(f"  {r.ym:<9}{r.telco_share:>9.2f}%{r.telco_ma12:>14,.1f}"
              f"{r.cable_ma12:>14,.1f}{r.telco_cum_net:>15,}{r.cable_cum_net:>15,}")

    # ── 已知的兩個資料斷點（decisions.log 決定 A：標記，不修改數字）──────
    print(f"\n{'=' * 78}\n  兩個資料斷點在指標上的樣子（僅標記，不修改任何數值）\n{'=' * 78}")
    print(f"  {'年月':<9}{'電信淨增':>12}{'Cable 淨增':>13}{'電信占比':>10}{'占比月變動':>12}")
    for ym in ("2009-03", "2009-04", "2009-05", "2019-12", "2020-01", "2020-02"):
        r = by_ym[ym]
        prev = rows[rows.index(r) - 1]
        mark = "  ← 斷點" if ym in ("2009-04", "2020-01") else ""
        print(f"  {r.ym:<9}{r.telco_net:>12,}{r.cable_net:>13,}{r.telco_share:>9.2f}%"
              f"{r.telco_share - prev.telco_share:>11.4f}pp{mark}")

    print("\n  ⚠️ 成因未能證實（已查 data.gov.tw 中繼資料、NCC 官網 403、公開搜尋，"
          "皆無口徑說明）。\n     依 logs/decisions.log 決定 A：看板標記 ＋ 限制章節寫明查證過程，**不宣稱成因**。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
