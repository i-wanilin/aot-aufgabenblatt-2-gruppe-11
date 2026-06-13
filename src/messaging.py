"""Leichtgewichtiger, simulierter Nachrichtenbus (FIPA-ähnliche Performative).

Einzel-threaded: Agenten tauschen ``Message``-Objekte aus, die der Bus
protokolliert. Die *Dauer* der Interaktionsprotokolle spielt laut Aufgabe keine
Rolle, daher wird hier keine echte Nebenläufigkeit benötigt -- der Bus dient vor
allem dem nachvollziehbaren Logging für die Screencasts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# FIPA-orientierte Performative
CFP = "cfp"
PROPOSE = "propose"
ACCEPT = "accept-proposal"
REJECT = "reject-proposal"
# eCNP-spezifisch
PROV_ACCEPT = "provisional-accept"
PROV_REJECT = "provisional-reject"
DEF_BID = "definitive-bid"
DEF_ACCEPT = "definitive-accept"
DEF_REJECT = "definitive-reject"
CANCEL = "cancel"
INFORM = "inform"


@dataclass
class Message:
    performative: str
    sender: str
    receiver: str
    conversation: str            # Protokollinstanz, z.B. "LA1:A"
    content: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        body = ", ".join(f"{k}={v}" for k, v in self.content.items())
        return (f"{self.performative:<18} {self.sender:>5} -> {self.receiver:<5} "
                f"[{self.conversation:<7}] {body}")


class Bus:
    """Protokolliert jede Nachricht und kann sie live ausgeben."""

    def __init__(self, verbose: bool = True) -> None:
        self.verbose = verbose
        self.log: list[Message] = []
        self._round = 0

    def round(self, label: str = "") -> None:
        self._round += 1
        if self.verbose:
            tag = f" {label}" if label else ""
            print(f"\n-------- Runde {self._round}{tag} --------")

    def send(self, msg: Message) -> None:
        self.log.append(msg)
        if self.verbose:
            print(f"  {msg}")

    def note(self, text: str) -> None:
        """Erläuternde Log-Zeile (keine Agentennachricht)."""
        if self.verbose:
            print(f"  - {text}")

    def count(self, performative: str | None = None) -> int:
        if performative is None:
            return len(self.log)
        return sum(1 for m in self.log if m.performative == performative)
