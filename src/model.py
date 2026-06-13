"""Domänenmodell für die kooperative Transportlogistik (AOT Aufgabenblatt 2).

Vollständige Information, keine Grid-Repräsentation: Lager und Zentralen werden
nur über ihre Koordinaten verwaltet. Die Entfernung ergibt sich aus der
Koordinatendifferenz (Manhattan- oder euklidische Metrik, konfigurierbar).

Eine Route eines Transportagenten ist eine *Rundreise* von der Zentrale zu den
benötigten Lagern und zurück. Da ein Auftrag aus maximal 3 Itemtypen besteht,
ist die kürzeste Rundreise über die (höchstens 3 verschiedenen) Lagerkoordinaten
durch vollständige Enumeration aller Permutationen trivial bestimmbar.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from itertools import permutations

Coord = tuple[float, float]
ITEM_TYPES = ("A", "B", "C")


# --------------------------------------------------------------------------- #
# Entfernungen / Routenkosten
# --------------------------------------------------------------------------- #
def distance(a: Coord, b: Coord, metric: str = "manhattan") -> float:
    """Entfernung zwischen zwei Orten im Grid."""
    if metric == "manhattan":
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
    if metric == "euclidean":
        return math.hypot(a[0] - b[0], a[1] - b[1])
    raise ValueError(f"unbekannte Metrik: {metric}")


def round_trip_cost(start: Coord, stops: list[Coord], metric: str = "manhattan") -> float:
    """Kürzeste Rundreise von ``start`` über alle ``stops`` und zurück.

    ``stops`` darf Duplikate enthalten (z.B. zwei Itemtypen aus demselben Lager);
    diese werden zusammengefasst, da ein Lager nur einmal angefahren werden muss.
    Bei <= 3 verschiedenen Stopps werden alle Permutationen (<= 6) enumeriert.
    """
    uniq = list(dict.fromkeys(stops))  # Reihenfolge-stabil deduplizieren
    if not uniq:
        return 0.0
    best = math.inf
    for perm in permutations(uniq):
        cost = distance(start, perm[0], metric)
        for u, v in zip(perm, perm[1:], strict=False):
            cost += distance(u, v, metric)
        cost += distance(perm[-1], start, metric)  # Rückweg -> Rundreise
        best = min(best, cost)
    return best


# --------------------------------------------------------------------------- #
# Statische Welt-Objekte
# --------------------------------------------------------------------------- #
@dataclass
class Warehouse:
    """Lager (durch einen Lageragenten LA repräsentiert)."""
    id: str
    coord: Coord
    stock: dict[str, int]  # Itemtyp -> verfügbare Stückzahl

    def total(self) -> int:
        return sum(self.stock.values())


@dataclass
class Central:
    """Fertigungsstandort/Zentrale (durch einen Transportagenten TA besetzt)."""
    id: str
    coord: Coord
    order: list[str]  # benötigte Itemtypen (Menge je Typ == 1)


@dataclass
class World:
    metric: str
    penalty: float            # Konventionalstrafe je nicht erfülltem Item
    warehouses: list[Warehouse]
    centrals: list[Central]
    name: str = "world"
    grid_size: tuple[int, int] = (9, 9)

    # -- abgeleitete Kennzahlen ------------------------------------------- #
    def supply(self) -> dict[str, int]:
        s = dict.fromkeys(ITEM_TYPES, 0)
        for w in self.warehouses:
            for t, n in w.stock.items():
                s[t] += n
        return s

    def demand(self) -> dict[str, int]:
        d = dict.fromkeys(ITEM_TYPES, 0)
        for c in self.centrals:
            for t in c.order:
                d[t] += 1
        return d

    def warehouse(self, wid: str) -> Warehouse:
        return next(w for w in self.warehouses if w.id == wid)


def load_world(path: str) -> World:
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    warehouses = [
        Warehouse(id=w["id"], coord=tuple(w["coord"]), stock=dict(w["stock"]))
        for w in raw["warehouses"]
    ]
    centrals = [
        Central(id=c["id"], coord=tuple(c["coord"]), order=list(c["order"]))
        for c in raw["centrals"]
    ]
    return World(
        metric=raw.get("metric", "manhattan"),
        penalty=float(raw.get("penalty", 100)),
        warehouses=warehouses,
        centrals=centrals,
        name=raw.get("name", "world"),
        grid_size=tuple(raw.get("grid_size", [9, 9])),
    )
