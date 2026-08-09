"""Hero 用的 SVG：把發現本身畫成 hero。

不是「大數字＋標籤＋漸層」那種模板解。這裡畫的是兩條陣營占比軌跡，
以及它們之間**逐年收窄的缺口**——那個缺口就是標題說的 9 個百分點。
資料與主圖同源，不是裝飾用的假曲線。
"""
from __future__ import annotations


def hero_svg(rows, telco_c: str, cable_c: str, anchor_ym: str = "",
             w: int = 1120, h: int = 300) -> str:
    """兩陣營占比軌跡 ＋ 中間的缺口。座標由實際資料算出。

    ``anchor_ym`` 給定時，在該期畫一條垂直錨線。畫全期的形狀才看得到收窄，
    但右側讀數講的是錨點之後那一段——不標出錨點，兩者的關係要讀者自己猜。
    """
    share = [r.telco_share for r in rows]
    # 值域必須涵蓋**兩條**線。第一版只用 telco 的範圍算，
    # 結果 Cable 的 14–34% 全部掉到畫布外，hero 只剩一條線。
    both = share + [100 - v for v in share]
    lo, hi = min(both) - 5, max(both) + 5

    def pt(i: int, v: float) -> tuple[float, float]:
        x = i / (len(rows) - 1) * w
        y = h - (v - lo) / (hi - lo) * h
        return x, y

    telco = [pt(i, v) for i, v in enumerate(share)]
    cable = [pt(i, 100 - v) for i, v in enumerate(share)]

    def path(points) -> str:
        return "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in points)

    # 缺口：兩條線之間的面積。它從左邊很寬、往右收窄——那就是那 9 個百分點。
    gap = (path(telco) + " L " + " L ".join(
        f"{x:.1f} {y:.1f}" for x, y in reversed(cable)) + " Z")

    mark = ""
    if anchor_ym:
        idx = next((i for i, r in enumerate(rows) if r.ym == anchor_ym), -1)
        if idx >= 0:
            ax = idx / (len(rows) - 1) * w
            ay_t, ay_c = pt(idx, share[idx])[1], pt(idx, 100 - share[idx])[1]
            mark = (
                f'<line x1="{ax:.1f}" y1="0" x2="{ax:.1f}" y2="{h}" '
                f'stroke="rgba(220,234,242,.34)" stroke-width="1" '
                f'stroke-dasharray="3 4" vector-effect="non-scaling-stroke"/>'
                f'<circle cx="{ax:.1f}" cy="{ay_t:.1f}" r="3.5" fill="{telco_c}"/>'
                f'<circle cx="{ax:.1f}" cy="{ay_c:.1f}" r="3.5" fill="{cable_c}"/>')

    # 深場上兩條線會發光。缺口填色從左邊亮、往右淡，
    # 讓「收窄」不只靠形狀，也靠明度被讀出來。
    return f"""<svg class="herofig" viewBox="0 0 {w} {h}" preserveAspectRatio="none"
     aria-hidden="true" focusable="false">
  <defs>
    <linearGradient id="gapfill" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{telco_c}" stop-opacity=".30"/>
      <stop offset="1" stop-color="{telco_c}" stop-opacity=".04"/>
    </linearGradient>
    <filter id="glow" x="-6%" y="-30%" width="112%" height="160%">
      <feGaussianBlur stdDeviation="5" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <path d="{gap}" fill="url(#gapfill)"/>
  <g filter="url(#glow)" opacity=".55">
    <path d="{path(telco)}" fill="none" stroke="{telco_c}" stroke-width="2.4"
          vector-effect="non-scaling-stroke"/>
    <path d="{path(cable)}" fill="none" stroke="{cable_c}" stroke-width="2.4"
          vector-effect="non-scaling-stroke"/>
  </g>
  {mark}
  <path d="{path(telco)}" fill="none" stroke="{telco_c}" stroke-width="2.2"
        vector-effect="non-scaling-stroke"/>
  <path d="{path(cable)}" fill="none" stroke="{cable_c}" stroke-width="2.2"
        vector-effect="non-scaling-stroke"/>
</svg>"""
