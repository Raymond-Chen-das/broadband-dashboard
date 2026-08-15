"""階段 5：單頁 HTML 看板（Plotly，可離線開啟）。

四個區塊，排序**以發現開場**：
  0  核心發現 ＋ 陣營消長主圖（＋ 三個限制，畫在圖旁不放附錄）
  1  四張 KPI 可追蹤性卡片（兩張部分可追、兩張追不到，**不得美化成可追蹤**）
  2  完整版 MOCK（假資料，**明顯標示**）
  3  方法說明頁（資料來源、接合校驗、7.1 五行、限制章節）

**禁止 matplotlib**（繁中支援）。**不做因果宣稱**——事件時點只做視覺標記。

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
from hero_svg import hero_svg

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dashboard"
OUT.mkdir(parents=True, exist_ok=True)

# --inline：把 Plotly 內嵌成單一自足檔案（約 4.7MB），供寄送或單獨上傳。
INLINE = "--inline" in sys.argv

# ══════════════════════════════════════════════════════════════════════════
#  視覺方向：**冷靛藍紙上的量測報告**（2026-08-09 改版）
#
#  前一版走深色機殼。改掉的理由有二：
#  （1）繁體中文筆畫密度高，淺字在深底會產生光暈，系統字體沒有為深色調整字重；
#  （2）整頁只有 hero 是重色，其餘一路淺到底，明暗節奏落在裝飾而不是內容上。
#
#  這一版整份文件鋪**冷靛藍紙**（#e9ecf7），卡片是同色系的近白階（#f6f8fd），
#  版面靠三階明度分層：紙 → 深階帶 → 卡。**不使用純白**——純白會讓整頁退回
#  「一份 Word 報告」，也是前一版被指出最樸素的地方。
#  姊妹專案 hamivideo-events 用同一套結構與中性色，主色改為青藍，兩者是同一系列。
#
#  字體：IBM Plex Sans／Mono 搭 Noto Sans TC，透過 Google Fonts 載入；
#  三個字體堆疊都保留系統字後備，離線開啟時自動退回，版面不破。
#  數據一律走等寬字：儀表的母語是等寬字，數字對齊本來也該用它。
#
#  本頁**預設給桌機觀看**。
# ══════════════════════════════════════════════════════════════════════════

# 資料色：兩陣營是兩個實體，categorical 兩槽（靛藍／琥珀，色覺安全的經典對）。
TELCO_C, CABLE_C = "#4a56c9", "#c1762a"
CABLE_D = "#a05a18"                       # 琥珀的深階，供文字用
ACCENT, ACCENT_D = "#4a56c9", "#333db3"

# 版面的三階明度。紙不能跟卡同色，否則 600px 高的卡會像懸在半空。
PAPER = "#e9ecf7"        # 紙：冷靛藍，整份文件的底
PAPER2 = "#dfe3f2"       # 次階：限制區、統計磚、引用區
BAND = "#dde2f1"         # 深階帶：整頁的第二個重音，留給「一個都追不到」
TOPBAR = "#e0e4f4"       # 頁首列
HERO_TOP = "#dee3f3"     # hero 漸層的起點
CARD = "#f6f8fd"         # 卡片與圖表面（近白，但不是白）
FOOT = "#171b24"         # 頁尾：整頁唯一的深色，只承擔收尾

RULE = "rgba(19,24,34,.09)"
RULE_D = "rgba(19,24,34,.16)"

INK = "#131822"          # 主墨：深海軍藍，不用純黑
INK2 = "#4c5666"
MUTED = "#8b94a3"
MUTED2 = "#7c8695"

# Plotly 畫在卡上，底色透明，跟著卡走
SURFACE = "rgba(0,0,0,0)"
GRID = "rgba(19,24,34,0.07)"
AXIS = "rgba(19,24,34,0.15)"

# 事件時點＝中性；資料斷點＝警示紅，一律附 ⚠ 圖示與文字標籤，
# 不讓顏色單獨承載意義。兩者刻意用不同線型：事件實線、斷點虛線。
EVENT_C, BREAK_C, BREAK_D = "#6f7889", "#c0483c", "#a83a2e"

# 三個角色的字體。Google Fonts 載入，系統字後備，離線時自動退回。
SANS = ("'IBM Plex Sans', 'Noto Sans TC', system-ui, -apple-system, "
        "'Segoe UI', 'Microsoft JhengHei', sans-serif")
MONO = ("'IBM Plex Mono', 'Noto Sans TC', ui-monospace, 'Cascadia Mono', "
        "'SF Mono', Consolas, monospace")
FONT = SANS      # Plotly 內文沿用無襯線
FONTS_HREF = ("https://fonts.googleapis.com/css2?"
              "family=IBM+Plex+Sans:wght@400;500;600"
              "&family=IBM+Plex+Mono:wght@400;500;600"
              "&family=Noto+Sans+TC:wght@300;400;500;700&display=swap")

BYLINE = "陳嘉翔　資料工程與分析作品集"

# 事件時點（**僅視覺標記，不估計任何效果**）
EVENTS = [
    (dt.date(2022, 5, 1), "2022-05　MSO 價格戰", "工商時報 2022-05-23"),
    (dt.date(2026, 3, 18), "2026-03-18　中華電信降價", "經濟日報／MoneyDJ"),
]
# 資料斷點（處置看資料前即固定：標記，不修改數字，不宣稱成因）
BREAKS = [
    (dt.date(2009, 4, 1), "2009-04"),
    (dt.date(2020, 1, 1), "2020-01"),
]

# 四個公開目標（⚠️ 職稱務必寫全）
KPIS = [
    dict(n=1, goal="寬頻淨增 7 萬戶", sub="", state="partial",
         badge="僅陣營層級",
         miss="缺中華電信自身用戶數。公開統計僅有技術別"
              "（ADSL／FTTX／Cable Modem），未提供業者別。",
         proxy="最接近的代理：兩陣營的月度淨增量（見上圖下半）。"),
    dict(n=2, goal="市占守住 51%", sub="", state="partial",
         badge="僅代理指標",
         miss="分母有（全台固網寬頻帳號數），<b>分子沒有</b>（HiNet 用戶數）。",
         proxy="最接近的代理：電信陣營占比 66.36%（2026-04），惟其單位為陣營而非業者，"
               "且分母僅含兩陣營（Leased Line 未計；其量級僅千餘帳號，影響 < 0.02 pp）。"),
    dict(n=3, goal="300M 以上占比破 50%", sub="2022:27% → 2025:46%",
         state="none", badge="追不到",
         miss="公開統計未提供訂閱方案的速率分佈。M-Lab 雖有 ISP 級實測速度，"
              "但<b>實測速率不等同訂閱方案</b>，且全球資料已於 2024-03 停更。",
         proxy="需要的內部欄位：方案別訂閱數（speed_tier × month）。"),
    dict(n=4, goal="Wi-Fi 全屋滲透 65%", sub="2022:18% → 2025:54%",
         state="none", badge="追不到",
         miss="屬純內部指標，查無任何公開來源。",
         proxy="需要的內部欄位：全屋 Wi-Fi 加購方案裝機數 ÷ 寬頻用戶數。"),
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
#  **刻意不用雙 y 軸**——帳號數與淨增量量綱不同，疊在同一組座標軸上是
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
    # ⚠️ x 範圍由資料算出，**不得寫死**——寫死的畫框會在下一次月更新後把新資料切掉，
    # 而測試層抓不到（它們驗的是數值，不是畫框）。
    x_lo = dt.date(x[0].year, x[0].month, 1) - dt.timedelta(days=150)
    x_hi = dt.date(x[-1].year, x[-1].month, 1) + dt.timedelta(days=120)
    span = (x_hi - x_lo).days
    for i, (when, label, _src) in enumerate(EVENTS):
        near_right = (x_hi - when).days / span < 0.15
        fig.add_vline(x=when, line=dict(color=EVENT_C, width=1.2), layer="below")
        fig.add_annotation(x=when, y=0.76 - 0.13 * i, yref="y domain", text=label,
                           showarrow=False,
                           xshift=-5 if near_right else 5,
                           xanchor="right" if near_right else "left",
                           font=dict(size=11, color=EVENT_C, family=MONO),
                           row=1, col=1)

    # 資料斷點：虛線、status critical，並附 ⚠ 圖示與文字——顏色不單獨承載意義。
    for when, label in BREAKS:
        fig.add_vline(x=when, line=dict(color=BREAK_C, width=1.2, dash="dash"),
                      layer="below")
        fig.add_annotation(x=when, y=0.0, yref="y domain", text=f"⚠ 資料斷點 {label}",
                           showarrow=False, yshift=14, xshift=3, xanchor="left",
                           font=dict(size=11.5, color=BREAK_C, family=MONO),
                           row=1, col=1)

    fig.update_xaxes(showgrid=False, zeroline=False, linecolor=AXIS,
                     ticks="outside", tickcolor=AXIS, ticklen=4,
                     tickfont=dict(size=11, color=MUTED, family=MONO),
                     range=[x_lo, x_hi])     # 同上：由資料算出，不是字面值
    fig.update_yaxes(showgrid=True, gridcolor=GRID, zeroline=False, linecolor=AXIS,
                     tickfont=dict(size=11, color=MUTED, family=MONO))
    fig.update_yaxes(tickformat=",.0f", row=1, col=1)
    fig.update_yaxes(tickformat=",.0f", zeroline=True, zerolinecolor=AXIS,
                     zerolinewidth=1, row=2, col=1)
    # barmode 必須是 group 不是 relative：兩陣營是**兩個實體**，堆疊會讓讀者看到
    # 一個沒有意義的「合計淨增」，而本圖的問題是「誰在增、誰在減」。
    fig.update_layout(
        height=600, barmode="group", bargap=0.15, bargroupgap=0,
        margin=dict(l=70, r=28, t=74, b=48),
        legend=dict(orientation="h", y=1.10, x=0, font=dict(size=12.5, family=FONT)),
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
                       xanchor="left", font=dict(size=11.5, color=MUTED, family=MONO),
                       row=1, col=1)
    fig.add_trace(go.Scatter(x=months, y=[54.0, 55.8, 57.9, 59.6, 61.2, 62.8],
                             mode="lines+markers", line=dict(color=CABLE_C, width=2),
                             marker=dict(size=8), name="Wi-Fi 全屋滲透",
                             showlegend=False,
                             hovertemplate="%{x}<br>%{y}%（假資料）<extra></extra>"),
                  row=1, col=2)
    fig.add_hline(y=65, line=dict(color=MUTED, width=1, dash="dot"), row=1, col=2)
    fig.add_annotation(x=months[0], y=65, text="目標 65%", showarrow=False, yshift=10,
                       xanchor="left", font=dict(size=11.5, color=MUTED, family=MONO),
                       row=1, col=2)
    fig.update_xaxes(showgrid=False, linecolor=AXIS,
                     tickfont=dict(size=11, color=MUTED, family=MONO))
    fig.update_yaxes(showgrid=True, gridcolor=GRID, ticksuffix="%",
                     linecolor=AXIS, tickfont=dict(size=11, color=MUTED, family=MONO))
    # y 範圍寫死並涵蓋目標線——autorange 只框住資料，65% 的目標線會被切到框外，
    # 而「距離目標還有多遠」正是這兩張示範圖唯一要傳達的事。
    fig.update_yaxes(range=[45.5, 52.0], row=1, col=1)
    fig.update_yaxes(range=[52.0, 67.5], row=1, col=2)
    fig.update_layout(height=300, margin=dict(l=56, r=24, t=54, b=40), **BASE_LAYOUT)
    for a in fig.layout.annotations[:2]:
        a.font = dict(size=12.5, color=INK, family=FONT)
    return fig


CSS = f"""
*{{box-sizing:border-box;}}
html{{-webkit-text-size-adjust:100%;scroll-behavior:smooth;}}
body{{margin:0;background:{PAPER};color:{INK};font-family:{SANS};
     line-height:1.72;letter-spacing:.005em;-webkit-font-smoothing:antialiased;}}
.wrap{{max-width:1180px;margin:0 auto;padding:0 56px;}}

/* ══ 頁首列：一秒對上人與資料來源 ═══════════════════════════════ */
.topbar{{background:{TOPBAR};border-bottom:1px solid {RULE};}}
.topbar .wrap{{display:flex;align-items:center;justify-content:space-between;
             height:60px;gap:24px;}}
.brand{{display:flex;align-items:center;gap:11px;min-width:0;}}
.brand .dot{{width:16px;height:16px;border-radius:4px;background:{ACCENT};flex:none;}}
.brand .name{{font-size:13.5px;font-weight:500;letter-spacing:.01em;}}
.brand .bar{{width:1px;height:14px;background:rgba(19,24,34,.14);margin:0 4px;}}
.brand .who{{font-size:12.5px;color:#6c7686;}}
.topbar .src{{font-family:{MONO};font-size:11px;color:{MUTED};letter-spacing:.04em;
            white-space:nowrap;}}

/* ══ 眉標：標的是「這一段回答哪個問題」 ═══════════════════════════ */
.eyebrow{{font-family:{MONO};font-size:10.5px;letter-spacing:.24em;
        text-transform:uppercase;color:{ACCENT};display:block;
        margin-bottom:14px;font-weight:500;}}

/* ══ HERO ═══════════════════════════════════════════════════════
   上帶分兩欄：左邊說話，右邊是讀數。下帶是軌跡圖自己的版面列，
   兩者各自佔位，不用 absolute 互相穿透。 */
.masthead{{background:linear-gradient(180deg,{HERO_TOP} 0%,{PAPER} 58%);}}
.mast-type{{padding:76px 0 0;display:grid;grid-template-columns:1fr 268px;
          gap:0 64px;align-items:start;}}
h1{{font-size:clamp(2.4rem,4.4vw,3.6rem);font-weight:600;line-height:1.14;
   letter-spacing:-.035em;margin:0 0 26px;max-width:17ch;text-wrap:balance;}}
h1 em{{font-style:normal;color:{ACCENT};}}
/* 中文可以在任意兩字之間斷行，`text-wrap:balance` 只調整每行長度、
   不認識詞界，所以標題會斷成「電信陣營的固／網份額」。把標題切成幾個
   nowrap 的語意塊，斷行就只會落在塊與塊之間。 */
h1 span{{white-space:nowrap;}}
.standfirst{{font-size:16.5px;font-weight:300;color:{INK2};max-width:50ch;margin:0;}}
.standfirst b{{color:{INK};font-weight:500;}}

/* 讀數欄：直排，像儀表側邊的數值窗，靠一條左界線與左欄分開 */
.readout{{font-family:{MONO};font-variant-numeric:tabular-nums;
        border-left:1px solid rgba(19,24,34,.12);padding-left:28px;
        display:flex;flex-direction:column;align-items:flex-start;}}
.readout .rlab{{font-size:10.5px;letter-spacing:.18em;color:#98a0ad;}}
.readout .from{{font-size:30px;font-weight:400;color:#9aa2af;letter-spacing:-.03em;
              line-height:1.15;margin-bottom:18px;}}
.readout .to{{font-size:50px;font-weight:600;color:{INK};letter-spacing:-.045em;
            line-height:1.05;}}
.delta{{margin-top:14px;font-size:13px;font-weight:500;color:{CABLE_D};
      background:rgba(193,118,42,.14);padding:3px 10px;border-radius:5px;
      white-space:nowrap;}}
.readout .rsrc{{font-size:10.5px;line-height:1.9;color:#98a0ad;margin-top:24px;
              padding-top:16px;border-top:1px solid {RULE};}}

/* ── hero 下帶：軌跡圖 ── */
.mast-fig{{padding:44px 0 0;}}
.herofig{{display:block;width:100%;height:196px;}}
.figscale{{display:flex;justify-content:space-between;align-items:center;
         font-family:{MONO};font-size:10.5px;letter-spacing:.1em;color:#98a0ad;
         padding:10px 0 0;border-top:1px solid rgba(19,24,34,.12);}}
.figkey{{display:flex;gap:22px;align-items:center;}}
.figkey i{{font-style:normal;display:inline-flex;align-items:center;gap:7px;}}
.figkey i::before{{content:"";width:16px;height:2.5px;background:currentColor;}}
.figkey em{{font-style:normal;color:#a9b0bd;}}

/* ══ 統計磚：用直線分隔，不用邊框盒 ═══════════════════════════════ */
.statwrap{{padding:42px 0 8px;}}
.statlab{{font-family:{MONO};font-size:10.5px;letter-spacing:.22em;
        text-transform:uppercase;color:#98a0ad;margin-bottom:12px;}}
.stats{{display:grid;grid-template-columns:repeat(4,1fr);
      border-top:1px solid {RULE_D};border-bottom:1px solid {RULE};}}
.stat{{padding:22px 24px 22px 0;border-right:1px solid {RULE};}}
.stat:first-child{{padding-left:0;}}
.stat:last-child{{border-right:0;padding-right:0;padding-left:24px;}}
.stat .num{{font-family:{MONO};font-size:26px;font-weight:500;letter-spacing:-.02em;
          line-height:1.15;font-variant-numeric:tabular-nums;}}
.stat .lab{{font-size:12.5px;color:{MUTED2};margin-top:6px;line-height:1.55;}}

/* ══ 區塊 ═════════════════════════════════════════════════════ */
.sec{{padding:64px 0 0;}}
h2{{font-size:clamp(1.5rem,2.6vw,1.9rem);font-weight:500;margin:0 0 10px;
   letter-spacing:-.025em;line-height:1.3;}}
h3{{font-size:15px;font-weight:500;margin:32px 0 8px;letter-spacing:-.005em;}}
h3:first-of-type{{margin-top:0;}}
.sectionnote{{font-size:15px;font-weight:300;color:{INK2};margin:0 0 26px;
            max-width:74ch;}}
.sectionnote b{{color:{INK};font-weight:500;}}

/* 深階帶：整頁的第二個重音，留給「一個都追不到」 */
.sec.band{{margin-top:64px;background:{BAND};padding:60px 0 64px;
         border-top:1px solid {RULE};border-bottom:1px solid {RULE};}}

/* ══ 圖表卡 ═══════════════════════════════════════════════════ */
.card{{background:{CARD};border:1px solid rgba(19,24,34,.10);border-radius:12px;
     padding:14px 12px 6px;overflow-x:auto;}}
.card > div{{min-width:880px;}}

/* ══ 限制與斷點：兩張並排 ═════════════════════════════════════ */
.notes{{display:grid;grid-template-columns:1.25fr 1fr;gap:26px;margin-top:26px;}}
.panel{{background:{PAPER2};border:1px solid rgba(19,24,34,.08);border-radius:12px;
      padding:24px 28px;}}
.panel h4{{font-size:13px;font-weight:500;letter-spacing:.01em;margin:0 0 14px;}}
.items{{display:flex;flex-direction:column;gap:12px;}}
.item{{display:flex;gap:14px;}}
.item .i{{font-family:{MONO};font-size:11.5px;color:{ACCENT};font-weight:500;
        padding-top:3px;flex:none;}}
.item .t{{font-size:13.5px;color:{INK2};}}
.item .t b{{color:{INK};font-weight:500;}}
.panel.warn{{background:#f2e6e2;border-color:rgba(192,72,60,.18);}}
.panel.warn h4{{display:flex;align-items:center;gap:9px;color:{BREAK_D};}}
.panel.warn h4::before{{content:"";width:7px;height:7px;border-radius:50%;
                      background:{BREAK_C};}}
.panel.warn p{{margin:0;font-size:13.5px;color:{INK2};}}
.panel.warn b{{color:{INK};font-weight:500;font-family:{MONO};}}

/* ══ KPI：訊號格把「可追蹤性」畫出來 ═════════════════════════════
   亮幾格＝這個目標追得到多少。顏色、格數、標籤三重編碼。 */
.kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-top:34px;}}
.kpi{{background:{CARD};border:1px solid rgba(19,24,34,.10);border-radius:12px;
    padding:24px 22px 22px;display:flex;flex-direction:column;
    transition:transform .25s ease,box-shadow .25s ease,border-color .25s ease;}}
.kpi:hover{{transform:translateY(-3px);border-color:rgba(19,24,34,.16);
          box-shadow:0 18px 34px -18px rgba(19,24,34,.26);}}
.kpi .idx{{font-family:{MONO};font-size:10.5px;letter-spacing:.2em;color:#98a0ad;}}
.signal{{display:flex;gap:3px;margin:14px 0 18px;}}
.seg{{height:6px;flex:1;border-radius:1px;background:rgba(19,24,34,.10);}}
.kpi.partial .seg.on{{background:{ACCENT};}}
.kpi .goal{{font-size:17px;font-weight:500;line-height:1.45;margin:0 0 14px;}}
.kpi .goal.hassub{{margin-bottom:6px;}}
.kpi .sub{{font-family:{MONO};font-size:11.5px;color:#98a0ad;margin-bottom:14px;}}
.badge{{align-self:flex-start;font-family:{MONO};font-size:10.5px;font-weight:500;
      padding:3px 8px;border-radius:4px;margin-bottom:16px;}}
.badge.partial{{color:{ACCENT};background:rgba(74,86,201,.11);}}
.badge.none{{color:{BREAK_D};background:rgba(192,72,60,.11);}}
.kpi .miss{{font-size:12.8px;color:{INK2};}}
.kpi .miss b{{color:{INK};font-weight:500;}}
.kpi .proxy{{font-size:12.2px;color:{MUTED};margin-top:16px;padding-top:14px;
           border-top:1px solid rgba(19,24,34,.09);}}
.kpinote{{font-size:14.5px;font-weight:300;color:{INK2};margin:26px 0 0;max-width:76ch;}}
.kpinote b{{color:{INK};font-weight:500;}}

/* ══ MOCK ═════════════════════════════════════════════════════ */
.mockwrap{{border:1px dashed rgba(192,72,60,.38);border-radius:12px;
         background:#f2e6e2;padding:20px 22px 10px;}}
.mockbar{{display:inline-flex;align-items:center;gap:8px;font-family:{MONO};
        font-size:10.5px;font-weight:500;letter-spacing:.14em;color:{BREAK_D};
        background:rgba(192,72,60,.12);padding:4px 10px;border-radius:4px;}}

/* ══ 方法：兩欄 ═══════════════════════════════════════════════ */
.cols{{display:grid;grid-template-columns:1fr 1fr;gap:44px;}}

/* ══ 表格 ═════════════════════════════════════════════════════ */
table{{border-collapse:collapse;font-size:13px;margin-top:10px;width:100%;
     font-variant-numeric:tabular-nums;}}
th,td{{padding:11px 16px 11px 0;text-align:left;vertical-align:top;}}
th{{font-family:{MONO};color:#98a0ad;font-weight:500;font-size:10px;
   letter-spacing:.16em;text-transform:uppercase;padding-top:0;padding-bottom:8px;
   border-bottom:1px solid rgba(19,24,34,.22);}}
td{{border-bottom:1px solid rgba(19,24,34,.08);color:{INK2};}}
td:first-child{{color:{INK};}}
tbody tr:hover{{background:rgba(19,24,34,.035);}}
td.ym{{font-family:{MONO};font-size:12px;}}
code{{font-family:{MONO};font-size:12px;background:rgba(19,24,34,.06);
    padding:2px 6px;border-radius:4px;color:{INK2};}}
.note{{font-size:13.5px;color:{INK2};margin:16px 0 0;max-width:80ch;}}
.note b{{color:{INK};font-weight:500;}}

/* ══ 頁尾：整頁唯一的深色，只承擔收尾 ═══════════════════════════ */
.foot{{background:{FOOT};color:rgba(236,239,244,.62);margin-top:70px;
     padding:36px 0;font-family:{MONO};font-size:11.5px;line-height:1.95;}}
.foot code{{background:rgba(255,255,255,.09);color:#c3cbd6;}}

/* ══ 捲動進度：長頁面的位置感 ═══════════════════════════════════ */
#prog{{position:fixed;top:0;left:0;height:2px;width:0;z-index:99;background:{ACCENT};}}

/* ══ 進場：一次、克制、尊重減少動態偏好 ═════════════════════════ */
.reveal{{opacity:0;transform:translateY(14px);}}
.reveal.in{{opacity:1;transform:none;
          transition:opacity .7s cubic-bezier(.2,.7,.2,1),
                     transform .7s cubic-bezier(.2,.7,.2,1);}}
.signal .seg{{transform:scaleX(0);transform-origin:left;}}
.in .signal .seg{{transform:scaleX(1);
                transition:transform .55s cubic-bezier(.2,.8,.2,1);}}
.in .signal .seg:nth-child(2){{transition-delay:.06s;}}
.in .signal .seg:nth-child(3){{transition-delay:.12s;}}
.in .signal .seg:nth-child(4){{transition-delay:.18s;}}
@media (prefers-reduced-motion: reduce){{
  html{{scroll-behavior:auto;}}
  .reveal,.reveal.in{{opacity:1;transform:none;transition:none;}}
  .signal .seg{{transform:none;transition:none;}}
  #prog{{display:none;}}
}}
a{{color:{ACCENT};text-decoration:none;border-bottom:1px solid rgba(74,86,201,.28);}}
a:hover{{color:{ACCENT_D};border-bottom-color:{ACCENT_D};}}
a:focus-visible,summary:focus-visible{{outline:2px solid {ACCENT};outline-offset:3px;}}

/* 本頁預設給桌機。此段只保證視窗拉窄時版面不破。 */
@media (max-width:1080px){{
  .wrap{{padding:0 28px;}}
  .stats,.kpis,.cols,.notes{{grid-template-columns:1fr 1fr;}}
  .mast-type{{padding-top:52px;grid-template-columns:1fr;gap:34px;}}
  .readout{{border-left:0;padding-left:0;border-top:1px solid rgba(19,24,34,.12);
          padding-top:26px;}}
  .herofig{{height:160px;}}
  .sec{{padding-top:46px;}}
  .sec.band{{margin-top:46px;padding:46px 0 52px;}}
}}
"""

# 規格 7.1：方法說明頁的完整區塊。**預先寫死，不得臨場改寫，不得刪減任何一條。**
WHY_NO_CAUSAL = """
  <h3>為什麼不做因果推論</h3>
  <p class="note" style="margin-top:0;">本分析<b>不估計降價的效果</b>，
  四種識別策略各自被一項具體事實排除：</p>
  <div class="items" style="margin-top:14px;">
    <div class="item"><span class="i">01</span><span class="t">M-Lab 的 ISP 級測速資料已於 2024-03 全球停更，2026 年的事件無資料可用。</span></div>
    <div class="item"><span class="i">02</span><span class="t">即使有資料，2026-03 事件的後測期僅 4.5 個月，不足以估計穩定效果。</span></div>
    <div class="item"><span class="i">03</span><span class="t">政府統計僅有技術別而無業者別，無法建立 treatment 與 control 分組。</span></div>
    <div class="item"><span class="i">04</span><span class="t">改以技術陣營分組後，2022 年的價格戰係由對照組（有線電視業者）發動。</span></div>
  </div>
"""


def kpi_cards() -> str:
    """四張卡＋四格訊號條。

    訊號條是本頁的招牌元素：**亮幾格＝這個目標追得到多少**。
    部分可追蹤亮兩格、完全追不到零格。顏色、格數、文字三重編碼——
    顏色從不單獨承載意義。
    """
    lit_by_state = {"partial": 2, "none": 0}
    out = []
    for k in KPIS:
        lit = lit_by_state[k["state"]]
        segs = "".join(f'<span class="seg{" on" if i < lit else ""}"></span>'
                       for i in range(4))
        sub = f'<div class="sub">{k["sub"]}</div>' if k["sub"] else ""
        cls = "goal hassub" if k["sub"] else "goal"
        out.append(f"""
        <div class="kpi {k['state']}">
          <div class="idx">目標 {k['n']}</div>
          <div class="signal" role="img"
               aria-label="可追蹤性 {lit} / 4">{segs}</div>
          <div class="{cls}">{k['goal']}</div>{sub}
          <span class="badge {k['state']}">{k['badge']}</span>
          <div class="miss">{k['miss']}</div>
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
    # responsive: True 是 QR 掃進來的必要條件。
    opts = dict(full_html=False, config={"displayModeBar": False, "responsive": True})
    js = True if INLINE else "directory"
    fig_main = main_figure(rows).to_html(include_plotlyjs=js, **opts)
    fig_mock = mock_figure().to_html(include_plotlyjs=False, **opts)

    return f"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>中華電信固網 2026 公開目標追蹤板</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="{FONTS_HREF}" rel="stylesheet">
<style>{CSS}</style>
<div id="prog"></div>

<header class="topbar"><div class="wrap">
  <div class="brand">
    <span class="dot"></span>
    <span class="name">固網陣營追蹤板</span>
    <span class="bar"></span>
    <span class="who">{BYLINE}</span>
  </div>
  <div class="src">NCC / data.gov.tw　·　{first.ym} — {last.ym}　·　{len(rows)} mo</div>
</div></header>

<section class="masthead">
  <div class="wrap mast-type">
    <div>
      <span class="eyebrow">中華電信固網 2026 公開目標追蹤板</span>
      <h1><span>電信陣營的</span><span>固網份額，</span><em><span>{years} 年掉了</span><span> {abs(delta):.0f} 個百分點</span></em></h1>
      <p class="standfirst">
        本指標取自政府公開統計，計算過程可完整重現。需留意其衡量單位為技術陣營，
        <b>不等同於中華電信單一業者的市占</b>，因為公開統計未提供業者別欄位。
      </p>
    </div>
    <div class="readout">
      <span class="rlab">{a.ym}</span>
      <span class="from">{a.telco_share:.1f}%</span>
      <span class="rlab">{z.ym}</span>
      <span class="to">{z.telco_share:.1f}%</span>
      <span class="delta">{delta:+.2f} pp</span>
      <span class="rsrc">NCC／data.gov.tw<br>{first.ym} — {last.ym}　共 {len(rows)} 個月</span>
    </div>
  </div>
  <div class="wrap mast-fig">
    {hero_svg(rows, TELCO_C, CABLE_C, anchor_ym=a.ym)}
    <div class="figscale">
      <span>{first.ym}</span>
      <span class="figkey">
        <i style="color:{TELCO_C}">電信陣營</i><i style="color:{CABLE_C}">Cable</i>
        <em>虛線是右側讀數的起算點 {a.ym}</em>
      </span>
      <span>{last.ym}</span>
    </div>
  </div>
  <div class="wrap statwrap">
    <div class="statlab">可驗證的工程結果</div>
    <div class="stats">
      <div class="stat"><div class="num">16 / 16</div>
        <div class="lab">資料契約檢查全過，零容差</div></div>
      <div class="stat"><div class="num">60 / 60</div>
        <div class="lab">兩來源重疊 20 期比對，差異 0.0000%</div></div>
      <div class="stat"><div class="num">16,604 → 409</div>
        <div class="lab">查詢調校後的 buffers 讀取量（合成 200 萬列基準表）</div></div>
      <div class="stat"><div class="num">22</div>
        <div class="lab">自動化測試，CI 執行，不依賴資料庫</div></div>
    </div>
  </div>
</section>

<main>

<section class="sec reveal"><div class="wrap">
  <span class="eyebrow">核心發現</span>
  <h2>兩陣營的消長，以及看這張圖要一起知道的三件事</h2>
  <p class="sectionnote">上格為帳號數，下格為月度淨增量。
  <b>兩者量綱不同，疊於同一組座標軸將造成不當比較</b>，因此改為共用 x 軸的上下分格。</p>
  <div class="card">{fig_main}</div>
  <div class="notes">
    <div class="panel">
      <h4>這張圖的三個限制，寫在圖旁而不是附錄</h4>
      <div class="items">
        <div class="item"><span class="i">01</span><span class="t"><b>FTTX 不等於中華電信。</b>台灣大與遠傳的光纖同樣計入本陣營，中華電信自身的貢獻無法自公開資料中分離。</span></div>
        <div class="item"><span class="i">02</span><span class="t"><b>帳號數不等於用戶數。</b>一戶可能有多個帳號，一個帳號也可能對應多人。</span></div>
        <div class="item"><span class="i">03</span><span class="t"><b>不做因果宣稱。</b>圖上的事件時點僅為時間標記，本分析不估計價格戰的處理效果。</span></div>
      </div>
    </div>
    <div class="panel warn">
      <h4>兩處資料斷點（圖上的紅色虛線）</h4>
      <p>2009-04 與 2020-01 各出現一次單月劇變，次月即回歸原趨勢。2020-01 落於兩份來源的重疊期，
      兩份數值完全一致，可判定成因位於上游資料本身而非接合程序。該月使占比單月下降
      <b>{abs(brk_pp):.2f} pp</b>，佔全期 {abs(delta):.2f} pp 的 <b>{brk_share:.1f}%</b>。
      成因未能證實，故不作宣稱。</p>
    </div>
  </div>
</div></section>

<section class="sec band reveal"><div class="wrap">
  <span class="eyebrow">可追蹤性診斷</span>
  <h2>四個公開目標，用公開資料一個都追不到</h2>
  <p class="sectionnote">個人家庭分公司總經理胡學海 2026-03-18 公開宣布（經濟日報／MoneyDJ）。
  各卡的訊號格表示該目標的可追蹤程度：亮兩格代表僅能取得陣營層級的代理指標，
  全暗代表公開資料中不存在對應欄位。</p>
  {kpi_cards()}
  <p class="kpinote"><b>「追不到」本身即為本專案的結論。</b>此一判定同時界定了三件事：
  中華電信公開追蹤的指標為何、公開資料的覆蓋上限落在哪裡，以及補足缺口所需的內部欄位。</p>
</div></section>

<section class="sec reveal"><div class="wrap">
  <span class="eyebrow">需要哪些內部欄位</span>
  <h2>如果接上內部資料，這個板會長什麼樣</h2>
  <div class="mockwrap">
    <div class="mockbar">MOCK：以下全部是假資料</div>
    <p class="note" style="margin-top:14px;">
      目標 3 與目標 4 需要的內部欄位是 <code>方案別訂閱數（speed_tier × month）</code> 與
      <code>全屋 Wi-Fi 裝機數 ÷ 寬頻用戶數</code>。
      現有管線在接入這兩張表後即可產出完整版本，無須重構。
    </p>
    {fig_mock}
  </div>
</div></section>

<section class="sec reveal"><div class="wrap">
  <span class="eyebrow">方法</span>
  <h2>資料怎麼來、判準怎麼定、為什麼不做因果推論</h2>
  <div class="cols" style="margin-top:30px;">
    <div>
      <h3>資料來源</h3>
      <table>
        <tr><th>來源</th><th>粒度</th><th>期間</th><th>狀態</th></tr>
        <tr><td><code>7164</code> 寬頻上網帳號數</td><td>技術別 × 月</td>
            <td class="ym">2019-01 → {last.ym}</td><td>仍更新</td></tr>
        <tr><td><code>27953</code> 有線寬頻用戶數</td><td>技術別 × 月</td>
            <td class="ym">2007-01 → 2020-08</td><td>已停更</td></tr>
      </table>
      <p class="note"><b>陣營歸類</b>於檢視資料前即固定並標上時間戳：
      電信陣營為 ADSL 與 FTTX，Cable 陣營為 Cable Modem；
      Leased_Line 與 PWLAN 排除。</p>

      <h3>兩來源接合校驗</h3>
      <p class="note" style="margin-top:0;">
      兩份資料重疊 20 個月（2019-01 到 2020-08）。逐月逐欄比對 ADSL、FTTX、Cable Modem
      共 60 筆，結果全數完全相等，差異的中位數與最大值皆為 0.0000%，
      低於預先登記的 5% 放棄門檻。<br>
      20 期完全一致，較合理的解釋為兩份資料出自同一份上游 NCC 報表。因此本報告一律表述為
      <b>同源確認，可安全接合</b>，而不是交叉驗證。<br>
      接合規則：以 7164 為主，2019-01 之前用 27953 補；重疊的 20 期一律採 7164。
      </p>
    </div>
    <div>
      {WHY_NO_CAUSAL}

      <h3>資料斷點的查證過程</h3>
      <p class="note" style="margin-top:0;">
      2009-04（FTTX 單月 −187,856）與 2020-01（ADSL 單月 −207,430，同月 FTTX +107,873）
      各出現一次單月劇變，次月即回歸原趨勢。為確認成因查證三處來源：
      兩個資料集的 API 中繼資料未附欄位說明、NCC 官網開放資料頁回應 HTTP 403、
      公開搜尋亦無口徑調整的紀錄。三者皆無所獲，因此本看板僅陳述觀察到的事實，
      <b>不宣稱成因</b>。
      旁證是千分位逗號在整份 7164 中只出現在 2020-01 與 2020-02 兩列，
      格式變動與數值劇變同時發生；這仍然只是旁證。
      </p>
    </div>
  </div>

  <h3 style="margin-top:40px;">限制</h3>
  <div class="panel" style="margin-top:12px;">
    <div class="items">
      <div class="item"><span class="i">01</span><span class="t"><b>技術別不等於業者別。</b>FTTX 含台灣大與遠傳，中華電信的貢獻無法分離。同理，<b>若有線電視業者佈建的 FTTH 依技術別歸入 FTTX 欄</b>，本分析會系統性低估 Cable 陣營的實際份額，亦即電信陣營的份額變化可能比觀測到的更大。NCC 的填報規則未經查證，也無法用本資料驗證；<b>此一偏誤的方向對本文結論為保守。</b></span></div>
      <div class="item"><span class="i">02</span><span class="t"><b>帳號數不等於用戶數。</b>一戶多帳號、一帳號多人的情況無法辨識。</span></div>
      <div class="item"><span class="i">03</span><span class="t"><b>不做因果宣稱。</b>事件時點僅供對照，不估計處理效果。</span></div>
      <div class="item"><span class="i">04</span><span class="t"><b>兩來源接合的殘餘不確定性。</b>0.0000% 代表同源而非互證，兩份共同的系統性偏誤無法用彼此檢出。</span></div>
      <div class="item"><span class="i">05</span><span class="t"><b>事件時點僅為視覺標記。</b>2022-05 MSO 價格戰（工商時報 2022-05-23）與 2026-03-18 中華電信降價（經濟日報／MoneyDJ）。</span></div>
      <div class="item"><span class="i">06</span><span class="t"><b>兩處資料斷點成因未證實。</b>若 2020-01 確為統計口徑變更，則 {years} 年降幅中約 {brk_share:.0f}% 屬定義效果而非市場變化，其餘約 {residual:+.1f} 個百分點仍為實在的趨勢。</span></div>
    </div>
  </div>
</div></section>

</main>

<footer class="foot"><div class="wrap">
本看板由 <code>src/build_dashboard.py</code> 產生，指標在 PostgreSQL 內以視窗函數計算。
判準在檢視資料前固定並標上時間戳（紀錄 append-only）。<br>
外部求職者以公開資料製作，非中華電信內部文件，不代表該公司立場。
</div></footer>

<script>
(() => {{
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;

  const prog = document.getElementById('prog');
  if (prog && !reduced) {{
    const onScroll = () => {{
      const h = document.documentElement.scrollHeight - innerHeight;
      prog.style.width = (h > 0 ? (scrollY / h) * 100 : 0) + '%';
    }};
    addEventListener('scroll', onScroll, {{passive: true}});
    onScroll();
  }}

  if (reduced) {{
    document.querySelectorAll('.reveal').forEach(el => el.classList.add('in'));
    return;
  }}

  const io = new IntersectionObserver((entries) => {{
    entries.forEach(e => {{ if (e.isIntersecting) {{
      e.target.classList.add('in'); io.unobserve(e.target);
    }} }});
  }}, {{threshold: 0.06, rootMargin: '0px 0px -6% 0px'}});
  document.querySelectorAll('.reveal').forEach(el => io.observe(el));
}})();
</script>"""


def write_plotlyjs() -> Path:
    """把 plotly.min.js 寫進輸出目錄。

    **`to_html(include_plotlyjs="directory")` 只產生 <script src> 引用，
    不會幫你把檔案放過去**——少了這一步，看板開起來圖區全白。
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
