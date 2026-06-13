"""Variante a) -- Contract Net Protocol (FIPA-orientiert, sequenziell/iterativ).

Jeder Lageragent (LA) führt für jeden Itemtyp, von dem er Bestand hat, ein CNP
durch: cfp an alle interessierten TA, die TA bieten mit ihrer (marginalen)
Entfernung, der LA erteilt den Zuschlag an die günstigsten Gebote.

Ein TA bietet je Itemtyp nur einmal und stoppt für diesen Typ, sobald er den
Zuschlag erhalten hat. Da der Zuschlag eines Items die Rundreise und damit die
marginalen Kosten für die übrigen Items verändert, werden die Auktionen iterativ
in mehreren Durchläufen abgehalten, bis sich nichts mehr ändert (Re-Bidding).
"""
from __future__ import annotations

from agents import Result, TransportAgent, compute_result
from messaging import ACCEPT, CFP, PROPOSE, REJECT, Bus, Message
from model import World


def run(world: World, verbose: bool = True, max_passes: int = 20) -> Result:
    bus = Bus(verbose=verbose)
    tas = [TransportAgent(c, world) for c in world.centrals]
    # Arbeitsbestand der Lager (wird beim Zuschlag reduziert)
    stock = {w.id: dict(w.stock) for w in world.warehouses}

    if verbose:
        print(f"=== CNP - Welt '{world.name}' ===")
        print(f"Angebot {world.supply()} | Nachfrage {world.demand()} | "
              f"Strafe {world.penalty:g}/Item")

    for p in range(1, max_passes + 1):
        bus.round(f"(Durchlauf {p})")
        changed = False

        for wh in world.warehouses:
            for item_type in ("A", "B", "C"):
                if stock[wh.id].get(item_type, 0) <= 0:
                    continue
                conv = f"{wh.id}:{item_type}"
                # --- cfp an alle TA, die diesen Typ noch brauchen ---------
                bidders = [ta for ta in tas if ta.needs(item_type)]
                if not bidders:
                    continue
                for ta in bidders:
                    bus.send(Message(CFP, wh.id, ta.id, conv,
                                     {"item": item_type, "ort": wh.coord}))

                # --- Gebote (marginale Entfernung) -----------------------
                proposals = []
                for ta in bidders:
                    bid = ta.marginal_bid(wh.coord)
                    proposals.append((bid, ta))
                    bus.send(Message(PROPOSE, ta.id, wh.id, conv, {"gebot": round(bid, 1)}))

                # --- Zuschläge an die günstigsten Gebote -----------------
                # so viele Einheiten vergeben, wie Bestand vorhanden ist
                proposals.sort(key=lambda x: (x[0], x[1].id))
                while stock[wh.id].get(item_type, 0) > 0 and proposals:
                    bid, winner = proposals.pop(0)
                    bus.send(Message(ACCEPT, wh.id, winner.id, conv,
                                     {"item": item_type, "gebot": round(bid, 1)}))
                    winner.commit(item_type, wh.id)
                    stock[wh.id][item_type] -= 1
                    changed = True
                # Absagen an den Rest
                for _bid, loser in proposals:
                    bus.send(Message(REJECT, wh.id, loser.id, conv, {"item": item_type}))

        if not changed:
            bus.note("keine Aenderung -> Konvergenz")
            break

    if verbose:
        print()
    return compute_result("CNP", world, tas, bus.count())
