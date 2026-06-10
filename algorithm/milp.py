"""Kesin (exact) MILP çözücü — PuLP / CBC.

Karar değişkenleri:
    y[e,r] = 1 -> e talep olayı, r rotasıyla (bir sefer) karşılanır
    rent[v]    -> v gemisinin boş günleri kiraya verilir (idle>=5 ise)

Modelleme ilkeleri:
  * Her talep olayı (müşteri, gün) BÖLÜNEMEZ ve kendi seferiyle karşılanır;
    bir rota (sefer) en fazla BİR talep olayı taşır. Böylece hem günlük-bölünemez
    talep hem de "tek seferde tek günün teslimatı" gerçekçiliği korunur.
  * Bir gemiye atanan seferlerin toplam süresi 35 günlük döngüyü aşamaz.
  * 7-gün bacak, bölge ayrımı, max-2 durak, kapasite kısıtları ROTANIN kendisinde
    (data.py'de) inşa-gereği sağlanır; uygun olmayan rotalar havuza alınmaz.
  * Boşta kalma: idle>=5 -> kiralama geliri; 0<idle<5 -> verimsizlik cezası.

Ceza terimi YOKTUR (kısıtlar serttir); CBC küresel optimumu bulur.
"""
from __future__ import annotations

import pulp

from .data import CYCLE_DAYS, IDLE_RENT_THRESHOLD, Problem
from .solution import (IDLE_PENALTY_PER_DAY, OP_COST_PER_DAY, Solution)


def solve_milp(problem: Problem, time_limit: int = 120, msg: bool = False) -> Solution:
    routes = problem.routes
    events = problem.demand_events
    ships = problem.ships
    cap = {s.ship_id: s.capacity for s in ships}

    routes_by_ship = {s.ship_id: [] for s in ships}
    for r in routes:
        routes_by_ship[r.ship_id].append(r)

    # e talebini karşılayabilecek rotalar: müşteriye uğrayan + kapasitesi yeten
    serving = {
        i: [r for r in routes if ev.customer in r.customers and cap[r.ship_id] >= ev.qty]
        for i, ev in enumerate(events)
    }
    # bir rotaya atanabilecek talep olayları (ters indeks)
    events_for_route = {r.route_id: [] for r in routes}
    for i, rs in serving.items():
        for r in rs:
            events_for_route[r.route_id].append(i)

    m = pulp.LpProblem("GemiRotalama", pulp.LpMinimize)

    y = {
        (i, r.route_id): pulp.LpVariable(f"y_{i}_{r.route_id}", cat="Binary")
        for i in range(len(events)) for r in serving[i]
    }
    idleP = {s.ship_id: pulp.LpVariable(f"idle_{s.ship_id}", lowBound=0, upBound=CYCLE_DAYS) for s in ships}
    rent = {s.ship_id: pulp.LpVariable(f"rent_{s.ship_id}", cat="Binary") for s in ships}
    w = {s.ship_id: pulp.LpVariable(f"w_{s.ship_id}", lowBound=0) for s in ships}

    # rota "kullanıldı" göstergesi = o rotaya atanan talep (0/1)
    used = {r.route_id: pulp.lpSum(y[(i, r.route_id)] for i in events_for_route[r.route_id])
            for r in routes}
    # gemi başına toplam aktif süre
    dur_expr = {
        s.ship_id: pulp.lpSum(r.duration * used[r.route_id] for r in routes_by_ship[s.ship_id])
        for s in ships
    }

    # --- Amaç fonksiyonu ---
    route_cost = pulp.lpSum(r.cost * used[r.route_id] for r in routes)
    op_cost = pulp.lpSum(
        OP_COST_PER_DAY * dur_expr[s.ship_id] for s in ships if s.is_company_owned
    )
    idle_pen = pulp.lpSum(IDLE_PENALTY_PER_DAY * (idleP[s.ship_id] - w[s.ship_id]) for s in ships)
    rental_income = pulp.lpSum(s.rental_income_per_day * w[s.ship_id] for s in ships)
    m += route_cost + op_cost + idle_pen - rental_income

    # --- Kısıtlar ---
    # (1) Her talep tam bir kez karşılanır (bölünemez talep)
    for i in range(len(events)):
        m += pulp.lpSum(y[(i, r.route_id)] for r in serving[i]) == 1, f"cover_{i}"

    # (2) Bir rota (sefer) en fazla bir talep olayı taşır
    for r in routes:
        if events_for_route[r.route_id]:
            m += used[r.route_id] <= 1, f"oneevent_{r.route_id}"

    # (3) 35-gün / boşta-kalma kuralı (sert döngü sınırı + idle/kira ekonomisi)
    for s in ships:
        sid = s.ship_id
        m += dur_expr[sid] <= CYCLE_DAYS, f"durmax_{sid}"
        m += idleP[sid] == CYCLE_DAYS - dur_expr[sid], f"idledef_{sid}"
        m += idleP[sid] >= IDLE_RENT_THRESHOLD * rent[sid], f"rentgate_{sid}"  # rent=1 => idle>=5
        # w = rent * idleP  (linearizasyon): sadece idle>=5 iken kiralanabilir
        m += w[sid] <= CYCLE_DAYS * rent[sid], f"w1_{sid}"
        m += w[sid] <= idleP[sid], f"w2_{sid}"
        m += w[sid] >= idleP[sid] - CYCLE_DAYS * (1 - rent[sid]), f"w3_{sid}"

    solver = pulp.PULP_CBC_CMD(msg=msg, timeLimit=time_limit)
    m.solve(solver)

    status = pulp.LpStatus[m.status]
    if status != "Optimal":
        raise RuntimeError(f"MILP çözülemedi: durum={status}")

    # --- Çözümü çıkar ---
    sol = Solution()
    route_by_id = {r.route_id: r for r in routes}
    for (i, rid), var in y.items():
        if var.value() is not None and var.value() > 0.5:
            sol.event_assignment[i] = rid
            r = route_by_id[rid]
            sol.ship_routes.setdefault(r.ship_id, []).append(r)
    return sol
