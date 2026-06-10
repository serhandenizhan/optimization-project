"""Feasibility-korumalı Genetik Algoritma + VNS (önerilen metasezgisel).

Eski bozuk GA'dan temel farkı:
  * Kromozom = her talep olayının HANGİ SEFERLE karşılanacağı (gerçek karar).
    Eski kod yalnızca "rotaya gemi atıyordu", rota seçimini hiç değiştirmiyordu;
    bu yüzden kısıtları asla sağlayamıyordu.

Mimari (memetik GA + iterated local search):
  1. GA katmanı: genom popülasyonu, elitizm, çaprazlama, mutasyon.
  2. Yerel arama (VNS relocate): ARTIMLI (incremental) maliyetle, çok hızlı.
  3. Shaking + yerel arama (ILS) ile yerel optimumlardan kaçış.
  4. Multi-start: birkaç tohumla çalışıp en iyiyi tutar -> optimumu güvenilir bulur.

Performans için yerel arama, ağır Solution kopyaları yerine basit bir "atama
dizisi" (assign[i] = Route) üzerinde çalışır ve hamle maliyetini O(1) hesaplar.
Sonuç en sonda Solution'a çevrilir ve bağımsız validator ile doğrulanır.
"""
from __future__ import annotations

import random
from typing import Dict, List, Optional, Tuple

from .data import CYCLE_DAYS, IDLE_RENT_THRESHOLD, Problem, Route
from .solution import (IDLE_PENALTY_PER_DAY, OP_COST_PER_DAY,
                       Solution, compute_cost)


class GeneticOptimizer:
    def __init__(self, problem: Problem, pop_size: int = 40, generations: int = 15,
                 mutation_rate: float = 0.2, elite_frac: float = 0.2, seed: int = 42,
                 restarts: int = 4, shake_iters: int = 200):
        self.p = problem
        self.pop_size = pop_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.elite = max(2, int(pop_size * elite_frac))
        self.seed = seed
        self.restarts = restarts
        self.shake_iters = shake_iters
        self.rng = random.Random(seed)

        self.ships = problem.ships
        self.ships_by_id = problem.ships_by_id
        cap = {s.ship_id: s.capacity for s in problem.ships}
        self.n = len(problem.demand_events)
        # her talep olayı için uygun seferler (müşteriye uğrayan + kapasite yeten)
        self.serving: List[List[Route]] = [
            [r for r in problem.routes if ev.customer in r.customers and cap[r.ship_id] >= ev.qty]
            for ev in problem.demand_events
        ]
        for i, rs in enumerate(self.serving):
            if not rs:
                raise ValueError(f"Talep {problem.demand_events[i]} için uygun sefer yok!")

    # ================= Maliyet (artımlı) =================
    @staticmethod
    def _ship_cost(ship, dur: int) -> float:
        """Bir geminin gün sayısına göre maliyeti (işletme + boşta/kira)."""
        c = 0.0
        if dur > 0 and ship.is_company_owned:
            c += OP_COST_PER_DAY * dur
        idle = CYCLE_DAYS - dur
        if idle >= IDLE_RENT_THRESHOLD:
            c -= ship.rental_income_per_day * idle
        elif idle > 0:
            c += IDLE_PENALTY_PER_DAY * idle
        return c

    def _total_cost(self, assign: List[Route]) -> float:
        ship_days: Dict[str, int] = {}
        route_cost = 0.0
        for r in assign:
            route_cost += r.cost
            ship_days[r.ship_id] = ship_days.get(r.ship_id, 0) + r.duration
        total = route_cost
        for s in self.ships:
            total += self._ship_cost(s, ship_days.get(s.ship_id, 0))
        return total

    # ================= Genom <-> atama =================
    def _random_genome(self) -> List[int]:
        return [self.rng.randrange(len(rs)) for rs in self.serving]

    def _greedy_genome(self) -> List[int]:
        used = set()
        ship_days: Dict[str, int] = {}
        genome = [0] * self.n
        order = sorted(range(self.n), key=lambda i: len(self.serving[i]))
        for i in order:
            best_k, best_marg = None, float("inf")
            for k, r in enumerate(self.serving[i]):
                if r.route_id in used:
                    continue
                if ship_days.get(r.ship_id, 0) + r.duration > CYCLE_DAYS:
                    continue
                marg = r.cost + (OP_COST_PER_DAY * r.duration if self.ships_by_id[r.ship_id].is_company_owned else 0.0)
                if marg < best_marg:
                    best_marg, best_k = marg, k
            if best_k is None:
                best_k = self.rng.randrange(len(self.serving[i]))
            genome[i] = best_k
            r = self.serving[i][best_k]
            used.add(r.route_id)
            ship_days[r.ship_id] = ship_days.get(r.ship_id, 0) + r.duration
        return genome

    def _decode_assign(self, genome: List[int]) -> Tuple[List[Optional[Route]], bool]:
        """Genomu onararak atama dizisine çevirir. (assign, feasible)."""
        used = set()
        ship_days: Dict[str, int] = {}
        assign: List[Optional[Route]] = [None] * self.n
        feasible = True
        order = sorted(range(self.n), key=lambda i: len(self.serving[i]))
        for i in order:
            rs = self.serving[i]
            pref = [genome[i]] + [k for k in range(len(rs)) if k != genome[i]]
            placed = False
            for k in pref:
                r = rs[k]
                if r.route_id in used:
                    continue
                if ship_days.get(r.ship_id, 0) + r.duration > CYCLE_DAYS:
                    continue
                used.add(r.route_id)
                ship_days[r.ship_id] = ship_days.get(r.ship_id, 0) + r.duration
                assign[i] = r
                placed = True
                break
            if not placed:
                feasible = False
        return assign, feasible

    def _assign_to_solution(self, assign: List[Route]) -> Solution:
        sol = Solution()
        for i, r in enumerate(assign):
            sol.event_assignment[i] = r.route_id
            sol.ship_routes.setdefault(r.ship_id, []).append(r)
        return sol

    # ================= Yerel arama (VNS relocate, artımlı) =================
    def _local_search(self, assign: List[Route]) -> Tuple[List[Route], float]:
        ship_days: Dict[str, int] = {}
        used = set()
        for r in assign:
            ship_days[r.ship_id] = ship_days.get(r.ship_id, 0) + r.duration
            used.add(r.route_id)
        cost = self._total_cost(assign)

        improved = True
        while improved:
            improved = False
            best_i, best_route, best_delta = -1, None, -1e-6
            for i in range(self.n):
                old = assign[i]
                sa = old.ship_id
                da = ship_days[sa]
                for r in self.serving[i]:
                    if r is old or r.route_id in used:
                        continue
                    sb = r.ship_id
                    # 35-gün kontrolü
                    if sa == sb:
                        new_da = da - old.duration + r.duration
                        if new_da > CYCLE_DAYS:
                            continue
                        delta = (r.cost - old.cost) + (
                            self._ship_cost(self.ships_by_id[sa], new_da) - self._ship_cost(self.ships_by_id[sa], da))
                    else:
                        db = ship_days.get(sb, 0)
                        if db + r.duration > CYCLE_DAYS:
                            continue
                        delta = (r.cost - old.cost) + (
                            self._ship_cost(self.ships_by_id[sa], da - old.duration) - self._ship_cost(self.ships_by_id[sa], da)) + (
                            self._ship_cost(self.ships_by_id[sb], db + r.duration) - self._ship_cost(self.ships_by_id[sb], db))
                    if delta < best_delta:
                        best_delta, best_i, best_route = delta, i, r
            if best_route is not None:
                old = assign[best_i]
                sa, sb = old.ship_id, best_route.ship_id
                used.discard(old.route_id)
                used.add(best_route.route_id)
                ship_days[sa] -= old.duration
                ship_days[sb] = ship_days.get(sb, 0) + best_route.duration
                assign[best_i] = best_route
                cost += best_delta
                improved = True
        return assign, cost

    def _shake(self, assign: List[Route], k: int) -> List[Route]:
        genome = [0] * self.n
        for i, r in enumerate(assign):
            genome[i] = self.serving[i].index(r)
        for i in self.rng.sample(range(self.n), min(k, self.n)):
            genome[i] = self.rng.randrange(len(self.serving[i]))
        a, _ = self._decode_assign(genome)
        if any(x is None for x in a):           # onarım nadiren başarısız -> eskiye dön
            return assign[:]
        return a

    # ================= GA katmanı =================
    def _crossover(self, a: List[int], b: List[int]) -> List[int]:
        return [a[i] if self.rng.random() < 0.5 else b[i] for i in range(len(a))]

    def _mutate(self, g: List[int]) -> List[int]:
        g = g[:]
        for i in range(len(g)):
            if self.rng.random() < self.mutation_rate:
                g[i] = self.rng.randrange(len(self.serving[i]))
        return g

    def _genome_cost(self, genome: List[int]) -> float:
        assign, feasible = self._decode_assign(genome)
        if not feasible:
            return 1e12
        return self._total_cost(assign)

    def _single_run(self) -> Tuple[List[Route], float, List[float]]:
        pop = [self._greedy_genome() for _ in range(max(2, self.pop_size // 5))]
        pop += [self._random_genome() for _ in range(self.pop_size - len(pop))]
        best_assign, best_cost = None, float("inf")
        history: List[float] = []

        for _ in range(self.generations):
            scored = sorted(((self._genome_cost(g), g) for g in pop), key=lambda t: t[0])
            # memetik: en iyi bireye yerel arama
            assign, _ = self._decode_assign(scored[0][1])
            if all(x is not None for x in assign):
                assign, c = self._local_search(assign)
                if c < best_cost:
                    best_cost, best_assign = c, assign[:]
            history.append(best_cost)

            parents = [g for _, g in scored[:self.elite]]
            newpop = parents[:]
            while len(newpop) < self.pop_size:
                child = self._mutate(self._crossover(self.rng.choice(parents),
                                                     self.rng.choice(parents)))
                newpop.append(child)
            pop = newpop

        # --- Iterated Local Search (VNS shaking) ---
        for it in range(self.shake_iters):
            k = 2 + (it % 6)
            cand, c = self._local_search(self._shake(best_assign, k))
            if c < best_cost - 1e-6:
                best_cost, best_assign = c, cand[:]
            history.append(best_cost)
        return best_assign, best_cost, history

    def run(self) -> Tuple[Solution, List[float]]:
        """Multi-start GA+VNS: birkaç tohumla çalışır, en iyi çözümü döner."""
        best_assign, best_cost, hist = None, float("inf"), []
        for r in range(self.restarts):
            self.rng = random.Random(self.seed + r * 7919)
            assign, cost, h = self._single_run()
            hist.extend(min(best_cost, x) if best_cost < float("inf") else x for x in h)
            if cost < best_cost:
                best_cost, best_assign = cost, assign
            hist.append(best_cost)
        return self._assign_to_solution(best_assign), hist
