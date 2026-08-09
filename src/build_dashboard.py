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
from hero_svg import hero_svg

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dashboard"
OUT.mkdir(parents=True, exist_ok=True)

# --inline：把 Plotly 內嵌成單一自足檔案（約 4.7MB），供寄送或單獨上傳。
# 預設不內嵌，理由見 build() 內的註解。
INLINE = "--inline" in sys.argv

# ══════════════════════════════════════════════════════════════════════════
#  視覺方向：**量測儀表**（2026-08-09）
#
#  本專案的論點是「我能看到多少、看不到什麼」——那是關於**可見性與盲區**的命題。
#  所以介面做成一塊量測儀表：**能測到的亮起來，測不到的暗著**。
#  四張 KPI 卡的訊號格就是這件事——把專案的論點變成視覺系統，而不是加裝飾。
#  數據一律走等寬字：儀表的母語是等寬字，數字對齊本來也該用它。
#
#  本頁**預設給桌機觀看**。
# ══════════════════════════════════════════════════════════════════════════

# 底色選擇（同日二次調整，深色版已淘汰）：
# **理由不是喜好**：繁體中文的筆畫密度遠高於拉丁字母，淺字在暗底會產生光暈
# （stroke bleed），而系統字體沒有為深色調整字重——同一套字在深色底就是會糊。
# 英文介面沒有這個問題，中文有。所以改回淺底，但用**冷調水藍**而不是原本的米白，
# 才不會退回「一份白底報告」。
#
# 兩陣營是**兩個實體**，用 categorical 兩槽，不是同色相深淺。
#   node validate_palette.js "#2a78d6,#eb6834" --mode light --surface "#f2f8fc"
#   → ALL CHECKS PASS（最差相鄰 CVD ΔE 24.7、常視覺 ΔE 33.6，門檻 8 與 15）
# 資料色：兩陣營是兩個實體，categorical 兩槽。圖畫在白卡上。
#   node validate_palette.js "#2a78d6,#eb6834" --mode light → ALL CHECKS PASS
TELCO_C, CABLE_C = "#2a78d6", "#eb6834"
CABLE_D = "#a8420c"                       # 橘的深階，供文字用（白底對比足夠）
ACCENT, ACCENT_D = "#2a78d6", "#1b5590"

PAPER = "#eef2f6"        # 紙：冷調，上面鋪細方格
PAPER2 = "#e3eaf1"       # 次階紙：引用區、表格 hover
CARD = "#ffffff"         # 圖表卡
RULE = "rgba(15,35,51,0.16)"

INK = "#0f2333"          # 主墨：深海軍藍，不用純黑
INK2 = "#43596d"
MUTED = "#7b8fa3"

# Plotly 圖畫在白卡上
SURFACE = CARD
GRID = "rgba(15,35,51,0.09)"
AXIS = "rgba(15,35,51,0.26)"

# 事件時點＝中性；資料斷點＝警示紅，一律附 ⚠ 圖示與文字標籤，
# 不讓顏色單獨承載意義。兩者刻意用不同線型：事件實線、斷點虛線。
EVENT_C, BREAK_C = "#3d5568", "#c0392b"
# 訊號格的「亮」用系列藍而非綠：亮起來代表「這個目標有資料可測」，
# 而藍正是那份資料本身的顏色。綠會被讀成「達標」，那是另一個意思。
LIT = "#2a78d6"

# 三個角色的字體，全部走系統字——載外部字型會讓頁面失去離線開啟能力。
# 標題用**襯線**：整頁的個性由它承擔，而不是把無襯線放大了事。
SERIF = ('"Noto Serif TC", "Source Han Serif TC", "Songti TC", '
         '"PMingLiU", Georgia, "Times New Roman", serif')
SANS = ('system-ui, -apple-system, "Segoe UI", "Noto Sans TC", '
        '"Microsoft JhengHei", sans-serif')
# 數據一律等寬：數字對齊本來就該用它。
MONO = ('ui-monospace, "Cascadia Mono", "SF Mono", Consolas, '
        '"Noto Sans Mono CJK TC", monospace')
FONT = SANS      # Plotly 內文沿用無襯線

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
    # ⚠️ x 範圍由資料算出，**不得寫死**。
    # 前一版把上限寫成 dt.date(2026, 9, 1)，而且同一個字面值在兩處各寫一次——
    # 月更新管線每月重生看板，2026-09 的資料一到就會被切在圖框外，
    # 而測試層完全抓不到（它們驗的是數值，不是畫框）。
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
                     range=[x_lo, x_hi])     # 同上：由資料算出，不是字面值
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
html{{-webkit-text-size-adjust:100%;scroll-behavior:smooth;}}
body{{margin:0;background:{PAPER};color:{INK};font-family:{SANS};
     line-height:1.72;letter-spacing:.005em;}}
/* 細方格紋理：訊號圖紙的暗示，不是裝飾用的雜訊 */
body::before{{content:"";position:fixed;inset:0;z-index:-1;pointer-events:none;
  background-image:linear-gradient(rgba(15,35,51,.045) 1px,transparent 1px),
                   linear-gradient(90deg,rgba(15,35,51,.045) 1px,transparent 1px);
  background-size:34px 34px;}}
.wrap{{max-width:1120px;margin:0 auto;padding:0 26px;}}

/* ══ 眉標：標的是「這一段回答哪個問題」 ═══════════════════════════ */
.eyebrow{{font-family:{MONO};font-size:11px;letter-spacing:.28em;text-transform:uppercase;
        color:{ACCENT_D};display:block;margin-bottom:16px;font-weight:600;}}

/* ══ HERO：發現本身就是 hero ════════════════════════════════════
   不是「大數字＋標籤＋漸層」那種模板解。兩條陣營軌跡橫貫整個 hero，
   中間逐年收窄的缺口就是標題講的那 9 個百分點。資料與主圖同源。 */
.masthead{{position:relative;padding:76px 0 0;border-bottom:1.5px solid {INK};
         overflow:hidden;}}
.herofig{{position:absolute;left:0;right:0;bottom:0;width:100%;height:250px;
        opacity:.55;}}
.masthead .wrap{{position:relative;z-index:1;}}
h1{{font-family:{SERIF};font-size:clamp(2.6rem,6.6vw,5.2rem);font-weight:900;
   line-height:.97;letter-spacing:-.022em;margin:0 0 22px;max-width:19ch;}}
h1 em{{font-style:normal;color:{ACCENT_D};}}
.standfirst{{font-size:16px;color:{INK2};max-width:60ch;margin:0 0 30px;}}
.standfirst b{{color:{INK};font-weight:650;}}

.readout{{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;
        font-family:{MONO};font-variant-numeric:tabular-nums;margin:0 0 14px;}}
.readout .from{{font-size:clamp(1.6rem,3.4vw,2.6rem);font-weight:600;color:{MUTED};
              letter-spacing:-.03em;line-height:1;}}
.readout .arrow{{font-size:1.3rem;color:{MUTED};line-height:1;}}
.readout .to{{font-size:clamp(2.6rem,6vw,4.4rem);font-weight:800;color:{INK};
            letter-spacing:-.04em;line-height:1;}}
.delta{{font-family:{MONO};font-size:14px;font-weight:650;color:{CABLE_D};
      border-bottom:2px solid {CABLE_C};padding-bottom:2px;}}
.masthead .meta{{font-family:{MONO};font-size:12px;color:{MUTED};letter-spacing:.02em;
               padding:0 0 150px;}}

/* ══ 區塊：用線分隔，不是到處堆盒子 ═══════════════════════════════ */
.blk{{padding:66px 0;border-bottom:1px solid {RULE};}}
.blk:last-of-type{{border-bottom:0;}}
h2{{font-family:{SERIF};font-size:clamp(1.55rem,3vw,2.3rem);font-weight:800;
   margin:0 0 10px;letter-spacing:-.018em;line-height:1.2;}}
h3{{font-family:{SERIF};font-size:1.15rem;font-weight:700;margin:34px 0 8px;}}
.sectionnote{{font-size:15px;color:{INK2};margin:12px 0 0;max-width:72ch;}}
.sectionnote b{{color:{INK};font-weight:650;}}

/* ══ 統計磚：用直線分隔，不用邊框盒 ═══════════════════════════════ */
.stats{{display:grid;grid-template-columns:repeat(4,1fr);margin-top:34px;
      border-top:2px solid {INK};}}
.stat{{padding:24px 22px 22px 0;border-right:1px solid {RULE};}}
.stat:last-child{{border-right:0;}}
.stat .num{{font-family:{MONO};font-size:clamp(1.5rem,2.6vw,2.05rem);font-weight:700;
          letter-spacing:-.02em;line-height:1.1;font-variant-numeric:tabular-nums;}}
.stat .lab{{font-size:12.5px;color:{MUTED};margin-top:8px;line-height:1.55;}}

/* ══ 圖表 ═════════════════════════════════════════════════════ */
.card{{background:{CARD};border:1px solid {RULE};border-radius:2px;
     padding:16px 14px 10px;margin-top:30px;overflow-x:auto;}}
.card > div{{min-width:860px;}}

.limits{{border-left:3px solid {ACCENT};background:{PAPER2};
       padding:22px 26px;margin-top:24px;font-size:13.5px;color:{INK2};}}
.limits b{{color:{INK};}}
.limits ol{{margin:12px 0 0;padding-left:22px;}} .limits li{{margin:9px 0;}}
.limits ol::marker{{font-family:{MONO};color:{ACCENT_D};font-weight:700;}}
.breaknote{{margin-top:18px;padding-top:14px;border-top:1px solid {RULE};}}
.breaknote b{{color:{BREAK_C};}}

/* ══ KPI：訊號格把「可追蹤性」畫出來 ═════════════════════════════
   亮幾格＝這個目標追得到多少。顏色、格數、圖示、文字四重編碼。 */
.kpis{{display:grid;grid-template-columns:repeat(4,1fr);margin-top:34px;
     border-top:2px solid {INK};}}
.kpi{{padding:26px 22px 24px 0;border-right:1px solid {RULE};
    display:flex;flex-direction:column;}}
.kpi:last-child{{border-right:0;}}
.kpi .idx{{font-family:{MONO};font-size:10.5px;letter-spacing:.24em;color:{MUTED};}}
.signal{{display:flex;gap:3px;margin:14px 0 16px;max-width:120px;}}
.seg{{height:7px;flex:1;background:rgba(15,35,51,.11);}}
.kpi.partial .seg.on{{background:{ACCENT};}}
.kpi .goal{{font-family:{SERIF};font-size:1.2rem;font-weight:700;margin:0 0 12px;
          line-height:1.42;}}
.kpi .goal .sub{{display:block;font-family:{MONO};font-size:11.5px;color:{MUTED};
               font-weight:400;margin-top:8px;letter-spacing:.02em;}}
.badge{{font-family:{MONO};font-size:11px;font-weight:650;letter-spacing:.06em;
      margin-bottom:14px;align-self:flex-start;}}
.badge.partial{{color:{ACCENT_D};}} .badge.none{{color:{BREAK_C};}}
.kpi .miss{{font-size:12.8px;color:{INK2};}}
.kpi .proxy{{font-size:12.2px;color:{MUTED};margin-top:14px;padding-top:14px;
           border-top:1px solid {RULE};}}

/* ══ MOCK ═════════════════════════════════════════════════════ */
.mockwrap{{border:1px dashed rgba(176,58,42,.45);padding:14px 18px 18px;margin-top:26px;
         background:rgba(176,58,42,.028);}}
.mockbar{{font-family:{MONO};font-size:11.5px;font-weight:700;letter-spacing:.1em;
        color:{BREAK_C};border-bottom:2px solid {BREAK_C};padding-bottom:4px;
        display:inline-block;margin-bottom:12px;}}

/* ══ 表格 ═════════════════════════════════════════════════════ */
table{{border-collapse:collapse;font-size:13px;margin-top:16px;width:100%;
     font-variant-numeric:tabular-nums;}}
th,td{{border-bottom:1px solid {RULE};padding:11px 18px 11px 0;text-align:left;
     vertical-align:top;}}
th{{font-family:{MONO};color:{MUTED};font-weight:600;font-size:10.5px;
   letter-spacing:.14em;text-transform:uppercase;border-bottom:1.5px solid {INK};}}
tbody tr:hover{{background:{PAPER2};}}
code{{font-family:{MONO};font-size:12px;background:{PAPER2};padding:2px 6px;
    color:{INK2};}}
.note{{font-size:13.5px;color:{INK2};margin-top:16px;max-width:80ch;}}
.note b{{color:{INK};}}

/* ══ 頁尾 ═════════════════════════════════════════════════════ */
.foot{{background:{INK};color:#9db3c4;margin-top:0;padding:40px 0;
     font-family:{MONO};font-size:12px;line-height:1.95;}}
.foot code{{background:rgba(255,255,255,.10);color:#cfe0ee;}}

/* ══ 捲動進度：長頁面的位置感 ═══════════════════════════════════ */
#prog{{position:fixed;top:0;left:0;height:2px;width:0;z-index:99;
     background:{ACCENT};}}

/* ══ 進場：一次、克制、尊重減少動態偏好 ═════════════════════════ */
.reveal{{opacity:0;transform:translateY(18px);}}
.reveal.in{{opacity:1;transform:none;
          transition:opacity .8s cubic-bezier(.2,.7,.2,1),
                     transform .8s cubic-bezier(.2,.7,.2,1);}}
.signal .seg{{transform:scaleX(0);transform-origin:left;}}
.in .signal .seg{{transform:scaleX(1);
                transition:transform .5s cubic-bezier(.2,.8,.2,1);}}
.in .signal .seg:nth-child(2){{transition-delay:.07s;}}
.in .signal .seg:nth-child(3){{transition-delay:.14s;}}
.in .signal .seg:nth-child(4){{transition-delay:.21s;}}
@media (prefers-reduced-motion: reduce){{
  html{{scroll-behavior:auto;}}
  .reveal,.reveal.in{{opacity:1;transform:none;transition:none;}}
  .signal .seg{{transform:none;transition:none;}}
  #prog{{display:none;}}
}}
a{{color:{ACCENT_D};}}
a:focus-visible,summary:focus-visible{{outline:2px solid {ACCENT};outline-offset:3px;}}

/* 本頁預設給桌機。此段只保證視窗拉窄時版面不破。 */
@media (max-width:900px){{
  .stats,.kpis{{grid-template-columns:1fr 1fr;}}
  .stat,.kpi{{padding-right:18px;}}
  .masthead{{padding-top:52px;}}
  .masthead .meta{{padding-bottom:150px;}}
  .blk{{padding:46px 0;}}
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
    """四張卡＋四格訊號條。

    訊號條是本頁的招牌元素：**亮幾格＝這個目標追得到多少**。
    ⚠️ 部分可追蹤亮兩格、❌ 完全追不到零格。
    顏色、格數、圖示、文字四重編碼——顏色從不單獨承載意義。
    """
    lit_by_state = {"partial": 2, "none": 0}
    out = []
    for k in KPIS:
        lit = lit_by_state[k["state"]]
        segs = "".join(f'<span class="seg{" on" if i < lit else ""}"></span>'
                       for i in range(4))
        out.append(f"""
        <div class="kpi {k['state']}">
          <div class="idx">目標 {k['n']}</div>
          <div class="signal" role="img"
               aria-label="可追蹤性 {lit} / 4">{segs}</div>
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
<div id="prog"></div>

<header class="masthead">
  {hero_svg(rows, TELCO_C, CABLE_C)}
  <div class="wrap">
    <span class="eyebrow">中華電信固網 2026 公開目標追蹤板</span>
    <h1>電信陣營的固網份額，<em>{years} 年掉了 {abs(delta):.0f} 個百分點</em></h1>
    <div class="readout">
      <span class="from">{a.telco_share:.1f}%</span>
      <span class="arrow">→</span>
      <span class="to">{z.telco_share:.1f}%</span>
      <span class="delta">{delta:+.2f} pp</span>
    </div>
    <p class="standfirst">
      政府公開統計、可驗證，也是中華電信在 2026 年打這場降價保衛戰的原因。
      <b>這是技術陣營層級的代理指標，不是中華電信自身市占</b>——公開統計沒有業者別。
    </p>
    <p class="meta">NCC／data.gov.tw　·　{first.ym} — {last.ym}　·　{len(rows)} 個月</p>
  </div>
</header>

<main class="wrap">

<section class="sec reveal">
  <div class="card">{fig_main}</div>
  <div class="limits">
    <b>這張圖的三個限制（不放附錄，就寫在圖旁）</b>
    <ol>
      <li><b>FTTX ≠ 中華電信</b>——台灣大、遠傳的光纖也計入本陣營，中華電信的貢獻無法分離。</li>
      <li><b>帳號數 ≠ 用戶數</b>——一戶可能有多個帳號，一個帳號也可能對應多人。</li>
      <li><b>不做因果宣稱</b>——圖上的事件時點只是時點標記，本看板不估計價格戰的處理效果。</li>
    </ol>
    <div class="breaknote">
      <b>⚠ 兩處資料斷點（紅色虛線）</b>——2009-04 與 2020-01 各出現一次單月劇變，次月即回到原趨勢。
      2020-01 落在兩份來源的重疊期內，兩份報一模一樣的數字，所以是上游資料本身如此，不是接合造成。
      該月使電信陣營占比單月下降 <b>{abs(brk_pp):.2f} 個百分點，佔全期 {abs(delta):.2f} pp 的 {brk_share:.1f}%</b>。
      成因未能證實，查證過程見文末方法說明。
    </div>
  </div>
</section>

<section class="sec reveal">
  <span class="eyebrow">可追蹤性診斷</span>
  <h2>四個公開目標，用公開資料一個都追不到</h2>
  <p class="sectionnote"><b>個人家庭分公司總經理</b>胡學海 2026-03-18 公開宣布（來源：經濟日報／MoneyDJ）。
  每張卡的訊號格顯示這個目標能追到多少：亮兩格代表只追得到陣營層級的代理，全暗代表公開資料沒有。</p>
  {kpi_cards()}
</section>

<section class="sec reveal">
  <span class="eyebrow">需要哪些內部欄位</span>
  <h2>如果有內部資料，這個板會長什麼樣</h2>
  <div class="mockwrap">
    <div class="mockbar">⚠ MOCK — 以下全部是假資料，僅示範版面與所需欄位</div>
    <div class="note" style="margin-top:2px;">
      目標 3 與目標 4 需要的內部欄位：<code>方案別訂閱數（speed_tier × month）</code>、
      <code>全屋 Wi-Fi 裝機數 ÷ 寬頻用戶數（month）</code>。
      管線接上內部資料就能跑完整版。
    </div>
    {fig_mock}
  </div>
</section>

<section class="sec reveal">
  <span class="eyebrow">方法</span>
  <h2>資料怎麼來、判準怎麼定、為什麼不做因果推論</h2>

  <h3>資料來源</h3>
  <table>
    <tr><th>來源</th><th>粒度</th><th>期間</th><th>狀態</th></tr>
    <tr><td><code>data.gov.tw / 7164</code> 寬頻上網帳號數</td><td>技術別 × 月</td>
        <td>2019-01 ~ {last.ym}</td><td>仍更新</td></tr>
    <tr><td><code>data.gov.tw / 27953</code> 有線寬頻用戶數</td><td>技術別 × 月</td>
        <td>2007-01 ~ 2020-08</td><td>已停更</td></tr>
  </table>
  <p class="note"><b>陣營歸類</b>（看資料前寫死，存於 <code>logs/decisions.log</code>）：
  電信＝ADSL＋FTTX；Cable＝Cable Modem；Leased_Line 與 PWLAN 排除。</p>

  <h3>兩來源接合校驗</h3>
  <p class="note">
  兩份資料重疊 20 個月（2019-01 ~ 2020-08）。逐月逐欄比對 ADSL／FTTX／Cable Modem
  共 60 筆，全部完全相等，差異中位數與最大值皆 0.0000%，低於預先登記的 5% 放棄門檻。<br>
  20 期完全一致，比起兩個獨立來源互相驗證，更合理的解釋是兩份出自同一份上游 NCC 報表。
  因此本報告一律表述為<b>同源確認，可安全接合</b>，不寫成交叉驗證。<br>
  接合規則：以 7164 為主，2019-01 之前用 27953 補；重疊的 20 期一律採 7164。
  </p>

  {WHY_NO_CAUSAL}

  <h3>資料斷點的查證過程</h3>
  <p class="note">
  2009-04（FTTX 單月 −187,856）與 2020-01（ADSL 單月 −207,430、同月 FTTX +107,873）
  各出現一次單月劇變，次月即回歸原趨勢。為確認成因查了三個來源：
  <code>data.gov.tw</code> 兩個資料集的 API 中繼資料（無欄位說明、無統計口徑）、
  NCC 官網開放資料項目頁（HTTP 403）、公開搜尋（無口徑調整說明）。
  三者皆無所獲，因此本看板只陳述觀察到的事實，不宣稱成因。
  旁證是千分位逗號在整份 7164 中只出現在 2020-01 與 2020-02 兩列，格式變動與數值劇變同時發生；
  這仍然只是旁證。
  </p>

  <h3>限制</h3>
  <div class="limits">
    <ol>
      <li><b>技術別 ≠ 業者別</b>——FTTX 含台灣大、遠傳，中華電信的貢獻無法分離。</li>
      <li><b>帳號數 ≠ 用戶數</b>——一戶多帳號、一帳號多人的情況無法辨識。</li>
      <li><b>不做因果宣稱</b>——事件時點僅供對照，不估計處理效果。</li>
      <li><b>兩來源接合的殘餘不確定性</b>——0.0000% 代表同源而非互證，
          兩份共同的系統性偏誤無法用彼此檢出。</li>
      <li><b>事件時點僅為視覺標記</b>——2022-05 MSO 價格戰（工商時報 2022-05-23）與
          2026-03-18 中華電信降價（經濟日報／MoneyDJ）。</li>
      <li><b>兩處資料斷點成因未證實</b>——若 2020-01 確為統計口徑變更，
          則 {years} 年降幅中約 {brk_share:.0f}% 屬定義效果而非市場變化，
          其餘約 {residual:+.1f} 個百分點仍為實在的趨勢。</li>
    </ol>
  </div>
</section>

</main>

<footer class="foot"><div class="wrap">
本看板由 <code>src/build_dashboard.py</code> 產生，指標於 PostgreSQL 內以視窗函數計算。
判準在看資料前寫死並存於 <code>logs/decisions.log</code>（append-only）；
設計推翻歷程見 <code>docs/decision-trail.md</code>。<br>
外部求職者以公開資料製作，非中華電信內部文件，不代表該公司立場。
</div></footer>

<script>
(() => {{
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;

  // 捲動進度條：長頁面的位置感
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

  // 區塊進場
  const io = new IntersectionObserver((entries) => {{
    entries.forEach(e => {{ if (e.isIntersecting) {{
      e.target.classList.add('in'); io.unobserve(e.target);
    }} }});
  }}, {{threshold: 0.08, rootMargin: '0px 0px -8% 0px'}});
  document.querySelectorAll('.reveal').forEach(el => io.observe(el));

}})();
</script>"""


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
