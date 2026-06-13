# Aufgabenblatt 2 – Kooperative Transportlogistik (AOT, SoSe 2026)

Implementierung zweier Varianten des kooperativen Problemlösens für die
verteilte Transportlogistik im Kurs *Agententechnologien – Grundlagen und
Anwendungen* (TU Berlin, ISIS‑Modul 2228091):

* **a) Contract Net Protocol (CNP)** – sequenzielle/iterative Auktionen.
* **b) erweitertes Contract Net Protocol (eCNP)** – parallele Protokollinstanzen
  mit vorläufigen/definitiven Geboten und Stornierungen.

**Abgabe:** 21.06.2026 · Implementierung = 60 % (CNP 25 %, eCNP 35 %),
Dokumentation/Report = 40 %.

## Szenario

Mehrere Fertigungsstandorte (*Zentralen*) werden je von einem **Transportagenten
(TA)** besetzt, der die Itemtypen `{A, B, C}` (oder eine Teilmenge) benötigt.
Die Items liegen in **Lagern**, jeweils durch einen **Lageragenten (LA)**
repräsentiert. Globales Ziel: minimaler **Gesamtenergieverbrauch** = Summe der
Rundreise‑Weglängen aller TA. Nicht erfüllte Items kosten eine pauschale
Konventionalstrafe (Standard: 100 Energieeinheiten/Item).

Es wird – wie in der Aufgabe erlaubt – **keine Grid‑Repräsentation** verwendet:
Lager und Zentralen sind nur über Koordinaten bekannt (vollständige Information),
Entfernungen ergeben sich aus der Koordinatendifferenz (Manhattan‑Metrik). Da ein
Auftrag ≤ 3 Items umfasst, wird die kürzeste Rundreise durch Enumeration aller
Permutationen (≤ 6) exakt bestimmt.

## Struktur

```
.
├── src/
│   ├── model.py       # Welt, Lager, Zentrale, Entfernungen, Rundreisen-Optimierung
│   ├── messaging.py   # FIPA-ähnlicher Nachrichtenbus + Logging
│   ├── agents.py      # TA-Buchhaltung (marginale Gebote) + Ergebnis-/Energiebilanz
│   ├── cnp.py         # Variante a) Contract Net Protocol
│   ├── ecnp.py        # Variante b) erweitertes Contract Net Protocol
│   └── simulate.py    # CLI-Einstiegspunkt
├── config/
│   ├── world_balanced.json    # Experiment 1: Angebot == Nachfrage, Engpass am Eck-Lager
│   ├── world_overhang.json    # Experiment 2: Nachfrageüberhang -> Konventionalstrafe
│   └── world.schema.json      # JSON-Schema (Draft 2020-12)
├── experiments/
│   └── run_all.sh     # erzeugt die vier Logs (2 je Protokoll) für die Screencasts
├── report/
│   └── report.md      # Report-Gerüst (2–4 Seiten, -> PDF für ISIS)
└── materials/         # Original-Aufgabenblatt
```

## Ausführen

```bash
# beide Protokolle auf einer Welt, nur Ergebnis:
python3 src/simulate.py --world config/world_balanced.json --protocol both --quiet

# eCNP mit vollständigem Nachrichten-Log (für Screencast):
python3 src/simulate.py --world config/world_overhang.json --protocol ecnp

# alle vier Experiment-Logs erzeugen:
bash experiments/run_all.sh
```

Keine externen Abhängigkeiten – reines Python 3 (Standardbibliothek). Die
Schema‑Validierung der Welt‑JSON ist optional (`jsonschema`).

## Tests

```bash
python3 -m unittest discover -s tests          # schnelle Suite (<1s)
AOT_SLOW=1 python3 -m unittest discover -s tests   # inkl. exaktem B&B-Optimumsbeweis (~90s)
```

Die Suite enthält einen unabhängigen **Branch-&-Bound-Optimierer** (`tests/`),
der die exakte optimale Gesamtenergie berechnet und gegen die Protokollergebnisse
prüft (Vollprüfer), sowie Invariantentests (Bestandsgrenzen, Energiebilanz,
Determinismus) für CNP und eCNP auf beiden Welten. Auf allen getesteten
Instanzen erreichen **beide Protokolle das nachgewiesene Optimum**.

## Protokolle in Kürze

**CNP (a):** Jeder LA versteigert je Itemtyp seinen Bestand. TA bieten mit ihrer
*marginalen* Wegverlängerung; der LA vergibt an die günstigsten Gebote. Ein TA
bietet je Itemtyp nur einmal und stoppt nach erhaltenem Zuschlag. Weil ein
Zuschlag die Folgekosten verändert, laufen die Auktionen in mehreren Durchläufen
(Re‑Bidding), bis nichts mehr wechselt.

**eCNP (b):** Alle Auktionen starten parallel. Pro Runde: `cfp → propose →
vorläufiges accept/reject → definitives Gebot (+ cancel) → definitives accept`.
TA bestätigen je Itemtyp die attraktivste vorläufige Zusage und ziehen
konkurrierende Zusagen per `cancel` zurück; nach Absagen planen sie um und bieten
in den verbliebenen Instanzen neu.
