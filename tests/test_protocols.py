"""Korrektheits- und Invariantentests für CNP/eCNP (AOT Aufgabenblatt 2).

Enthält einen *Brute-Force-Optimierer* (Orakel) als unabhängigen Vollprüfer:
für kleine Instanzen wird die garantiert optimale Gesamtenergie durch
vollständige Enumeration aller zulässigen Zuordnungen berechnet und mit den
Protokoll-Ergebnissen verglichen.
"""
from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import cnp  # noqa: E402
import ecnp  # noqa: E402
from agents import Result  # noqa: E402
from model import Central, Warehouse, World, distance, load_world, round_trip_cost  # noqa: E402

CFG = os.path.join(ROOT, "config")


# --------------------------------------------------------------------------- #
# Unabhängiges Orakel: exakte optimale Gesamtenergie via Brute Force
# --------------------------------------------------------------------------- #
def brute_force_optimum(world: World) -> float:
    """Exaktes Optimum der Gesamtenergie (Fahrt + Strafe) via Branch & Bound.

    Pro TA wird jeder benötigte Itemtyp einem Lager (mit Bestand) oder ``None``
    (= unerfüllt, Strafe) zugeordnet; Lagerbestände je (Lager,Typ) sind harte
    Schranken. Geprunt wird über (a) Kapazität und (b) eine untere Schranke
    (aktuelle Fahrt + aktuelle Strafe), da Fahrt durch Hinzufügen weiterer
    Stopps nie sinkt. Exakt für alle hier verwendeten Instanzgrößen.
    """
    centrals = world.centrals
    coord = {w.id: w.coord for w in world.warehouses}
    cap = {(w.id, t): n for w in world.warehouses for t, n in w.stock.items()}
    slots = [(ti, t) for ti, c in enumerate(centrals) for t in c.order]
    # Optionen je Slot, Lager nach Nähe zur Zentrale sortiert (gute Lösungen
    # zuerst -> frühes, scharfes Pruning), None (unerfüllt) zuletzt.
    options = []
    for (ti, t) in slots:
        whs = [w.id for w in world.warehouses if w.stock.get(t, 0) > 0]
        whs.sort(key=lambda wid: distance(centrals[ti].coord, coord[wid], world.metric))
        options.append(whs + [None])

    stops: dict = {i: [] for i in range(len(centrals))}
    used: dict = {}

    def travel_now() -> float:
        return sum(round_trip_cost(centrals[i].coord, s, world.metric)
                   for i, s in stops.items())

    # Greedy-Startlösung als Inkumbent (nur zum Pruning; ändert das Optimum nicht)
    g_pen = 0.0
    for k, (ti, t) in enumerate(slots):
        placed = False
        for wid in options[k]:
            if wid is not None and used.get((wid, t), 0) < cap.get((wid, t), 0):
                used[(wid, t)] = used.get((wid, t), 0) + 1
                stops[ti].append(coord[wid])
                placed = True
                break
        if not placed:
            g_pen += world.penalty
    best = travel_now() + g_pen
    for i in stops:
        stops[i].clear()
    used.clear()

    def rec(k: int, penalty: float) -> None:
        nonlocal best
        lower = travel_now() + penalty
        if lower >= best:           # Pruning: kann das Inkumbent nicht schlagen
            return
        if k == len(slots):
            best = lower
            return
        ti, t = slots[k]
        for wid in options[k]:
            if wid is None:
                rec(k + 1, penalty + world.penalty)
            elif used.get((wid, t), 0) < cap.get((wid, t), 0):
                used[(wid, t)] = used.get((wid, t), 0) + 1
                stops[ti].append(coord[wid])
                rec(k + 1, penalty)
                stops[ti].pop()
                used[(wid, t)] -= 1

    rec(0, 0.0)
    return best


def lower_bound(world: World) -> float:
    """Billige, zulässige untere Schranke der Gesamtenergie.

    Unvermeidbare Strafe = Σ_t max(0, Nachfrage_t − Angebot_t) · Strafe; die
    Fahrtkosten werden mit 0 nach unten abgeschätzt. Dient als schnelle
    Plausibilitätsschranke (Protokollenergie darf nie darunter liegen).
    """
    sup, dem = world.supply(), world.demand()
    shortfall = sum(max(0, dem[t] - sup[t]) for t in ("A", "B", "C"))
    return shortfall * world.penalty


# --------------------------------------------------------------------------- #
# Hilfsfunktionen für Invarianten
# --------------------------------------------------------------------------- #
def assert_valid(tc: unittest.TestCase, world: World, res: Result) -> None:
    supply = {(w.id, t): n for w in world.warehouses for t, n in w.stock.items()}
    order = {c.id: list(c.order) for c in world.centrals}
    used: dict = {}
    for ta_id, assign in res.routes.items():
        for t, wid in assign.items():
            # nur benötigte Typen werden kontraktiert
            tc.assertIn(t, order[ta_id], f"{ta_id} hat Fremd-Item {t}")
            used[(wid, t)] = used.get((wid, t), 0) + 1
    # Bestände nicht überschritten
    for key, n in used.items():
        tc.assertLessEqual(n, supply.get(key, 0),
                           f"Lagerbestand überschritten bei {key}: {n} > {supply.get(key,0)}")
    # unmet == bestellt aber nicht kontraktiert; Bilanz konsistent
    total_needed = sum(len(v) for v in order.values())
    total_assigned = sum(len(a) for a in res.routes.values())
    tc.assertEqual(res.n_unmet, total_needed - total_assigned,
                   "n_unmet passt nicht zur Zuordnungsbilanz")


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #
class TestPrimitives(unittest.TestCase):
    def test_distance_manhattan(self):
        self.assertEqual(distance((1, 1), (4, 5)), 7)
        self.assertEqual(distance((4, 5), (1, 1)), 7)
        self.assertEqual(distance((2, 2), (2, 2)), 0)

    def test_distance_euclidean(self):
        self.assertAlmostEqual(distance((0, 0), (3, 4), "euclidean"), 5.0)

    def test_round_trip_single(self):
        # ein Stopp -> Hin und zurück
        self.assertEqual(round_trip_cost((0, 0), [(0, 3)]), 6)

    def test_round_trip_dedupe(self):
        # zweimal dasselbe Lager -> nur einmal anfahren
        self.assertEqual(round_trip_cost((0, 0), [(0, 3), (0, 3)]), 6)

    def test_round_trip_empty(self):
        self.assertEqual(round_trip_cost((0, 0), []), 0)

    def test_round_trip_picks_shortest_perm(self):
        # Stopps auf einer Linie: optimale Reihenfolge 1->2->3 (kein Zickzack)
        c = round_trip_cost((0, 0), [(0, 2), (0, 1), (0, 3)])
        self.assertEqual(c, 6)  # 0->1->2->3->0 = 3 + 3 zurück


class TestInvariants(unittest.TestCase):
    """Beide Protokolle auf beiden Welten: Gültigkeit + Bilanz + Determinismus."""

    def _worlds(self):
        return [load_world(os.path.join(CFG, f"world_{n}.json"))
                for n in ("balanced", "overhang")]

    def test_validity_and_determinism(self):
        for world in self._worlds():
            for runner, name in ((cnp.run, "CNP"), (ecnp.run, "eCNP")):
                r1 = runner(world, verbose=False)
                r2 = runner(world, verbose=False)
                with self.subTest(world=world.name, proto=name):
                    assert_valid(self, world, r1)
                    self.assertEqual(r1.routes, r2.routes, "nicht deterministisch (Routen)")
                    self.assertEqual(r1.total_energy, r2.total_energy,
                                     "nicht deterministisch (Energie)")
                    # Energiebilanz
                    self.assertAlmostEqual(
                        r1.total_energy, r1.travel_energy + r1.penalty_energy)


class TestBalanced(unittest.TestCase):
    def setUp(self):
        self.world = load_world(os.path.join(CFG, "world_balanced.json"))

    def test_all_satisfied_no_penalty(self):
        for runner in (cnp.run, ecnp.run):
            r = runner(self.world, verbose=False)
            with self.subTest(proto=r.protocol):
                self.assertEqual(r.n_unmet, 0, "in balanced sollten alle versorgt sein")
                self.assertEqual(r.penalty_energy, 0)

    def test_reaches_optimum(self):
        opt = brute_force_optimum(self.world)
        for runner in (cnp.run, ecnp.run):
            r = runner(self.world, verbose=False)
            with self.subTest(proto=r.protocol):
                self.assertGreaterEqual(
                    r.total_energy, opt - 1e-9,
                    "Protokoll besser als Optimum -> Orakel/Modell fehlerhaft")
                self.assertAlmostEqual(
                    r.total_energy, opt,
                    msg=f"{r.protocol} suboptimal: {r.total_energy} vs Opt {opt}")


class TestOverhang(unittest.TestCase):
    def setUp(self):
        self.world = load_world(os.path.join(CFG, "world_overhang.json"))

    # Per B&B-Orakel offline verifiziertes Optimum dieser Instanz (≈87s Beweis).
    KNOWN_OPTIMUM = 328.0

    def test_unavoidable_penalty(self):
        # Nachfrage(5/Typ) - Angebot(4/Typ) = 1 unerfüllt je Typ = 3 gesamt
        for runner in (cnp.run, ecnp.run):
            r = runner(self.world, verbose=False)
            with self.subTest(proto=r.protocol):
                self.assertEqual(r.n_unmet, 3)
                self.assertEqual(r.penalty_energy, 300)

    def test_reaches_known_optimum_and_lb(self):
        lb = lower_bound(self.world)
        self.assertEqual(lb, 300)
        for runner in (cnp.run, ecnp.run):
            r = runner(self.world, verbose=False)
            with self.subTest(proto=r.protocol):
                self.assertGreaterEqual(r.total_energy, lb - 1e-9,
                                        "Protokollenergie unter zulässiger Schranke")
                self.assertAlmostEqual(r.total_energy, self.KNOWN_OPTIMUM)

    @unittest.skipUnless(os.environ.get("AOT_SLOW"),
                         "langsamer exakter B&B-Beweis (~90s); AOT_SLOW=1 zum Aktivieren")
    def test_bruteforce_confirms_optimum(self):
        self.assertEqual(brute_force_optimum(self.world), self.KNOWN_OPTIMUM)


class TestOptimalityOracleTiny(unittest.TestCase):
    """Winzige, handgerechnete Instanz: beide Protokolle müssen das Optimum treffen."""

    def _tiny(self):
        return World(
            metric="manhattan", penalty=100, name="tiny-2x2",
            warehouses=[
                Warehouse("W1", (0, 1), {"A": 1, "B": 1}),
                Warehouse("W2", (10, 1), {"A": 1, "B": 1}),
            ],
            centrals=[
                Central("Ta", (0, 0), ["A", "B"]),
                Central("Tb", (10, 0), ["A", "B"]),
            ],
        )

    def test_tiny_optimum(self):
        world = self._tiny()
        opt = brute_force_optimum(world)
        self.assertEqual(opt, 4.0)  # jeder TA nimmt sein nahes Lager komplett
        for runner in (cnp.run, ecnp.run):
            r = runner(world, verbose=False)
            with self.subTest(proto=r.protocol):
                assert_valid(self, world, r)
                self.assertEqual(r.n_unmet, 0)
                self.assertAlmostEqual(r.total_energy, opt)

    def test_tiny_contested(self):
        # Beide TA sehr nah an W1, W2 weit weg -> Engpass, einer muss weichen
        world = World(
            metric="manhattan", penalty=100, name="tiny-contested",
            warehouses=[
                Warehouse("W1", (0, 1), {"A": 1}),
                Warehouse("W2", (0, 5), {"A": 1}),
            ],
            centrals=[
                Central("Ta", (0, 0), ["A"]),
                Central("Tb", (0, 2), ["A"]),
            ],
        )
        opt = brute_force_optimum(world)
        for runner in (cnp.run, ecnp.run):
            r = runner(world, verbose=False)
            with self.subTest(proto=r.protocol):
                assert_valid(self, world, r)
                self.assertAlmostEqual(r.total_energy, opt,
                                       msg=f"{r.protocol}={r.total_energy}, opt={opt}")


class TestMarginalBids(unittest.TestCase):
    def test_marginal_never_negative(self):
        from agents import TransportAgent
        world = load_world(os.path.join(CFG, "world_balanced.json"))
        ta = TransportAgent(world.centrals[0], world)
        for w in world.warehouses:
            self.assertGreaterEqual(ta.marginal_bid(w.coord), 0)
        ta.commit("A", world.warehouses[0].id)
        for w in world.warehouses:
            self.assertGreaterEqual(ta.marginal_bid(w.coord), -1e-9)


if __name__ == "__main__":
    unittest.main(verbosity=2)
