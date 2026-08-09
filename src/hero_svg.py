"""Hero 用的 SVG：把發現本身畫成 hero。

不是「大數字＋標籤＋漸層」那種模板解。這裡畫的是兩條陣營占比軌跡，
以及它們之間**逐年收窄的缺口**——那個缺口就是標題說的 9 個百分點。
資料與主圖同源，不是裝飾用的假曲線。
"""
from __future__ import annotations


def hero_svg(rows, telco_c: str, cable_c: str, w: int = 1120, h: int = 300) -> str:
    """兩陣營占比軌跡 ＋ 中間的缺口。座標由實際資料算出。"""
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

    return f"""<svg class="herofig" viewBox="0 0 {w} {h}" preserveAspectRatio="none"
     aria-hidden="true" focusable="false">
  <defs>
    <linearGradient id="gapfill" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{telco_c}" stop-opacity=".26"/>
      <stop offset="1" stop-color="{telco_c}" stop-opacity=".05"/>
    </linearGradient>
  </defs>
  <path d="{gap}" fill="url(#gapfill)"/>
  <path d="{path(telco)}" fill="none" stroke="{telco_c}" stroke-width="2.4"
        vector-effect="non-scaling-stroke"/>
  <path d="{path(cable)}" fill="none" stroke="{cable_c}" stroke-width="2.4"
        vector-effect="non-scaling-stroke"/>
</svg>"""
