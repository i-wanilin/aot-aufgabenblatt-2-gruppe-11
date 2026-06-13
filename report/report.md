# Aufgabenblatt 2 – Kooperative Transportlogistik

> **Gruppennummer:** _____  ·  **Bearbeiter:** Ivan Ilin (_______)
> Kurs: Agententechnologien – Grundlagen und Anwendungen, TU Berlin, SoSe 2026
> *(Titelseite – Gruppennummer und alle Namen vor der Abgabe ergänzen.)*

---

## 1. Umsetzung der kooperativen Agenten und der beiden CNP‑Varianten

**Domäne und Repräsentation.** Implementiert wird ein verteiltes
Transportlogistik‑Szenario: Jede *Zentrale* wird durch einen **Transportagenten
(TA)** besetzt, jedes *Lager* durch einen **Lageragenten (LA)**. Wegen der
vollständigen Information (Hinweis 1) wird keine Grid‑Welt simuliert; Lager und
Zentralen sind nur über Koordinaten bekannt, die Entfernung ist die
Manhattan‑Koordinatendifferenz. Da ein Auftrag ≤ 3 Items umfasst, berechnet
`round_trip_cost` die kürzeste Rundreise durch vollständige Enumeration der ≤ 6
Permutationen über die (deduplizierten) Lagerkoordinaten. Die **Lösungsqualität**
ist der Gesamtenergieverbrauch = Σ Rundreise‑Weglängen aller TA + Σ
Konventionalstrafen (100 Energieeinheiten je nicht erfülltem Item).

**Gebote.** Ein TA bietet stets seine *marginale* Wegverlängerung
(`marginal_bid`): die Zunahme seiner aktuellen Rundreisekosten, wenn er das
betreffende Lager zusätzlich anfährt. Bereits (definitiv) kontraktierte Lager
fließen in die Basisroute ein, sodass spätere Gebote den schon geplanten Pfad
berücksichtigen (geforderte Konsistenz/„Pfad zu bereits kontraktierten Items").

**CNP (a).** Jeder LA versteigert je Itemtyp seinen Bestand per `cfp` an alle TA,
die diesen Typ noch benötigen. Die TA antworten mit ihrem marginalen Gebot, der
LA erteilt den günstigsten Geboten den Zuschlag (`accept`) und sagt den übrigen
ab (`reject`). Ein TA bietet je Itemtyp nur einmal und scheidet nach erhaltenem
Zuschlag aus der jeweiligen Instanz aus. Da ein Zuschlag die marginalen Kosten
der übrigen Items verändert, werden die Auktionen **iterativ in mehreren
Durchläufen** abgehalten, bis sich keine Zuteilung mehr ändert (Re‑Bidding /
Konvergenz). – *Code: `src/cnp.py`.*

**eCNP (b).** Alle Auktionen laufen **parallel** (jeder LA startet je Itemtyp eine
Protokollinstanz). Jede Runde durchläuft: `cfp` (Broadcast) → `propose`
(marginale Gebote) → **vorläufiges** `accept` an das beste Gebot bzw. `reject`
(inkl. bestem Gebot) an die übrigen → je Itemtyp **definitives Gebot** für die
attraktivste Zusage, `cancel` für konkurrierende Zusagen desselben Typs →
**definitives** `accept` an das beste definitive Gebot, womit die Instanz
terminiert (bei Restbestand wird n‑1 weitervergeben). Nach Zu‑/Absagen plant ein
TA um: seine marginalen Gebote der Folgerunde berücksichtigen die neu
kontraktierten Lager. – *Code: `src/ecnp.py`.*

## 2. Analyse der Simulationsverläufe (Screencasts)

> *Screencast‑Bezüge nach der Aufnahme eintragen, z.B. „CNP‑Experiment 1, ab
> Runde 2 im Log".*

**Experiment 1 – `balanced-9x9` (Angebot == Nachfrage, Engpass).** 4 Eck‑Lager mit
je 1×{A,B,C}, 4 Zentralen nahe der Mitte, jede mit Auftrag {A,B,C}. Angebot und
Nachfrage sind exakt ausgewogen, aber TA1 (1,6) und TA2 (4,9) präferieren beide
das nächstgelegene Lager LA3 (1,9) → **Konkurrenz um eine knappe Ressource**.

* Ergebnis (beide Protokolle): jeder TA übernimmt komplett *ein* Eck‑Lager; der
  Konflikt um LA3 wird zugunsten von TA1 (näher) aufgelöst, TA2 weicht auf LA4
  aus. **Gesamtenergie = 28,0** (optimal, keine Strafe).
* CNP: 90 Nachrichten · eCNP: 168 Nachrichten.
* *Im Screencast zu zeigen:* die ausgehandelte Konfliktauflösung um LA3 (vorläufige
  Zusage an TA1, Absage + Umplanung von TA2 auf LA4).

**Experiment 2 – `demand-overhang-9x9` (Nachfrageüberhang).** Wie Exp. 1, aber 5
Zentralen → Nachfrage (5/Typ) übersteigt Angebot (4/Typ). Eine optimale
vollständige Lösung ist **unmöglich** (Hinweis 6): genau 1 TA bleibt je Itemtyp
unversorgt.

* Ergebnis (beide Protokolle): TA1–TA4 erhalten je ein volles Lager, der zentrale
  TA5 (5,5) geht leer aus. Fahrenergie 28,0 + 3×100 Strafe → **Gesamtenergie =
  328,0**.
* CNP: 126 Nachrichten · eCNP: 204 Nachrichten.
* *Im Screencast zu zeigen:* TA5 verliert in jeder Instanz die Auktion (höhere
  Gebote) und endet mit `UNERFÜLLT: A,B,C` → Konventionalstrafe.

**Vergleich.** Auf beiden Instanzen erreichen CNP und eCNP dieselbe (optimale bzw.
straf‑minimale) Allokation; eCNP benötigt durch die parallelen Instanzen und die
zweistufige (vorläufig/definitiv) Verhandlung deutlich mehr Nachrichten. Der
Vorteil von eCNP liegt nicht in besserer Qualität *auf diesen Instanzen*, sondern
in der Robustheit gegen die Reihenfolge‑Abhängigkeit von CNP (siehe §3).

## 3. Zwei Schwächen des Contracting (in dieser Umsetzung) + Behebung

**Schwäche 1 – Gier/Reihenfolge‑Abhängigkeit ohne Backtracking (CNP).** CNP
vergibt Zuschläge endgültig und greedy je Auktion in fester Lager‑Reihenfolge.
Ein früh erteilter Zuschlag kann einen TA an ein Lager binden, das im
Gesamtbild ungünstig ist (lokal optimales, global suboptimales Commitment); ein
nachträgliches Aufbrechen ist nicht vorgesehen.
*Behebung:* (a) das in eCNP umgesetzte zweistufige Verfahren mit *vorläufigen*
Zusagen, das endgültige Bindungen aufschiebt und Umplanung erlaubt; (b) ein
*decommit*-Mechanismus mit Strafgebühr (Leveled‑Commitment‑Contracts), der einen
Vertrag gegen Ablöse auflösen kann, wenn sich später ein deutlich besseres
Gesamtarrangement ergibt.

**Schwäche 2 – Item‑weise Auktionen statt Bündel (beide).** Da je Itemtyp
einzeln versteigert wird, kann die Synergie „mehrere Items aus *einem* Lager"
nur indirekt über die marginalen Gebote (Folgegebot = 0 für dasselbe Lager)
entstehen und hängt von der Auktionsreihenfolge ab. Echte Komplementaritäten
werden nicht direkt ausgedrückt.
*Behebung:* **kombinatorische Auktionen** – TA bieten auf *Bündel* von
Items/Lagern, sodass ein LA komplementäre Items gemeinsam vergeben kann; bzw.
ein LA versteigert „alle meine Items als Paket" mit Paketgeboten. Das erhöht die
Lösungsqualität bei Synergien, allerdings auf Kosten der Berechnungs‑ und
Kommunikationskomplexität.

*(Optionale dritte Schwäche, falls Platz: hoher Nachrichten‑Overhead des eCNP
durch rundenweisen Broadcast – behebbar durch gezieltes `cfp` nur an plausible
Bieter bzw. Mindestgebote im `cfp`.)*

## 4. Möglicher alternativer Ansatz

> *Die Aufgabe verlangt „einen Absatz zu einer möglichen Umsetzung Ihres …" –
> Satz im Aufgabenblatt unvollständig; sinngemäß: eine alternative Umsetzung /
> Verbesserung. Vor Abgabe ggf. an der genauen Formulierung der Tutoren
> ausrichten.*

Statt der dezentralen Aushandlung ließe sich das Problem als **zentrale
Optimierung** formulieren: ein generalisiertes Zuordnungs‑/Mehrdepot‑VRP, das mit
Integer‑Programmierung exakt lösbar ist (Variablen `x[TA, Lager, Item]`,
Nebenbedingungen: jeder Bedarf gedeckt oder bestraft, Lagerbestände eingehalten;
Zielfunktion: Σ Rundreisekosten + Σ Strafen). Das liefert die garantiert optimale
untere Schranke als **Benchmark** für die agentenbasierten Verfahren, opfert aber
die Autonomie, Skalierbarkeit und Robustheit des Multiagentenansatzes. Ein
*hybrider* Weg wäre marktbasiert mit Ausgleich: eCNP zur schnellen, dezentralen
Erstlösung, gefolgt von lokalen, agenten‑initiierten *Swap/Decommit*-Verhandlungen
(Leveled‑Commitment), die paarweise Tauschvorteile realisieren und sich so der
IP‑Optimallösung annähern, ohne zentrale Planung.

---

### Anhang: Reproduktion

```bash
python3 src/simulate.py --world config/world_balanced.json --protocol both --quiet
python3 src/simulate.py --world config/world_overhang.json --protocol both --quiet
bash experiments/run_all.sh   # erzeugt experiments/logs/*.log
```
