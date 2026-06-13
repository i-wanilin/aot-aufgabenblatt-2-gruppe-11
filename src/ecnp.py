"""Variante b) -- erweitertes Contract Net Protocol (eCNP).

Alle Auktionen laufen *parallel*: jeder LA startet je Itemtyp (mit Bestand) eine
eigene Protokollinstanz. Pro Runde:

  1. cfp        -- jede offene Instanz ruft (per Broadcast) zur Gebotsabgabe auf.
  2. propose    -- jeder TA bietet für jede offene, noch benötigte Instanz mit
                   seinen marginalen Wegkosten (konsistent zur eigenen Route).
  3. prov-accept/prov-reject -- jede Instanz akzeptiert vorläufig das beste Gebot,
                   weist die übrigen vorläufig ab (inkl. Angabe des besten Gebots).
  4. definitive-bid / cancel -- ein TA bestätigt je Itemtyp die attraktivste
                   vorläufige Zusage mit einem definitiven Gebot und *storniert*
                   etwaige weitere vorläufige Zusagen desselben Typs.
  5. definitive-accept -- die Instanz erteilt dem besten definitiven Gebot den
                   Zuschlag und terminiert (bzw. vergibt n-1 Restbestand weiter).

Nach Zu-/Absagen plant ein TA implizit um: seine marginalen Gebote der nächsten
Runde berücksichtigen die bereits definitiv kontraktierten Lager.
"""
from __future__ import annotations

from dataclasses import dataclass

from agents import Result, TransportAgent, compute_result
from messaging import (
    CANCEL,
    CFP,
    DEF_ACCEPT,
    DEF_BID,
    DEF_REJECT,
    PROPOSE,
    PROV_ACCEPT,
    PROV_REJECT,
    Bus,
    Message,
)
from model import World


@dataclass
class Instance:
    warehouse_id: str
    coord: tuple
    item_type: str
    remaining: int

    @property
    def conv(self) -> str:
        return f"{self.warehouse_id}:{self.item_type}"

    @property
    def open(self) -> bool:
        return self.remaining > 0


def run(world: World, verbose: bool = True, max_rounds: int = 30) -> Result:
    bus = Bus(verbose=verbose)
    tas = [TransportAgent(c, world) for c in world.centrals]
    instances: list[Instance] = [
        Instance(w.id, w.coord, t, n)
        for w in world.warehouses for t, n in w.stock.items() if n > 0
    ]

    if verbose:
        print(f"=== eCNP · Welt '{world.name}' ===")
        print(f"Angebot {world.supply()} | Nachfrage {world.demand()} | "
              f"Strafe {world.penalty:g}/Item")
        print(f"{len(instances)} parallele Protokollinstanzen gestartet")

    for _round in range(1, max_rounds + 1):
        open_instances = [i for i in instances if i.open]
        # Gibt es überhaupt noch ein Item, das ein TA braucht und das verfügbar ist?
        live = [i for i in open_instances if any(ta.needs(i.item_type) for ta in tas)]
        if not live:
            bus.note("keine offenen, benötigten Instanzen mehr -> Ende")
            break
        bus.round("(eCNP)")

        # 1. cfp ------------------------------------------------------------
        for inst in live:
            for ta in tas:
                if ta.needs(inst.item_type):
                    bus.send(Message(CFP, inst.warehouse_id, ta.id, inst.conv,
                                     {"item": inst.item_type, "ort": inst.coord}))

        # 2. propose: marginales Gebot je offener, benötigter Instanz --------
        # proposals[conv] = list[(bid, ta)]
        proposals: dict[str, list] = {i.conv: [] for i in live}
        for ta in tas:
            for inst in live:
                if ta.needs(inst.item_type):
                    bid = ta.marginal_bid(inst.coord)
                    proposals[inst.conv].append((bid, ta))
                    bus.send(Message(PROPOSE, ta.id, inst.warehouse_id, inst.conv,
                                     {"gebot": round(bid, 1)}))

        # 3. vorläufige Zu-/Absagen -----------------------------------------
        # prov_accepts[ta_id][item_type] = list[(bid, inst)]
        prov_accepts: dict[str, dict[str, list]] = {ta.id: {} for ta in tas}
        for inst in live:
            offers = sorted(proposals[inst.conv], key=lambda x: (x[0], x[1].id))
            if not offers:
                continue
            best_bid, best_ta = offers[0]
            bus.send(Message(PROV_ACCEPT, inst.warehouse_id, best_ta.id, inst.conv,
                             {"gebot": round(best_bid, 1)}))
            prov_accepts[best_ta.id].setdefault(inst.item_type, []).append((best_bid, inst))
            for _bid, ta in offers[1:]:
                bus.send(Message(PROV_REJECT, inst.warehouse_id, ta.id, inst.conv,
                                 {"bestes_gebot": round(best_bid, 1)}))

        # 4. definitive Gebote + Stornierungen ------------------------------
        # def_bids[conv] = list[(bid, ta)]
        def_bids: dict[str, list] = {}
        for ta in tas:
            for accepts in prov_accepts[ta.id].values():
                accepts.sort(key=lambda x: x[0])
                bid, chosen = accepts[0]
                def_bids.setdefault(chosen.conv, []).append((bid, ta))
                bus.send(Message(DEF_BID, ta.id, chosen.warehouse_id, chosen.conv,
                                 {"gebot": round(bid, 1)}))
                for _, other in accepts[1:]:  # weitere Zusagen desselben Typs zurückziehen
                    bus.send(Message(CANCEL, ta.id, other.warehouse_id, other.conv, {}))

        # 5. definitive Zuschläge -------------------------------------------
        for inst in live:
            bids = sorted(def_bids.get(inst.conv, []), key=lambda x: (x[0], x[1].id))
            if not bids:
                continue
            best_bid, winner = bids[0]
            bus.send(Message(DEF_ACCEPT, inst.warehouse_id, winner.id, inst.conv,
                             {"item": inst.item_type, "gebot": round(best_bid, 1)}))
            winner.commit(inst.item_type, inst.warehouse_id)
            inst.remaining -= 1
            for _bid, loser in bids[1:]:
                bus.send(Message(DEF_REJECT, inst.warehouse_id, loser.id, inst.conv, {}))

        if all(ta.satisfied() for ta in tas):
            bus.note("alle TA versorgt -> Ende")
            break

    if verbose:
        print()
    return compute_result("eCNP", world, tas, bus.count())
