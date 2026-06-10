"""Bağımsız kısıt doğrulayıcı.

Çözücüden TAMAMEN bağımsız çalışır: bir çözümü alır, modeldeki HER sert kısıtı
tek tek kontrol eder ve ihlalleri döner. "0 ihlal" => çözüm gerçekten feasible.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .data import (CYCLE_DAYS, MAX_LEG_DAYS, Problem, region_of)
from .solution import Solution


@dataclass
class ValidationReport:
    violations: List[str]

    @property
    def feasible(self) -> bool:
        return len(self.violations) == 0

    def pretty(self) -> str:
        if self.feasible:
            return "✅ FEASIBLE — tüm sert kısıtlar sağlanıyor (0 ihlal)."
        lines = [f"❌ {len(self.violations)} KISIT İHLALİ:"]
        lines += [f"   - {v}" for v in self.violations]
        return "\n".join(lines)


def validate(problem: Problem, sol: Solution) -> ValidationReport:
    v: List[str] = []
    events = problem.demand_events
    route_by_id = {r.route_id: r for r in problem.routes}

    # 1) Her talep olayı tam olarak bir kez karşılanmalı (bölünemez talep)
    for i, ev in enumerate(events):
        rid = sol.event_assignment.get(i)
        if rid is None:
            v.append(f"Talep karşılanmadı: {ev.customer} gün{ev.day} ({ev.qty:.0f})")
            continue
        r = route_by_id.get(rid)
        if r is None:
            v.append(f"Talep {ev.customer} gün{ev.day} geçersiz rotaya atandı: {rid}")
            continue
        if ev.customer not in r.customers:
            v.append(f"Talep {ev.customer} gün{ev.day}, müşteriye uğramayan {rid} rotasına atandı")
        # rota gerçekten seçilmiş mi?
        if r not in sol.ship_routes.get(r.ship_id, []):
            v.append(f"Talep {ev.customer} gün{ev.day}, seçilmemiş {rid} rotasına atandı")

    # 2) Rota başına kapasite: atanan taleplerin toplamı <= gemi kapasitesi
    load_per_route = {}
    for i, ev in enumerate(events):
        rid = sol.event_assignment.get(i)
        if rid:
            load_per_route[rid] = load_per_route.get(rid, 0.0) + ev.qty
    for rid, load in load_per_route.items():
        r = route_by_id.get(rid)
        if r is None:
            continue
        cap = problem.ships_by_id[r.ship_id].capacity
        if load > cap + 1e-6:
            v.append(f"Kapasite aşımı: {rid} yük={load:.0f} > kapasite={cap:.0f}")

    # 3) Gemi başına süre + rota seviyesinde bacak/bölge/durak kısıtları
    for ship in problem.ships:
        routes = sol.ship_routes.get(ship.ship_id, [])
        if not routes:
            continue
        dur = sum(r.duration for r in routes)
        if dur > CYCLE_DAYS:
            v.append(f"35-gün kuralı: {ship.ship_id} toplam süre={dur} > {CYCLE_DAYS} (döngü aşıldı)")
        for r in routes:
            if r.ship_id != ship.ship_id:
                v.append(f"Rota sahibi uyuşmazlığı: {r.route_id} -> {ship.ship_id}")
            if max(r.legs) > MAX_LEG_DAYS:
                v.append(f"7-gün bacak kuralı: {r.route_id} bacaklar={r.legs}")
            ms = [c for c in r.customers if c.startswith("M")]
            if len(ms) > 2:
                v.append(f"Max 2 durak kuralı: {r.route_id} {ms}")
            if len({region_of(c) for c in ms}) > 1:
                v.append(f"Bölge ayrımı kuralı: {r.route_id} {ms} (Kuzey/Güney karışık)")

    # 4) Aynı rota iki gemiye atanmamalı / tekrar seçilmemeli
    seen = {}
    for sid, routes in sol.ship_routes.items():
        for r in routes:
            if r.route_id in seen:
                v.append(f"Rota çift atandı: {r.route_id}")
            seen[r.route_id] = sid

    return ValidationReport(violations=v)
