"""階段 5：單頁 HTML 看板（Plotly，可離線開啟）。

四個區塊（規格第六節），排序依規格第七節分鏡——**以發現開場**：
  0  核心發現 ＋ 陣營消長主圖（＋ 三個限制，畫在圖旁不放附錄）
  1  四張 KPI 可追蹤性卡片（兩張 ⚠️、兩張 ❌，**不得美化成可追蹤**）
  2  完整版 MOCK（假資料，**明顯標示**）
  3  方法說明頁（資料來源、接合校驗、7.1 五行、限制章節）

**禁止 matplotlib**（規格第六節）。**不做因果宣稱**——事件時點只做視覺標記。

用法：
    .\\.venv\\Scripts\\python.exe src\\build_dashboard.py
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from compute_metrics import fetch_metrics

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dashboard"
OUT.mkdir(parents=True, exist_ok=True)

# --inline：把 Plotly 內嵌成單一自足檔案（約 4.7MB），供寄送或單獨上傳。
# 預設不內嵌，理由見 build() 內的註解。
INLINE = "--inline" in sys.argv

# ── 調色盤（dataviz 參考實例，validate_palette.js 全 PASS）────────────────
# 兩陣營是**兩個實體**，所以用 categorical 兩槽，不是同色相深淺。
#   node validate_palette.js "#2a78d6,#eb6834" --mode light → ALL CHECKS PASS
#   （最差相鄰 CVD ΔE 24.7、常視覺 ΔE 33.6，門檻分別為 8 與 15）
TELCO_C, CABLE_C = "#2a78d6", "#eb6834"
SURFACE, PLANE = "#fcfcfb", "#f9f9f7"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS = "#e1e0d9", "#c3c2b7"
# 事件時點＝中性次要墨色；資料斷點＝status critical（4.68:1），並一律附 ⚠ 圖示與文字標籤，
# 不讓顏色單獨承載意義。兩者刻意用不同線型：事件實線、斷點虛線。
EVENT_C, BREAK_C = "#52514e", "#d03b3b"
FONT = 'system-ui, -apple-system, "Segoe UI", "Microsoft JhengHei", sans-serif'

# 事件時點（規格第九節第 5 條：**僅視覺標記，不估計任何效果**）
EVENTS = [
    (dt.date(2022, 5, 1), "2022-05　MSO 價格戰", "工商時報 2022-05-23"),
    (dt.date(2026, 3, 18), "2026-03-18　中華電信降價", "經濟日報／MoneyDJ"),
]
# 資料斷點（logs/decisions.log 決定 A：標記，不修改數字，不宣稱成因）
BREAKS = [
    (dt.date(2009, 4, 1), "2009-04"),
    (dt.date(2020, 1, 1), "2020-01"),
]

# 四個公開目標（規格第二節。⚠️ 職稱務必寫全）
KPIS = [
    dict(n=1, goal="寬頻淨增 <b>7 萬戶</b>", state="partial",
         badge="⚠️ 僅陣營層級",
         miss="缺中華電信自身用戶數——公開統計只有技術別（ADSL／FTTX／Cable Modem），無業者別。",
         proxy="能追到的最接近代理：電信陣營 vs Cable 陣營的月度淨增量（見上圖下半）。"),
    dict(n=2, goal="市占 <b>守住 51%</b>", state="partial",
         badge="⚠️ 僅代理指標",
         miss="分母有（全台固網寬頻帳號數），<b>分子沒有</b>（HiNet 用戶數）。",
         proxy="能追到的最接近代理：電信陣營占比 66.36%（2026-04）——但那是陣營，不是中華電信。"),
    dict(n=3, goal="<b>300M 以上占比破 50%</b><br><span class='sub'>2022:27% → 2025:46%</span>",
         state="none", badge="❌ 追不到",
         miss="公開統計無訂閱方案速率分佈。M-Lab 有 ISP 級實測速度，但<b>測速 ≠ 訂閱方案</b>，且資料全球停更於 2024-03。",
         proxy="需要的內部資料：方案別訂閱數（speed tier × month）。"),
    dict(n=4, goal="<b>Wi-Fi 全屋滲透 65%</b><br><span class='sub'>2022:18% → 2025:54%</span>",
         state="none", badge="❌ 追不到",
         miss="純內部指標，<b>無任何公開來源</b>。",
         proxy="需要的內部資料：全屋 Wi-Fi 加購方案的裝機數 ÷ 寬頻用戶數。"),
]

BASE_LAYOUT = dict(
    paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
    font=dict(family=FONT, size=12.5, color=INK2),
    hovermode="x unified",
)


def to_date(ym: str) -> dt.date:
    y, m = ym.split("-")
    return dt.date(int(y), int(m), 1)


# ══════════════════════════════════════════════════════════════════════════
#  主圖：上格＝兩陣營帳號數（雙線），下格＝月度淨增量（長條）
#  **刻意不用雙 y 軸**——帳號數與淨增量是兩個尺度，疊在同一張圖是
#  資料視覺化的頭號錯誤。改用共用 x 軸的上下兩格，讀者的比較基準才不會被扭曲。
# ══════════════════════════════════════════════════════════════════════════
def main_figure(rows) -> go.Figure:
    x = [to_date(r.ym) for r in rows]

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.07,
        row_heights=[0.62, 0.38],
        subplot_titles=("兩陣營固網寬頻帳號數（月）", "月度淨增量（月差分）"),
    )

    for name, color, vals in (
        ("電信陣營（ADSL＋FTTX）", TELCO_C, [r.telco for r in rows]),
        ("Cable 陣營（Cable Modem）", CABLE_C, [r.cable for r in rows]),
    ):
        fig.add_trace(go.Scatter(
            x=x, y=vals, mode="lines", name=name,
            line=dict(color=color, width=2),
            hovertemplate=f"{name}<br>%{{y:,.0f}} 帳號<extra></extra>"),
            row=1, col=1)

    for name, color, vals in (
        ("電信陣營淨增", TELCO_C, [r.telco_net for r in rows]),
        ("Cable 陣營淨增", CABLE_C, [r.cable_net for r in rows]),
    ):
        fig.add_trace(go.Bar(
            x=x, y=vals, name=name, marker=dict(color=color, line_width=0),
            showlegend=False,
            hovertemplate=f"{name}<br>%{{y:+,.0f}}<extra></extra>"),
            row=2, col=1)

    # 事件時點：實線、中性色。**只標時點，不估計效果。**
    # 標籤放在圖內、兩條線之間的空白帶並上下錯開。放在圖頂會有兩個問題：
    # 靠右的 2026-03 會被右緣切掉（改右錨後又與 2022-05 的左錨標籤水平重疊）。
    # 2022 年後藍線約 4.3~4.9M、橘線約 2.1~2.5M，中間 y domain 0.5~0.8 是空的。
    x_lo, x_hi = dt.date(2006, 8, 1), dt.date(2026, 9, 1)
    span = (x_hi - x_lo).days
    for i, (when, label, _src) in enumerate(EVENTS):
        near_right = (x_hi - when).days / span < 0.15
        fig.add_vline(x=when, line=dict(color=EVENT_C, width=1.2), layer="below")
        fig.add_annotation(x=when, y=0.76 - 0.13 * i, yref="y domain", text=label,
                           showarrow=False,
                           xshift=-5 if near_right else 5,
                           xanchor="right" if near_right else "left",
                           font=dict(size=11, color=EVENT_C), row=1, col=1)

    # 資料斷點：虛線、status critical，並附 ⚠ 圖示與文字——顏色不單獨承載意義。
    for when, label in BREAKS:
        fig.add_vline(x=when, line=dict(color=BREAK_C, width=1.2, dash="dash"),
                      layer="below")
        # 11.5px 不是美感選擇：手機上圖在捲動容器裡是原尺寸顯示，
        # 10.5px 在小螢幕上是勉強可讀的邊緣值，而這是圖上最需要被讀到的警語。
        fig.add_annotation(x=when, y=0.0, yref="y domain", text=f"⚠ 資料斷點 {label}",
                           showarrow=False, yshift=14, xshift=3, xanchor="left",
                           font=dict(size=11.5, color=BREAK_C), row=1, col=1)

    fig.update_xaxes(showgrid=False, zeroline=False, linecolor=AXIS,
                     ticks="outside", tickcolor=AXIS, ticklen=4,
                     tickfont=dict(size=11.5, color=MUTED),
                     range=[dt.date(2006, 8, 1), dt.date(2026, 9, 1)])
    fig.update_yaxes(showgrid=True, gridcolor=GRID, zeroline=False, linecolor=AXIS,
                     tickfont=dict(size=11.5, color=MUTED))
    fig.update_yaxes(tickformat=",.0f", row=1, col=1)
    fig.update_yaxes(tickformat=",.0f", zeroline=True, zerolinecolor=AXIS,
                     zerolinewidth=1, row=2, col=1)
    # barmode 必須是 group 不是 relative：兩陣營是**兩個實體**，堆疊會讓讀者看到
    # 一個沒有意義的「合計淨增」，而本圖的問題是「誰在增、誰在減」。
    fig.update_layout(
        height=620, barmode="group", bargap=0.15, bargroupgap=0,
        margin=dict(l=70, r=28, t=74, b=48),
        legend=dict(orientation="h", y=1.10, x=0, font=dict(size=12)),
        **BASE_LAYOUT)
    for a in fig.layout.annotations[:2]:
        a.font = dict(size=13, color=INK, family=FONT)
    return fig


# ══════════════════════════════════════════════════════════════════════════
#  MOCK：若有內部資料，四張卡會長什麼樣。**全部是假資料。**
# ══════════════════════════════════════════════════════════════════════════
def mock_figure() -> go.Figure:
    months = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.13,
                        subplot_titles=("【假資料】300M 以上方案占比",
                                        "【假資料】Wi-Fi 全屋滲透率"))
    fig.add_trace(go.Scatter(x=months, y=[46.2, 47.1, 47.9, 48.8, 49.4, 50.3],
                             mode="lines+markers", line=dict(color=TELCO_C, width=2),
                             marker=dict(size=8), name="300M 以上占比",
                             showlegend=False,
                             hovertemplate="%{x}<br>%{y}%（假資料）<extra></extra>"),
                  row=1, col=1)
    fig.add_hline(y=50, line=dict(color=MUTED, width=1, dash="dot"), row=1, col=1)
    fig.add_annotation(x=months[0], y=50, text="目標 50%", showarrow=False, yshift=10,
                       xanchor="left", font=dict(size=11.5, color=MUTED), row=1, col=1)
    fig.add_trace(go.Scatter(x=months, y=[54.0, 55.8, 57.9, 59.6, 61.2, 62.8],
                             mode="lines+markers", line=dict(color=CABLE_C, width=2),
                             marker=dict(size=8), name="Wi-Fi 全屋滲透",
                             showlegend=False,
                             hovertemplate="%{x}<br>%{y}%（假資料）<extra></extra>"),
                  row=1, col=2)
    fig.add_hline(y=65, line=dict(color=MUTED, width=1, dash="dot"), row=1, col=2)
    fig.add_annotation(x=months[0], y=65, text="目標 65%", showarrow=False, yshift=10,
                       xanchor="left", font=dict(size=11.5, color=MUTED), row=1, col=2)
    fig.update_xaxes(showgrid=False, linecolor=AXIS, tickfont=dict(size=11, color=MUTED))
    fig.update_yaxes(showgrid=True, gridcolor=GRID, ticksuffix="%",
                     linecolor=AXIS, tickfont=dict(size=11, color=MUTED))
    # y 範圍寫死並涵蓋目標線——autorange 只框住資料，65% 的目標線會被切到框外，
    # 而「距離目標還有多遠」正是這兩張示範圖唯一要傳達的事。
    fig.update_yaxes(range=[45.5, 52.0], row=1, col=1)
    fig.update_yaxes(range=[52.0, 67.5], row=1, col=2)
    fig.update_layout(height=310, margin=dict(l=56, r=24, t=54, b=40), **BASE_LAYOUT)
    for a in fig.layout.annotations[:2]:
        a.font = dict(size=12.5, color=INK, family=FONT)
    return fig


CSS = f"""
*{{box-sizing:border-box;}}
body{{margin:0;background:{PLANE};color:{INK};font-family:{FONT};line-height:1.7;}}
.wrap{{max-width:1180px;margin:0 auto;padding:40px 22px 80px;}}
h1{{font-size:27px;font-weight:660;margin:0 0 10px;letter-spacing:-.015em;line-height:1.35;}}
h2{{font-size:19px;font-weight:640;margin:52px 0 8px;letter-spacing:-.01em;}}
h3{{font-size:14.5px;font-weight:640;margin:22px 0 6px;}}
.lede{{font-size:15px;color:{INK2};margin:0 0 4px;}}
.card{{background:{SURFACE};border:1px solid rgba(11,11,11,.10);border-radius:11px;
      padding:10px 10px 6px;margin-top:18px;
      /* 圖表在自己的容器裡橫向捲動，頁面本體永不橫向捲動。
         在 375px 手機上把兩格子圖硬壓進去，軸標籤會擠成看不懂的東西——
         給最小寬度讓使用者左右滑，比壓扁誠實。 */
      overflow-x:auto;-webkit-overflow-scrolling:touch;}}
.card > div{{min-width:700px;}}
.scrollhint{{display:none;font-size:11.5px;color:{MUTED};margin:6px 2px 0;}}
.hero{{background:{SURFACE};border:1px solid rgba(11,11,11,.10);border-radius:11px;
      padding:22px 26px;margin:20px 0 0;}}
.figure{{font-size:44px;font-weight:680;letter-spacing:-.02em;color:{TELCO_C};line-height:1.15;}}
.figure small{{font-size:16px;font-weight:600;color:{INK2};}}
.note{{font-size:12.8px;color:{INK2};margin-top:14px;line-height:1.75;}}
.note b{{color:{INK};}}
.limits{{background:{SURFACE};border:1px solid rgba(11,11,11,.10);border-left:3px solid {MUTED};
        border-radius:0 9px 9px 0;padding:14px 18px;margin-top:14px;font-size:13px;color:{INK2};}}
.limits li{{margin:5px 0;}} .limits ol{{margin:6px 0 0;padding-left:20px;}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(255px,1fr));gap:14px;margin-top:18px;}}
.kpi{{background:{SURFACE};border:1px solid rgba(11,11,11,.10);border-radius:11px;padding:16px 18px;
     display:flex;flex-direction:column;}}
.kpi.partial{{border-top:3px solid #fab219;}}
.kpi.none{{border-top:3px solid {BREAK_C};}}
.kpi .idx{{font-size:11.5px;color:{MUTED};font-weight:600;letter-spacing:.06em;}}
.kpi .goal{{font-size:17px;font-weight:600;margin:5px 0 12px;line-height:1.5;}}
.kpi .goal .sub{{font-size:12.5px;color:{MUTED};font-weight:500;}}
.badge{{display:inline-block;font-size:12.5px;font-weight:640;padding:3px 10px;border-radius:999px;
       margin-bottom:11px;align-self:flex-start;}}
.badge.partial{{background:rgba(250,178,25,.16);color:#7a5300;}}
.badge.none{{background:rgba(208,59,59,.12);color:#9c2020;}}
.kpi .miss{{font-size:12.8px;color:{INK2};}}
.kpi .proxy{{font-size:12.4px;color:{MUTED};margin-top:9px;padding-top:9px;
            border-top:1px solid {GRID};}}
.mockwrap{{border:2px dashed {BREAK_C};border-radius:12px;padding:6px 10px 10px;
          background:repeating-linear-gradient(45deg,rgba(208,59,59,.035) 0 12px,transparent 12px 24px);}}
.mockbar{{background:{BREAK_C};color:#fff;font-size:12.5px;font-weight:660;letter-spacing:.04em;
         padding:6px 14px;border-radius:7px;display:inline-block;margin:10px 0 4px;}}
table{{border-collapse:collapse;font-size:12.8px;margin-top:10px;width:100%;
      font-variant-numeric:tabular-nums;}}
th,td{{border-bottom:1px solid {GRID};padding:7px 12px 7px 0;text-align:left;vertical-align:top;}}
th{{color:{MUTED};font-weight:600;}}
code{{font-size:12px;background:rgba(11,11,11,.05);padding:1px 5px;border-radius:4px;}}
.foot{{font-size:12px;color:{MUTED};margin-top:44px;padding-top:16px;border-top:1px solid {GRID};}}

/* ── 行動裝置（QR 掃進來的主要情境）──────────────────────────────
   375px（iPhone SE）／390px（iPhone 14）實測後加入。
   先前所有碰撞檢查只跑 900／1100／1400px，完全沒涵蓋這一段。 */
@media (max-width: 640px) {{
  .wrap {{ padding: 22px 14px 56px; }}
  h1 {{ font-size: 22px; }}
  h2 {{ font-size: 17px; margin-top: 38px; }}
  .lede {{ font-size: 14px; }}
  .hero {{ padding: 16px 16px; }}
  .figure {{ font-size: 30px; }}
  .figure small {{ display: block; margin-top: 4px; font-size: 14px; }}
  .scrollhint {{ display: block; }}
  .kpis {{ grid-template-columns: 1fr; }}
  .limits {{ padding: 12px 14px; }}
  .mockwrap {{ padding: 6px 8px 8px; }}
  table {{ font-size: 12px; }}
  /* 長字串（URL、路徑）在窄螢幕會把版面撐開 */
  code {{ word-break: break-all; }}
}}
"""

# 規格 7.1：方法說明頁的完整區塊。**預先寫死，不得臨場改寫，不得刪減任何一條。**
WHY_NO_CAUSAL = """
<h3>為什麼不做因果推論</h3>
<p style="font-size:13.2px;margin:4px 0 0;">
本分析<b>不估計降價的效果</b>，因為四種識別策略都被具體事實否決：</p>
<ol style="font-size:13px;margin:7px 0 0;padding-left:22px;">
  <li>M-Lab 的 ISP 級測速資料全球停更於 2024-03，2026 事件無資料</li>
  <li>即使有資料，2026-03 事件的後測期僅 4.5 個月，估不出穩定效果</li>
  <li>政府統計只有技術別、無業者別，做不出 treatment／control 分組</li>
  <li>改用技術陣營分組後，2022 的價格戰是由對照組（有線電視業者）發動的</li>
</ol>
"""


def kpi_cards() -> str:
    out = []
    for k in KPIS:
        out.append(f"""
        <div class="kpi {k['state']}">
          <div class="idx">目標 {k['n']}</div>
          <div class="goal">{k['goal']}</div>
          <span class="badge {k['state']}">{k['badge']}</span>
          <div class="miss"><b>缺什麼資料：</b>{k['miss']}</div>
          <div class="proxy">{k['proxy']}</div>
        </div>""")
    return f'<div class="kpis">{"".join(out)}</div>'


def build(rows) -> str:
    first, last = rows[0], rows[-1]
    # 錨點固定在 2019-01（7164 的起點，也是核心發現的基準），終點跟著最新資料走。
    # **這些數字一律由資料算出，不得寫死**——寫死的顯示值會在下一次月更新後
    # 與圖上的資料靜靜地分家，而那正是本專案定義的失敗模式。
    a, z = next(r for r in rows if r.ym == "2019-01"), last
    delta = z.telco_share - a.telco_share
    years = round((int(z.ym[:4]) - int(a.ym[:4])) + (int(z.ym[5:]) - int(a.ym[5:])) / 12)

    # 2020-01 斷點對占比的單月衝擊，以及它佔全期變化的比例——同樣由資料算，不寫死。
    i = next(k for k, r in enumerate(rows) if r.ym == "2020-01")
    brk_pp = rows[i].telco_share - rows[i - 1].telco_share
    brk_share = abs(brk_pp / delta) * 100
    residual = delta - brk_pp          # 扣掉該月之後剩下的降幅

    # 預設把 plotly.min.js 放成同目錄的獨立檔（`directory`），不內嵌。
    # 內嵌版是 4.7MB，而月更新管線每個月都會重生一次看板——每年就往 git
    # 塞 56MB 的新 blob，而其中 99% 是每次都一樣的函式庫。
    # 外部引用同樣可離線開啟（只要 plotly.min.js 跟著同一個資料夾）。
    # 要寄出或單獨上傳的單一檔版本，用 `--inline` 產生。
    # responsive: True 是 QR 掃進來的必要條件——沒有它，Plotly 把寬度釘在
    # 產生當下的值，手機上就是一張切一半的圖。（先前只設了 displayModeBar。）
    opts = dict(full_html=False, config={"displayModeBar": False, "responsive": True})
    js = True if INLINE else "directory"
    fig_main = main_figure(rows).to_html(include_plotlyjs=js, **opts)
    fig_mock = mock_figure().to_html(include_plotlyjs=False, **opts)

    return f"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>中華電信固網 2026 公開目標追蹤板</title>
<style>{CSS}</style>
<div class="wrap">

<h1>台灣固網市場，電信陣營的份額 {years} 年掉了 {abs(delta):.0f} 個百分點</h1>
<p class="lede">中華電信固網 2026 公開目標追蹤板　·　資料來源：NCC／data.gov.tw 公開統計　·
資料期間 {first.ym} ~ {last.ym}</p>

<div class="hero">
  <div class="figure">{a.telco_share:.1f}% → {z.telco_share:.1f}%　<small>{years} 年 {delta:+.2f} 個百分點</small></div>
  <div class="note">
    這是政府公開統計、可驗證的硬數字，也是<b>為什麼中華電信要在 2026 年打這場降價保衛戰</b>。<br>
    <b>但請先記住這個數字的身分</b>：它是<b>技術陣營層級的代理指標</b>，不是中華電信自己的市占——
    原因在下一節說明。
  </div>
</div>

<div class="card">{fig_main}</div>
<p class="scrollhint">← 圖表可左右滑動</p>

<div class="limits">
  <b>這張圖的三個限制（不放附錄，就寫在圖旁）</b>
  <ol>
    <li><b>FTTX ≠ 中華電信</b>——台灣大、遠傳的光纖也計入本陣營，中華電信的貢獻無法分離。</li>
    <li><b>帳號數 ≠ 用戶數</b>——一戶可能有多個帳號，一個帳號也可能對應多人。</li>
    <li><b>不做因果宣稱</b>——圖上的事件時點<b>只是時點標記</b>，本看板不估計價格戰的處理效果。
        四種識別策略被否決的理由見文末方法說明。</li>
  </ol>
  <div style="margin-top:10px;padding-top:9px;border-top:1px solid {GRID};">
    <b style="color:{BREAK_C};">⚠ 兩處資料斷點（紅色虛線）</b>——2009-04 與 2020-01 各出現一次單月劇變，
    次月即回到原趨勢。<b>2020-01 落在兩份來源的重疊期內，兩份報一模一樣的數字</b>，
    所以是上游資料本身如此，不是接合造成的。
    該月使電信陣營占比單月下降 <b>{abs(brk_pp):.2f} 個百分點，佔全期 {abs(delta):.2f} pp 的 {brk_share:.1f}%</b>。
    成因<b>未能證實</b>——查證過程見方法說明。
  </div>
</div>

<h2>中華電信 2026 年公開了四個固網目標。我用公開資料試著追蹤，一個都追不到。</h2>
<p class="lede"><b>個人家庭分公司總經理</b>胡學海 2026-03-18 公開宣布（來源：經濟日報／MoneyDJ）。
<b>「追不到」不是這個專案的失敗，是它的內容</b>——它標出了公開資料的天花板在哪。</p>

{kpi_cards()}

<h2>如果我有內部資料，這個板會長什麼樣</h2>
<div class="mockwrap">
  <div class="mockbar">⚠ MOCK — 以下全部是假資料，僅示範版面與所需欄位，不代表任何真實數值</div>
  <div style="font-size:13px;color:{INK2};margin:2px 0 6px;">
    目標 3 與目標 4 需要的內部欄位：<code>方案別訂閱數（speed_tier × month）</code>、
    <code>全屋 Wi-Fi 裝機數 ÷ 寬頻用戶數（month）</code>。
    這兩張圖示範「拿到那兩張表之後，追蹤板長什麼樣」——<b>管線接上內部資料就能跑完整版</b>。
  </div>
  {fig_mock}
</div>

<h2>方法說明</h2>

<h3>資料來源</h3>
<table>
  <tr><th>來源</th><th>粒度</th><th>期間</th><th>狀態</th></tr>
  <tr><td><code>data.gov.tw / 7164</code> 寬頻上網帳號數</td><td>技術別 × 月</td>
      <td>2019-01 ~ 2026-04</td><td>仍更新</td></tr>
  <tr><td><code>data.gov.tw / 27953</code> 有線寬頻用戶數</td><td>技術別 × 月</td>
      <td>2007-01 ~ 2020-08</td><td>已停更</td></tr>
</table>
<p class="note"><b>陣營歸類（看資料前寫死，存於 <code>logs/decisions.log</code>）</b>：
電信＝ADSL＋FTTX；Cable＝Cable Modem；Leased_Line 與 PWLAN 排除（非家戶固網寬頻）。</p>

<h3>兩來源接合校驗</h3>
<p class="note">
兩份資料重疊 <b>20 個月</b>（2019-01 ~ 2020-08）。逐月逐欄比對 ADSL／FTTX／Cable Modem
共 <b>60 筆，全部完全相等</b>，差異中位數與最大值皆 <b>0.0000%</b>，
低於預先登記的放棄門檻（中位數 &gt; 5%），<b>接合通過</b>。<br>
<b>0.0000% 的正確詮釋</b>：20 期完全一致，<b>更可能代表兩個資料集出自同一個上游（NCC 報表）</b>，
而非兩個獨立來源互相驗證。因此本報告一律表述為
<b>「同源確認，可安全接合」</b>，<b>不寫成「交叉驗證」或「兩來源互證」</b>。<br>
接合規則：以 7164 為主，2019-01 之前用 27953 補；<b>重疊的 20 期一律採 7164，不混用</b>。
</p>

{WHY_NO_CAUSAL}

<h3>資料斷點的查證過程</h3>
<p class="note">
2009-04（FTTX 單月 −187,856）與 2020-01（ADSL 單月 −207,430、同月 FTTX +107,873）
各出現一次單月劇變，次月即回歸原趨勢。為確認成因，查了三個來源：
<b>(1)</b> <code>data.gov.tw</code> 兩個資料集的 API 中繼資料——無欄位說明、無統計口徑、無備註；
<b>(2)</b> NCC 官網開放資料項目頁——<b>HTTP 403</b>；
<b>(3)</b> 公開搜尋——無 2020-01 口徑調整的說明文件。<br>
<b>三者皆無所獲，因此本看板只陳述觀察到的事實，不宣稱成因。</b>
可佐證的旁證是：千分位逗號在整份 7164 中<b>只出現在 2020-01 與 2020-02 兩列</b>，
格式變動與數值劇變同時發生。<b>這仍然只是旁證，不是結論。</b>
</p>

<h3>限制</h3>
<div class="limits">
  <ol>
    <li><b>技術別 ≠ 業者別</b>——FTTX 含台灣大、遠傳，中華電信的貢獻無法分離。</li>
    <li><b>帳號數 ≠ 用戶數</b>——一戶多帳號、一帳號多人的情況無法辨識。</li>
    <li><b>不做因果宣稱</b>——事件時點僅供對照，不估計處理效果。</li>
    <li><b>兩來源接合的殘餘不確定性</b>——重疊期 20 期差異 0.0000%，但這代表同源而非互證，
        兩份共同的系統性偏誤無法用彼此檢出。</li>
    <li><b>事件時點僅為視覺標記</b>——2022-05 MSO 價格戰（工商時報 2022-05-23）與
        2026-03-18 中華電信降價（經濟日報／MoneyDJ），<b>僅在圖上標示，不估計任何效果</b>。</li>
    <li><b>兩處資料斷點成因未證實</b>——2009-04 與 2020-01。若 2020-01 確為統計口徑變更，
        則 {years} 年降幅中約 <b>{brk_share:.0f}%</b> 屬定義效果而非市場變化，
        其餘約 {residual:+.1f} 個百分點仍為實在的趨勢。</li>
  </ol>
</div>

<p class="foot">
本看板由 <code>src/build_dashboard.py</code> 產生，指標於 PostgreSQL 內以視窗函數計算。
判準在看資料前寫死並存於 <code>logs/decisions.log</code>（append-only）；
設計推翻歷程見 <code>docs/decision-trail.md</code>。<br>
外部求職者以公開資料製作，非中華電信內部文件，不代表該公司立場。
</p>

</div>"""


def write_plotlyjs() -> Path:
    """把 plotly.min.js 寫進輸出目錄。

    **`to_html(include_plotlyjs="directory")` 只產生 <script src> 引用，
    不會幫你把檔案放過去**——少了這一步，看板開起來圖區全白。
    （2026-08-08 實測踩到：改成外部引用後只看檔案變小就以為成功，
    渲染截圖才發現整張圖沒了。）
    """
    import plotly.offline
    js = OUT / "plotly.min.js"
    if not js.exists():
        js.write_text(plotly.offline.get_plotlyjs(), encoding="utf-8")
    return js


def main() -> int:
    rows = fetch_metrics()
    html = build(rows)
    path = OUT / "index.html"
    path.write_text(html, encoding="utf-8")
    print(f"已產生：{path.relative_to(ROOT)}　{path.stat().st_size:,} bytes"
          f"　({'內嵌' if INLINE else '外部引用'})")
    if not INLINE:
        js = write_plotlyjs()
        print(f"　　　　　{js.relative_to(ROOT)}　{js.stat().st_size:,} bytes"
              "（與 index.html 同目錄即可離線開啟）")
    a = next(r for r in rows if r.ym == "2019-01")
    z = rows[-1]
    print(f"  期間 {rows[0].ym} ~ {z.ym}（{len(rows)} 期）")
    print(f"  核心發現 2019-01 {a.telco_share:.2f}% → {z.ym} {z.telco_share:.2f}%"
          f"　（{z.telco_share - a.telco_share:+.2f} pp）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
