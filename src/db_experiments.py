"""資料庫實驗：查詢調校與索引寫入代價。

**先講一件誠實的事**：本專案的真實事實表 `fact_subscriptions_monthly` 只有 **1,160 列**。
在這個量級，PostgreSQL 一律走 Seq Scan 而且永遠是毫秒級——**任何索引都測不出差異**。
這不是缺陷，是資料本身的規模（技術別 × 月，19 年）。

所以量級相關的實驗跑在另一張**明確標示為合成**的 `bench_subscriptions` 上：
同樣的欄位語意，額外加上 region／operator 兩個維度把列數放大。
**合成資料只用來量測引擎行為，不產生任何業務數字，不進看板。**

實驗（第三項刻意排除，理由見 docs/20-db-experiments.md）：
  1. 慢查詢調校——`EXPLAIN ANALYZE` 前後對照
  2. 索引的寫入代價——加索引後 upsert 吞吐掉多少（實測秒數）
  3. Teradata PI／skew 對照——**不做**，理由見 docs/20-db-experiments.md

用法：
    .\\.venv\\Scripts\\python.exe src\\db_experiments.py
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from db import connect

LOGS = Path(__file__).resolve().parent.parent / "logs"

BENCH_ROWS_TARGET = 2_000_000
UPSERT_BATCH = 60_000

DDL_BENCH = """
DROP TABLE IF EXISTS bench_subscriptions;
CREATE TABLE bench_subscriptions (
  year_month  date    NOT NULL,
  tech_code   text    NOT NULL,
  region_code text    NOT NULL,
  operator_id int     NOT NULL,
  accounts    bigint  NOT NULL CHECK (accounts >= 0),
  loaded_at   timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (year_month, tech_code, region_code, operator_id)
);
"""

# 以真實事實表的期間與技術別為骨架，往 region／operator 兩個維度展開。
# accounts 用確定性的算式產生（不是亂數），重跑結果相同，便於前後對照。
SEED_BENCH = f"""
INSERT INTO bench_subscriptions (year_month, tech_code, region_code, operator_id, accounts)
SELECT p.year_month,
       t.tech_code,
       'R' || lpad(r::text, 2, '0'),
       o,
       ((extract(epoch from p.year_month)::bigint / 86400) * 7 + r * 131 + o * 17
         + length(t.tech_code) * 991) % 500000
FROM dim_period p
CROSS JOIN dim_technology t
CROSS JOIN generate_series(1, 22) AS r
CROSS JOIN generate_series(1, {max(1, BENCH_ROWS_TARGET // (232 * 5 * 22))}) AS o
"""

# 實驗 1 的目標查詢：挑一個技術別、一段期間，按區域彙總並排序。
# 這是看板「某技術別的區域分佈」這類需求最典型的形狀。
SLOW_QUERY = """
SELECT region_code,
       SUM(accounts) AS total,
       AVG(accounts)::bigint AS avg_accounts
FROM bench_subscriptions
WHERE tech_code = 'FTTX'
  AND year_month BETWEEN DATE '2018-01-01' AND DATE '2021-12-01'
GROUP BY region_code
ORDER BY total DESC
"""

IDX_QUERY = ("CREATE INDEX idx_bench_tech_ym ON bench_subscriptions "
             "(tech_code, year_month) INCLUDE (region_code, accounts)")

# 實驗 2 用的三個「業務上會想加」的索引——重點是它們對寫入的代價。
IDX_WRITE_COST = [
    "CREATE INDEX idx_bench_region ON bench_subscriptions (region_code)",
    "CREATE INDEX idx_bench_operator ON bench_subscriptions (operator_id, year_month)",
    "CREATE INDEX idx_bench_loaded ON bench_subscriptions (loaded_at DESC)",
]

UPSERT = """
INSERT INTO bench_subscriptions (year_month, tech_code, region_code, operator_id, accounts)
SELECT p.year_month, t.tech_code, 'R' || lpad(r::text, 2, '0'), 1,
       ((extract(epoch from p.year_month)::bigint / 86400) * 11 + r * 37) %% 500000
FROM dim_period p
CROSS JOIN dim_technology t
CROSS JOIN generate_series(1, %s) AS r
ON CONFLICT (year_month, tech_code, region_code, operator_id) DO UPDATE
   SET accounts = EXCLUDED.accounts, loaded_at = now()
"""


def explain(cur, sql: str) -> dict:
    cur.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + sql)
    return cur.fetchone()[0][0]


def summarise(plan: dict) -> dict:
    """彙總一份 EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)。

    兩個踩過的坑：
    1. 計畫一旦平行化（Gather / Gather Merge），做過濾的是**子節點**——
       只讀頂層節點的 `Rows Removed by Filter` 會拿到 None。所以走整棵樹取。
    2. 但 **buffers 是累計值**：父節點已經包含子節點的量。
       把整棵樹的 buffers 加起來會嚴重灌水（實測 17,593 被算成 99,595）。
       所以 buffers **只取根節點**，那本來就是整個查詢的總量。
    """
    nodes: list[str] = []
    removed = 0
    heap = None

    def walk(node):
        nonlocal removed, heap
        nodes.append(node["Node Type"])
        removed += node.get("Rows Removed by Filter") or 0
        if "Heap Fetches" in node:      # 只出現在 Index Only Scan 節點，不在根節點
            heap = node["Heap Fetches"]
        for c in node.get("Plans", []):
            walk(c)

    root = plan["Plan"]
    walk(root)
    return dict(
        exec_ms=plan["Execution Time"],
        plan_ms=plan["Planning Time"],
        rows_removed=removed,
        shared_blocks=(root.get("Shared Read Blocks") or 0)
                      + (root.get("Shared Hit Blocks") or 0),
        heap_fetches=heap,
        nodes=" → ".join(dict.fromkeys(nodes)),
    )


def measure(cur, sql: str, runs: int = 7) -> dict:
    """跑 runs 次取中位數。

    單次計時在這裡沒有意義——同一組前後對照，冷快取量到 9.5×、暖快取量到 1.5×。
    **快取狀態主導了測量**，所以報告時間必須附上樣本數與全距，
    而真正穩定、可跨機器比較的是 buffers 與計畫形狀。
    """
    import statistics
    samples = []
    last = None
    for i in range(runs + 1):
        s = summarise(explain(cur, sql))
        if i:                       # 第一次當暖機，不計入
            samples.append(s["exec_ms"])
        last = s
    last["exec_ms_median"] = statistics.median(samples)
    last["exec_ms_min"] = min(samples)
    last["exec_ms_max"] = max(samples)
    last["runs"] = runs
    return last


def timed(cur, sql, params=None) -> float:
    t0 = time.perf_counter()
    cur.execute(sql, params)
    return time.perf_counter() - t0


def main() -> int:
    conn = connect()
    conn.autocommit = True
    cur = conn.cursor()

    print("=" * 78)
    print("  階段 6：資料庫實驗")
    print("=" * 78)

    cur.execute("SELECT count(*) FROM fact_subscriptions_monthly")
    real_n = cur.fetchone()[0]
    print(f"\n真實事實表 fact_subscriptions_monthly：{real_n:,} 列")
    print("→ 這個量級 PostgreSQL 一律 Seq Scan、恆為毫秒級，索引測不出差異。")
    print("→ 量級相關的實驗改跑在明確標示為合成的 bench_subscriptions 上。\n")

    print("建立合成表…", end=" ", flush=True)
    t = timed(cur, DDL_BENCH) + timed(cur, SEED_BENCH)
    cur.execute("SELECT count(*) FROM bench_subscriptions")
    bench_n = cur.fetchone()[0]
    cur.execute("SELECT pg_size_pretty(pg_total_relation_size('bench_subscriptions'))")
    print(f"{bench_n:,} 列（{cur.fetchone()[0]}），耗時 {t:.1f}s")
    cur.execute("VACUUM ANALYZE bench_subscriptions")

    results = {"real_rows": real_n, "bench_rows": bench_n}

    # ── 實驗 1：慢查詢調校 ────────────────────────────────────────────
    print(f"\n{'-' * 78}\n  實驗 1：慢查詢調校（EXPLAIN ANALYZE 前後對照）\n{'-' * 78}")
    cur.execute("DROP INDEX IF EXISTS idx_bench_tech_ym")
    cur.execute("VACUUM ANALYZE bench_subscriptions")
    before = measure(cur, SLOW_QUERY)
    print(f"  【前】{before['nodes']}")
    print(f"       執行中位數 {before['exec_ms_median']:.1f} ms"
          f"（{before['runs']} 次，{before['exec_ms_min']:.1f}–{before['exec_ms_max']:.1f}）")
    print(f"       被 filter 丟棄 {before['rows_removed']:,} 列"
          f"　buffers {before['shared_blocks']:,} blocks")

    print(f"\n  建立索引：{IDX_QUERY.split('ON')[0].strip()} …", end=" ", flush=True)
    idx_build = timed(cur, IDX_QUERY)
    cur.execute("VACUUM ANALYZE bench_subscriptions")
    print(f"耗時 {idx_build:.1f}s")

    after = measure(cur, SLOW_QUERY)
    print(f"\n  【後】{after['nodes']}")
    print(f"       執行中位數 {after['exec_ms_median']:.1f} ms"
          f"（{after['runs']} 次，{after['exec_ms_min']:.1f}–{after['exec_ms_max']:.1f}）")
    print(f"       被 filter 丟棄 {after['rows_removed']:,} 列"
          f"　buffers {after['shared_blocks']:,} blocks"
          f"　Heap Fetches {after['heap_fetches']}")
    speedup = before["exec_ms_median"] / after["exec_ms_median"]
    blk = before["shared_blocks"] / after["shared_blocks"]
    print(f"\n  → 時間加速 {speedup:.1f}×"
          f"（中位數 {before['exec_ms_median']:.1f} → {after['exec_ms_median']:.1f} ms）")
    print(f"  → buffers 減少 {blk:.0f}×"
          f"（{before['shared_blocks']:,} → {after['shared_blocks']:,} blocks）"
          f"　← 這個數字不受快取狀態影響，比時間可靠")
    results["exp1"] = dict(before=before, after=after, speedup=speedup,
                           index_build_s=idx_build)

    # ── 實驗 2：索引的寫入代價 ────────────────────────────────────────
    print(f"\n{'-' * 78}\n  實驗 2：索引的寫入代價（upsert 吞吐）\n{'-' * 78}")
    r_per_batch = max(1, UPSERT_BATCH // (232 * 5))

    import statistics

    def upsert_median(runs: int = 5) -> tuple[float, float, float]:
        """第一次當暖機不計入，其餘取中位數。

        單次計時不可靠——同一組對照，兩次獨立執行分別量到 1.77× 與 2.36×。
        所有量測都在「更新既有列」的狀態下進行（暖機那次已把列插進去），前後條件一致。
        """
        timed(cur, UPSERT, (r_per_batch,))
        s = [timed(cur, UPSERT, (r_per_batch,)) for _ in range(runs)]
        return statistics.median(s), min(s), max(s)

    cur.execute("SELECT count(*) FROM pg_indexes WHERE tablename = 'bench_subscriptions'")
    n_idx_a = cur.fetchone()[0]
    t_before, lo_b, hi_b = upsert_median()
    n_rows = 232 * 5 * r_per_batch
    print(f"  索引數 {n_idx_a}（PK ＋ 實驗 1 的索引）　upsert {n_rows:,} 列")
    print(f"    中位數 {t_before:.2f}s（5 次，{lo_b:.2f}–{hi_b:.2f}）")

    print("  加三個索引…", end=" ", flush=True)
    idx_t = sum(timed(cur, s) for s in IDX_WRITE_COST)
    cur.execute("VACUUM ANALYZE bench_subscriptions")
    cur.execute("SELECT count(*) FROM pg_indexes WHERE tablename = 'bench_subscriptions'")
    n_idx_b = cur.fetchone()[0]
    print(f"耗時 {idx_t:.1f}s，索引數 {n_idx_a} → {n_idx_b}")

    t_after, lo_a, hi_a = upsert_median()
    slowdown = t_after / t_before
    print(f"  同樣的 upsert：中位數 {t_after:.2f}s（5 次，{lo_a:.2f}–{hi_a:.2f}）")
    print(f"\n  → 寫入變慢 {slowdown:.2f}×（{t_before:.2f}s → {t_after:.2f}s），"
          f"吞吐掉 {(1 - t_before / t_after) * 100:.0f}%")

    cur.execute("""SELECT indexrelname, pg_size_pretty(pg_relation_size(indexrelid))
                   FROM pg_stat_user_indexes WHERE relname = 'bench_subscriptions'
                   ORDER BY pg_relation_size(indexrelid) DESC""")
    print("\n  索引佔用：")
    for name, size in cur.fetchall():
        print(f"    {name:<28} {size}")

    results["exp2"] = dict(idx_before=n_idx_a, idx_after=n_idx_b,
                           upsert_rows=n_rows,
                           t_before_median=t_before, t_before_range=[lo_b, hi_b],
                           t_after_median=t_after, t_after_range=[lo_a, hi_a],
                           slowdown=slowdown, index_build_s=idx_t)

    # ── 實驗 3：不做 ──────────────────────────────────────────────────
    print(f"\n{'-' * 78}\n  實驗 3：Teradata PI／skew 對照——**不執行**\n{'-' * 78}")
    print("  依展示深度規則（『被追問三層答得出來嗎』）排除。")
    print("  理由與替代方案寫在 docs/20-db-experiments.md。")

    out = LOGS / "db-experiments.json"
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n原始量測值已存：{out.name}")

    cur.close()
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
