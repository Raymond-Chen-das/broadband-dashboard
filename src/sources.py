"""兩份 NCC 來源的載入與正規化（階段 2、3、4 共用）。

輸出統一長格式：`Record(year, month, tech_code, accounts, source)`。

**技術別與陣營歸類在看資料前即固定並標上時間戳，本模組不得自行更改。**
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"

F_7164 = RAW / "ncc_7164_寬頻上網帳號數.csv"
F_27953 = RAW / "ncc_27953_有線寬頻用戶數.csv"

SRC_7164 = "ncc_7164"
SRC_27953 = "ncc_27953"

# --- 陣營歸類（預先登記，寫死）---------------------------------------------
# TELCO = ADSL, FTTX ／ CABLE = Cable Modem ／ EXCLUDED = Leased_Line, PWLAN
CAMP: dict[str, str] = {
    "ADSL": "TELCO",
    "FTTX": "TELCO",
    "CABLE_MODEM": "CABLE",
    "LEASED_LINE": "EXCLUDED",
    "PWLAN": "EXCLUDED",
}

TECH_NAME: dict[str, str] = {
    "ADSL": "ADSL",
    "FTTX": "光纖（FTTX）",
    "CABLE_MODEM": "Cable Modem",
    "LEASED_LINE": "固接專線",
    "PWLAN": "PWLAN",
}

# 接合校驗只比對這三欄。**絕不可比對兩份的總計欄**——27953 的總計含 PWLAN，
# 7164 的小計固網不含。
COMPARABLE = ("ADSL", "FTTX", "CABLE_MODEM")

# 來源欄位 → tech_code。未列入者一律不載入：
#   7164 的「行動寬頻」屬無線寬頻，預先登記時即排除（非家戶固網寬頻），
#   且 27953 無對應欄位，載入會製造兩來源不對稱的技術別清單。
#   各種「小計 / 合計 / Data+Voice / Data only」為衍生欄，非分項，不入事實表。
MAP_7164 = {
    "ADSL_固網（有線）寬頻帳號數": "ADSL",
    "FTTX_固網（有線）寬頻帳號數": "FTTX",
    "Cable_Modem固網（有線）寬頻帳號數": "CABLE_MODEM",
    "Leased_Line_固網（有線）寬頻帳號數": "LEASED_LINE",
    "PWLAN_無線寬頻帳號數": "PWLAN",
}

MAP_27953 = {
    "有線寬頻帳號-ADSL": "ADSL",
    "有線寬頻帳號-FTTX": "FTTX",
    "有線寬頻帳號-Cable Modem": "CABLE_MODEM",
    "有線寬頻帳號-固接專線": "LEASED_LINE",
    "無線寬頻帳號-PWLAN": "PWLAN",
}

# 接合切點（預先登記：以 7164 為主，2019-01 之前用 27953 補）
SPLICE_CUTOVER = (2019, 1)


@dataclass(frozen=True)
class Record:
    year: int
    month: int
    tech_code: str
    accounts: int
    source: str

    @property
    def period(self) -> tuple[int, int]:
        return (self.year, self.month)

    @property
    def ym(self) -> str:
        return f"{self.year}-{self.month:02d}"


def _to_int(raw: str) -> int:
    """陷阱 1：部分數值帶千分位逗號（僅 109/1、109/2 兩列），naive int() 會炸。"""
    return int(raw.replace(",", "").strip())


def _read(path: Path) -> list[dict[str, str]]:
    """陷阱 5、6：DictReader（勿用 split(',')）＋ utf-8-sig（吃掉 BOM）。"""
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def load_7164() -> list[Record]:
    out: list[Record] = []
    for row in _read(F_7164):
        roc, month = row["年月"].split("/")
        year = int(roc) + 1911  # 陷阱 3：西元 = 民國 + 1911
        for col, tech in MAP_7164.items():
            out.append(Record(year, int(month), tech, _to_int(row[col]), SRC_7164))
    # 陷阱 4：原檔為降序，統一為升序
    return sorted(out, key=lambda r: (r.year, r.month, r.tech_code))


def load_27953() -> list[Record]:
    out: list[Record] = []
    for row in _read(F_27953):
        year = int(row["年度"]) + 1911
        for col, tech in MAP_27953.items():
            out.append(Record(year, int(row["月份"]), tech, _to_int(row[col]), SRC_27953))
    return sorted(out, key=lambda r: (r.year, r.month, r.tech_code))


def overlap_periods() -> list[tuple[int, int]]:
    """兩份共同涵蓋的期間（依實際資料求交集，不寫死）。"""
    p1 = {r.period for r in load_7164()}
    p2 = {r.period for r in load_27953()}
    return sorted(p1 & p2)


def spliced() -> list[Record]:
    """接合後的序列：2019-01 起用 7164，之前用 27953。

    **重疊期不混用**——重疊的 20 期一律採 7164（預先登記）。
    呼叫端必須先確認階段 2 的校驗已通過。
    """
    early = [r for r in load_27953() if r.period < SPLICE_CUTOVER]
    late = [r for r in load_7164() if r.period >= SPLICE_CUTOVER]
    return sorted(early + late, key=lambda r: (r.year, r.month, r.tech_code))
