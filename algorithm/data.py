"""Veri yükleme katmanı.

KRİTİK DÜZELTME (eski koda göre):
  * Gun1/Gun2/Gun3 sütunları ARDIŞIK (kümülatif) varış günleridir, per-bacak süre
    DEĞİLDİR. Bir rotanın toplam süresi = Gun3 (son kümülatif gün).
    Bacak süreleri = [Gun1, Gun2-Gun1, Gun3-Gun2] ve her biri <= 7 olmalıdır.
    Eski kod bunları toplayarak (Gun1+Gun2+Gun3) hem süreyi hem 7-gün kuralını
    tamamen yanlış hesaplıyordu (ör. tek gemiye 336 gün çıkıyordu).
  * 'Kira6/Kira8/Kira10' satırları gerçek sefer değil, gemiyi DIŞARI KİRALAMA
    sözde-rotalarıdır (negatif maliyet = gelir).
  * Gemiler her zaman 'Lokasyon' limanından kalkmaz; veride i limanı serbesttir,
    bu yüzden ev-limanı kısıtı uygulanmaz.

Bölge (Kuzey/Güney) bilgisi Excel'de bulunmadığından, takımın önceki kararıyla
tutarlı açık bir varsayım olarak tanımlanır (KUZEY_PORTS). Bu, raporda
"varsayım" olarak belgelenmelidir.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import pandas as pd

# --- Bölge varsayımı (Excel'de yok; belgelenecek varsayım) ---
KUZEY_PORTS = {"M2", "M4", "M7", "M10", "M11", "M13"}

# İlk 8 gemi şirkete ait, son 3'ü (G9, G10, G11) kiralık filodur.
N_COMPANY_SHIPS = 8

MAX_LEG_DAYS = 7
CYCLE_DAYS = 35
DUR_MIN, DUR_MAX = 33, 37          # 35 ± 2 sert kısıt
IDLE_RENT_THRESHOLD = 5            # >=5 gün boşta -> kiraya verilir


def region_of(customer: str) -> str:
    return "Kuzey" if customer in KUZEY_PORTS else "Guney"


@dataclass
class Ship:
    ship_id: str
    capacity: float
    home_port: str
    is_company_owned: bool
    rental_income_per_day: float = 0.0


@dataclass(frozen=True)
class Route:
    """Gemiye özgü aday rota (Gun_Maliyet'ten bir satır)."""
    route_id: str
    ship_id: str
    start_port: str
    end_port: str
    customers: Tuple[str, ...]     # uğranılan M-müşterileri (0-2 adet)
    duration: int                  # = Gun3 (toplam sefer süresi, gün)
    legs: Tuple[int, ...]          # ardışık bacak süreleri
    cost: float
    is_rental: bool                # gemiyi dışarı kiralama sözde-rotası mı

    @property
    def region(self) -> str:
        regs = {region_of(c) for c in self.customers}
        return next(iter(regs)) if len(regs) == 1 else "KARISIK"


@dataclass(frozen=True)
class DemandEvent:
    """(müşteri, gün, miktar) bölünemez talep olayı."""
    customer: str
    day: int
    qty: float


@dataclass
class Problem:
    ships: List[Ship]
    routes: List[Route]              # SADECE feasible (inşa-gereği) gerçek rotalar
    rental_routes: List[Route]       # kira sözde-rotaları
    demand_events: List[DemandEvent]
    ships_by_id: Dict[str, Ship] = field(default_factory=dict)

    def __post_init__(self):
        self.ships_by_id = {s.ship_id: s for s in self.ships}


def _parse_customers(j, k) -> Tuple[str, ...]:
    out = []
    for v in (j, k):
        s = str(v).strip()
        if s.startswith("M"):
            out.append(s)
    # tekrarları koru ama sıralı tekilleştir (M6,M6 olmaz zaten)
    return tuple(dict.fromkeys(out))


def _legs(g1: int, g2: int, g3: int) -> Tuple[int, ...]:
    return (g1, g2 - g1, g3 - g2)


def load_problem(excel_path: str) -> Problem:
    # --- Gemiler ---
    cap_df = pd.read_excel(excel_path, sheet_name="Kapasite")
    ships: List[Ship] = []
    for idx, row in cap_df.iterrows():
        sid = str(row["Gemi"]).strip()
        ships.append(
            Ship(
                ship_id=sid,
                capacity=float(row["Kapasite"]),
                home_port=str(row["Lokasyon"]).strip(),
                is_company_owned=(idx < N_COMPANY_SHIPS),
            )
        )
    cap_by_ship = {s.ship_id: s.capacity for s in ships}

    # --- Talep olayları (bölünemez) ---
    dem_df = pd.read_excel(excel_path, sheet_name="Musteri_Talepleri")
    events: List[DemandEvent] = []
    for _, row in dem_df.iterrows():
        day = int(row["Gün"])
        for col in dem_df.columns:
            if col == "Gün":
                continue
            q = float(row[col])
            if q > 0:
                events.append(DemandEvent(customer=str(col).strip(), day=day, qty=q))

    # --- Rota havuzu ---
    gm = pd.read_excel(excel_path, sheet_name="Gun_Maliyet")
    real_routes: List[Route] = []
    rental_routes: List[Route] = []

    for _, r in gm.iterrows():
        g = str(r["g"]).strip()
        j_raw = str(r["j"]).strip()
        g1, g2, g3 = int(r["Gun1"]), int(r["Gun2"]), int(r["Gun3"])
        cost = float(r["Maliyet"])
        rid = f"{g}_{int(r['se'])}"

        if j_raw.startswith("Kira"):
            rental_routes.append(
                Route(
                    route_id=rid, ship_id=g, start_port=str(r["i"]).strip(),
                    end_port=str(r["o"]).strip(), customers=tuple(),
                    duration=g3, legs=_legs(g1, g2, g3), cost=cost, is_rental=True,
                )
            )
            continue

        if int(r["Mumkun"]) != 1:
            continue

        customers = _parse_customers(r["j"], r["k"])
        if not customers:
            continue  # müşteriye uğramayan boş sefer -> ele

        legs = _legs(g1, g2, g3)
        # KISIT (inşa-gereği): hiçbir bacak 7 günü geçemez
        if max(legs) > MAX_LEG_DAYS:
            continue
        # KISIT (inşa-gereği): bölge saflığı (Kuzey/Güney karışamaz)
        if len({region_of(c) for c in customers}) > 1:
            continue
        # KISIT (inşa-gereği): en fazla 2 müşteri (j,k zaten <=2)
        if len(customers) > 2:
            continue

        real_routes.append(
            Route(
                route_id=rid, ship_id=g, start_port=str(r["i"]).strip(),
                end_port=str(r["o"]).strip(), customers=customers,
                duration=g3, legs=legs, cost=cost, is_rental=False,
            )
        )

    prob = Problem(
        ships=ships,
        routes=real_routes,
        rental_routes=rental_routes,
        demand_events=events,
    )
    
    # Her geminin maksimum günlük kira getirisini hesapla
    # (cost negatiftir, gelir = -cost / duration)
    rental_income_by_ship = {}
    for r in rental_routes:
        if r.duration > 0:
            daily_income = -r.cost / r.duration
            if daily_income > rental_income_by_ship.get(r.ship_id, 0.0):
                rental_income_by_ship[r.ship_id] = daily_income
                
    for ship in prob.ships:
        ship.rental_income_per_day = rental_income_by_ship.get(ship.ship_id, 0.0)
        
    return prob


if __name__ == "__main__":
    path = os.path.join(os.path.dirname(__file__), "..", "context", "Data_Emre2.xlsx")
    prob = load_problem(path)
    print(f"Gemi: {len(prob.ships)}  ({sum(s.is_company_owned for s in prob.ships)} şirket)")
    print(f"Feasible gerçek rota: {len(prob.routes)}")
    print(f"Kira sözde-rotası: {len(prob.rental_routes)}")
    print(f"Talep olayı: {len(prob.demand_events)}")
    print(f"Talep eden müşteriler: {sorted({e.customer for e in prob.demand_events})}")
    
    print("\n--- Gemi Bazlı Dinamik Günlük Kira Gelirleri ---")
    for s in prob.ships:
        print(f"Gemi {s.ship_id} (Kapasite: {s.capacity}): {s.rental_income_per_day:.2f} $/gün")
