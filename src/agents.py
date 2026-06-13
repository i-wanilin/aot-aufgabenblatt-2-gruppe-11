"""Gemeinsame Agenten-Buchhaltung für beide Protokollvarianten.

Ein Transportagent (TA) merkt sich, welche Itemtypen er noch braucht und welche
er bereits (vorläufig/definitiv) an konkrete Lager kontraktiert hat. Aus den
definitiv kontraktierten Lagern ergibt sich seine aktuelle Rundreise; das
*marginale* Gebot für ein weiteres Lager ist der Zuwachs an Rundreisekosten.
"""
from __future__ import annotations

from dataclasses import dataclass

from model import Central, World, round_trip_cost


class TransportAgent:
    def __init__(self, central: Central, world: World) -> None:
        self.id = central.id
        self.central = central
        self.world = world
        self.needed: list[str] = list(central.order)
        # Itemtyp -> Lager-ID (definitiv kontraktiert)
        self.committed: dict[str, str] = {}

    # -- Routen / Kosten --------------------------------------------------- #
    def _stops(self, extra_coord=None) -> list:
        coords = [self.world.warehouse(wid).coord for wid in self.committed.values()]
        if extra_coord is not None:
            coords = coords + [extra_coord]
        return coords

    def current_cost(self) -> float:
        return round_trip_cost(self.central.coord, self._stops(), self.world.metric)

    def marginal_bid(self, warehouse_coord) -> float:
        """Zuwachs der Rundreisekosten, wenn dieses Lager zusätzlich angefahren wird."""
        with_extra = round_trip_cost(
            self.central.coord, self._stops(warehouse_coord), self.world.metric)
        return with_extra - self.current_cost()

    # -- Status ------------------------------------------------------------ #
    def open_items(self) -> list[str]:
        """Noch nicht kontraktierte, aber benötigte Itemtypen."""
        return [t for t in self.needed if t not in self.committed]

    def needs(self, item_type: str) -> bool:
        return item_type in self.needed and item_type not in self.committed

    def commit(self, item_type: str, warehouse_id: str) -> None:
        self.committed[item_type] = warehouse_id

    def satisfied(self) -> bool:
        return not self.open_items()


@dataclass
class Result:
    """Ergebnis einer Simulation -- Grundlage der Energie-/Qualitätsmessung."""
    protocol: str
    world_name: str
    routes: dict[str, dict[str, str]]   # TA-ID -> {Itemtyp: Lager-ID}
    travel_energy: float
    unmet: dict[str, list[str]]         # TA-ID -> nicht erfüllte Itemtypen
    penalty_per_item: float
    messages: int

    @property
    def n_unmet(self) -> int:
        return sum(len(v) for v in self.unmet.values())

    @property
    def penalty_energy(self) -> float:
        return self.n_unmet * self.penalty_per_item

    @property
    def total_energy(self) -> float:
        return self.travel_energy + self.penalty_energy

    def summary(self) -> str:
        lines = [
            f"Protokoll      : {self.protocol}",
            f"Welt           : {self.world_name}",
            f"Nachrichten    : {self.messages}",
            "Routen:",
        ]
        for ta_id, assign in sorted(self.routes.items()):
            order = " ".join(f"{t}->{w}" for t, w in sorted(assign.items())) or "(leer)"
            miss = self.unmet.get(ta_id, [])
            tail = f"   UNERFUELLT: {','.join(miss)}" if miss else ""
            lines.append(f"  {ta_id}: {order}{tail}")
        lines += [
            f"Fahrenergie    : {self.travel_energy:.1f}",
            f"Strafenergie   : {self.penalty_energy:.1f} "
            f"({self.n_unmet} x {self.penalty_per_item:g})",
            f"GESAMTENERGIE  : {self.total_energy:.1f}",
        ]
        return "\n".join(lines)


def compute_result(protocol: str, world: World, tas: list[TransportAgent],
                   messages: int) -> Result:
    routes = {ta.id: dict(ta.committed) for ta in tas}
    travel = sum(ta.current_cost() for ta in tas)
    unmet = {ta.id: ta.open_items() for ta in tas if ta.open_items()}
    return Result(
        protocol=protocol,
        world_name=world.name,
        routes=routes,
        travel_energy=travel,
        unmet=unmet,
        penalty_per_item=world.penalty,
        messages=messages,
    )
