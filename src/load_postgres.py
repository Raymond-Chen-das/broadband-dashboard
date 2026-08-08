"""階段 3：落庫（星型 schema ＋ 冪等 upsert）。

schema 依 `docs/prompt-build-broadband-dashboard.md` 階段 3 的 DDL，
另補 `dim_period`——規格 5.3 明列星型為 `fact_subscriptions_monthly` ／
`dim_technology` ／ `dim_period` 三張表，prompt 的 DDL 漏了第三張。
**設計以規格為正本**（prompt 第〇節：設計爭議一律回規格）。

陣營歸類依規格第四節寫死，來自 `sources.CAMP`，本檔不重新定義。

用法：
    .\\.venv\\Scripts\\python.exe src\\load_postgres.py          # 建表 ＋ 載入
    .\\.venv\\Scripts\\python.exe src\\load_postgres.py --verify # 冪等驗證（連跑兩次比對）
"""

from __future__ import annotations

import sys

from db import connect, server_version
from sources import CAMP, TECH_NAME, spliced

DDL = """
CREATE TABLE IF NOT EXISTS dim_technology (
  tech_code   text PRIMARY KEY,
  tech_name   text NOT NULL,
  camp        text NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_period (
  year_month  date    PRIMARY KEY,   -- 當月 1 日
  year        int     NOT NULL,
  month       int     NOT NULL CHECK (month BETWEEN 1 AND 12),
  roc_year    int     NOT NULL,      -- 民國年，供對照原始檔
  quarter     int     NOT NULL CHECK (quarter BETWEEN 1 AND 4)
);

CREATE TABLE IF NOT EXISTS fact_subscriptions_monthly (
  year_month   date    NOT NULL REFERENCES dim_period(year_month),
  tech_code    text    NOT NULL REFERENCES dim_technology(tech_code),
  accounts     bigint  NOT NULL CHECK (accounts >= 0),
  source       text    NOT NULL,
  loaded_at    timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (year_month, tech_code)
);
"""


def create_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(DDL)
    conn.commit()


def load(conn) -> int:
    records = spliced()

    techs = [(code, TECH_NAME[code], CAMP[code]) for code in sorted(CAMP)]
    periods = sorted({r.period for r in records})

    with conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO dim_technology (tech_code, tech_name, camp)
               VALUES (%s, %s, %s)
               ON CONFLICT (tech_code) DO UPDATE
                 SET tech_name = EXCLUDED.tech_name, camp = EXCLUDED.camp""",
            techs,
        )
        cur.executemany(
            """INSERT INTO dim_period (year_month, year, month, roc_year, quarter)
               VALUES (make_date(%s, %s, 1), %s, %s, %s, %s)
               ON CONFLICT (year_month) DO NOTHING""",
            [(y, m, y, m, y - 1911, (m - 1) // 3 + 1) for y, m in periods],
        )
        # 冪等的核心：同一 (year_month, tech_code) 重跑只更新，不新增。
        # loaded_at 刻意更新——它記錄「最後一次寫入時間」，不是資料內容的一部分。
        cur.executemany(
            """INSERT INTO fact_subscriptions_monthly
                   (year_month, tech_code, accounts, source)
               VALUES (make_date(%s, %s, 1), %s, %s, %s)
               ON CONFLICT (year_month, tech_code) DO UPDATE
                 SET accounts  = EXCLUDED.accounts,
                     source    = EXCLUDED.source,
                     loaded_at = now()""",
            [(r.year, r.month, r.tech_code, r.accounts, r.source) for r in records],
        )
    conn.commit()
    return len(records)


def snapshot(conn) -> tuple[int, int, str, str, int, str]:
    """取一份可比對的狀態快照，用於冪等驗證。**不含 loaded_at**。

    最後一欄是全表逐列的 md5——**總和相同不代表逐列相同**，
    兩組不同的資料可以有相同的 count 與 sum。要證明冪等，必須比對逐列內容。
    """
    with conn.cursor() as cur:
        cur.execute(
            """SELECT count(*),
                      coalesce(sum(accounts), 0),
                      to_char(min(year_month), 'YYYY-MM'),
                      to_char(max(year_month), 'YYYY-MM'),
                      count(DISTINCT tech_code)
               FROM fact_subscriptions_monthly"""
        )
        agg = cur.fetchone()
        cur.execute(
            """SELECT md5(string_agg(
                        year_month::text || '|' || tech_code || '|' ||
                        accounts::text  || '|' || source,
                        E'\n' ORDER BY year_month, tech_code))
               FROM fact_subscriptions_monthly"""
        )
        return (*agg, cur.fetchone()[0])


def report(conn) -> None:
    with conn.cursor() as cur:
        print("\n各陣營載入結果：")
        cur.execute(
            """SELECT d.camp, count(*) AS rows, count(DISTINCT f.tech_code) AS techs,
                      to_char(min(f.year_month), 'YYYY-MM'),
                      to_char(max(f.year_month), 'YYYY-MM')
               FROM fact_subscriptions_monthly f
               JOIN dim_technology d USING (tech_code)
               GROUP BY d.camp ORDER BY d.camp"""
        )
        print(f"  {'陣營':<10}{'列數':>8}{'技術別':>8}   期間")
        for camp, rows, techs, lo, hi in cur.fetchall():
            print(f"  {camp:<10}{rows:>8}{techs:>8}   {lo} ~ {hi}")

        print("\n各來源列數（接合切點驗證）：")
        cur.execute(
            """SELECT source, count(*),
                      to_char(min(year_month), 'YYYY-MM'),
                      to_char(max(year_month), 'YYYY-MM')
               FROM fact_subscriptions_monthly GROUP BY source ORDER BY source"""
        )
        for src, n, lo, hi in cur.fetchall():
            print(f"  {src:<12}{n:>6} 列   {lo} ~ {hi}")


def main() -> int:
    verify = "--verify" in sys.argv
    conn = connect()
    print(f"連線成功：{server_version(conn).split(' on ')[0]}")

    create_schema(conn)
    print("schema 就緒：dim_technology / dim_period / fact_subscriptions_monthly")

    n = load(conn)
    first = snapshot(conn)
    print(f"\n第一次載入：來源 {n} 筆 → 表內 {first[0]} 列")
    print(f"  期間 {first[2]} ~ {first[3]}，技術別 {first[4]} 種，accounts 總和 {first[1]:,}")

    if verify:
        print("\n--- 冪等驗證：完全相同的輸入再跑一次 ---")
        load(conn)
        second = snapshot(conn)
        print(f"第二次載入：表內 {second[0]} 列，accounts 總和 {second[1]:,}")

        same = first == second
        print(f"\n  count(*)        {first[0]} → {second[0]}   {'✅' if first[0] == second[0] else '❌'}")
        print(f"  sum(accounts)   {first[1]:,} → {second[1]:,}   {'✅' if first[1] == second[1] else '❌'}")
        print(f"  期間            {first[2]}~{first[3]} → {second[2]}~{second[3]}   "
              f"{'✅' if first[2:4] == second[2:4] else '❌'}")
        print(f"  逐列 md5        {first[5][:16]}… → {second[5][:16]}…   "
              f"{'✅' if first[5] == second[5] else '❌'}")

        with conn.cursor() as cur:
            cur.execute(
                """SELECT count(*) FROM fact_subscriptions_monthly
                   WHERE loaded_at IS NULL OR accounts < 0"""
            )
            bad = cur.fetchone()[0]
        print(f"  異常列（accounts<0 或 loaded_at 空）  {bad}   {'✅' if bad == 0 else '❌'}")

        if not same:
            print("\n  ❌ 冪等驗證失敗：兩次結果不同。")
            conn.close()
            return 1
        print("\n  ✅ 冪等驗證通過：第二次跑完，列數與數值完全相同。")

    report(conn)
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
