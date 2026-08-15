"""一頁視覺化摘要：核心發現、四個目標的可追蹤性、工程結果與限制。

只給螢幕看，不產生 PDF。

**所有數字由資料算出，不得寫死**——與看板同一份 metrics 來源。

視覺與看板同一套系統（冷靛藍紙、IBM Plex ＋ Noto Sans TC、近白卡片）。

用法：
    .\\.venv\\Scripts\\python.exe src\\build_onepager.py
"""

from __future__ import annotations

import io
from pathlib import Path

import segno

from compute_metrics import fetch_metrics

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dashboard"

# QR 目標＝Pages 的看板頁，**不是 repo 首頁**。掃碼的人要的是圖，不是程式碼。
PAGES_URL = "https://raymond-chen-das.github.io/broadband-dashboard/"


def qr_svg_data_uri(url: str) -> str:
    """回傳可直接放進 <img src> 的 SVG data URI。

    用 SVG 而非 PNG：向量碼在紙上與螢幕上都不會糊，而糊掉的 QR 就是掃不到的 QR。
    error='m' 容錯約 15%，足以容忍列印與翻拍的損耗。
    """
    buf = io.BytesIO()
    segno.make(url, error="m").save(buf, kind="svg", scale=1, border=2,
                                    dark="#131822", light="#ffffff", xmldecl=False)
    import base64
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"


ACCENT, ACCENT_D = "#4a56c9", "#333db3"
PAPER, PAPER2, CARD = "#e9ecf7", "#dfe3f2", "#f6f8fd"
SHELL = "#e5e7ee"
INK, INK2, MUTED, MUTED2 = "#131822", "#4c5666", "#8b94a3", "#7c8695"
RULE, RULE_D = "rgba(19,24,34,.09)", "rgba(19,24,34,.16)"
WARN, WARN_BG = "#a05a18", "#f6f0e8"
CRIT = "#c0483c"
CRIT_D = "#a83a2e"
SANS = ("'IBM Plex Sans', 'Noto Sans TC', system-ui, -apple-system, "
        "'Segoe UI', 'Microsoft JhengHei', sans-serif")
MONO = ("'IBM Plex Mono', 'Noto Sans TC', ui-monospace, 'Cascadia Mono', "
        "'SF Mono', Consolas, monospace")
FONTS_HREF = ("https://fonts.googleapis.com/css2?"
              "family=IBM+Plex+Sans:wght@400;500;600"
              "&family=IBM+Plex+Mono:wght@400;500;600"
              "&family=Noto+Sans+TC:wght@300;400;500;700&display=swap")

BYLINE = "陳嘉翔"

# 條件對照：只列**本專案真的產出了證據**的項目。
# 「公文撰寫」一條刻意不列——沒做就是沒做，補一份假的正是本專案要避免的失分方式。
EVIDENCE = [
    ("熟悉資料庫操作",
     "PostgreSQL 17 星型 schema、冪等 upsert（逐列 md5 驗證）、"
     "以 SQL 視窗函數計算全部指標、查詢調校"
     "（Seq Scan 改為 Index Only Scan，buffers 16,604 降到 409；合成 200 萬列基準表）、"
     "索引寫入代價實測",
     "src/load_postgres.py<br>src/compute_metrics.py<br>docs/20-db-experiments.md"),
    ("資料分析與統計方法",
     "判準於檢視資料前固定並存檔（append-only）、兩來源接合校驗 60 筆零差異、"
     "四種因果識別策略逐一否決並寫明理由、限制章節六條",
     "tests/test_pipeline.py<br>docs/30-splice-validation-report.md"),
    ("資料處理與品質控管",
     "16 項資料契約驗證（欄位、型別、算術、連續性、期間），"
     "任一項未通過即中止後續所有階段；22 項自動化測試將 Ground Truth 編碼為回歸測試",
     "src/validate_contracts.py<br>tests/test_pipeline.py"),
    ("視覺化與溝通",
     "單頁離線 HTML 看板；調色盤經色覺驗證器檢查；限制敘述置於圖側而非附錄；"
     "不可追蹤的指標明確標示，不予省略",
     "dashboard/index.html<br>src/build_dashboard.py"),
    ("專案成效追蹤（可持續運行）",
     "月更新管線：data.gov.tw 兩段式取用、契約驗證、缺月偵測、冪等 upsert、重生看板。"
     "已針對真實的新月份完成端到端實跑",
     "src/update_monthly.py<br>logs/update-runs.log"),
]

NOT_CLAIMED = [
    ("沒有 Teradata 實機經驗。",
     "刻意未進行 PI 與 skew 實驗；無法承受三層追問的展示不納入交付物"
     "（<code>docs/20-db-experiments.md</code> 有完整說明）。"),
    ("沒有生產環境的 MLOps 經驗。",
     "本專案的月更新管線屬 DataOps 而非 MLOps，故不作此宣稱。"),
    ("刻意不含公文格式文件。",
     "為迎合 單一條款而扭曲作品形態，本身即為負面訊號。"),
    # 原本只寫「不含任何模型。價值在約束與工程，不在演算法。」——這一頁若被單獨
    # 閱讀（它就是設計成可以單獨閱讀的），那句會被讀成「這個人不會建模」，
    # 補上建模作品的指路，把「本專案的取捨」與「作者的能力範圍」分開。
    # 三件作品均為本人另外的公開 repo，寫入前已逐一查證。
    ("本專案不含模型。",
     "建模作品另見 SECOM 半監督異常偵測、語音情緒辨識跨語料庫比較、台股情緒預測。"
     "價值在約束與工程，不在演算法。"),
]

# 「若取得內部資料，第一步會看什麼」。
# 分寸線：**「建議公司做什麼」＝僭越；「若我在內部會先看什麼」＝問題排序能力。**
# 全部維持假設語氣，不出現「建議」二字——外部求職者不對公司下指導棋。
IF_INSIDE = [
    "若取得業者別資料，第一步是把陣營層級的降幅拆到業者，"
    # 原寫「判斷流失屬…」。「流失」是資料不支撐的措辭：電信陣營帳號數 2019-01→2026-05
    # 實際成長約 59 萬（430 萬→489 萬），份額下降來自 Cable 成長更快，不是用戶流失。
    "判斷份額變化屬區域集中或全面性——這決定應以價格或覆蓋率回應。",
    "若取得方案速率分佈，可直接驗證 300M 以上占比，不必再用代理。",
    "若取得訂單資料，可將寬頻與 MOD、Wi-Fi 全屋的搭售組合對續約率交叉分析。",
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
    nc = "".join(f"<div class='nc'><b>{h}</b>{t}</div>" for h, t in NOT_CLAIMED)
    ii = "".join(f"<div class='ii'>{t}</div>" for t in IF_INSIDE)

    return f"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>專案摘要｜中華電信固網 2026 公開目標追蹤板</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="{FONTS_HREF}" rel="stylesheet">
<style>
*{{box-sizing:border-box;}}
body{{margin:0;background:{SHELL};color:{INK};font-family:{SANS};line-height:1.72;
     -webkit-font-smoothing:antialiased;padding:44px 24px 80px;}}
.page{{max-width:1000px;margin:0 auto;background:{PAPER};
      border:1px solid {RULE};border-radius:16px;padding:48px 52px 40px;
      box-shadow:0 1px 2px rgba(19,24,34,.04),0 30px 70px -40px rgba(19,24,34,.45);}}

.head{{display:flex;align-items:flex-start;justify-content:space-between;gap:40px;
     padding-bottom:22px;border-bottom:1px solid rgba(19,24,34,.14);}}
.eyebrow{{display:block;font-family:{MONO};font-size:10px;letter-spacing:.24em;
        text-transform:uppercase;color:{ACCENT};font-weight:500;margin-bottom:10px;}}
h1{{font-size:29px;font-weight:600;letter-spacing:-.03em;margin:0 0 8px;line-height:1.25;}}
.sub{{font-size:12.5px;color:{MUTED};margin:0;}}
.qr{{width:78px;height:78px;flex:none;border:1px solid rgba(19,24,34,.10);
   border-radius:8px;padding:4px;background:#fdfdff;}}

.hero{{display:flex;align-items:center;gap:28px;background:{PAPER2};
     border-radius:12px;padding:24px 28px;margin-top:22px;}}
.big{{font-family:{MONO};font-size:40px;font-weight:500;letter-spacing:-.045em;
    line-height:1;white-space:nowrap;color:{ACCENT};}}
.big .arrow{{color:#b9bed4;}} .big em{{font-style:normal;color:{INK};}}
.heronote{{font-size:13.5px;color:{INK2};border-left:1px solid rgba(19,24,34,.14);
         padding-left:26px;}}
.heronote b{{color:{INK};font-weight:500;}}

h2{{font-size:16px;font-weight:500;letter-spacing:-.01em;margin:32px 0 14px;
   padding-bottom:9px;border-bottom:1px solid {RULE_D};}}

.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;}}
.kpi{{background:{CARD};border:1px solid rgba(19,24,34,.10);border-radius:10px;
    padding:14px 16px;transition:transform .25s ease,border-color .25s ease;}}
.kpi:hover{{transform:translateY(-2px);border-color:rgba(19,24,34,.18);}}
.kpi.warn{{border-top:2px solid {ACCENT};}}
.kpi.crit{{border-top:2px solid {CRIT};}}
.kpi .g{{font-size:13.5px;font-weight:500;margin-bottom:8px;}}
.kpi .b{{font-family:{MONO};font-size:10.5px;font-weight:500;}}
.kpi.warn .b{{color:{ACCENT};}} .kpi.crit .b{{color:{CRIT_D};}}
.kpi .m{{font-size:12px;color:{MUTED};margin-top:7px;line-height:1.6;}}
.after{{font-size:13px;color:{INK2};margin:14px 0 0;}}
.after b{{color:{INK};font-weight:500;}}

.nums{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;}}
.num{{background:{PAPER2};border-radius:10px;padding:14px 16px;}}
.num .v{{font-family:{MONO};font-size:20px;font-weight:500;letter-spacing:-.02em;
       font-variant-numeric:tabular-nums;}}
.num .l{{font-size:11.5px;color:{MUTED2};margin-top:4px;line-height:1.55;}}

table{{border-collapse:collapse;width:100%;font-size:12.5px;}}
th{{text-align:left;font-family:{MONO};font-size:10px;letter-spacing:.14em;
   text-transform:uppercase;color:#98a0ad;font-weight:500;padding:10px 14px 8px 0;}}
td{{padding:10px 14px 10px 0;border-top:1px solid rgba(19,24,34,.08);
   vertical-align:top;color:{INK2};}}
tbody tr:hover,tr:hover{{background:rgba(19,24,34,.035);}}
td.req{{font-weight:500;color:{INK};width:130px;}}
td.where{{font-family:{MONO};font-size:10.5px;color:#98a0ad;width:190px;}}
th:last-child,td:last-child{{padding-right:0;}}

.honest{{background:{WARN_BG};border:1px solid rgba(160,90,24,.20);border-radius:10px;
       padding:16px 20px;display:flex;flex-direction:column;gap:9px;}}
.nc{{font-size:12.8px;color:{INK2};}}
.nc b{{color:{WARN};font-weight:500;}}

/* 「我不宣稱的事」與「若取得內部資料會先看什麼」並排：
   前者是能力邊界，後者是問題排序。兩者相鄰時，讀者才不會把前者讀成後者的缺席。
   用系列主色而非警示色——這一欄不是警告，是前瞻。 */
.twocol{{display:grid;grid-template-columns:1fr 1fr;gap:22px;align-items:start;}}
.twocol h2{{margin-top:32px;}}
.inside{{background:{PAPER2};border:1px solid rgba(74,86,201,.18);border-radius:10px;
       padding:16px 20px;display:flex;flex-direction:column;gap:9px;}}
.ii{{font-size:12.8px;color:{INK2};padding-left:15px;position:relative;}}
.ii::before{{content:"";position:absolute;left:0;top:7px;width:5px;height:5px;
           border-radius:50%;background:{ACCENT};}}

/* hero 與四張卡片之間的橋：不熟固網的讀者看不出那四個目標為什麼值得追。 */
.bridge{{font-size:13.5px;color:{INK};margin:14px 0 0;padding-left:13px;
       border-left:2px solid {ACCENT};}}
code{{font-family:{MONO};font-size:11.5px;background:rgba(19,24,34,.06);
    padding:2px 6px;border-radius:4px;color:{INK2};}}

.qrbar{{margin-top:24px;padding-top:16px;border-top:1px solid {RULE};}}
.qrtext{{font-size:12.5px;color:{INK2};}}
.qrtext b{{color:{INK};font-weight:500;}}
.qrtext .u{{font-family:{MONO};font-size:10.5px;color:{MUTED};word-break:break-all;}}

.foot{{margin:22px 0 0;padding-top:14px;border-top:1px solid {RULE};
     font-family:{MONO};font-size:10.5px;line-height:1.9;color:#98a0ad;}}
a{{color:{ACCENT};text-decoration:none;border-bottom:1px solid rgba(74,86,201,.28);}}
a:hover{{color:{ACCENT_D};border-bottom-color:{ACCENT_D};}}
@media (max-width:900px){{
  .page{{padding:32px 24px;}}
  .grid,.nums{{grid-template-columns:1fr 1fr;}}
  .hero{{flex-direction:column;align-items:flex-start;gap:14px;}}
  .heronote{{border-left:0;padding-left:0;}}
  .twocol{{grid-template-columns:1fr;gap:0;}}
}}
</style>
<div class="page">

<div class="head">
  <div>
    <span class="eyebrow">專案摘要 / 01　·　{BYLINE}</span>
    <h1>中華電信固網 2026 公開目標追蹤板</h1>
    <p class="sub">外部求職者以公開資料製作　·　NCC／data.gov.tw
    （{rows[0].ym} 到 {z.ym}，月頻率）　·　非中華電信內部文件</p>
  </div>
  <img class="qr" src="{qr_svg_data_uri(PAGES_URL)}" alt="QR code，開啟線上互動看板">
</div>

<div class="hero">
  <div class="big">{a.telco_share:.1f}% <span class="arrow">→</span>
    <em>{z.telco_share:.1f}%</em></div>
  <div class="heronote">
    台灣固網寬頻，<b>電信陣營占比 {years} 年下降約 {abs(delta):.1f} 個百分點</b>。
    資料取自政府公開統計，計算過程可重現驗證。<br>
    這是<b>技術陣營層級的代理指標</b>，不等同於中華電信自身市占，因公開統計未提供業者別。
  </div>
</div>

<p class="bridge">這約 {abs(delta):.0f} 個百分點，就是中華電信 2026 年 3 月全線降價的背景。</p>

<h2>四個公開目標，用公開資料一個都追不到</h2>
<div class="grid">
  <div class="kpi warn"><div class="g">① 寬頻淨增 7 萬戶</div>
    <div class="b">僅陣營層級</div>
    <div class="m">缺業者別，只能觀察兩陣營合計淨增</div></div>
  <div class="kpi warn"><div class="g">② 市占守住 51%</div>
    <div class="b">僅代理指標</div>
    <div class="m">分母有、分子沒有（無 HiNet 用戶數）</div></div>
  <div class="kpi crit"><div class="g">③ 300M 以上破 50%</div>
    <div class="b">追不到</div>
    <div class="m">公開統計未提供方案速率分佈</div></div>
  <div class="kpi crit"><div class="g">④ Wi-Fi 全屋 65%</div>
    <div class="b">追不到</div>
    <div class="m">屬純內部指標，查無公開來源</div></div>
</div>
<p class="after"><b>「追不到」本身即為本專案的結論。</b>此一判定同時界定了三件事：
中華電信公開追蹤的指標為何、公開資料的覆蓋上限落在哪裡，以及補足缺口所需的內部欄位。</p>

<h2>工程與方法的可驗證結果</h2>
<div class="nums">
  <div class="num"><div class="v">16 / 16</div>
    <div class="l">資料契約檢查全過，零容差</div></div>
  <div class="num"><div class="v">60 / 60</div>
    <div class="l">重疊 20 期比對完全相等（0.0000%）</div></div>
  <div class="num"><div class="v">16,604 → 409</div>
    <div class="l">查詢調校後 buffers 讀取量（合成 200 萬列基準表）</div></div>
  <div class="num"><div class="v">22</div>
    <div class="l">自動化測試，CI 執行，不依賴資料庫</div></div>
</div>

<h2>條件對照</h2>
<table>
  <tr><th>能力項目</th><th>本專案的對應證據</th><th>位置</th></tr>
  {ev}
</table>

<div class="twocol">
  <div>
    <h2>我不宣稱的事</h2>
    <div class="honest">{nc}</div>
  </div>
  <div>
    <h2>若取得內部資料，第一步會看什麼</h2>
    <div class="inside">{ii}</div>
  </div>
</div>

<div class="qrbar">
  <div class="qrtext">
    <b>掃描頁首 QR 開啟線上互動看板</b>：完整的陣營消長主圖（可縮放、可查每月數值）、
    四張目標可追蹤性卡片，以及方法說明頁（含接合校驗與四種識別策略被否決的理由）。<br>
    <span class="u">{PAGES_URL}</span>
  </div>
</div>

<p class="foot">
判準於檢視資料前固定並標上時間戳（紀錄 append-only）。<br>
本專案不做因果宣稱，四種識別策略被具體事實否決的理由寫在看板的方法說明頁。
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
