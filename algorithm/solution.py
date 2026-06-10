"""Çözüm temsili ve maliyet muhasebesi (tek doğruluk kaynağı).

Hem MILP hem GA hem de validator AYNI maliyet fonksiyonunu kullanır; böylece
"çözücünün bildirdiği maliyet" ile "bağımsız doğrulanan maliyet" tutarlıdır.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from .data import (CYCLE_DAYS, IDLE_RENT_THRESHOLD, Problem, Route)

# --- Maliyet parametreleri ---
OP_COST_PER_DAY = 2000.0        # şirket gemisi günlük işletme gideri
IDLE_PENALTY_PER_DAY = 2000.0   # 0<idle<5 verimsizlik cezası (gün başına)


@dataclass
class Solution:
    # ship_id -> o gemiye atanan gerçek rotalar
    ship_routes: Dict[str, List[Route]] = field(default_factory=dict)
    # demand_event_index -> onu karşılayan route_id
    event_assignment: Dict[int, str] = field(default_factory=dict)

    def routes_flat(self) -> List[Route]:
        out: List[Route] = []
        for rs in self.ship_routes.values():
            out.extend(rs)
        return out


@dataclass
class CostBreakdown:
    route_cost: float = 0.0
    operating_cost: float = 0.0
    idle_penalty: float = 0.0
    rental_income: float = 0.0      # pozitif tutulur, Z'den düşülür

    @property
    def total(self) -> float:
        return (self.route_cost + self.operating_cost
                + self.idle_penalty - self.rental_income)

    def pretty(self) -> str:
        return (
            f"  Rota maliyeti      : {self.route_cost:>14,.2f}\n"
            f"  İşletme gideri     : {self.operating_cost:>14,.2f}\n"
            f"  Boşta-kalma cezası : {self.idle_penalty:>14,.2f}\n"
            f"  Kiralama geliri    : {-self.rental_income:>14,.2f}\n"
            f"  {'-'*32}\n"
            f"  TOPLAM Z           : {self.total:>14,.2f}"
        )


def compute_cost(problem: Problem, sol: Solution) -> CostBreakdown:
    """Maliyet muhasebesi — booklet'in idle/kira kuralını birebir uygular.

    Her gemi için idle = 35 - (toplam aktif gün):
        idle >= 5  -> boş günler dışarı kiralanır (gelir)
        0 < idle<5 -> verimsizlik cezası
        idle == 0  -> tam kullanım (ne ceza ne gelir)
    Pasif gemi (0 gün) -> idle=35 -> tamamen kiraya verilir.
    """
    cb = CostBreakdown()

    for ship in problem.ships:
        routes = sol.ship_routes.get(ship.ship_id, [])
        dur = sum(r.duration for r in routes)
        cb.route_cost += sum(r.cost for r in routes)
        if routes and ship.is_company_owned:
            cb.operating_cost += OP_COST_PER_DAY * dur

        idle = CYCLE_DAYS - dur
        if idle >= IDLE_RENT_THRESHOLD:
            cb.rental_income += ship.rental_income_per_day * idle
        elif idle > 0:
            cb.idle_penalty += IDLE_PENALTY_PER_DAY * idle

    return cb
