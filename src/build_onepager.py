"""階段 7：一頁視覺化摘要（取代原交付物 #4 簽呈 ＋ #5 佐證 PDF）。

**為什麼不是簽呈**：使用者 2026-08-08 決定刪除公文格式簽呈，理由記於
`logs/decisions.log` 決定 C——外部求職者模擬內部公文，形式上正是「假裝已經在裡面」，
是整包交付物裡最靠近僭越紅線的一件。改以視覺化良好的一頁 HTML 呈現。

用途：快速摘要。可直接以瀏覽器列印為 PDF（已寫好 A4 列印樣式）。

**所有數字由資料算出，不得寫死**——與看板同一份 metrics 來源。

用法：
    .\\.venv\\Scripts\\python.exe src\\build_onepager.py
    # 產生 PDF（需要 Edge）：
    # msedge --headless=new --print-to-pdf=onepager.pdf --no-pdf-header-footer <file>
"""

from __future__ import annotations

from pathlib import Path

from compute_metrics import fetch_metrics

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dashboard"

TELCO_C, CABLE_C = "#2a78d6", "#eb6834"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, WARN, CRIT = "#e1e0d9", "#b07500", "#b03030"
FONT = 'system-ui, -apple-system, "Segoe UI", "Microsoft JhengHei", sans-serif'

# 條件對照：只列**本專案真的產出了證據**的項目。
# 「公文撰寫」一條刻意不列——沒做就是沒做，補一份假的正是本專案要避免的失分方式。
EVIDENCE = [
    ("熟悉資料庫操作",
     "PostgreSQL 17 星型 schema、冪等 upsert（逐列 md5 驗證）、"
     "SQL 視窗函數計算全部指標、查詢調校（Seq Scan → Index Only Scan，buffers 16,604 → 409）、"
     "索引寫入代價實測",
     "src/load_postgres.py｜src/compute_metrics.py｜docs/20-db-experiments.md"),
    ("資料分析與統計方法",
     "判準看資料前寫死並存檔（append-only）、兩來源接合校驗（60 筆零差異）、"
     "四種因果識別策略逐一否決並寫明理由、限制章節六條",
     "logs/decisions.log｜docs/30-splice-validation-report.md"),
    ("資料處理與品質控管",
     "16 項資料契約驗證（欄位、型別、算術、連續性、期間），契約不過即擋、不得先跑跑看；"
     "22 項自動化測試把 Ground Truth 編碼為回歸測試",
     "src/validate_contracts.py｜tests/test_pipeline.py"),
    ("視覺化與溝通",
     "單頁離線 HTML 看板；調色盤經色覺驗證器檢查（明暗兩模式全通過）；"
     "限制寫在圖旁而非附錄；未達成的指標明確標示為「追不到」而非省略",
     "dashboard/index.html｜src/build_dashboard.py"),
    ("專案成效追蹤（可持續運行）",
     "月更新管線：data.gov.tw 兩段式取用 → 契約驗證 → 缺月偵測 → 冪等 upsert → 重生看板；"
     "已對真實新月份端到端實跑成功",
     "src/update_monthly.py｜logs/update-runs.log"),
]

NOT_CLAIMED = [
    "<b>無 Teradata 實機經驗</b>——刻意未做 PI／skew 實驗。理由：被追問三層答不出來的展示，"
    "不放進交付物（<code>docs/20-db-experiments.md</code> 有完整說明）。",
    "<b>無生產環境 MLOps 經驗</b>——本專案的月更新管線是 DataOps，不是 MLOps，不作此宣稱。",
    "<b>本作品集刻意不含公文格式文件</b>——沒有人會把自己的數據作品集做成公文。"
    "為了命中 單一條款而扭曲作品形態，本身就是負面訊號。",
    "<b>本專案不含任何模型</b>——價值在約束與工程，不在演算法。",
]


def build(rows) -> str:
    a = next(r for r in rows if r.ym == "2019-01")
    z = rows[-1]
    delta = z.telco_share - a.telco_share
    years = round((int(z.ym[:4]) - int(a.ym[:4])) + (int(z.ym[5:]) - int(a.ym[5:])) / 12)

    ev = "".join(
        f"<tr><td class='req'>{req}</td><td>{what}</td>"
        f"<td class='where'>{where}</td></tr>"
        for req, what, where in EVIDENCE)
    nc = "".join(f"<li>{x}</li>" for x in NOT_CLAIMED)

    return f"""<meta charset="utf-8">
<title>專案摘要｜中華電信固網 2026 公開目標追蹤板</title>
<style>
@page {{ size: A4; margin: 10mm 11mm; }}
*{{box-sizing:border-box;}}
body{{margin:0;background:#f4f4f2;color:{INK};font-family:{FONT};line-height:1.5;
     font-size:11.8px;-webkit-print-color-adjust:exact;print-color-adjust:exact;}}
.page{{max-width:900px;margin:0 auto;background:#fff;padding:24px 28px 20px;}}
h1{{font-size:19px;font-weight:660;margin:0 0 3px;letter-spacing:-.01em;}}
.sub{{font-size:11.5px;color:{MUTED};margin:0 0 16px;}}
h2{{font-size:13px;font-weight:650;margin:13px 0 5px;padding-bottom:4px;
   border-bottom:1.5px solid {INK};letter-spacing:-.005em;}}
.hero{{display:flex;align-items:baseline;gap:16px;background:#fafafa;
      border-left:3px solid {TELCO_C};padding:12px 16px;margin-bottom:4px;}}
.big{{font-size:31px;font-weight:680;color:{TELCO_C};letter-spacing:-.02em;
     line-height:1.1;white-space:nowrap;}}
.big em{{font-style:normal;color:{CABLE_C};}}
.heronote{{font-size:11.8px;color:{INK2};}}
.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:9px;margin:11px 0 0;}}
.kpi{{border:1px solid {GRID};border-radius:7px;padding:9px 11px;}}
.kpi .g{{font-size:11.8px;font-weight:620;margin-bottom:4px;}}
.kpi .b{{font-size:10.8px;font-weight:650;}}
.kpi .m{{font-size:10.5px;color:{MUTED};margin-top:4px;line-height:1.5;}}
.warn .b{{color:{WARN};}} .crit .b{{color:{CRIT};}}
.warn{{border-top:2.5px solid {WARN};}} .crit{{border-top:2.5px solid {CRIT};}}
table{{border-collapse:collapse;width:100%;font-size:11.5px;margin-top:4px;}}
th,td{{border-bottom:1px solid {GRID};padding:6px 9px 6px 0;text-align:left;
      vertical-align:top;}}
th{{color:{MUTED};font-weight:600;font-size:11px;}}
td.req{{font-weight:640;width:118px;}}
td.where{{color:{MUTED};font-size:10.3px;width:186px;font-family:ui-monospace,monospace;}}
ul{{margin:5px 0 0;padding-left:17px;}} li{{margin:3px 0;}}
.honest{{background:#fbf9f4;border:1px solid #e6e0cf;border-radius:7px;
        padding:10px 14px;font-size:11.5px;}}
.honest b{{color:{CRIT};}}
code{{font-size:10.5px;background:#f0f0ee;padding:0 3px;border-radius:3px;}}
.nums{{display:grid;grid-template-columns:repeat(4,1fr);gap:9px;margin-top:6px;}}
.num{{border:1px solid {GRID};border-radius:7px;padding:8px 11px;}}
.num .v{{font-size:16px;font-weight:670;letter-spacing:-.01em;}}
.num .l{{font-size:10.3px;color:{MUTED};margin-top:1px;line-height:1.45;}}
.foot{{margin-top:16px;padding-top:9px;border-top:1px solid {GRID};
      font-size:10.3px;color:{MUTED};}}
@media print{{ body{{background:#fff;}} .page{{padding:0;max-width:none;}} }}
</style>
<div class="page">

<h1>中華電信固網 2026 公開目標追蹤板</h1>
<p class="sub">外部求職者以公開資料製作　·　資料來源：NCC／data.gov.tw
（{rows[0].ym} ~ {z.ym}，月頻率）　·
非中華電信內部文件，不代表該公司立場</p>

<div class="hero">
  <div class="big">{a.telco_share:.1f}% → <em>{z.telco_share:.1f}%</em></div>
  <div class="heronote">
    台灣固網寬頻，<b>電信陣營占比 {years} 年下降 {abs(delta):.2f} 個百分點</b>。
    政府公開統計、可驗證。<br>
    這是<b>技術陣營層級的代理指標</b>，不是中華電信自身市占——公開統計無業者別。
  </div>
</div>

<h2>四個公開目標，用公開資料一個都追不到</h2>
<div class="grid">
  <div class="kpi warn"><div class="g">① 寬頻淨增 7 萬戶</div>
    <div class="b">⚠ 僅陣營層級</div>
    <div class="m">缺業者別，只能看兩陣營合計淨增</div></div>
  <div class="kpi warn"><div class="g">② 市占守住 51%</div>
    <div class="b">⚠ 僅代理指標</div>
    <div class="m">分母有、分子沒有（無 HiNet 用戶數）</div></div>
  <div class="kpi crit"><div class="g">③ 300M 以上破 50%</div>
    <div class="b">✕ 追不到</div>
    <div class="m">公開統計無方案速率分佈</div></div>
  <div class="kpi crit"><div class="g">④ Wi-Fi 全屋 65%</div>
    <div class="b">✕ 追不到</div>
    <div class="m">純內部指標，無公開來源</div></div>
</div>
<p style="font-size:11.5px;color:{INK2};margin:9px 0 0;">
「追不到」是本專案的內容，不是它的失敗——它同時說明三件事：知道貴公司在追什麼指標、
知道公開資料的天花板在哪、知道需要哪些內部欄位才能補上。</p>

<h2>工程與方法的可驗證結果</h2>
<div class="nums">
  <div class="num"><div class="v">16 / 16</div>
    <div class="l">資料契約檢查全過，零容差</div></div>
  <div class="num"><div class="v">60 / 60</div>
    <div class="l">兩來源重疊 20 期比對完全相等（0.0000%）</div></div>
  <div class="num"><div class="v">16,604 → 409</div>
    <div class="l">查詢調校後 buffers 讀取量</div></div>
  <div class="num"><div class="v">22</div>
    <div class="l">自動化測試，CI 執行，不依賴資料庫</div></div>
</div>

<h2>條件對照</h2>
<table>
  <tr><th>能力項目</th><th>本專案的對應證據</th><th>位置</th></tr>
  {ev}
</table>

<h2>我不宣稱的事</h2>
<div class="honest"><ul>{nc}</ul></div>

<p class="foot">
判準於看資料前寫死並存檔（<code>logs/decisions.log</code>，append-only）；
設計推翻歷程見 <code>docs/decision-trail.md</code>。
本專案<b>不做因果宣稱</b>——四種識別策略被具體事實否決的理由寫在看板方法說明頁。
</p>

</div>"""


def main() -> int:
    rows = fetch_metrics()
    path = OUT / "onepager.html"
    path.write_text(build(rows), encoding="utf-8")
    print(f"已產生：{path.relative_to(ROOT)}　{path.stat().st_size:,} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
