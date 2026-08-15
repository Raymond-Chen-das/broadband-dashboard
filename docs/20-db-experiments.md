# 20 — 資料庫實驗

> 兩個關聯式資料庫的基本功實測：**查詢調校**（Seq Scan → Index Only Scan）
> 與**索引的寫入代價**。兩者都跑在本專案自己的管線上，每個數字都能解釋機制。
> 量測環境：PostgreSQL 17.10（Debian／Linux 原生建置）跑在 Docker 容器，單台 Windows 筆電。

---

## 先講三件會被追問、而我選擇先講的事

**一、本專案的真實事實表只有 1,160 列。**

`fact_subscriptions_monthly` ＝ 232 個月 × 5 種技術別。在這個量級，PostgreSQL 一律走
Seq Scan，而且**永遠是毫秒級——任何索引都測不出差異**。這不是缺陷，是資料本身的規模
（NCC 的公開統計就是技術別 × 月，19 年份）。

所以量級相關的實驗跑在另一張**明確命名為 `bench_` 的合成表**上：同樣的欄位語意，額外加
`region_code`／`operator_id` 兩個維度把列數放大到 **199 萬列（259 MB）**。
**合成資料只用來量測引擎行為，不產生任何業務數字，不進看板。**

**二、牆鐘時間在這個環境裡不可靠。**

同一組前後對照，我跑了四次，時間比值分別是 **9.5×／3.9×／2.3×／4.5×**——
快取狀態主導了測量。但同樣四次，**buffers 每一次都是 16,604 → 409 blocks**。

所以本文件的主張建立在 **buffers 與執行計畫形狀**上，時間只附中位數與全距，
**不拿單次秒數當結論**。

**三、絕對數字不可外推到生產環境。**

這是筆電上的容器，不是生產叢集。有意義的是**同一環境下的前後對照**，不是秒數本身。

---

## 實驗 1：慢查詢調校

**問**：一個對 199 萬列事實表的區域彙總查詢，怎麼從 Seq Scan 調到 Index Only Scan？

**答（約 200 字）**：目標查詢是「取某技術別、某段期間，按區域彙總帳號數並排序」——
看板上「某技術別的區域分佈」這類需求最典型的形狀。調校前 PostgreSQL 選擇
Parallel Seq Scan：全表掃描 199 萬列，用 filter 丟掉 **636,064 列**，
讀取 **16,604 個 buffer**。問題不在排序或彙總，而在**為了找出 4% 的目標列而讀了整張表**。

我建立 `(tech_code, year_month)` 複合索引，並用 `INCLUDE (region_code, accounts)`
把彙總需要的兩個欄位放進索引葉節點。欄位順序是關鍵：`tech_code` 是等值條件放前，
`year_month` 是範圍條件放後——反過來的話範圍掃描會讓後續等值條件失去選擇性。

結果計畫變成 **Index Only Scan**，`Heap Fetches: 0`（完全不回主表），
buffers 從 16,604 降到 **409（41 倍）**，filter 丟棄列數降到 **0**。
執行時間中位數 217.8 ms → 48.3 ms，但**時間比值在四次執行間從 2.3× 跳到 9.5×，
以 buffers 為準**。索引建立耗時 3.5 秒、佔用 103 MB——代價見實驗 2。

### 執行計畫（`EXPLAIN (ANALYZE, BUFFERS)`）

**調校前**

```
Sort  (actual time=104.286..107.008 rows=51 loops=1)
  Sort Key: (sum(accounts)) DESC
  Buffers: shared hit=1240 read=16353
  ->  Finalize GroupAggregate  (actual time=104.107..106.970 rows=51 loops=1)
        Group Key: region_code
        ->  Gather Merge  (actual time=104.085..106.846 rows=102 loops=1)
              Workers Planned: 2   Workers Launched: 2
              ->  Partial HashAggregate  (actual time=97.752..97.772 rows=34 loops=3)
                    ->  Parallel Seq Scan on bench_subscriptions
                          (actual time=0.129..89.926 rows=27920 loops=3)
                          Filter: ((year_month >= '2018-01-01') AND
                                   (year_month <= '2021-12-01') AND (tech_code = 'FTTX'))
                          Rows Removed by Filter: 646813
                          Buffers: shared hit=1221 read=16353
Planning Time: 0.396 ms
Execution Time: 107.090 ms
```

**調校後**

```
Sort  (actual time=69.980..69.987 rows=51 loops=1)
  Sort Key: (sum(accounts)) DESC
  Buffers: shared hit=1 read=416
  ->  HashAggregate  (actual time=69.914..69.946 rows=51 loops=1)
        Group Key: region_code
        ->  Index Only Scan using idx_bench_tech_ym on bench_subscriptions
              (actual time=0.125..26.307 rows=83760 loops=1)
              Index Cond: ((tech_code = 'FTTX') AND (year_month >= '2018-01-01')
                           AND (year_month <= '2021-12-01'))
              Heap Fetches: 0
              Buffers: shared hit=1 read=416
Planning Time: 0.442 ms
Execution Time: 70.063 ms
```

> 上面兩份是同一輪（暖快取）擷取的文字計畫，所以時間比中位數那組溫和。
> **計畫形狀與 buffers 才是重點**：`Parallel Seq Scan` → `Index Only Scan`，
> `Rows Removed by Filter: 646813` → `Heap Fetches: 0`。

---

## 實驗 2：索引的寫入代價

**問**：加索引讓查詢快了，那寫入付出多少？

**答（約 200 字）**：這題比「加索引會變快」重要——**每一個索引都是寫入時的一份額外維護成本**，
而月更新管線每個月都要 upsert。前一個實驗加的索引是為讀優化的，這裡量它的反面。

量測方式：對合成表做 59,160 列的 `INSERT ... ON CONFLICT DO UPDATE`，
先在「PK ＋ 實驗 1 索引」共 2 個索引下量，再加三個業務上很可能會想要的索引
（`region_code`、`(operator_id, year_month)`、`loaded_at DESC`）後重量。
兩組都在「更新既有列」的狀態下進行——第一次當暖機不計入，確保前後條件一致；
各取 5 次的中位數。

結果索引數 2 → 5，upsert 中位數 **2.21s → 3.15s，變慢 1.42 倍，吞吐掉 30%**。
四次獨立執行的比值落在 **1.34×–2.36×**，所以我的結論是「**約多付三到五成，量級是同一個檔次**」，
不宣稱精確倍數。索引本身也佔空間：三個新索引共 49 MB，加上原有的 240 MB。

**這題真正的答案是取捨**：讀多寫少就加，寫多讀少就別加，而**唯一能決定的方法是兩邊都量**。

### 量測結果

| | 索引數 | upsert 59,160 列（中位數，5 次） | 全距 |
|---|---|---|---|
| 加索引前 | 2 | **2.21 s** | 1.64 – 3.20 |
| 加索引後 | 5 | **3.15 s** | 2.11 – 4.18 |

| 索引 | 大小 |
|---|---|
| `bench_subscriptions_pkey` | 137 MB |
| `idx_bench_tech_ym`（實驗 1 建的） | 103 MB |
| `idx_bench_region` | 17 MB |
| `idx_bench_operator` | 16 MB |
| `idx_bench_loaded` | 16 MB |

---

## 實驗 3：Teradata PRIMARY INDEX／skew 對照 — **不做**

原本規劃第三項：在 Teradata ClearScape（60 天免費）上做 PI 選對 vs 選錯的
資料傾斜對照。**依展示深度規則，這一項不放進交付物。**

### 為什麼

規則原文是：**每一項 Teradata 展示，動手前先問「被追問三層我答得出來嗎」。答不出來就不放。**

老實走一遍這三層：

1. 「你的 PI 怎麼選的？」——答得出來（選高基數、均勻分佈、常用於 join 的欄位）
2. 「那 skew factor 多少算可接受？你們的 AMP 數是多少？」——**開始心虛**
3. 「這張表在你們的生產叢集上會怎麼分佈？NUSI 要不要建？」——**答不出來**

Teradata 的正式環境我沒有跑過。註冊一個試用帳號、跑兩句 DDL 得到的「實驗」，
深度只夠停在第一層——**展示一項自己撐不到第三層的東西，代價高於不展示。**

### 所以我改講什麼

上面兩個實驗是**我真的在自己機器上跑出來、每個數字都能解釋機制**的東西。
被追問「為什麼 buffers 降 41 倍」我答得出來（`INCLUDE` 讓彙總所需欄位都在索引葉節點，
`Heap Fetches: 0` 代表完全不回主表）；被追問「為什麼寫入變慢」我也答得出來
（三個 B-tree 每列都要維護）。

**如果面試時被直接問到 Teradata**，我的答法是：
「我沒有 Teradata 實機經驗，不宣稱有。我做的是關聯式資料庫的同一組基本功——
執行計畫怎麼讀、索引的讀寫取捨怎麼量、冪等更新怎麼保證。
這些概念在 Teradata 上換個名字（PI、AMP、skew），但要量的東西是一樣的。」

---

## 復現

```bash
docker compose up -d
.\.venv\Scripts\python.exe src\db_experiments.py
```

原始量測值（JSON）：`logs/db-experiments.json`。
合成表 `bench_subscriptions` 每次執行都會 `DROP` 後重建，結果可復現
（`accounts` 用確定性算式產生，非亂數）。
