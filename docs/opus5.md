# OPUS-5 — Ministry of Railways Working Paper

## A Clean-Sheet Design for a National Railway Block & Train Management System

> **Document class:** Internal working paper / design brainstorm
> **Author role assumed:** Officer, Ministry of Railways (Directorate of Operations & Safety)
> **Status:** Draft for inter-directorate circulation
> **Approach:** Clean-sheet. This paper deliberately makes **no reference to any existing
> codebase, prototype, or prior implementation**. It begins from the railway itself — the
> track, the train, the gangman, the controller — and reasons forward to a system.

---

## Table of Contents

- [Part A — Grounding](#part-a--grounding)
  - [A0. Why this paper exists](#a0-why-this-paper-exists)
  - [A1. Terms of reference and scope](#a1-terms-of-reference-and-scope)
  - [A2. Domain primer and glossary](#a2-domain-primer-and-glossary)
  - [A3. How a block actually happens today (as-is narrative)](#a3-how-a-block-actually-happens-today-as-is-narrative)
- [Part B — The Real World](#part-b--the-real-world)
  - [B1. Scenario catalogue — method](#b1-scenario-catalogue--method)
  - [B2. Scenarios: Demand and request origination](#b2-scenarios-demand-and-request-origination)
  - [B3. Scenarios: Planning and coordination failure](#b3-scenarios-planning-and-coordination-failure)
  - [B4. Scenarios: Execution on the ground](#b4-scenarios-execution-on-the-ground)
  - [B5. Scenarios: Safety and protection](#b5-scenarios-safety-and-protection)
  - [B6. Scenarios: Traffic and passenger impact](#b6-scenarios-traffic-and-passenger-impact)
  - [B7. Scenarios: Freight, terminals and revenue](#b7-scenarios-freight-terminals-and-revenue)
  - [B8. Scenarios: Electrical, S&T and specialist departments](#b8-scenarios-electrical-st-and-specialist-departments)
  - [B9. Scenarios: Resources, machines and manpower](#b9-scenarios-resources-machines-and-manpower)
  - [B10. Scenarios: Weather, environment and external factors](#b10-scenarios-weather-environment-and-external-factors)
  - [B11. Scenarios: Emergencies and unplanned events](#b11-scenarios-emergencies-and-unplanned-events)
  - [B12. Scenarios: Projects, construction and third parties](#b12-scenarios-projects-construction-and-third-parties)
  - [B13. Scenarios: Data, records and accountability](#b13-scenarios-data-records-and-accountability)
  - [B14. Scenarios: Organisational and human factors](#b14-scenarios-organisational-and-human-factors)
  - [B15. Scenario frequency and severity heat map](#b15-scenario-frequency-and-severity-heat-map)
- [Part C — Problem Statement](#part-c--problem-statement)
  - [C1. The consolidated problem statement](#c1-the-consolidated-problem-statement)
  - [C2. Sub-problems decomposed](#c2-sub-problems-decomposed)
  - [C3. What the system must solve (mandatory)](#c3-what-the-system-must-solve-mandatory)
  - [C4. What the system must NOT do (non-goals and red lines)](#c4-what-the-system-must-not-do-non-goals-and-red-lines)
  - [C5. Success metrics — how the Ministry will judge this](#c5-success-metrics--how-the-ministry-will-judge-this)
- [Part D — Stakeholders, Governance and Regulation](#part-d--stakeholders-governance-and-regulation)
- [Part E — Landscape Review of Existing Solutions](#part-e--landscape-review-of-existing-solutions)
- [Part F — Solution Design](#part-f--solution-design)
- [Part G — The Block Request: Complete Field Catalogue](#part-g--the-block-request-complete-field-catalogue)
- [Part H — Lifecycle, Rules and the Decision Engine](#part-h--lifecycle-rules-and-the-decision-engine)
- [Part I — Architecture and System Flow](#part-i--architecture-and-system-flow)
- [Part J — Frontend and Experience Design](#part-j--frontend-and-experience-design)
- [Part K — The Map](#part-k--the-map)
- [Part L — Operations, Assurance and Rollout](#part-l--operations-assurance-and-rollout)
- [Part M — Traceability: Scenario → Solution](#part-m--traceability-scenario--solution)
- [Part N — Risks, Open Questions and Further Work](#part-n--risks-open-questions-and-further-work)
- [Part O — Implementation Blueprint](#part-o--implementation-blueprint)
  - [O0. How to read this Part](#o0-how-to-read-this-part) · scope, and what it does **not** repeat
  - [O1–O3. Stance, stack, repository layout](#o1-implementation-stance)
  - [O4–O5. Data layer and event contracts](#o4-data-layer-implementation)
  - [O6–O9. Write path, rules, topology expansion, conflicts and impact](#o6-command-service--the-write-path)
  - [O10–O13. Read path, gateway, ETL, real-time transport](#o10-query-service--the-read-path)
  - [O14. Frontend implementation](#o14-frontend-implementation)
  - [**O15. The Dynamic Map — implementation**](#o15-the-dynamic-map--implementation)
  - [O16–O21. Field app, notifications, security, observability, testing, deployment](#o16-the-field-application)
  - [O22. Delivery sequence](#o22-delivery-sequence)
  - [**O23. What is needed from you — the requirements guide**](#o23-what-is-needed-from-you--the-requirements-guide)
  - [O24–O26. Assumptions, the optimiser boundary, closing](#o24-assumptions-register)

> **Note on Part O:** it deliberately contains **no optimisation-service implementation**.
> The optimiser is treated as an external module behind a frozen interface ([O25](#o25-the-optimisation-service-boundary)).

---

# Part A — Grounding

## A0. Why this paper exists

A railway is a machine made of steel, copper, concrete, timetables and people. Every part of
it wears out. Rails fatigue, ballast fouls, sleepers crack, girders corrode, overhead
contact wire abrades, signal cables age, points motors seize, bridges silt up, vegetation
encroaches. None of this maintenance can be done while trains are running over the asset.

Therefore the railway must periodically **stop being a railway** on a chosen stretch of
track for a chosen period of time. That deliberate, planned, protected suspension is a
**block**. It is the single most contested resource in the entire organisation, because:

- The **Engineering department** needs it to keep the track from killing people.
- The **Electrical/Traction department** needs it to keep the wire from killing people.
- The **Signal & Telecom department** needs it to keep the signalling from lying to drivers.
- The **Operating department** loses capacity, punctuality and revenue every minute of it.
- The **Commercial department** answers to passengers whose trains were cancelled.
- The **Safety department** answers to the Commissioner of Railway Safety when it goes wrong.

Blocks are therefore negotiated, not simply granted. And today, across most of the network,
that negotiation happens by telephone, WhatsApp, spreadsheet, printed register and personal
relationship. The institutional memory of _why_ a particular block was granted, moved or
refused lives in one Section Controller's head and evaporates when he goes off duty.

This paper argues that block planning is a **scheduling and constraint-satisfaction problem
with a safety-critical human approval layer**, and that it is now tractable with software.
It sets out, from scratch, what such a system must know, must decide, must show and must
never do.

---

## A1. Terms of reference and scope

### A1.1 In scope

1. The complete lifecycle of a **block** — from the moment a department perceives a need,
   through request, scrutiny, conflict detection, optimisation, approval, notification,
   execution, hand-back, and post-block reporting.
2. The complete lifecycle of a **train movement** insofar as it interacts with blocks —
   timetabled paths, actual running, delay attribution, diversion, regulation, cancellation.
3. **Situational awareness**: a live and time-travellable geographic/schematic picture of
   where blocks are, where trains are, and where they conflict.
4. **Resource awareness**: track machines, tower wagons, gangs, materials, road-rail
   vehicles, tools and their availability windows.
5. **Decision support**: automated conflict detection, opportunity detection (bundling),
   feasibility checking, impact quantification, and ranked plan proposals.
6. **Accountability**: an immutable record of who asked, who approved, what happened, and
   what it cost in train-minutes.
7. **Multi-level rollup**: Section → Division → Zone → Board, with each level seeing the
   right granularity.

### A1.2 Out of scope (this paper)

- Interlocking logic, signalling design, or anything that issues a movement authority to a
  train. This system **advises**; it never commands a signal.
- Rolling stock maintenance scheduling (shed/depot workshops) except where it consumes a
  block or a line.
- Ticketing, reservation, freight rating, payroll, and general ERP.
- Track geometry recording science (the system consumes TRC/OMS outputs; it does not
  produce them).
- Autonomous approval. See [C4](#c4-what-the-system-must-not-do-non-goals-and-red-lines).

### A1.3 Design horizon

- **Year 0–1:** One pilot division, planned blocks only, advisory optimiser.
- **Year 1–3:** Zone-wide, emergency blocks, mobile field app, live train feed integration.
- **Year 3–5:** National, ML-based duration and delay prediction, corridor-level annual
  possession strategy.

---

## A2. Domain primer and glossary

A shared vocabulary is a precondition for a shared system. Terms below are used with
precise meaning throughout this paper.

### A2.1 Infrastructure

| Term                              | Definition                                                                                                                       |
| --------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| **Zone**                          | Highest territorial administrative unit of the railway.                                                                          |
| **Division**                      | Sub-unit of a Zone; the practical unit of operational control.                                                                   |
| **Section**                       | A stretch of line between two designated points, the unit of block working.                                                      |
| **Block Section**                 | The portion of line between two consecutive block stations; only one train may occupy it at a time under absolute block working. |
| **Station / Block Station**       | A location where a train may be received, dispatched or held, with signals controlling entry/exit.                               |
| **Yard**                          | A collection of lines for reception, dispatch, sorting or stabling.                                                              |
| **Line**                          | A single running track. Named e.g. UP Main, DN Main, UP Loop, Third Line, Goods Avoiding Line.                                   |
| **Track / Track Segment**         | The atomic maintainable and blockable unit of line in this system. Has two endpoints and a chainage extent.                      |
| **Chainage / Kilometrage**        | Linear position along a route, expressed in km + m from a datum. The railway's native coordinate system.                         |
| **Turnout / Points / Switch**     | Track apparatus allowing a train to move from one line to another.                                                               |
| **Crossover**                     | A pair of turnouts connecting two parallel lines; critical for single-line working during a block.                               |
| **Diamond Crossing**              | Track intersection at grade.                                                                                                     |
| **Level Crossing (LC)**           | Road-rail intersection at grade, manned or unmanned.                                                                             |
| **OHE / OCS**                     | Overhead Equipment / Overhead Contact System — the 25 kV AC catenary.                                                            |
| **Neutral Section**               | A short de-energised gap between traction supply phases.                                                                         |
| **Elementary Section (Traction)** | The smallest independently isolatable and earthable portion of OHE. Defines the granularity of a power block.                    |
| **TSS / SP / SSP**                | Traction Sub-Station / Sectioning Post / Sub-Sectioning Post — where OHE is switched.                                            |
| **Signal**                        | A fixed lineside or cab indication authorising or prohibiting movement.                                                          |
| **Interlocking / Panel / EI**     | The apparatus that ensures signals and points are set to mutually safe positions.                                                |
| **Axle Counter / Track Circuit**  | Train-detection devices.                                                                                                         |
| **Bridge (Major/Minor/ROB/RUB)**  | Structures carrying rail over water/road or road over/under rail.                                                                |
| **Asset**                         | Any maintainable physical item with an identity, location, and condition.                                                        |

### A2.2 Operations

| Term                                      | Definition                                                                           |
| ----------------------------------------- | ------------------------------------------------------------------------------------ |
| **Path**                                  | A reserved sequence of (location, time) pairs through the network for one train.     |
| **Timetable / WTT**                       | Working Timetable — the master plan of paths.                                        |
| **Rake**                                  | A formed set of coaches or wagons.                                                   |
| **Link**                                  | The rostered cyclic assignment of a rake or crew to successive services.             |
| **Section Controller**                    | The officer who, in real time, regulates train movement over a section.              |
| **Control Office**                        | The divisional nerve centre where controllers sit.                                   |
| **Caution Order**                         | A written instruction to a driver to observe a speed restriction.                    |
| **TSR / PSR**                             | Temporary / Permanent Speed Restriction.                                             |
| **Line Clear**                            | Authority for a train to enter a block section.                                      |
| **Regulation**                            | Real-time decisions on precedence, crossing, looping and holding of trains.          |
| **Detention**                             | Time a train is held beyond its booked timing; the primary unit of operational cost. |
| **Punctuality**                           | % of trains arriving within a defined tolerance.                                     |
| **Diversion**                             | Running a train over an alternative route.                                           |
| **Short-termination / Short-origination** | Ending or starting a service short of its booked terminal.                           |
| **Single Line Working (SLW)**             | Working both directions over one line of a double line, when the other is blocked.   |
| **Complete Traffic Block**                | No trains at all over the affected line(s).                                          |

### A2.3 Blocks and protection

| Term                                           | Definition                                                                                                                          |
| ---------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| **Traffic Block**                              | Line withdrawn from traffic for work.                                                                                               |
| **Power Block / Traction Block**               | OHE de-energised and earthed for work near live conductors.                                                                         |
| **Combined Block**                             | Traffic + power block together — the common case for OHE work.                                                                      |
| **Corridor Block**                             | A long, pre-declared, regularly recurring block window over a corridor, published in advance, into which many departments bid.      |
| **Mega Block**                                 | A large planned block, typically weekend, over a suburban or high-density section.                                                  |
| **Rolling Block**                              | A block that moves progressively along the line with the work front.                                                                |
| **Line Block vs Track Block**                  | Whether the whole line or a defined track segment is withdrawn.                                                                     |
| **Caution/Speed Restriction in lieu of Block** | Work done under restriction rather than full withdrawal.                                                                            |
| **Protection**                                 | The physical and procedural measures (detonators, banner flags, hand signals, disconnection, clamping) that make the worksite safe. |
| **Disconnection**                              | Formal isolation of signalling apparatus from the interlocking.                                                                     |
| **Permit to Work (PTW)**                       | Formal written authority handed to the person in charge of the work.                                                                |
| **Earthing**                                   | Physical connection of de-energised OHE to earth; the only proof that a power block is real.                                        |
| **Hand-back**                                  | Formal return of the line/OHE to the operating department, certifying fitness for traffic.                                          |
| **Overrun**                                    | Work continuing past the sanctioned block end time.                                                                                 |
| **Cancellation / Non-utilisation**             | A sanctioned block that was not used.                                                                                               |

### A2.4 Roles

| Term                                  | Definition                                                  |
| ------------------------------------- | ----------------------------------------------------------- |
| **PWI / SSE(P.Way)**                  | Permanent Way Inspector — responsible for track.            |
| **SSE/JE (OHE)**                      | Overhead equipment supervisor.                              |
| **SSE/JE (S&T)**                      | Signal & telecom supervisor.                                |
| **TPC**                               | Traction Power Controller — switches and earths OHE.        |
| **SCOR / Section Controller**         | Regulates traffic.                                          |
| **Dy. CHC / CHC**                     | Chief Controller, supervises the control office.            |
| **DOM / Sr.DOM**                      | Divisional Operations Manager.                              |
| **DRM / ADRM**                        | Divisional Railway Manager — the divisional head.           |
| **CRS**                               | Commissioner of Railway Safety — the independent regulator. |
| **Site-in-Charge / Nominated Person** | The competent person to whom the block is handed.           |

---

## A3. How a block actually happens today (as-is narrative)

To design the future we must be honest about the present. The following is a composite,
realistic account of a single OHE mast replacement block.

```
T-45 days   SSE/OHE notices mast 412/7 is corroded at base during foot inspection.
            Records it in a paper inspection register. Mentions it to the ADEE verbally.

T-30 days   ADEE compiles a list of OHE works for the monthly block demand meeting.
            The list is typed into a Word document, printed, and carried to the meeting.

T-21 days   Monthly Block Demand Meeting at Divisional HQ.
            Engineering, Electrical, S&T each read out their demands.
            Operating pushes back: "We cannot give you Sunday 10:00-14:00, there is a
            special train." Negotiation is verbal. Nobody records the reason.
            A block is tentatively agreed for a Sunday, 4 hours.

T-20 days   Nobody notices that the Engineering department has ALSO asked for a block on
            the SAME kilometre, on a different Sunday, for through-packing.
            Two blocks will be taken where one would have done.

T-14 days   Operating prepares the traffic implications. Two trains to be regulated,
            one goods to be diverted. This is worked out on paper.

T-7 days    Block is "confirmed" via a circular. The circular is emailed as a scanned PDF.
            Half the recipients do not open it.

T-2 days    A rail fracture occurs elsewhere. An emergency block is taken. The planned
            block is now at risk because the Tower Wagon is committed elsewhere.
            Nobody re-checks resource availability against the planned block.

T-1 day     Section Controller of the incoming shift is not aware of the block.
            Handover register mentions it in one line.

T-0 09:50   Block requested on line. Controller says "10 minutes, one more train."
T-0 10:15   Block granted. 15 minutes lost. Nobody records why.
T-0 10:20   TPC issues power block. Earthing done at 10:30.
T-0 10:35   Tower wagon arrives — late, because it was released late from the previous site.
T-0 10:40   Work starts. Effective work time so far: 0 minutes out of 50 elapsed.
T-0 13:45   Work is not finished. Site-in-charge asks for 45 minutes extension.
T-0 13:50   Controller has a Mail Express approaching. Refuses. Work is left incomplete.
T-0 14:20   Hand-back at 14:20 instead of 14:00. Two trains detained 18 and 24 minutes.
T-0 14:25   The job is NOT complete. A fresh block will be required. Nobody records that
            the root cause was late tower wagon placement.

T+1 day     Detention is attributed in the control chart to "Engg Block". No further detail.
T+30 days   The same mast is still not replaced. It appears again on the next month's list,
            with no memory that it failed once for a resource reason.
```

**Every single failure in that narrative is an information failure, not a competence
failure.** No individual acted unreasonably. The system had no shared memory, no shared
picture, and no ability to see the whole board at once.

That is the gap this design addresses.

---

# Part B — The Real World

## B1. Scenario catalogue — method

Each scenario is recorded in a fixed structure so it can be traced to a requirement and,
later, to a test case.

```
S-nn  <Title>
  Situation   — what actually happens on the ground
  Mechanism   — why it happens; the information or coordination failure beneath it
  Cost        — the measurable consequence (safety, punctuality, money, trust)
  Frequency   — Rare | Occasional | Frequent | Continuous
  Severity    — Low | Medium | High | Critical
  Requirement — SR-nnn the system must satisfy to address it
```

Scenarios are deliberately **over-collected**. It is easier to defer a scenario than to
discover one after go-live. Ninety-four scenarios follow.

---

## B2. Scenarios: Demand and request origination

### S-01 — The need exists but is never formally requested

- **Situation:** An inspector sees a defect, notes it in a field register, and intends to
  raise it at the next monthly meeting. He is transferred, goes on leave, or simply
  forgets. The defect is never converted into a block demand.
- **Mechanism:** The demand originates in an unstructured artefact (a paper register, a
  memory, a WhatsApp photograph) that has no lifecycle and no owner after handover.
- **Cost:** Deferred maintenance accumulates into a safety liability. Eventually the asset
  fails and becomes an emergency, which is 5–20× more disruptive than planned work.
- **Frequency:** Frequent · **Severity:** High
- **Requirement:** SR-001 — every observed defect must be capturable at the point of
  observation, from the field, on a phone, in under 60 seconds, and must then exist as a
  tracked object with an owner and an ageing clock.

### S-02 — Demand raised too late for meaningful planning

- **Situation:** A department submits a block demand three days before it is needed.
  Operating cannot re-plan paths, cannot issue traffic notices, and cannot inform
  passengers. The demand is refused; the department feels obstructed.
- **Mechanism:** No enforced lead-time discipline; no visibility of the planning calendar
  and its cut-off dates.
- **Cost:** Either the work does not happen, or it happens with disproportionate traffic
  damage.
- **Frequency:** Frequent · **Severity:** Medium
- **Requirement:** SR-002 — the system must publish a rolling planning calendar with
  explicit cut-off dates per block class, must show remaining lead time when a request is
  drafted, and must classify late requests distinctly rather than silently accepting them.

### S-03 — The same work is requested twice by two people

- **Situation:** A JE and an SSE independently raise demands for the same turnout renewal.
  Both appear on the list. Two blocks are sanctioned.
- **Mechanism:** No canonical asset identity in the request; work is described in prose
  ("points at Panjim end") rather than referencing an asset ID.
- **Cost:** A wasted block window that another department needed.
- **Frequency:** Occasional · **Severity:** Medium
- **Requirement:** SR-003 — every request must bind to structured asset/segment
  identifiers, and the system must detect and surface near-duplicate demands at entry time.

### S-04 — Work described so vaguely that it cannot be planned

- **Situation:** A demand reads "OHE attention, 3 hours, Section A–B". Operating has no
  idea which line, which kilometre, whether traffic can pass on the adjacent line, or
  whether a power block is needed.
- **Mechanism:** Free-text request forms with no mandatory structured fields.
- **Cost:** Multiple rounds of clarification; planning delayed; conservative (over-wide)
  blocks granted "to be safe", wasting capacity.
- **Frequency:** Continuous · **Severity:** High
- **Requirement:** SR-004 — a structured, department-specific, validated request schema
  (see [Part G](#part-g--the-block-request-complete-field-catalogue)) with hard mandatory
  fields; free text permitted only as supplementary notes.

### S-05 — Requester does not know what is already planned

- **Situation:** A department asks for a block on a date when a much larger corridor block
  is already sanctioned 5 km away — a window into which their work could have been folded
  at zero extra traffic cost.
- **Mechanism:** No shared forward calendar visible to requesting departments.
- **Cost:** A whole extra block taken; capacity destroyed for no reason.
- **Frequency:** Frequent · **Severity:** High
- **Requirement:** SR-005 — a read-only forward block calendar and map must be visible to
  every requesting user before they raise a demand, with a "join an existing window"
  affordance.

### S-06 — Estimated duration is guessed, not derived

- **Situation:** "4 hours" is written because 4 hours is what is always written. The job
  actually needs 2 hours 20 minutes, or 6 hours.
- **Mechanism:** No historical record of how long comparable jobs actually took.
- **Cost:** Systematic over-asking destroys capacity; systematic under-asking causes
  overruns and incomplete work.
- **Frequency:** Continuous · **Severity:** High
- **Requirement:** SR-006 — the system must retain actual durations of completed blocks by
  work type, asset class, quantum and resource set, and must offer a data-derived duration
  suggestion with a confidence band at request time.

### S-07 — Quantum of work not stated

- **Situation:** "Rail renewal" — 1 rail or 40 rails? The duration and resource
  implications differ by an order of magnitude.
- **Mechanism:** Work type captured without quantity.
- **Cost:** Wrong duration, wrong resources, overrun.
- **Frequency:** Frequent · **Severity:** Medium
- **Requirement:** SR-007 — every work item must carry a quantity and unit
  (rails, sleepers, metres, spans, masts, points, joints, cables).

### S-08 — Dependencies between works are invisible

- **Situation:** S&T must alter a track circuit _after_ Engineering shifts the track.
  Both departments request blocks independently, on dates in the wrong order.
- **Mechanism:** No representation of inter-request precedence.
- **Cost:** Rework, a third block, or work abandoned mid-way.
- **Frequency:** Occasional · **Severity:** High
- **Requirement:** SR-008 — requests must support typed dependency links
  (`must_precede`, `must_follow`, `must_be_simultaneous`, `must_not_overlap`), and the
  planner must enforce them.

### S-09 — No differentiation between "must do now" and "would like to do"

- **Situation:** A safety-critical rail fracture repair and a cosmetic painting job carry
  equal weight in the demand list. Sequencing becomes political rather than rational.
- **Mechanism:** No structured criticality/consequence-of-deferral field.
- **Cost:** Safety-critical work displaced by well-argued but low-value work.
- **Frequency:** Frequent · **Severity:** Critical
- **Requirement:** SR-009 — mandatory criticality classification with defined,
  auditable criteria, plus a consequence-of-deferral statement, both feeding the optimiser
  objective as weights, not as free choice.

### S-10 — Recurring maintenance is re-requested manually every cycle

- **Situation:** Monthly OHE patrolling blocks, quarterly bridge inspections, annual
  ultrasonic testing — each re-typed from scratch each cycle, sometimes forgotten.
- **Mechanism:** No recurring-demand template.
- **Cost:** Administrative waste; missed statutory inspections.
- **Frequency:** Continuous · **Severity:** Medium
- **Requirement:** SR-010 — recurring demand templates with automatic instantiation,
  statutory-due-date tracking, and escalation when a statutory window is at risk.

---

## B3. Scenarios: Planning and coordination failure

### S-11 — Two departments block the same track on different days

- **Situation:** Engineering blocks UP Main on Sunday for packing; S&T blocks the same
  stretch on Wednesday for cable work. Both could have shared Sunday.
- **Mechanism:** Nobody is looking at the whole demand set spatially and temporally at once.
- **Cost:** Double the traffic disruption for the same maintenance output.
- **Frequency:** Continuous · **Severity:** Critical
- **Requirement:** SR-011 — automated spatio-temporal overlap and adjacency detection
  across ALL open demands, with a bundling proposal ("these 3 demands can share one window").

### S-12 — Overlapping requests processed first-come-first-served

- **Situation:** Dept A asks 10:00–12:00 on Track 1. Dept B asks 11:00–14:00 on Track 1.
  A is approved; B is refused and told to re-apply. B's work slips a month.
- **Mechanism:** Requests evaluated in isolation, in arrival order.
- **Cost:** One 4-hour combined block becomes two blocks in different months, or work slips.
- **Frequency:** Frequent · **Severity:** High
- **Requirement:** SR-012 — the planner must evaluate the **set** of demands over a
  horizon, not each demand alone; merge candidates must be computed, costed and proposed.

### S-13 — Effects on adjacent and dependent tracks not understood

- **Situation:** Blocking the UP Main also makes the UP Loop unusable because the only
  crossover is inside the worksite. Nobody realises until the day.
- **Mechanism:** No machine-readable topology; dependency is folklore.
- **Cost:** Trains planned onto a line that turns out to be unreachable. Chaos on the day.
- **Frequency:** Frequent · **Severity:** High
- **Requirement:** SR-013 — a topology graph (nodes, edges, turnouts, connectivity) must
  exist, and blocking any element must automatically compute the **derived unavailability
  set** — other elements rendered unusable or capacity-reduced.

### S-14 — Traffic impact quantified only after approval, if at all

- **Situation:** A block is approved, then Operating discovers it clashes with three
  premium trains and a scheduled freight path. The block is then withdrawn.
- **Mechanism:** Impact analysis is manual and happens downstream of the decision.
- **Cost:** Wasted planning effort; late cancellations; loss of credibility with
  departments whose blocks keep getting withdrawn.
- **Frequency:** Frequent · **Severity:** High
- **Requirement:** SR-014 — impact must be computed **before** decision: affected trains,
  estimated aggregate detention minutes, cancellations, diversions, freight tonnage
  delayed — displayed on the approval screen.

### S-15 — No visibility of what the neighbouring division is doing

- **Situation:** Two adjacent divisions block adjacent sections of the same corridor on the
  same day in opposite halves of the route. Through traffic has no viable path at all.
- **Mechanism:** Planning is divisional; corridors are inter-divisional.
- **Cost:** Corridor effectively closed without anyone deciding to close it.
- **Frequency:** Occasional · **Severity:** Critical
- **Requirement:** SR-015 — corridor-level (cross-division, cross-zone) visibility and
  conflict detection; a corridor view that ignores administrative boundaries.

### S-16 — The plan exists in five inconsistent copies

- **Situation:** A spreadsheet with the Sr.DOM, a register in the control office, a PDF
  circular, a WhatsApp group message and a verbal understanding. They differ.
- **Mechanism:** No single system of record.
- **Cost:** Disputes on the day; blocks taken that were cancelled; blocks missed that were
  live.
- **Frequency:** Continuous · **Severity:** Critical
- **Requirement:** SR-016 — one authoritative system of record; all artefacts (notices,
  circulars, charts) generated **from** it, never maintained beside it.

### S-17 — Late change to the plan does not reach everyone

- **Situation:** A block is preponed by two hours at 22:00 the previous night. The gang
  supervisor is not told; he arrives at the original time.
- **Mechanism:** Change communication is manual and best-effort.
- **Cost:** Block granted with no one to use it; capacity destroyed and work not done.
- **Frequency:** Frequent · **Severity:** High
- **Requirement:** SR-017 — change events must fan out automatically to every stakeholder
  of the affected block through multiple channels, with delivery and acknowledgement
  tracking.

### S-18 — Acknowledgement is assumed, not verified

- **Situation:** A circular is emailed. Nobody confirms receipt. On the day, three of eight
  stakeholders were unaware.
- **Mechanism:** One-way broadcast communication.
- **Cost:** Coordination failure on the day.
- **Frequency:** Continuous · **Severity:** Medium
- **Requirement:** SR-018 — explicit acknowledgement workflow: named recipients, read
  receipts, outstanding-acknowledgement dashboard, escalation on non-acknowledgement.

### S-19 — Resource conflicts discovered on the day

- **Situation:** Two blocks 60 km apart both assume the same tamping machine.
- **Mechanism:** Resources not modelled or reserved as part of block approval.
- **Cost:** One block becomes useless; hand-back early; work not done.
- **Frequency:** Frequent · **Severity:** High
- **Requirement:** SR-019 — machines, tower wagons, road-rail vehicles, gangs, competent
  persons and key materials must be modelled as bookable resources with travel/positioning
  time, and a block cannot be approved with an unresolved resource double-booking.

### S-20 — Machine positioning time ignored

- **Situation:** A tamper is booked for a 06:00 block but is stabled 90 minutes away and
  must itself path over a busy section.
- **Mechanism:** Resources treated as instantaneously available.
- **Cost:** 90 minutes of a 180-minute block lost.
- **Frequency:** Frequent · **Severity:** High
- **Requirement:** SR-020 — resource model must include current location, mobilisation
  time, and a required path; the block plan must include machine movement as an explicit
  scheduled activity.

### S-21 — Competent-person availability not checked

- **Situation:** The block requires a certified welder / authorised OHE person / nominated
  Site-in-Charge. That person is on leave or already committed.
- **Mechanism:** Competency and rostering data not linked to block planning.
- **Cost:** Block cannot legally start.
- **Frequency:** Occasional · **Severity:** High
- **Requirement:** SR-021 — competency register integration; required-competency checklist
  per work type; validation of named nominated persons against roster and certification
  expiry.

### S-22 — Material not on site

- **Situation:** Block starts; the rails/sleepers/masts have not been unloaded at site.
- **Mechanism:** Material logistics planned separately from block planning.
- **Cost:** Total loss of the window.
- **Frequency:** Frequent · **Severity:** High
- **Requirement:** SR-022 — pre-block readiness checklist with mandatory material-at-site
  confirmation at T-24h, and automatic flagging of blocks whose readiness is unconfirmed.

### S-23 — No consideration of consecutive-day fatigue or gang capacity

- **Situation:** The same gang is assigned night blocks five nights running.
- **Mechanism:** No aggregate view of human resource loading.
- **Cost:** Fatigue → error → safety incident.
- **Frequency:** Occasional · **Severity:** Critical
- **Requirement:** SR-023 — human resource loading rules (max consecutive nights, minimum
  rest) enforced as hard constraints during planning.

### S-24 — Seasonal and event constraints ignored

- **Situation:** A block is planned during a major festival rush, an examination special
  period, or the monsoon patrolling season.
- **Mechanism:** Calendar constraints exist only in senior officers' heads.
- **Cost:** Block refused late, or granted and causing severe passenger hardship.
- **Frequency:** Frequent · **Severity:** Medium
- **Requirement:** SR-024 — a network calendar of embargo periods, festival rushes,
  examination specials, VIP movements and seasonal restrictions, applied automatically as
  constraints/penalties.

### S-25 — Plans are not comparable — no notion of "better"

- **Situation:** Two alternative block plans are proposed. There is no agreed way to say
  which is better; the decision is made by seniority.
- **Mechanism:** No objective function; no quantified trade-off.
- **Cost:** Sub-optimal choices, and no way to defend the choice afterwards.
- **Frequency:** Continuous · **Severity:** High
- **Requirement:** SR-025 — an explicit, configurable, published objective function
  (detention minutes, cancellations, maintenance backlog reduction, block-hour efficiency,
  safety-criticality weighting) with the score of each option shown side by side.

---

## B4. Scenarios: Execution on the ground

### S-26 — The last-train delay: block granted late

- **Situation:** Block due 10:00. Controller holds it for "one more train". Granted 10:22.
- **Mechanism:** Real-time trade-off made without visibility of the downstream cost of the
  shortened block.
- **Cost:** 22 minutes of a 180-minute window lost — 12% of the maintenance output.
- **Frequency:** Continuous · **Severity:** High
- **Requirement:** SR-026 — record actual grant time against sanctioned time, with a
  mandatory structured reason code; report "block grant punctuality" as a first-class KPI
  per section and per controller shift.

### S-27 — Late arrival of the work party

- **Situation:** Block granted at 10:00; gang reaches site at 10:25.
- **Mechanism:** No pre-block readiness confirmation; travel time to site not planned.
- **Cost:** Window loss.
- **Frequency:** Frequent · **Severity:** High
- **Requirement:** SR-027 — mandatory "party at site" confirmation from the field app
  before the block is formally started; time-stamped; and pre-block mobilisation modelled.

### S-28 — Protection takes longer than assumed

- **Situation:** Detonators, banner flags, disconnection and earthing consume 25 minutes at
  each end of the block.
- **Mechanism:** Protection time not modelled; block duration quoted as work time only.
- **Cost:** Effective work time far below sanctioned block time.
- **Frequency:** Continuous · **Severity:** High
- **Requirement:** SR-028 — block duration must be decomposed into
  `protection_setup + effective_work + testing + protection_removal + handback_check`,
  each estimated and each recorded actual.

### S-29 — Overrun beyond sanctioned time

- **Situation:** Work is 80% done at the sanctioned end. Extension requested by phone.
- **Mechanism:** Ad-hoc verbal extension process; controller has no view of what extension
  would cost in detention.
- **Cost:** Either uncontrolled overrun (severe traffic damage) or abandoned incomplete
  work (wasted block).
- **Frequency:** Frequent · **Severity:** High
- **Requirement:** SR-029 — in-system extension request from the field with progress %,
  reason and requested duration; instant impact computation (which trains, how many
  minutes); explicit approve/refuse decision recorded with reason.

### S-30 — Early completion not exploited

- **Situation:** Work finishes 40 minutes early. Line is handed back but the controller has
  already regulated trains on the assumption of the full block. The 40 minutes are wasted.
- **Mechanism:** Hand-back information not propagated in real time to regulation decisions.
- **Cost:** Avoidable detention.
- **Frequency:** Frequent · **Severity:** Medium
- **Requirement:** SR-030 — real-time hand-back event, pushed instantly to control,
  with automatic re-computation of the regulation picture and a prompt to release held
  trains.

### S-31 — Block taken but not used at all

- **Situation:** Machine failed / material missing / rain. The block is granted and then
  surrendered.
- **Mechanism:** No readiness gate; no cancellation deadline.
- **Cost:** Capacity destroyed for nothing; another department could have used it.
- **Frequency:** Frequent · **Severity:** High
- **Requirement:** SR-031 — a **standby/reserve demand queue**: when a block is
  surrendered, the system immediately proposes the highest-value alternative work that can
  use the same window and is ready.

### S-32 — Partial work completion not recorded

- **Situation:** 60% of the rails were renewed. The record says "block taken, 3 hours".
  Next month, the balance is planned as if it were a fresh job.
- **Mechanism:** No output/quantum reporting against block.
- **Cost:** Loss of continuity; wrong duration estimates for follow-up work.
- **Frequency:** Frequent · **Severity:** Medium
- **Requirement:** SR-032 — mandatory post-block output reporting: quantity achieved vs
  planned, balance carried forward, automatically generating a follow-up demand.

### S-33 — Hand-back certification informal

- **Situation:** Line handed back verbally. No record of who certified fitness for traffic,
  at what speed, with what restriction.
- **Mechanism:** Paper memo at best.
- **Cost:** Safety exposure; if a derailment follows, no evidence of due process.
- **Frequency:** Frequent · **Severity:** Critical
- **Requirement:** SR-033 — structured digital hand-back certificate: named certifier,
  timestamp, fitness declaration, speed restriction imposed (if any) with value, extent,
  duration and review date, and automatic issue of the corresponding caution order data.

### S-34 — Speed restriction imposed after work is forgotten

- **Situation:** A 30 kmph restriction imposed after track work remains in force for months
  because nobody tracked its review.
- **Mechanism:** Restrictions live in caution orders, not in a managed register.
- **Cost:** Permanent, unnecessary loss of section capacity; cumulative delay to every train.
- **Frequency:** Frequent · **Severity:** High
- **Requirement:** SR-034 — every restriction is a first-class object with imposition
  reason, extent, value, expected relaxation date, owner, and an ageing dashboard that
  escalates overdue relaxations.

### S-35 — Rolling block loses track of the actual work front

- **Situation:** A rolling block progresses along the section; control's picture of where
  the work front is becomes stale.
- **Mechanism:** No live positional reporting of the worksite.
- **Cost:** Trains cautioned over the wrong extent; or unsafe assumptions.
- **Frequency:** Occasional · **Severity:** High
- **Requirement:** SR-035 — worksite position reporting from the field (chainage or GPS),
  with the block extent updating live on the map.

### S-36 — Multiple worksites inside one block are not tracked separately

- **Situation:** One corridor block hosts six different work parties. One overruns; the
  others are ready to hand back. Hand-back becomes all-or-nothing.
- **Mechanism:** Block modelled as a single monolithic entity.
- **Cost:** The whole block is extended for one party's delay.
- **Frequency:** Occasional · **Severity:** Medium
- **Requirement:** SR-036 — a block may contain multiple **work packages**, each with its
  own party, extent, progress and readiness; partial hand-back supported where safe.

---

## B5. Scenarios: Safety and protection

### S-37 — Work party on track without a valid block

- **Situation:** A gang goes on track believing a block is in force. It was cancelled.
- **Mechanism:** Verbal communication; no positive confirmation channel to the field.
- **Cost:** **Fatality risk. This is the single worst outcome in the domain.**
- **Frequency:** Rare · **Severity:** Critical
- **Requirement:** SR-037 — the field app must display an unambiguous, positively-refreshed
  block state; the block must be _granted to a named person_ who must acknowledge; the app
  must alarm loudly if the block state changes or if connectivity is lost beyond a
  threshold, defaulting to "assume NOT protected".

### S-38 — Power block believed live but OHE not actually earthed

- **Situation:** Traffic block granted; staff assume OHE is dead. Earthing was not completed.
- **Mechanism:** Traffic block and power block are separate processes with separate actors.
- **Cost:** Electrocution.
- **Frequency:** Rare · **Severity:** Critical
- **Requirement:** SR-038 — traffic block and power block must be modelled as **distinct,
  separately confirmed states** on the same block object; work near live OHE cannot be
  marked "started" until the TPC-confirmed earthing event is recorded; the field app must
  display both states as separate, explicit indicators.

### S-39 — Adjacent line not protected; staff struck by a train on the open line

- **Situation:** UP line blocked; DN line open. A worker strays.
- **Mechanism:** Adjacent-line risk not formally assessed per worksite.
- **Cost:** Fatality.
- **Frequency:** Occasional · **Severity:** Critical
- **Requirement:** SR-039 — mandatory adjacent-line risk assessment field per block, with
  options (adjacent line open / cautioned / blocked / physical barrier / lookout posted),
  approval rules that escalate when adjacent line remains open, and visible display of
  adjacent-line status on the field app and map.

### S-40 — Disconnection of signalling not properly recorded or restored

- **Situation:** S&T disconnects apparatus for work; restoration is incomplete or
  unrecorded.
- **Mechanism:** Disconnection notices are paper.
- **Cost:** Signalling irregularity — potentially a wrong-side failure.
- **Frequency:** Occasional · **Severity:** Critical
- **Requirement:** SR-040 — digital disconnection/reconnection register bound to the block,
  with mandatory paired entries; a block cannot reach `handed_back` with an open
  disconnection.

### S-41 — Competency of the person in charge not verified at the moment of grant

- **Situation:** The block is handed to whoever is present.
- **Mechanism:** No verification step.
- **Cost:** Unqualified supervision of a safety-critical activity.
- **Frequency:** Occasional · **Severity:** Critical
- **Requirement:** SR-041 — block grant requires selection of a named nominated person
  whose competency for that work class is valid on that date; expired competency blocks
  the grant.

### S-42 — Detonator/flag protection not actually placed

- **Situation:** Protection is assumed rather than confirmed.
- **Mechanism:** No confirmation step.
- **Cost:** Safety exposure.
- **Frequency:** Occasional · **Severity:** Critical
- **Requirement:** SR-042 — protection checklist with per-item confirmation, timestamped,
  from the field, before "work started" is permitted.

### S-43 — Emergency arises during the block and cannot be communicated

- **Situation:** A worker is injured; the site has no mobile signal.
- **Mechanism:** Sole reliance on cellular telephony.
- **Cost:** Delayed medical response.
- **Frequency:** Rare · **Severity:** Critical
- **Requirement:** SR-043 — the field app must have an offline-capable emergency escalation
  path (queued alert, control-office phone fallback, and integration with existing railway
  telephone/VHF procedures documented in the block's safety plan).

### S-44 — Lessons from an incident are not fed back into planning

- **Situation:** An incident enquiry recommends "adjacent line to be blocked for this type
  of work". The recommendation lives in a report.
- **Mechanism:** Safety learning is not encoded as a rule.
- **Cost:** Recurrence.
- **Frequency:** Frequent · **Severity:** Critical
- **Requirement:** SR-044 — a **rules engine** where safety learnings become machine-
  enforced constraints, versioned, attributable to their source recommendation, and
  reportable ("show me all rules derived from enquiry X").

---

## B6. Scenarios: Traffic and passenger impact

### S-45 — Trains cancelled with insufficient notice to passengers

- **Situation:** Block confirmed at T-3 days; cancellations published at T-1; passengers
  who booked months earlier are stranded.
- **Mechanism:** Block decision cycle is decoupled from the passenger information cycle.
- **Cost:** Reputational damage; refunds; political consequence.
- **Frequency:** Frequent · **Severity:** High
- **Requirement:** SR-045 — block classes must have defined minimum notice periods tied to
  passenger impact; the system must compute affected services and emit a
  passenger-information payload as soon as a block reaches `approved`.

### S-46 — Detention not attributed correctly

- **Situation:** A train is delayed by a block, then further delayed by a signal failure.
  All the delay is attributed to "Engineering".
- **Mechanism:** Manual, coarse attribution in the control chart.
- **Cost:** Departments distrust the data; the data cannot be used to improve.
- **Frequency:** Continuous · **Severity:** High
- **Requirement:** SR-046 — structured delay attribution linking each detention segment to
  a cause object (block ID, failure ID, external cause), enabling defensible departmental
  reporting.

### S-47 — Diversion route itself has a block

- **Situation:** Trains diverted via an alternate route which is also under block.
- **Mechanism:** Diversion planning without network-wide block visibility.
- **Cost:** Trains stranded; severe cascading delay.
- **Frequency:** Occasional · **Severity:** Critical
- **Requirement:** SR-047 — routing/diversion proposals must be validated against the
  block picture on the diversion route, including neighbouring divisions.

### S-48 — Single line working introduced without capacity analysis

- **Situation:** One line blocked; the other worked in both directions. Section capacity
  falls by ~60% but the same number of trains is offered.
- **Mechanism:** No capacity model.
- **Cost:** Compounding delay; trains queued into adjacent sections.
- **Frequency:** Frequent · **Severity:** High
- **Requirement:** SR-048 — capacity model per section under normal / SLW / partial-block
  configurations; the impact engine must apply the correct configuration and warn when
  offered traffic exceeds available capacity.

### S-49 — Knock-on delay beyond the blocked section not considered

- **Situation:** Delay caused by a block propagates through rake links and crew links for
  the next 18 hours across the network.
- **Mechanism:** Impact assessed only within the section and only during the block.
- **Cost:** Massive under-estimation of true block cost.
- **Frequency:** Continuous · **Severity:** High
- **Requirement:** SR-049 — impact model must consider primary delay **and** propagated
  delay via rake links, crew links and platform occupancy, over a configurable horizon.

### S-50 — Premium and time-sensitive services not protected

- **Situation:** A block is placed across the path of the network's flagship service.
- **Mechanism:** No service-priority model.
- **Cost:** High-visibility punctuality failure.
- **Frequency:** Frequent · **Severity:** High
- **Requirement:** SR-050 — service priority classes with configurable protection windows;
  the optimiser penalises or hard-forbids impact on protected services.

### S-51 — Suburban peak destroyed by a poorly timed block

- **Situation:** A suburban section block extends into the morning peak.
- **Mechanism:** Peak windows not modelled as constraints.
- **Cost:** Tens of thousands of commuters affected.
- **Frequency:** Occasional · **Severity:** Critical
- **Requirement:** SR-051 — hard "no block" windows configurable per section
  (peak hours, defined dates), enforced as inviolable constraints requiring an explicit
  senior override with recorded justification.

### S-52 — Passenger-facing information is inconsistent with the operational plan

- **Situation:** Station displays, the app and announcements disagree.
- **Mechanism:** Multiple downstream consumers fed manually.
- **Cost:** Passenger confusion, crowding, complaints.
- **Frequency:** Frequent · **Severity:** Medium
- **Requirement:** SR-052 — one machine-readable "service disruption" output stream
  consumed by every passenger information channel.

---

## B7. Scenarios: Freight, terminals and revenue

### S-53 — Freight loading/unloading windows collide with blocks

- **Situation:** A block prevents placement of a rake at a siding on the day a customer's
  plant is scheduled to load.
- **Mechanism:** Freight terminal schedules not visible to block planning.
- **Cost:** Demurrage, customer dissatisfaction, revenue loss, possible modal shift to road.
- **Frequency:** Frequent · **Severity:** High
- **Requirement:** SR-053 — freight terminal and siding placement schedules modelled as
  constraints; the impact engine must quantify affected tonnage and demurrage exposure.

### S-054 — Block causes yard congestion and knock-on stabling failure

- **Situation:** Trains held outside a yard fill reception lines; the yard locks up.
- **Mechanism:** Yard capacity not modelled.
- **Cost:** Section blocked by queued trains; recovery takes many hours.
- **Frequency:** Occasional · **Severity:** High
- **Requirement:** SR-054 — yard/loop holding capacity modelled; the impact engine must
  warn when projected holds exceed available stabling.

### S-55 — Perishable and time-critical consignments not prioritised

- **Situation:** A block delays a refrigerated or livestock consignment.
- **Mechanism:** No consignment sensitivity attribute in planning.
- **Cost:** Spoilage claims; welfare issues.
- **Frequency:** Occasional · **Severity:** Medium
- **Requirement:** SR-055 — consignment sensitivity flags propagated into the impact model
  and shown to the approver.

### S-56 — Revenue cost of a block never calculated

- **Situation:** The organisation cannot say what a block costs.
- **Mechanism:** No costing model.
- **Cost:** Impossible to make rational trade-offs or to justify investment in faster
  methods (e.g. mechanised gangs that halve block time).
- **Frequency:** Continuous · **Severity:** High
- **Requirement:** SR-056 — configurable cost model translating detention minutes,
  cancellations, diversions and freight delay into indicative monetary cost, reported per
  block and aggregated per department, section and period.

---

## B8. Scenarios: Electrical, S&T and specialist departments

### S-57 — Power block granularity mismatched to the work

- **Situation:** Work needs one span de-energised; the smallest isolatable elementary
  section is 12 km, taking out four stations.
- **Mechanism:** Elementary section topology not represented; planners guess.
- **Cost:** Grossly over-wide isolation; unnecessary disruption.
- **Frequency:** Frequent · **Severity:** High
- **Requirement:** SR-057 — model the traction network as its own graph (feeders,
  TSS/SP/SSP, elementary sections) and compute the **minimal isolation set** for a given
  worksite, showing the operator exactly what will go dead.

### S-58 — Traffic block and power block requested separately and granted at different times

- **Situation:** Traffic block from 10:00; power block from 10:40.
- **Mechanism:** Two departments, two processes.
- **Cost:** 40 minutes lost; or unsafe assumption made.
- **Frequency:** Frequent · **Severity:** High
- **Requirement:** SR-058 — a single combined-block object with linked sub-blocks that are
  planned together, granted together, and displayed together.

### S-59 — S&T work needs the block only for a short verification window

- **Situation:** Cable laying can proceed alongside traffic; only the final connection and
  testing needs a block. The whole activity is requested as a block.
- **Mechanism:** Work not decomposed into "block-required" and "non-block" phases.
- **Cost:** Hours of unnecessary line withdrawal.
- **Frequency:** Frequent · **Severity:** High
- **Requirement:** SR-059 — work packages must declare which phases require a block; the
  request captures only the block-required duration, with preparatory phases scheduled
  outside.

### S-60 — Testing and commissioning windows underestimated

- **Situation:** New interlocking commissioning needs a long, non-negotiable window;
  it is planned like routine work.
- **Mechanism:** No distinct handling for commissioning-class events.
- **Cost:** Failed commissioning; reversion; repeat mega-block.
- **Frequency:** Occasional · **Severity:** Critical
- **Requirement:** SR-060 — a distinct **commissioning/major-works** block class with its
  own approval chain, contingency/reversion plan field, rehearsal record and go/no-go gate.

### S-61 — No reversion plan when major works fail

- **Situation:** A commissioning fails at 04:00; there is no documented way back to the
  previous state before traffic resumes.
- **Mechanism:** Contingency planning informal.
- **Cost:** Extended closure; emergency timetable.
- **Frequency:** Rare · **Severity:** Critical
- **Requirement:** SR-061 — mandatory reversion plan, point-of-no-return time, and a
  go/no-go decision checkpoint recorded in the system for major-works blocks.

---

## B9. Scenarios: Resources, machines and manpower

### S-62 — Track machine utilisation is very low

- **Situation:** An expensive machine works a fraction of its available hours because
  blocks are short, late and fragmented.
- **Mechanism:** Machine scheduling and block scheduling are separate optimisations.
- **Cost:** Enormous capital under-utilisation.
- **Frequency:** Continuous · **Severity:** High
- **Requirement:** SR-062 — joint optimisation of machine deployment and block windows;
  machine-centric view showing a machine's forward itinerary and idle gaps, with
  suggestions to fill them.

### S-63 — Machine breakdown mid-block

- **Situation:** The tamper fails at the halfway point.
- **Mechanism:** No contingency; no rapid re-planning.
- **Cost:** Partial work, and possibly a line that cannot be handed back at full speed.
- **Frequency:** Occasional · **Severity:** High
- **Requirement:** SR-063 — in-block incident reporting that triggers immediate
  re-computation of hand-back time, restriction implications and consequent traffic advice.

### S-64 — Gangs idle because no block was available

- **Situation:** Staff report for a night block that was never sanctioned.
- **Mechanism:** Sanction status not visible to the gang.
- **Cost:** Wasted manpower cost and morale.
- **Frequency:** Frequent · **Severity:** Medium
- **Requirement:** SR-064 — a personal "my blocks" view for every field user showing
  confirmed, provisional and cancelled assignments with clear status.

### S-65 — Contractor availability and contractual windows not modelled

- **Situation:** A contractor is mobilised for a window that then moves; contractual
  idle-charge claims follow.
- **Mechanism:** Contract terms not linked to block scheduling.
- **Cost:** Financial claims; disputes.
- **Frequency:** Occasional · **Severity:** Medium
- **Requirement:** SR-065 — contract entities with mobilisation notice periods and
  idle-charge terms; warnings when a change breaches a contractual notice period.

---

## B10. Scenarios: Weather, environment and external factors

### S-66 — Rain washes out a block that was known to be weather-sensitive

- **Situation:** Concreting/welding/painting planned in monsoon; block granted; work
  impossible.
- **Mechanism:** Weather sensitivity not an attribute; forecast not consulted systematically.
- **Cost:** Capacity destroyed.
- **Frequency:** Frequent · **Severity:** Medium
- **Requirement:** SR-066 — weather-sensitivity attribute per work type; automated forecast
  check at T-72h/T-24h; risk flag and a suggested standby alternative from the reserve
  queue.

### S-67 — Extreme heat/cold restrictions interact with block planning

- **Situation:** Rail temperature restrictions and welding constraints conflict with the
  chosen window.
- **Mechanism:** Environmental constraints not modelled.
- **Cost:** Work done outside safe parameters, or abandoned.
- **Frequency:** Occasional · **Severity:** High
- **Requirement:** SR-067 — environmental constraint rules (rail temperature ranges,
  wind limits for tower wagon/OHE work, visibility limits) applied as feasibility checks.

### S-68 — Flooding, cyclone or landslide invalidates the entire plan

- **Situation:** A weather event closes a route; all planned blocks are irrelevant and
  emergency restoration takes over.
- **Mechanism:** No mass re-planning capability.
- **Cost:** Manual chaos; planned work forgotten during recovery.
- **Frequency:** Occasional · **Severity:** High
- **Requirement:** SR-068 — bulk re-planning: declare a disruption, auto-suspend affected
  blocks, preserve them in a re-planning queue, and support rapid emergency-restoration
  block creation.

### S-69 — Public events, agitations, or law-and-order situations

- **Situation:** An agitation blocks the line; or a public event forbids night noise.
- **Mechanism:** External calendar not modelled.
- **Cost:** Blocks planned into impossible windows.
- **Frequency:** Occasional · **Severity:** Medium
- **Requirement:** SR-069 — external constraint calendar with sources (district
  administration advisories, event permissions, noise ordinances).

---

## B11. Scenarios: Emergencies and unplanned events

### S-70 — Rail fracture requires an immediate block

- **Situation:** A fracture is detected; traffic must be stopped now.
- **Mechanism:** Emergency handled entirely by phone; system records nothing until later.
- **Cost:** The single most disruptive event type; no analytics; no learning.
- **Frequency:** Frequent · **Severity:** Critical
- **Requirement:** SR-070 — an **emergency block** path: raiseable in under 30 seconds from
  a phone with minimum fields, immediately visible to control and on the map, formalised
  retrospectively without blocking the operational response.

### S-71 — Emergency block collides with a planned block

- **Situation:** An emergency consumes the resources and the window of a planned block.
- **Mechanism:** No automatic reconciliation.
- **Cost:** Planned work silently lost.
- **Frequency:** Frequent · **Severity:** High
- **Requirement:** SR-071 — when an emergency is declared, automatically identify affected
  planned blocks, mark them at-risk, notify their owners, and place them in the re-planning
  queue.

### S-72 — Asset failure (points, signal, OHE) requires unplanned attention

- **Situation:** A failure occurs; attention is given under traffic pressure with minimal
  protection time.
- **Mechanism:** Failure management and block management are separate systems.
- **Cost:** Repeated failures; unsafe expedients.
- **Frequency:** Continuous · **Severity:** High
- **Requirement:** SR-072 — failure events must be first-class objects that can spawn
  emergency or planned blocks, and must link failure history to the asset for reliability
  analytics.

### S-73 — Accident/derailment restoration

- **Situation:** A derailment requires a long unplanned closure, cranes, ART/ARME.
- **Mechanism:** Managed entirely outside any planning system.
- **Cost:** No situational picture for senior management; poor resource coordination.
- **Frequency:** Rare · **Severity:** Critical
- **Requirement:** SR-073 — an incident/restoration mode: a special block class with
  resource mobilisation tracking, live situation reporting, and a senior-management
  situation dashboard.

### S-74 — Security alerts and bomb threats

- **Situation:** Line stopped for security reasons.
- **Mechanism:** Ad-hoc.
- **Cost:** Disruption without record.
- **Frequency:** Occasional · **Severity:** High
- **Requirement:** SR-074 — a security-cause block class with restricted visibility and
  a separate approval chain.

---

## B12. Scenarios: Projects, construction and third parties

### S-75 — Doubling/electrification project needs recurring long blocks

- **Situation:** A construction project requires dozens of blocks over two years.
- **Mechanism:** Each requested individually; no programme-level view.
- **Cost:** Project delay; unpredictable access; contractor claims.
- **Frequency:** Continuous · **Severity:** High
- **Requirement:** SR-075 — a **programme** object: a project owns a portfolio of block
  demands with a programme schedule, milestone linkage, and progress tracking against the
  access plan.

### S-76 — Third-party works (road authority, utility, pipeline) affect the railway

- **Situation:** A road overbridge contractor needs to swing a girder over the line.
- **Mechanism:** External party has no channel into railway planning.
- **Cost:** Unsafe improvisation, or endless delay.
- **Frequency:** Occasional · **Severity:** High
- **Requirement:** SR-076 — an external-party request portal with sponsorship by a railway
  officer, mandatory method statement and risk assessment attachments, and a distinct
  approval chain.

### S-77 — Contractor safety competence not verified

- **Situation:** Contractor staff on track without railway safety training.
- **Mechanism:** No competency register for contractor personnel.
- **Cost:** Fatality risk.
- **Frequency:** Occasional · **Severity:** Critical
- **Requirement:** SR-077 — contractor personnel competency records, validity checks at
  block grant, and refusal when invalid.

### S-78 — Project block conflicts with maintenance block on the same asset

- **Situation:** Both need the same track on the same weekend.
- **Mechanism:** Project and maintenance planning are separate.
- **Cost:** One is displaced arbitrarily.
- **Frequency:** Frequent · **Severity:** Medium
- **Requirement:** SR-078 — a single demand pool: project and maintenance demands compete
  and combine within the same optimisation.

---

## B13. Scenarios: Data, records and accountability

### S-79 — Nobody can reconstruct why a decision was made

- **Situation:** An audit asks why a block was granted on a date that caused a major delay.
  No record of the reasoning exists.
- **Mechanism:** Decisions are verbal.
- **Cost:** Indefensible position; officers exposed; no institutional learning.
- **Frequency:** Continuous · **Severity:** Critical
- **Requirement:** SR-079 — immutable decision record: options considered, scores, the
  option chosen, the deciding officer, timestamp, and a mandatory justification when the
  chosen option is not the top-ranked one.

### S-80 — Statistics are compiled manually and are unreliable

- **Situation:** Monthly block statistics are typed from registers; numbers disagree
  between departments.
- **Mechanism:** Manual compilation.
- **Cost:** Management flies blind; departments argue about facts instead of solutions.
- **Frequency:** Continuous · **Severity:** High
- **Requirement:** SR-080 — all statistics derived automatically from operational records;
  a single figure of record; drill-down from any aggregate to the underlying blocks.

### S-81 — Data captured but never analysed

- **Situation:** Registers are filled diligently and never read again.
- **Mechanism:** No analytical layer.
- **Cost:** No improvement loop.
- **Frequency:** Continuous · **Severity:** High
- **Requirement:** SR-081 — an analytics layer with standing questions answered
  automatically (block efficiency trend, top overrun causes, worst grant-punctuality
  sections, restriction ageing, backlog by asset class).

### S-82 — Handover between shifts loses context

- **Situation:** Incoming controller does not know the state of ongoing and upcoming blocks.
- **Mechanism:** Verbal handover plus a one-line register entry.
- **Cost:** Errors in the first hours of every shift.
- **Frequency:** Continuous · **Severity:** High
- **Requirement:** SR-082 — an auto-generated shift handover pack: live blocks, blocks due
  this shift, at-risk items, open extensions, outstanding acknowledgements, restrictions
  imposed.

### S-83 — Data quality degrades because entry is burdensome

- **Situation:** Staff enter the minimum to get past the form; fields are filled with
  "NA", "as per rules", "-".
- **Mechanism:** Forms designed for the database, not for the user.
- **Cost:** Garbage in; the whole analytical edifice collapses.
- **Frequency:** Continuous · **Severity:** Critical
- **Requirement:** SR-083 — progressive disclosure, smart defaults, template-based
  pre-fill, asset-driven auto-population, and a hard rule that **no field is mandatory
  unless it changes a decision**.

---

## B14. Scenarios: Organisational and human factors

### S-84 — Departmental mistrust: "Operating never gives us blocks"

- **Situation:** Engineering believes Operating obstructs; Operating believes Engineering
  wastes windows.
- **Mechanism:** Neither side sees the other's data.
- **Cost:** Adversarial culture; escalation to senior officers for routine matters.
- **Frequency:** Continuous · **Severity:** High
- **Requirement:** SR-084 — shared, symmetric transparency: sanction rates, utilisation
  rates, grant punctuality and overrun rates visible to **both** sides, with no hidden
  ledgers.

### S-85 — Escalation is personal, not procedural

- **Situation:** A stuck request is resolved by phoning a senior officer.
- **Mechanism:** No SLA, no defined escalation ladder.
- **Cost:** Unfair outcomes; senior time wasted; unrecorded decisions.
- **Frequency:** Frequent · **Severity:** Medium
- **Requirement:** SR-085 — SLA clocks per workflow stage with automatic, recorded
  escalation up a defined ladder.

### S-86 — Approval bottleneck on one officer

- **Situation:** All approvals wait for one person who is travelling.
- **Mechanism:** No delegation model.
- **Cost:** Planning paralysis.
- **Frequency:** Frequent · **Severity:** Medium
- **Requirement:** SR-086 — role-based approval with formal, time-bounded, recorded
  delegation.

### S-87 — Transfers destroy institutional knowledge

- **Situation:** A new SSE inherits a section with no record of pending works, chronic
  defects or past decisions.
- **Mechanism:** Knowledge is personal.
- **Cost:** Months of reduced effectiveness after every transfer.
- **Frequency:** Continuous · **Severity:** High
- **Requirement:** SR-087 — asset- and section-centric history views that survive personnel
  changes; a "section dossier" available to any authorised incoming officer.

### S-88 — Staff resist a system that adds work without giving benefit

- **Situation:** A new system is mandated; staff maintain the old register in parallel.
- **Mechanism:** Value not delivered back to the person doing the data entry.
- **Cost:** Dual records; worse than before.
- **Frequency:** Continuous · **Severity:** Critical
- **Requirement:** SR-088 — every user role must receive concrete, immediate value from the
  system (the field user gets his sanction status and his safety indicator; the controller
  gets his impact picture; the officer gets his dashboard). Nothing may be collected that
  is not visibly used.

### S-89 — Low connectivity in the field

- **Situation:** Worksites are in cuttings, tunnels, remote sections with no data signal.
- **Mechanism:** Assumption of always-on connectivity.
- **Cost:** System unusable exactly where it matters most.
- **Frequency:** Continuous · **Severity:** Critical
- **Requirement:** SR-089 — offline-first field application with local persistence, queued
  synchronisation, conflict resolution, explicit staleness indication, and **fail-safe**
  behaviour for safety-relevant state.

### S-90 — Language and literacy diversity

- **Situation:** Field staff are more comfortable in regional languages.
- **Mechanism:** English-only interfaces.
- **Cost:** Errors, avoidance, reliance on intermediaries.
- **Frequency:** Continuous · **Severity:** High
- **Requirement:** SR-090 — multilingual UI, icon-led design for safety-critical
  indications, large touch targets, high contrast for outdoor sunlight readability.

### S-91 — Training and turnover

- **Situation:** New users arrive constantly; nobody is trained.
- **Mechanism:** No embedded guidance.
- **Cost:** Data quality and adoption failure.
- **Frequency:** Continuous · **Severity:** Medium
- **Requirement:** SR-091 — in-app contextual guidance, a sandbox/simulation environment
  for training, and template-driven flows that make the correct path the easy path.

### S-92 — Gaming the system

- **Situation:** Departments inflate criticality or duration to secure windows.
- **Mechanism:** No feedback loop between claimed and actual.
- **Cost:** Optimiser input corrupted; the whole model degrades.
- **Frequency:** Frequent · **Severity:** High
- **Requirement:** SR-092 — claimed-vs-actual tracking per requesting unit
  (asked 4h / used 2h, claimed critical / deferred twice), surfaced in departmental
  scorecards, and used to calibrate future estimates.

### S-93 — Over-reliance on the optimiser

- **Situation:** Staff accept the machine's proposal without scrutiny.
- **Mechanism:** Opaque recommendations presented as answers.
- **Cost:** Automation complacency — a recognised safety hazard.
- **Frequency:** Occasional · **Severity:** Critical
- **Requirement:** SR-093 — every recommendation must be **explainable**: which constraints
  bound it, which alternatives were rejected and why, and what would change the answer.
  The UI must present it as a proposal requiring judgement, never as a verdict.

### S-94 — System becomes a single point of failure

- **Situation:** The system is down; nobody knows what blocks are in force.
- **Mechanism:** Digitisation without degraded-mode design.
- **Cost:** Operational paralysis or unsafe improvisation.
- **Frequency:** Rare · **Severity:** Critical
- **Requirement:** SR-094 — mandatory degraded-mode operation: continuously refreshed
  offline artefacts (printable block sheets, local caches), documented manual fallback
  procedures, and a defined recovery/reconciliation process.

---

## B15. Scenario frequency and severity heat map

```
             │ Rare        │ Occasional      │ Frequent            │ Continuous
─────────────┼─────────────┼─────────────────┼─────────────────────┼──────────────────────
 CRITICAL    │ S-37 S-38   │ S-15 S-23 S-39  │ S-11 S-33 S-44 S-70 │ S-09 S-16 S-79 S-83
             │ S-43 S-61   │ S-40 S-41 S-42  │                     │ S-88 S-89
             │ S-73 S-94   │ S-47 S-51 S-60  │                     │
             │             │ S-93            │                     │
─────────────┼─────────────┼─────────────────┼─────────────────────┼──────────────────────
 HIGH        │             │ S-08 S-13 S-35  │ S-01 S-05 S-12 S-14 │ S-04 S-06 S-25 S-26
             │             │ S-54 S-55 S-63  │ S-17 S-19 S-20 S-22 │ S-28 S-46 S-49 S-56
             │             │ S-67 S-68 S-72  │ S-27 S-29 S-31 S-34 │ S-62 S-72 S-80 S-81
             │             │ S-74 S-76 S-77  │ S-45 S-48 S-50 S-53 │ S-82 S-84 S-87 S-90
             │             │                 │ S-57 S-58 S-59 S-64 │
             │             │                 │ S-71 S-75 S-92      │
─────────────┼─────────────┼─────────────────┼─────────────────────┼──────────────────────
 MEDIUM      │             │ S-03 S-21 S-24  │ S-02 S-07 S-30 S-32 │ S-10 S-18 S-91
             │             │ S-65 S-69 S-78  │ S-52 S-64 S-66 S-85 │
             │             │                 │ S-86                │
```

**Reading of the map.** The mass of the problem sits in the _Frequent × High_ and
_Continuous × Critical_ cells. These are not dramatic accidents; they are daily,
grinding, information-coordination failures. That is precisely the class of problem that
software addresses well — and it is the reason a block-planning system is a higher-return
safety and capacity investment than most physical works of comparable cost.

---

# Part C — Problem Statement

## C1. The consolidated problem statement

> **The railway cannot see its own maintenance demand, its own network topology, its own
> resources and its own traffic in one picture at one time. Consequently it allocates its
> scarcest and most safety-critical resource — protected access to the track — by verbal
> negotiation, personal memory and incomplete paper records.**
>
> The result is threefold:
>
> 1. **Capacity is destroyed.** Blocks are granted late, started late, over-scoped,
>    duplicated, surrendered unused, and overrun. A large fraction of every sanctioned
>    block-hour produces no maintenance output at all.
> 2. **Maintenance is deferred.** Work that cannot obtain a window is postponed, and
>    deferred maintenance converts into asset failure, which converts into emergency
>    blocks — the most disruptive and least safe form of access.
> 3. **Safety depends on individuals rather than on system design.** Protection,
>    isolation, competency and hand-back are enforced by discipline and habit rather than
>    by an enforced, recorded, verifiable process.
>
> **The problem to be solved is therefore not "build a form to request blocks".**
> It is: _give the railway a single, shared, live, machine-reasoned picture of demand,
> network, resources, traffic and risk, so that access to the track is allocated
> deliberately, safely, transparently and optimally — and so that every decision, every
> minute and every outcome is recorded and learned from._

## C2. Sub-problems decomposed

| #   | Sub-problem                | One-line statement                                                                                                      |
| --- | -------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| P1  | **Demand capture**         | Maintenance need is not reliably converted into a structured, tracked, well-specified demand.                           |
| P2  | **Network representation** | The railway has no machine-readable model of its own topology, so consequences of blocking anything cannot be computed. |
| P3  | **Conflict detection**     | Overlapping, adjacent and dependent demands are not detected systematically.                                            |
| P4  | **Opportunity detection**  | Combinable work is not identified, so the same window is bought twice.                                                  |
| P5  | **Impact quantification**  | The traffic, passenger, freight and financial cost of a candidate block is not computed before the decision.            |
| P6  | **Resource feasibility**   | Machines, people, materials and competencies are not checked against the window.                                        |
| P7  | **Decision support**       | There is no ranked, explained set of options, and no objective definition of "better".                                  |
| P8  | **Communication**          | Approved plans and subsequent changes do not reliably reach everyone who must act on them.                              |
| P9  | **Execution discipline**   | Grant, start, protection, progress, extension and hand-back are not measured, so they cannot be improved.               |
| P10 | **Safety assurance**       | Protection, isolation and competency are not systematically verified and recorded.                                      |
| P11 | **Situational awareness**  | No live spatial picture of blocks, trains and restrictions exists for controllers and management.                       |
| P12 | **Memory and learning**    | Actuals are not captured, so estimates never improve and mistakes recur.                                                |
| P13 | **Accountability**         | Decisions cannot be reconstructed or defended.                                                                          |
| P14 | **Resilience**             | Emergencies invalidate plans and there is no systematic re-planning.                                                    |

## C3. What the system must solve (mandatory)

The system is accepted only if it demonstrably delivers all fourteen capability blocks
below. Each maps to the sub-problems above and to the SR-nnn requirements in Part B.

**M1 — Structured demand intake.** Any authorised user, from any location including the
field, can raise a block demand that is bound to real assets and real geometry, validated
at entry, and tracked through an explicit lifecycle with an owner and an ageing clock.
_(P1; SR-001..010, 083, 089, 090)_

**M2 — A machine-readable network model.** Nodes, edges, lines, turnouts, chainages,
stations, elementary traction sections, signalling elements, level crossings and their
connectivity — sufficient to compute what else becomes unusable when any element is
blocked. _(P2; SR-013, 057)_

**M3 — Automated conflict and dependency detection.** Spatial, temporal, resource, topological
and rule-based conflicts detected across the entire open demand set and the approved plan,
continuously, not at a monthly meeting. _(P3; SR-011..013, 019, 047, 078)_

**M4 — Opportunity and bundling engine ("shadow finding").** Identification of demands that
can share a window, a corridor, a protection setup or an isolation, with a costed proposal
for the merged block and full traceability to the contributing demands.
_(P4; SR-005, 011, 012, 058)_

**M5 — Impact quantification before decision.** Affected trains, detention minutes,
cancellations, diversions, freight tonnage and indicative cost — computed for every
candidate option and shown on the approval screen. _(P5; SR-014, 045..056)_

**M6 — Resource and readiness management.** Machines, gangs, competent persons, materials,
contractors and their mobilisation times modelled, reserved, and verified through a
pre-block readiness gate. _(P6; SR-019..023, 062..065, 077)_

**M7 — Optimisation and ranked recommendation.** A published objective function, hard
safety constraints that cannot be violated, soft constraints that are penalised, and a
ranked, explained set of feasible plans. _(P7; SR-025, 093)_

**M8 — Workflow, approval and escalation.** An explicit lifecycle, role-based multi-level
approval, SLA clocks, recorded delegation, and automatic escalation.
_(P8, P13; SR-085, 086)_

**M9 — Assured communication.** Automatic, multi-channel, acknowledged distribution of
plans and changes to every stakeholder, with an outstanding-acknowledgement dashboard.
_(P8; SR-017, 018, 052, 064)_

**M10 — Execution management.** Digital grant, start, protection checklist, progress,
extension request with instant impact, incident reporting, hand-back certification and
output recording — all timestamped. _(P9; SR-026..036, 063)_

**M11 — Safety enforcement.** Separate confirmed states for traffic block and power block,
adjacent-line risk declaration, disconnection register, competency validation, protection
checklist, and fail-safe field behaviour. _(P10; SR-037..044, 077, 089, 094)_

**M12 — Live spatial and temporal situational picture.** A map showing active blocks,
planned blocks, restrictions, train positions and conflicts, with a time slider to view
past, present and future states. _(P11; SR-035, 070, 073, 082)_

**M13 — Analytics, learning and feedback.** Actual durations, grant punctuality, utilisation,
overrun causes, restriction ageing, backlog by asset class, departmental scorecards, and
data-derived duration estimates. _(P12; SR-006, 032, 080..084, 092)_

**M14 — Resilience and degraded operation.** Emergency block path, disruption declaration
with bulk re-planning, offline field operation, printable fallback artefacts and a defined
recovery procedure. _(P14; SR-068, 070..074, 089, 094)_

## C4. What the system must NOT do (non-goals and red lines)

These are stated as firmly as the requirements, because a system that violates them will
be — and should be — rejected by the safety organisation.

1. **It must never issue a movement authority.** It does not set signals, does not operate
   points, does not grant line clear, and does not replace the interlocking or the block
   instrument. It is an information and planning system.
2. **It must never be the sole guarantee of a worker's safety.** Physical protection —
   detonators, banner flags, earthing, clamping, disconnection — remains primary. The
   system records and prompts; it does not protect. All field UI must state this.
3. **It must never auto-approve a block.** The optimiser proposes; an accountable human
   with the requisite authority disposes. Automation is advisory by design.
4. **It must never silently overwrite a human decision.** Any system-initiated change to an
   approved plan must be surfaced as a proposal requiring confirmation.
5. **It must not become an unaudited parallel rule book.** Every enforced constraint must
   cite its source authority (rule, circular, enquiry recommendation) and be versioned.
6. **It must not require connectivity to keep a worker informed of his protection status.**
   Offline behaviour must be fail-safe and explicit about staleness.
7. **It must not collect data that no one uses.** Every field must earn its place by
   changing a decision, a calculation, or a report.
8. **It must not create a new single point of failure.** Degraded-mode artefacts and
   procedures are a delivery requirement, not an afterthought.
9. **It must not present recommendations without explanation.** Opacity breeds either
   blind compliance or total rejection; both are failures.
10. **It must not lock the railway into a vendor or a schema it cannot evolve.** Open,
    versioned, documented interfaces.

## C5. Success metrics — how the Ministry will judge this

### C5.1 Primary outcome metrics

| Metric                       | Definition                                            | Baseline         | Target (24 months)    |
| ---------------------------- | ----------------------------------------------------- | ---------------- | --------------------- |
| **Block utilisation ratio**  | effective work time ÷ sanctioned block time           | measure at pilot | +25 percentage points |
| **Grant punctuality**        | % of blocks granted within 5 min of sanctioned start  | measure          | ≥ 85%                 |
| **Overrun rate**             | % of blocks exceeding sanctioned end                  | measure          | ≤ 10%                 |
| **Non-utilisation rate**     | % of sanctioned blocks not used                       | measure          | ≤ 3%                  |
| **Bundling ratio**           | % of demands executed inside a shared/corridor window | ~0               | ≥ 40%                 |
| **Detention per block-hour** | train-minutes lost per sanctioned block-hour          | measure          | −20%                  |
| **Maintenance backlog**      | overdue statutory + condition-based works outstanding | measure          | −30%                  |
| **Emergency block share**    | emergency block-hours ÷ total block-hours             | measure          | −25%                  |
| **Restriction ageing**       | count of TSRs older than their review date            | measure          | −60%                  |
| **Duration estimate error**  | mean absolute % error, planned vs actual              | measure          | ≤ 15%                 |

### C5.2 Process and adoption metrics

| Metric                                            | Target                     |
| ------------------------------------------------- | -------------------------- |
| Demands raised through the system (vs outside it) | ≥ 95%                      |
| Median time from demand to decision               | ≤ 7 days for routine class |
| SLA breach / escalation rate                      | ≤ 5%                       |
| Acknowledgement completion before block date      | ≥ 98%                      |
| Field app usage at block start/hand-back          | ≥ 90% of blocks            |
| Post-block output reporting completeness          | ≥ 95%                      |
| Parallel manual registers still maintained        | 0 after month 12           |

### C5.3 Safety and assurance metrics

| Metric                                                                  | Target |
| ----------------------------------------------------------------------- | ------ |
| Blocks with complete protection checklist recorded                      | 100%   |
| Blocks with valid competency at grant                                   | 100%   |
| Open disconnections at hand-back                                        | 0      |
| Power blocks with confirmed earthing before "work started"              | 100%   |
| Adjacent-line risk declared                                             | 100%   |
| Decisions with recorded justification when overriding top-ranked option | 100%   |

### C5.4 The single question the Board will ask

> _"For every hour we take the railway away from the passenger, how many minutes of real
> maintenance did we get, and did we get it safely?"_

The system exists to make that question answerable, and then to improve the answer.

---

# Part D — Stakeholders, Governance and Regulation

## D1. Persona catalogue

Each persona is specified by what they must _see_, what they must _do_, and what would
make them abandon the system.

### D1.1 Field Inspector / Supervisor (PWI, SSE/JE — P.Way, OHE, S&T)

- **Sees:** his section's assets and defect backlog; his forward block assignments; the
  status of every demand he raised; his site's protection status during a block.
- **Does:** raises defects and demands from the field; confirms readiness; confirms party
  at site and protection; reports progress; requests extension; certifies work output.
- **Abandons if:** the app does not work offline; entry takes more than a couple of minutes;
  his demands vanish into a black hole without status.

### D1.2 Nominated Person / Site-in-Charge

- **Sees:** an unambiguous, large, high-contrast indication of whether the block is granted,
  whether OHE is earthed, whether the adjacent line is open, and the sanctioned end time
  with a countdown.
- **Does:** accepts the block; runs the protection checklist; declares work start; requests
  extension; declares hand-back.
- **Abandons if:** the safety indication is ever ambiguous or stale without saying so.

### D1.3 Section Controller (Operating)

- **Sees:** the live map; blocks due this shift; trains approaching worksites; impact of
  any pending extension; restrictions in force; the shift handover pack.
- **Does:** grants blocks on line; regulates trains; decides extensions; records reasons;
  declares emergencies.
- **Abandons if:** the system adds keystrokes during the busiest minutes of the shift, or
  if its picture ever contradicts what he knows to be true on the ground.

### D1.4 Chief Controller / Deputy Chief Controller

- **Sees:** the whole division's live picture; at-risk blocks; escalations; SLA breaches.
- **Does:** arbitrates between sections; authorises emergency measures; approves within
  delegated powers.

### D1.5 Divisional Operations Manager (Sr.DOM/DOM)

- **Sees:** the forward plan, the ranked options with their impact, the departmental
  scorecards, the corridor picture.
- **Does:** chairs the block planning process; approves the periodic block plan; balances
  departmental demands; sets local policy weights.

### D1.6 Divisional Engineering / Electrical / S&T Officers (Sr.DEN, Sr.DEE, Sr.DSTE)

- **Sees:** their department's demand portfolio, backlog, sanction rate, utilisation
  performance, and how their demands were scored against others.
- **Does:** prioritises within their department; sponsors demands; commits resources.
- **Abandons if:** they perceive the scoring as a black box biased against them — hence the
  explainability requirement is not a nicety, it is an adoption requirement.

### D1.7 Divisional Safety Officer

- **Sees:** safety-class blocks, protection compliance, competency exceptions, incident
  linkage, rules derived from enquiries.
- **Does:** signs off high-risk classes; audits; converts enquiry recommendations into rules.

### D1.8 Divisional Railway Manager (DRM/ADRM)

- **Sees:** an executive dashboard — punctuality impact, backlog, utilisation, emergencies,
  exceptions requiring attention.
- **Does:** approves exceptional cases; sets divisional priorities; answers to the Zone.

### D1.9 Traction Power Controller (TPC)

- **Sees:** power block requests, the computed minimal isolation set, elementary section
  status, earthing confirmations.
- **Does:** issues and cancels power blocks; confirms earthing; coordinates with grid.

### D1.10 Zonal / Board-level Planning Officer

- **Sees:** corridor-level access plans across divisions and zones; programme progress;
  national KPI comparison.
- **Does:** sets corridor strategy; allocates mega-block windows; arbitrates inter-divisional.

### D1.11 Project Manager / Construction Organisation

- **Sees:** the programme's access plan, granted vs required windows, slippage.
- **Does:** raises programme demands; mobilises contractors; reports progress.

### D1.12 Contractor / Third Party

- **Sees:** only their own works, sponsored by a railway officer; their competency status.
- **Does:** submits method statements; confirms readiness; reports on site.

### D1.13 Commercial / Passenger Information

- **Sees:** approved blocks with passenger impact; cancellation and diversion lists.
- **Does:** publishes information; handles refunds and enquiries.

### D1.14 Auditor / Enquiry Officer

- **Sees:** the immutable record — everything, read-only, as at any past instant.
- **Does:** reconstructs decisions; verifies compliance.

### D1.15 System Administrator

- **Does:** manages master data, users, roles, delegations, rule configuration, calendars.

## D2. Responsibility matrix (RACI) for the block lifecycle

| Stage                       | Field Insp. | Dept Officer | Controller | DOM              | Safety | DRM   | TPC     |
| --------------------------- | ----------- | ------------ | ---------- | ---------------- | ------ | ----- | ------- |
| Raise demand                | **R**       | A            | I          | I                | –      | –     | –       |
| Departmental prioritisation | C           | **R/A**      | I          | I                | –      | –     | –       |
| Conflict/impact analysis    | I           | C            | C          | **A** (system R) | C      | I     | C       |
| Resource commitment         | **R**       | A            | I          | C                | –      | –     | –       |
| Routine approval            | I           | C            | C          | **R/A**          | I      | I     | C       |
| High-risk approval          | I           | C            | C          | R                | **A**  | C     | C       |
| Exceptional/peak override   | I           | C            | C          | R                | C      | **A** | C       |
| Power block sanction        | I           | C            | C          | I                | I      | –     | **R/A** |
| Grant on line               | I           | I            | **R/A**    | I                | –      | –     | C       |
| Protection & work start     | **R/A**     | I            | I          | –                | C      | –     | C       |
| Extension decision          | R (request) | I            | **A**      | C                | –      | –     | C       |
| Hand-back certification     | **R/A**     | I            | C          | I                | C      | –     | C       |
| Output & actuals reporting  | **R**       | A            | I          | I                | –      | –     | –       |
| Post-block review           | C           | R            | C          | **A**            | C      | I     | C       |

_(R = Responsible, A = Accountable, C = Consulted, I = Informed)_

## D3. Regulatory and assurance context

The system operates inside an existing safety regime and must be designed to serve it,
not to substitute for it.

1. **Rule books and manuals remain authoritative.** The system encodes rules; it does not
   create them. Every enforced constraint carries a citation field naming its authority.
2. **Independent safety regulation.** Major works, commissioning and any change to the
   signalling or track layout remain subject to the statutory sanction and inspection
   process. The system produces the evidence pack; it does not shortcut the process.
3. **Records retention.** Block, protection, disconnection, competency and hand-back
   records are safety records. They must be immutable, time-stamped, attributable, and
   retained for the statutorily required period, and must be producible in a form
   acceptable to an enquiry.
4. **Change control.** Any change to a machine-enforced safety rule requires the same
   scrutiny as a change to a written instruction: proposal, safety assessment, approval by
   the safety authority, versioning, and an effective-from date. Rules are never edited in
   place.
5. **Human authority preserved.** Nothing in the system may be capable of being cited as
   "the computer allowed it". Accountability rests with named individuals at every gate.

## D4. Governance of the system itself

- **Design authority:** a standing committee with Operating, Engineering, Electrical, S&T
  and Safety representation; chaired by Operating; safety holds a veto on rule changes.
- **Data ownership:** each master data domain has a named owner (topology → Engineering;
  traction network → Electrical; signalling assets → S&T; timetable → Operating).
- **Configuration vs code:** objective weights, calendars, SLA durations, notice periods,
  peak windows and approval matrices are **configuration**, changeable by authorised
  officers with an audit trail, never requiring a software release.
- **Release discipline:** safety-affecting changes follow a stricter release path than
  cosmetic ones; a documented safety case accompanies each release.

---

# Part E — Landscape Review of Existing Solutions

> **Caveat on sourcing.** This section is written from professional domain familiarity, not
> from vendor documentation obtained for this paper. Named systems are cited as
> _categories of capability that demonstrably exist in the industry_. Before any of this is
> used in a procurement or tender document, each specific claim must be verified against
> current vendor literature and, where possible, a site visit. Items marked **[verify]**
> are those where detail matters most.

## E1. Why review the landscape at all

Three reasons, in order of importance:

1. **To avoid re-inventing solved problems.** Timetable conflict detection, capacity
   simulation and possession planning are mature disciplines with decades of tooling.
2. **To identify the genuine gap.** Most existing tools solve _one_ of our fourteen
   capability blocks extremely well and ignore the rest. The gap is integration.
3. **To set a realistic ambition.** Where the state of the art is heuristic and advisory,
   we should not promise optimality.

## E2. Categories of existing capability

### E2.1 Train control and traffic management systems (TMS / CTC)

_Examples of the category: centralised traffic control installations; modern traffic
management systems supplied by the major signalling houses._ **[verify vendor specifics]**

- **What they do well:** real-time train describer/berth-level tracking, automatic route
  setting, conflict detection between train paths, automatic regulation proposals,
  train graph (time–distance chart) display, delay recording.
- **What they typically do not do:** originate and adjudicate _maintenance demand_. They
  usually accept a possession as an externally-given input, not as something to be planned,
  bundled and optimised against maintenance value.
- **Lesson for us:** we must consume their train position and delay data, and we must
  present a train-graph view because that is the operator's native mental model. We must
  not attempt to replace their real-time control function.

### E2.2 Possession / access planning systems

_The category exists most maturely in networks that run a formal "access planning" regime —
e.g. an infrastructure manager publishing an engineering access statement and running a
possession planning application into which works are bid._ **[verify]**

- **What they do well:** a published rules-of-the-route baseline; a formal bidding calendar
  with lead-time tiers; possession objects with worksites nested inside; conflict checking
  between possessions and train paths; publication of the agreed access plan.
- **What they typically do not do:** optimise. They are largely _validation and workflow_
  systems: a human proposes, the system checks. Bundling is a human negotiation.
  Field execution, protection confirmation and actual-versus-planned learning are usually
  separate systems or not digital at all.
- **Lesson for us:** the concepts of a **published access baseline**, **lead-time tiers**,
  and **nested worksites inside a possession** are proven and should be adopted directly.
  Our differentiator is the optimisation, the impact quantification and the execution loop.

### E2.3 Enterprise asset management / maintenance management (EAM / CMMS)

_Examples of the category: general-purpose EAM suites configured for rail infrastructure._

- **What they do well:** asset registers, hierarchies, condition records, work orders,
  preventive maintenance schedules, spares, costing, statutory inspection tracking.
- **What they typically do not do:** understand _track access as a constrained resource_.
  A work order says "renew rail at 412/7"; it does not know that doing so costs the
  railway 340 train-minutes on a Sunday morning but only 60 on a Tuesday night.
- **Lesson for us:** we should **not** build an EAM. We should integrate: consume work
  orders as demand, return actual execution back. Our system is the _access_ layer sitting
  between the asset world and the operations world.

### E2.4 Timetable planning and capacity simulation

_Examples of the category: microscopic railway simulation and timetabling packages used
for capacity studies and possession impact analysis._ **[verify]**

- **What they do well:** microscopic infrastructure modelling, blocking-time theory,
  conflict-free timetable construction, capacity consumption analysis, robust simulation of
  delay propagation, evaluation of possession scenarios.
- **What they typically do not do:** operate in the daily planning loop. They are studio
  tools used by specialists for studies, not services called by a workflow at T-21 days.
- **Lesson for us:** the _methods_ are what we need — blocking-time theory, capacity
  consumption, stochastic delay propagation. The delivery model must be different: an
  always-on service, answering in seconds, embedded in the approval screen.

### E2.5 Real-time train information and tracking

_Examples of the category: GPS/GNSS-based locomotive tracking, train describer integration,
mobile train information services._ **[verify]**

- **What they do well:** position, speed, delay, ETA; passenger-facing information.
- **Lesson for us:** this is our train-position data source. We must design for **variable
  quality**: some trains tracked to the metre, some only to the last reporting station,
  some not at all. The map must be honest about position confidence.

### E2.6 Freight operations and terminal management

- **What they do well:** rake tracking, terminal placement/release, demurrage.
- **Lesson for us:** a required integration for freight impact (S-53, S-55) and a source of
  the "what does this block cost in tonnage" figure.

### E2.7 Workforce safety and protection technologies

_Examples of the category: track worker warning systems, lookout-operated warning devices,
train-approach warning, geofenced safe-zone applications, competency/sentinel-style
credential schemes._ **[verify]**

- **What they do well:** credential verification at the worksite; automated train-approach
  warning; safe-zone definition.
- **Lesson for us:** the competency-credential concept is directly adoptable (SR-041,
  SR-077). Warning systems are complementary hardware; our system should record their
  deployment as part of the protection checklist but must not claim to replace them.

### E2.8 Generic scheduling and optimisation platforms

- **What they do well:** constraint programming, mixed-integer programming, metaheuristics.
- **Lesson for us:** the optimisation core is a well-understood engineering problem. The
  hard part is not the solver; it is the **model fidelity** and the **explainability**.

## E3. Feature comparison — what exists vs what we need

| Capability                              | TMS/CTC | Possession planning | EAM | Simulation | RT tracking | **Our target** |
| --------------------------------------- | :-----: | :-----------------: | :-: | :--------: | :---------: | :------------: |
| Structured demand intake from field     |    –    |          ◐          |  ●  |     –      |      –      |       ●        |
| Asset-bound demand                      |    –    |          ◐          |  ●  |     –      |      –      |       ●        |
| Machine-readable topology               |    ●    |          ●          |  ◐  |     ●      |      ◐      |       ●        |
| Derived unavailability (what else dies) |    ◐    |          ◐          |  –  |     ●      |      –      |       ●        |
| Traction elementary-section model       |    –    |          –          |  ◐  |     –      |      –      |       ●        |
| Conflict detection (demand vs demand)   |    –    |          ●          |  –  |     –      |      –      |       ●        |
| Conflict detection (demand vs traffic)  |    ●    |          ●          |  –  |     ●      |      –      |       ●        |
| **Bundling / shadow finding**           |    –    |          –          |  –  |     –      |      –      |     **●**      |
| Impact quantification in train-minutes  |    ◐    |          ◐          |  –  |     ●      |      –      |       ●        |
| Financial cost of a block               |    –    |          –          |  ◐  |     –      |      –      |       ●        |
| Resource & competency feasibility       |    –    |          ◐          |  ●  |     –      |      –      |       ●        |
| Ranked, explained plan options          |    –    |          –          |  –  |     ◐      |      –      |       ●        |
| Multi-level approval workflow + SLA     |    –    |          ●          |  ●  |     –      |      –      |       ●        |
| Acknowledged distribution               |    –    |          ◐          |  ◐  |     –      |      –      |       ●        |
| Field execution & protection checklist  |    –    |          –          |  ◐  |     –      |      –      |       ●        |
| Separate traffic/power block states     |    –    |          ◐          |  –  |     –      |      –      |       ●        |
| Live map of blocks + trains + conflicts |    ◐    |          –          |  –  |     –      |      ●      |       ●        |
| Time-travel (past/future) map           |    –    |          ◐          |  –  |     ●      |      –      |       ●        |
| Actual-vs-planned learning loop         |    –    |          –          |  ◐  |     –      |      –      |       ●        |
| Emergency block fast path               |    ◐    |          –          |  –  |     –      |      –      |       ●        |
| Offline-capable field operation         |    –    |          –          |  ◐  |     –      |      –      |       ●        |
| Immutable decision audit                |    ◐    |          ●          |  ●  |     –      |      –      |       ●        |

`●` strong · `◐` partial · `–` absent

## E4. The genuine gap

Reading the table down the columns rather than across the rows:

> **No single existing category joins maintenance demand to traffic cost to field execution
> to learning.** Asset systems know _what_ needs doing. Traffic systems know _what it
> costs_. Neither talks to the other, and neither closes the loop with what actually
> happened on site.

The differentiating capabilities — the ones that do not exist off the shelf in an
integrated form — are:

1. **Bundling / shadow finding** across departments and across time.
2. **Impact quantification in train-minutes and rupees at the moment of decision.**
3. **A closed execution loop** from sanction to protection to actuals to better estimates.
4. **A unified spatio-temporal picture** of blocks, trains, restrictions and conflicts.

These four are where the value is, and where the design effort should be concentrated.

## E5. Build / buy / integrate posture

| Component                             | Posture                                  | Reasoning                                                                                 |
| ------------------------------------- | ---------------------------------------- | ----------------------------------------------------------------------------------------- |
| Asset register & work orders          | **Integrate**                            | Mature EAM market; not our differentiator.                                                |
| Train positions & delays              | **Integrate**                            | Owned by control/tracking systems.                                                        |
| Timetable / paths                     | **Integrate**                            | Owned by the timetable system.                                                            |
| Topology model                        | **Build (own the schema)**               | Nobody else will model it to the granularity we need; it is the foundation of everything. |
| Demand, workflow, approval            | **Build**                                | Deeply organisation-specific.                                                             |
| Conflict, bundling, impact, optimiser | **Build core, use standard solvers**     | The model is the value; the solver is a commodity.                                        |
| Map / geospatial                      | **Buy libraries, build the application** | Rendering is commodity; railway symbology is not.                                         |
| Field app                             | **Build**                                | Offline-first, safety-critical UX is not a generic problem.                               |
| Notification transport                | **Buy/integrate**                        | Commodity.                                                                                |
| Analytics/BI                          | **Buy the tool, build the model**        | Commodity presentation, specific semantics.                                               |

---

# Part F — Solution Design

## F1. Design principles

These principles are binding on every downstream design decision in this paper.

1. **The topology is the foundation.** Nothing works without a truthful, machine-readable
   network model. Every other capability degrades to guesswork without it. Invest here first.
2. **Advisory, never autonomous.** The system computes and proposes; a named human decides.
3. **Explain everything.** Any number the system shows must be traceable to its inputs and
   assumptions; any recommendation must state its binding constraints and rejected
   alternatives.
4. **Safety states are explicit, separate, and fail-safe.** Traffic protection, power
   isolation and adjacent-line status are distinct facts, individually confirmed, and
   default to "unsafe/unknown" when uncertain.
5. **Capture actuals or the system dies.** Without actual grant, start, protection,
   progress, hand-back and output data, there is no learning, no calibration, no KPI, and
   no reason for anyone to trust the estimates. Actuals capture must be effortless.
6. **Offline-first at the edge.** The field is where connectivity is worst and consequences
   are highest.
7. **Configuration over code.** Weights, calendars, SLAs, notice periods, approval matrices
   and rules are data, versioned and auditable.
8. **Immutability for anything safety- or accountability-relevant.** Append-only; never
   update in place; corrections are new records referencing the old.
9. **Progressive disclosure.** A gangman sees three things. A DRM sees a dashboard. Nobody
   sees a 90-field form all at once.
10. **Degrade gracefully, loudly.** When data is stale, missing, or the system is impaired,
    say so prominently rather than presenting a confident-looking lie.
11. **One system of record; many generated artefacts.** Circulars, charts, notices, caution
    orders and registers are _outputs_, never parallel inputs.
12. **Design for the transfer.** Every view must be usable by an officer who arrived
    yesterday; institutional memory belongs to the asset and the section, not the person.

## F2. Conceptual model — the five worlds

The system reconciles five distinct "worlds" that today live in different heads and
different files. Understanding this is the key to the whole architecture.

```
   ┌───────────────────────┐        ┌───────────────────────┐
   │   WORLD 1: NETWORK    │        │   WORLD 2: DEMAND     │
   │  What the railway IS  │        │  What must be DONE    │
   │  • stations, lines    │        │  • defects            │
   │  • tracks, chainages  │        │  • work orders        │
   │  • turnouts, signals  │        │  • statutory items    │
   │  • OHE elementary sec │        │  • project works      │
   │  • connectivity graph │        │  • criticality        │
   └───────────┬───────────┘        └───────────┬───────────┘
               │                                │
               │        ┌───────────────────────┴──────────┐
               │        │                                  │
               ▼        ▼                                  ▼
   ┌────────────────────────────────┐        ┌───────────────────────┐
   │   WORLD 3: ACCESS (BLOCKS)     │◄──────►│  WORLD 4: TRAFFIC     │
   │  The negotiated intersection   │        │  What must MOVE       │
   │  • block windows               │        │  • timetabled paths   │
   │  • worksites & work packages   │        │  • actual running     │
   │  • protection & isolation      │        │  • capacity, priority │
   │  • restrictions imposed        │        │  • freight, passengers│
   └────────────────┬───────────────┘        └───────────────────────┘
                    │
                    ▼
   ┌────────────────────────────────┐
   │   WORLD 5: RESOURCES           │
   │  What makes work POSSIBLE      │
   │  • machines, tower wagons      │
   │  • gangs, competent persons    │
   │  • materials, contractors      │
   │  • their locations & calendars │
   └────────────────────────────────┘
```

A **block** is the object where all five worlds must simultaneously be satisfied:

> A block is _feasible_ only if the **network** permits it (topology, derived
> unavailability), the **demand** justifies it (criticality, quantum), the **traffic** can
> absorb it (capacity, priority, notice), and the **resources** exist to use it
> (machines, people, materials, competencies) — at the same place, at the same time.

Everything the optimiser does is a search over that joint feasible region.

## F3. Solution overview in one page

```
                       ┌──────────────────────────────────────────┐
                       │  DEMAND INTAKE                           │
   Field app  ────────►│  defect → demand → structured request    │
   Web form   ────────►│  asset-bound, validated, templated       │
   EAM feed   ────────►│  duration suggested from history         │
                       └───────────────────┬──────────────────────┘
                                           │
                       ┌───────────────────▼──────────────────────┐
                       │  ANALYSIS ENGINE (continuous)            │
                       │  1. Topology expansion                   │
                       │     → derived unavailability set         │
                       │  2. Conflict detection                   │
                       │     → demand×demand, demand×traffic,     │
                       │       demand×resource, demand×rule       │
                       │  3. Shadow finder                        │
                       │     → bundling & corridor candidates     │
                       │  4. Impact engine                        │
                       │     → trains, minutes, cancellations,    │
                       │       tonnage, cost                      │
                       │  5. Feasibility                          │
                       │     → resources, competency, materials   │
                       └───────────────────┬──────────────────────┘
                                           │
                       ┌───────────────────▼──────────────────────┐
                       │  OPTIMISER                               │
                       │  hard constraints  (safety, statutory)   │
                       │  soft constraints  (penalised)           │
                       │  objective         (published weights)   │
                       │  → RANKED, EXPLAINED PLAN OPTIONS        │
                       └───────────────────┬──────────────────────┘
                                           │  proposes
                       ┌───────────────────▼──────────────────────┐
                       │  HUMAN APPROVAL (multi-level, SLA)       │
                       │  sees impact + explanation + options     │
                       │  approves / modifies / refuses + reason  │
                       └───────────────────┬──────────────────────┘
                                           │  decides
                       ┌───────────────────▼──────────────────────┐
                       │  DISTRIBUTION                            │
                       │  acknowledged notices, calendars,        │
                       │  caution data, passenger info, rosters   │
                       └───────────────────┬──────────────────────┘
                                           │
                       ┌───────────────────▼──────────────────────┐
                       │  EXECUTION (field + control)             │
                       │  readiness → grant → protection →        │
                       │  isolation → work → progress →           │
                       │  extension? → hand-back → output         │
                       └───────────────────┬──────────────────────┘
                                           │  actuals
                       ┌───────────────────▼──────────────────────┐
                       │  LEARNING                                │
                       │  duration models, delay models,          │
                       │  scorecards, KPIs, rule refinement       │
                       └───────────────────┬──────────────────────┘
                                           │
                                           └──► feeds back into ANALYSIS
```

Running across all of it, continuously: **the live map and the situational picture**
(Part K), and **the immutable audit record** (Part L).

## F4. Core domain entities

The entity list below is the vocabulary of the system. Attributes are indicative; the
authoritative field catalogue for requests is [Part G](#part-g--the-block-request-complete-field-catalogue).

### F4.1 Network entities

| Entity                                 | Key attributes                                                                                      | Notes                          |
| -------------------------------------- | --------------------------------------------------------------------------------------------------- | ------------------------------ |
| `Zone` / `Division` / `Section`        | code, name, parent, jurisdiction                                                                    | Organisational hierarchy.      |
| `Station`                              | code, name, category, section, coordinates, chainage                                                | Block stations and halts.      |
| `Line`                                 | code, name, type (main/loop/siding/goods-avoiding), direction, electrified                          | Named running line.            |
| `TrackSegment`                         | id, line, from_node, to_node, chainage_start, chainage_end, geometry, max_speed, gauge, electrified | **The atomic blockable unit.** |
| `Node`                                 | id, type (station/junction/signal/LC/bridge/neutral-section), coordinates, chainage                 | Graph vertex.                  |
| `Turnout`                              | id, node, from_segment, to_segments, normal/reverse, speed                                          | Enables/denies routing.        |
| `Crossover`                            | id, turnouts, connects_lines                                                                        | Critical for SLW planning.     |
| `LevelCrossing`                        | id, chainage, type, road class, gate staff                                                          | Blocks affect LC operation.    |
| `Structure`                            | id, type (bridge/tunnel/ROB/RUB), chainage, inspection regime                                       | Access constraints.            |
| `TractionFeeder` / `ElementarySection` | id, TSS/SP/SSP endpoints, covered segments                                                          | The **power block** graph.     |
| `SignallingElement`                    | id, type (signal/point machine/axle counter/track circuit), location, interlocking                  | Disconnection targets.         |
| `Asset`                                | id, class, location (segment + chainage), install date, condition, criticality                      | The maintainable thing.        |

### F4.2 Demand and access entities

| Entity                | Key attributes                                                                                 |
| --------------------- | ---------------------------------------------------------------------------------------------- |
| `Defect`              | id, asset, observed_by, observed_at, class, severity, photo, status                            |
| `WorkOrder`           | id, source (EAM/defect/statutory/project), asset, work_type, quantum, due_date                 |
| `BlockDemand`         | the request — see [Part G](#part-g--the-block-request-complete-field-catalogue)                |
| `Block`               | id, class, status, planned/actual windows, extent, protection, isolation, worksites            |
| `WorkPackage`         | id, block, party, extent, work_orders, progress, readiness, handback_state                     |
| `Worksite`            | id, work_package, chainage_from, chainage_to, live position                                    |
| `Restriction`         | id, type (speed/blockage/adhesion/caution), value, extent, from, to, review_date, origin_block |
| `Disconnection`       | id, block, signalling_element, disconnected_at, reconnected_at, by_whom                        |
| `Isolation`           | id, block, elementary_sections, requested/granted/earthed/removed timestamps, TPC              |
| `HandbackCertificate` | id, block, certifier, timestamp, fitness, imposed_restriction                                  |
| `Programme`           | id, project, portfolio of demands, milestones                                                  |

### F4.3 Traffic entities

| Entity              | Key attributes                                                                     |
| ------------------- | ---------------------------------------------------------------------------------- |
| `Train`             | id, number, type, priority_class, formation                                        |
| `Path`              | id, train, ordered (location, arrive, depart) with line usage                      |
| `RunningRecord`     | train, location, actual times, delay, cause_attribution                            |
| `TrainPosition`     | train, timestamp, position (segment + chainage or coordinates), confidence, source |
| `CapacityProfile`   | section, configuration (normal/SLW/partial), trains-per-hour by direction          |
| `ServiceDisruption` | derived from block: cancellations, diversions, short-terminations, regulation      |

### F4.4 Resource entities

| Entity            | Key attributes                                                                                                          |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `Machine`         | id, type (tamper/regulator/BCM/tower wagon/RRV), home base, current location, availability calendar, mobilisation model |
| `Gang`            | id, unit, strength, base, roster, competencies                                                                          |
| `Person`          | id, designation, competencies with validity dates, roster, contact                                                      |
| `Material`        | id, type, quantity, location, reserved_for                                                                              |
| `Contractor`      | id, scope, personnel, competency status, contract terms                                                                 |
| `ResourceBooking` | resource, block, from, to, status                                                                                       |

### F4.5 Decision and governance entities

| Entity         | Key attributes                                                                   |
| -------------- | -------------------------------------------------------------------------------- |
| `PlanOption`   | id, planning_run, set of proposed blocks, objective score, component scores      |
| `PlanningRun`  | id, horizon, inputs snapshot, weights used, options produced, timestamp          |
| `Decision`     | id, subject, options_considered, chosen, decider, timestamp, justification       |
| `ApprovalStep` | id, block, role, decision, timestamp, SLA state, delegation                      |
| `Rule`         | id, text, citation, machine expression, version, effective_from, safety_approval |
| `Notification` | id, event, recipients, channels, sent, delivered, acknowledged                   |
| `AuditRecord`  | id, actor, action, entity, before, after, timestamp, correlation_id              |
| `Calendar`     | id, type (embargo/peak/festival/statutory), entries, scope                       |

## F5. Block classes

Different work needs different treatment. Class determines notice period, approval chain,
mandatory fields and default constraints. This is the single most useful piece of
configuration in the system.

| Class                           | Typical use                                              | Min. notice        | Approval chain                                | Notes                                            |
| ------------------------------- | -------------------------------------------------------- | ------------------ | --------------------------------------------- | ------------------------------------------------ |
| **Routine**                     | Recurring maintenance, patrolling, minor attention       | 14 days            | Dept officer → Operating                      | Bulk-plannable; strong candidate for bundling    |
| **Corridor**                    | Pre-declared recurring window into which departments bid | Published annually | Division → Zone                               | The strategic instrument for capacity protection |
| **Mega / Weekend**              | Large multi-department suburban or trunk works           | 30 days            | Division → Zone; Safety consulted             | High passenger impact; passenger info mandatory  |
| **Major Works / Commissioning** | New interlocking, layout change, girder launch           | 60–90 days         | Division → Zone → Safety → statutory          | Reversion plan and go/no-go gate mandatory       |
| **Project**                     | Doubling, electrification, third line                    | Programme-level    | Project + Division                            | Portfolio-managed via `Programme`                |
| **Third Party**                 | Utility, road authority, adjacent developer              | 45 days            | Sponsor → Division → Safety                   | Method statement + risk assessment mandatory     |
| **Short/Micro**                 | < 30 min attention, often between trains                 | 24 h or on-shift   | Controller within delegation                  | Very light form; still recorded                  |
| **Emergency**                   | Fracture, failure, safety threat                         | Immediate          | Controller grants; formalised retrospectively | Minimum-field fast path                          |
| **Restoration**                 | Accident/derailment/weather recovery                     | Immediate          | Incident command                              | Resource mobilisation tracking                   |
| **Security**                    | Threat, VIP, law-and-order                               | Immediate          | Restricted chain                              | Restricted visibility                            |

## F6. How the design answers each problem

| Sub-problem               | Mechanism in this design                                                                              |
| ------------------------- | ----------------------------------------------------------------------------------------------------- |
| P1 Demand capture         | Field app defect capture (F/J), structured demand schema (G), templates, EAM ingestion, ageing clocks |
| P2 Network representation | Topology graph + traction graph (F4.1), derived unavailability (H3)                                   |
| P3 Conflict detection     | Continuous analysis engine (F3, H4)                                                                   |
| P4 Opportunity detection  | Shadow finder (H5)                                                                                    |
| P5 Impact quantification  | Impact engine (H6) with capacity, propagation and cost models                                         |
| P6 Resource feasibility   | Resource model + readiness gate (H7)                                                                  |
| P7 Decision support       | Optimiser with published objective and explanations (H8, H9)                                          |
| P8 Communication          | Acknowledged notification fabric (I6)                                                                 |
| P9 Execution discipline   | Execution state machine with timestamped events (H2, J6)                                              |
| P10 Safety assurance      | Separate safety states, checklists, competency gates, immutable records (H10)                         |
| P11 Situational awareness | The map and the train graph (Part K)                                                                  |
| P12 Memory and learning   | Actuals capture + learning loop (H11)                                                                 |
| P13 Accountability        | Decision records + audit (L3)                                                                         |
| P14 Resilience            | Emergency path, disruption mode, offline, degraded artefacts (L5)                                     |

---

# Part G — The Block Request: Complete Field Catalogue

## G1. Form design philosophy

The block request form is where the whole system succeeds or fails. Too thin, and the
planner cannot reason (S-04). Too thick, and users fill it with "NA" and the data is
worthless (S-83).

Six rules govern it:

1. **No field is mandatory unless it changes a decision, a calculation, or a legal record.**
   For every mandatory field in this catalogue, the "Why it exists" column names the
   decision it feeds. If a field cannot name one, it is deleted.
2. **Ask the machine before asking the human.** Chainage, line, electrification status,
   adjacent line, elementary section, affected trains, and derived unavailability are all
   _computed_ from the selected asset/extent, not typed.
3. **Progressive disclosure.** The form opens with 6 fields. Department-specific and
   risk-specific sections appear only when relevant.
4. **Templates carry the burden.** A recurring demand is instantiated from a template with
   90% pre-filled; the user changes the date and the quantum.
5. **Validate at entry, explain the failure.** Never accept a demand that will fail
   downstream; never reject without saying exactly what to fix.
6. **Every field has a stable identifier and a version.** Forms evolve; historical records
   must remain interpretable.

Notation used below:
`M` mandatory · `C` conditionally mandatory · `O` optional · `S` system-computed (read-only)

---

## G2. Block 1 — Identification and origin

| #    | Field                          | Type     | Req                      | Validation                                                                   | Why it exists / what it changes                                                                |
| ---- | ------------------------------ | -------- | ------------------------ | ---------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| 1.1  | Request ID                     | string   | S                        | auto                                                                         | Immutable handle for all downstream references, notices and audit.                             |
| 1.2  | Request version                | int      | S                        | auto-increment                                                               | Every amendment creates a version; old versions immutable (accountability).                    |
| 1.3  | Block class                    | enum     | M                        | see [F5](#f5-block-classes)                                                  | **Drives everything**: notice period, approval chain, mandatory sections, default constraints. |
| 1.4  | Requesting department          | enum     | M                        | from master                                                                  | Routing, scorecards, cost attribution.                                                         |
| 1.5  | Requesting unit / sub-division | ref      | M                        | from master                                                                  | Scorecard granularity; who is accountable for utilisation.                                     |
| 1.6  | Requester (name, designation)  | ref      | S                        | from session                                                                 | Accountability; contact for clarification.                                                     |
| 1.7  | Sponsoring officer             | ref      | C (third-party, project) | must hold sponsor role                                                       | A railway officer must own every external demand (S-76).                                       |
| 1.8  | Origin type                    | enum     | M                        | defect / statutory / condition-based / project / failure / directive / audit | Determines criticality defaults and whether a due date is legally binding.                     |
| 1.9  | Origin reference               | ref      | C (if origin ≠ ad-hoc)   | must resolve                                                                 | Links to `Defect`, `WorkOrder`, statutory schedule, enquiry recommendation.                    |
| 1.10 | Programme / project            | ref      | C (class = project)      | must exist                                                                   | Portfolio rollup and slippage tracking (S-75).                                                 |
| 1.11 | Date raised                    | datetime | S                        | auto                                                                         | Lead-time and SLA clocks.                                                                      |
| 1.12 | Contact number (site)          | phone    | M                        | format                                                                       | Control must be able to reach the site during the block.                                       |
| 1.13 | Alternate contact              | phone    | O                        | format                                                                       | Resilience when the primary is out of coverage.                                                |

---

## G3. Block 2 — Location and extent

This section is **selected on the map, not typed.** The user draws or picks; the system
resolves the identifiers.

| #    | Field                         | Type       | Req                     | Validation                                                  | Why it exists / what it changes                                                                         |
| ---- | ----------------------------- | ---------- | ----------------------- | ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| 2.1  | Zone / Division / Section     | ref        | S                       | derived                                                     | Jurisdiction, approval routing, rollup.                                                                 |
| 2.2  | Between stations (from / to)  | ref        | M                       | adjacent or connected                                       | Human-readable extent; notice text; controller mental model.                                            |
| 2.3  | Line(s) affected              | multi-ref  | M                       | must exist between the stations                             | **The core of the request.** Determines derived unavailability, capacity configuration, traffic impact. |
| 2.4  | Track segment IDs             | multi-ref  | S                       | resolved from 2.2/2.3 + chainage                            | Atomic blockable units; the optimiser works on these.                                                   |
| 2.5  | Chainage from (km + m)        | numeric    | M                       | within section extent                                       | Precise extent; caution order data; worksite mapping.                                                   |
| 2.6  | Chainage to (km + m)          | numeric    | M                       | ≥ 2.5; length sane for work type                            | As above; also validates duration plausibility.                                                         |
| 2.7  | Extent length                 | numeric    | S                       | computed                                                    | Duration estimation input; protection extent.                                                           |
| 2.8  | Direction affected            | enum       | M                       | UP / DN / both                                              | Capacity model; which trains are affected.                                                              |
| 2.9  | Whole line or partial         | enum       | M                       | complete / partial-width / single-line-working              | Determines whether traffic can pass and at what capacity.                                               |
| 2.10 | Specific assets               | multi-ref  | C (asset-specific work) | must lie within extent                                      | Duplicate detection (S-03); asset history; reliability analytics.                                       |
| 2.11 | Adjacent line status required | enum       | M                       | open / cautioned at X kmph / blocked / physically separated | **Safety-critical** (S-39). Escalates approval when adjacent line stays open.                           |
| 2.12 | Level crossings within extent | multi-ref  | S                       | computed                                                    | LC gate operation and road-user impact.                                                                 |
| 2.13 | Structures within extent      | multi-ref  | S                       | computed                                                    | Access and protection implications.                                                                     |
| 2.14 | Stations/yards within extent  | multi-ref  | S                       | computed                                                    | Shunting and platform impact.                                                                           |
| 2.15 | Derived unavailability set    | list       | S                       | computed from topology                                      | **What ELSE becomes unusable** (S-13). Shown to the requester before submission.                        |
| 2.16 | Adjacent-division impact      | flag + ref | S                       | computed                                                    | Triggers cross-divisional coordination (S-15).                                                          |

---

## G4. Block 3 — Work definition

| #    | Field                                     | Type        | Req                            | Validation                                                                              | Why it exists / what it changes                                      |
| ---- | ----------------------------------------- | ----------- | ------------------------------ | --------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| 3.1  | Work category                             | enum        | M                              | taxonomy below                                                                          | Drives duration model, competency requirements, protection template. |
| 3.2  | Work type                                 | enum        | M                              | child of 3.1                                                                            | Same, finer.                                                         |
| 3.3  | Work description                          | text        | M                              | ≥ 20 chars, no placeholder text                                                         | Human comprehension; notice text.                                    |
| 3.4  | Quantum                                   | numeric     | M                              | > 0                                                                                     | **Duration estimation** (S-07).                                      |
| 3.5  | Quantum unit                              | enum        | M                              | rails / sleepers / metres / spans / masts / points / joints / cable-km / m³ / nos.      | As above.                                                            |
| 3.6  | Method of execution                       | enum        | M                              | manual / mechanised / machine type / hybrid                                             | Duration, resources, risk profile.                                   |
| 3.7  | Criticality                               | enum        | M                              | safety-critical / statutory-due / condition-based / preventive / improvement / cosmetic | **Optimiser weight** (S-09). Auditable criteria per level.           |
| 3.8  | Consequence of deferral                   | text        | M (if criticality ≥ statutory) | ≥ 30 chars                                                                              | Forces reasoning; defensible prioritisation.                         |
| 3.9  | Statutory due date                        | date        | C (origin = statutory)         | ≥ today                                                                                 | Hard constraint; escalation when at risk (S-10).                     |
| 3.10 | Can it be done under restriction instead? | enum        | M                              | yes at X kmph / no + reason                                                             | **Capacity saver.** Many blocks are avoidable (S-59).                |
| 3.11 | Phases requiring block                    | multi       | M                              | at least one                                                                            | Only the block-required portion consumes the window (S-59).          |
| 3.12 | Weather sensitivity                       | enum        | M                              | none / rain / temperature / wind / visibility                                           | Forecast checking and standby planning (S-66, S-67).                 |
| 3.13 | Noise/vibration sensitive location        | bool        | O                              | –                                                                                       | Night-work restrictions near habitation.                             |
| 3.14 | Expected output on completion             | text        | M                              | –                                                                                       | Post-block verification against plan (S-32).                         |
| 3.15 | Balance work expected                     | bool + text | O                              | –                                                                                       | Pre-declares a follow-up demand.                                     |

### G4.1 Work category taxonomy (indicative, extensible)

```
ENGINEERING / P.WAY
  Track renewal        : rail renewal, sleeper renewal, complete track renewal, turnout renewal
  Track maintenance    : through packing, spot attention, deep screening, ballast injection
  Welding & destressing: AT welding, flash butt, destressing, joint repair
  Geometry             : tamping, lifting, slewing, alignment correction
  Testing              : ultrasonic rail testing, track recording, gauge measurement
  Formation & drainage : blanketing, drain clearing, slope protection
  Bridges & structures : girder work, bearing replacement, painting, inspection, ROB/RUB
  LC & road            : level crossing renewal, road surface, gate mechanism
  Vegetation & fencing : tree cutting, boundary, encroachment removal

ELECTRICAL / TRACTION (OHE)
  Structures           : mast replacement, portal work, foundation
  Conductors           : contact wire renewal, catenary, dropper, jumper
  Insulation & fittings: insulator replacement, cantilever adjustment
  Switching            : isolator, interrupter, feeder work, neutral section
  Measurement          : OHE parameter recording, thermovision, height/stagger correction
  General electrical   : lighting mast, cable route, earthing

SIGNAL & TELECOM
  Signalling           : signal replacement, LED conversion, aspect alteration
  Interlocking         : panel/EI work, relay room, cable termination, testing
  Detection            : axle counter, track circuit installation/alteration
  Points               : point machine replacement, adjustment, locking
  Cables               : cable laying, jointing, fault rectification
  Telecom              : OFC, block instrument, control communication
  Level crossing       : LC interlocking, gate signalling

CIVIL / PROJECT / OTHER
  Construction         : doubling, third line, yard remodelling, platform work
  Third party          : utility crossing, pipeline, road works, girder launching over track
  Environmental        : drainage, flood protection, wildlife measures
```

---

## G5. Block 4 — Timing

| #    | Field                                      | Type            | Req                    | Validation                                                  | Why it exists / what it changes                                                 |
| ---- | ------------------------------------------ | --------------- | ---------------------- | ----------------------------------------------------------- | ------------------------------------------------------------------------------- |
| 4.1  | Preferred date(s)                          | date / range    | M                      | ≥ today + class notice period                               | The ask.                                                                        |
| 4.2  | Alternative dates acceptable               | date list       | O                      | –                                                           | **Gives the optimiser room to bundle.** Strongly encouraged in UI.              |
| 4.3  | Preferred start time                       | time            | M                      | –                                                           | The ask.                                                                        |
| 4.4  | Time flexibility                           | enum            | M                      | fixed / ±1h / ±3h / any time of day / night only / day only | Optimiser freedom; critical for bundling success.                               |
| 4.5  | Requested duration                         | duration        | M                      | > 0, ≤ class max                                            | Capacity consumed.                                                              |
| 4.6  | — protection setup time                    | duration        | M                      | –                                                           | **Decomposition** (S-28); prevents "work time" being quoted as block time.      |
| 4.7  | — effective work time                      | duration        | M                      | –                                                           | The number the learning loop compares against actuals.                          |
| 4.8  | — testing/verification time                | duration        | C (S&T, commissioning) | –                                                           | Frequently underestimated (S-60).                                               |
| 4.9  | — protection removal / hand-back           | duration        | M                      | –                                                           | As 4.6.                                                                         |
| 4.10 | System-suggested duration                  | duration + band | S                      | from history                                                | Anchors the estimate in evidence (S-06). Deviation > 30% prompts justification. |
| 4.11 | Justification if deviating from suggestion | text            | C                      | –                                                           | Counters systematic over-asking (S-92).                                         |
| 4.12 | Minimum viable duration                    | duration        | M                      | ≤ 4.5                                                       | Lets the optimiser offer a shorter window rather than refusing outright.        |
| 4.13 | Is the work divisible?                     | bool            | M                      | –                                                           | Can it be split across two shorter blocks? Major flexibility lever.             |
| 4.14 | Latest acceptable date                     | date            | C (statutory/critical) | –                                                           | Hard deadline for the optimiser.                                                |
| 4.15 | Recurrence                                 | pattern         | C (recurring template) | –                                                           | Auto-instantiation (S-10).                                                      |
| 4.16 | Lead time remaining                        | duration        | S                      | computed                                                    | Shown live while drafting (S-02).                                               |

---

## G6. Block 5 — Traffic and operating implications (requester's declaration)

The requester states what they _believe_; the system computes what is _true_ and shows the
difference. Divergence is itself useful data.

| #    | Field                                 | Type                             | Req | Validation                                        | Why it exists / what it changes                                                |
| ---- | ------------------------------------- | -------------------------------- | --- | ------------------------------------------------- | ------------------------------------------------------------------------------ |
| 5.1  | Can trains pass on the affected line? | enum                             | M   | no / yes at X kmph / one direction only           | Capacity configuration.                                                        |
| 5.2  | Single line working proposed?         | bool                             | C   | crossovers must exist and be outside the worksite | Feasibility check (S-13); big capacity implication (S-48).                     |
| 5.3  | Crossovers to be used for SLW         | multi-ref                        | C   | must be usable                                    | Validates 5.2.                                                                 |
| 5.4  | Requester-anticipated train impact    | text                             | O   | –                                                 | Compared with computed impact; calibrates requester realism.                   |
| 5.5  | Shunting/yard operations affected     | bool + detail                    | C   | –                                                 | Yard congestion risk (S-54).                                                   |
| 5.6  | Freight sidings affected              | multi-ref                        | S   | computed                                          | Demurrage exposure (S-53).                                                     |
| 5.7  | Platform(s) affected                  | multi-ref                        | S   | computed                                          | Passenger information.                                                         |
| 5.8  | Speed restriction expected after work | bool + value + extent + duration | M   | –                                                 | **Pre-declares the post-block capacity penalty** (S-34) so it enters the cost. |
| 5.9  | Caution order requirement             | bool                             | S   | derived from 5.8                                  | Feeds caution order generation.                                                |
| 5.10 | Computed affected trains              | list                             | S   | computed                                          | Approval screen (S-14).                                                        |
| 5.11 | Computed detention (train-minutes)    | numeric                          | S   | computed                                          | Approval screen; objective function.                                           |
| 5.12 | Computed cancellations / diversions   | list                             | S   | computed                                          | Passenger information trigger.                                                 |
| 5.13 | Computed freight tonnage delayed      | numeric                          | S   | computed                                          | Revenue impact (S-56).                                                         |
| 5.14 | Computed indicative cost              | currency                         | S   | computed                                          | Trade-off transparency.                                                        |

---

## G7. Block 6 — Protection and safety

| #    | Field                                     | Type         | Req                          | Validation                                                                                                      | Why it exists / what it changes                      |
| ---- | ----------------------------------------- | ------------ | ---------------------------- | --------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------- |
| 6.1  | Protection method                         | multi-enum   | M                            | detonators / banner flags / hand signals / clamping & padlocking / disconnection / point clamping / stop boards | The protection plan; becomes the field checklist.    |
| 6.2  | Nominated Person / Site-in-Charge         | ref          | M                            | competency valid on the date                                                                                    | **Grant gate** (S-41).                               |
| 6.3  | Deputy nominated person                   | ref          | C (duration > 4h or night)   | competency valid                                                                                                | Continuity across long/night blocks.                 |
| 6.4  | Number of persons on site                 | int          | M                            | > 0                                                                                                             | Emergency response planning; safety briefing record. |
| 6.5  | Contractor personnel involved             | bool + count | C                            | competency verified (S-77)                                                                                      | Grant gate for third parties.                        |
| 6.6  | Adjacent line risk assessment             | structured   | M                            | see 2.11                                                                                                        | Escalation trigger.                                  |
| 6.7  | Lookout / warning arrangement             | enum         | C (adjacent line open)       | lookout / automatic warning / safe-zone marking                                                                 | Mandatory when adjacent line is open.                |
| 6.8  | Machines/vehicles on track                | multi-ref    | C                            | –                                                                                                               | Movement authority and protection implications.      |
| 6.9  | Road-rail vehicle access point            | ref          | C                            | must be a valid access point                                                                                    | On/off tracking arrangements.                        |
| 6.10 | Emergency evacuation plan                 | text/ref     | C (tunnel, bridge, remote)   | –                                                                                                               | Life safety (S-43).                                  |
| 6.11 | Nearest medical facility & response route | ref          | C (high-risk class)          | –                                                                                                               | As above.                                            |
| 6.12 | Site safety briefing to be recorded       | bool         | M                            | default true                                                                                                    | Compliance evidence.                                 |
| 6.13 | Special hazards                           | multi-enum   | O                            | live OHE proximity / height / confined space / hot work / heavy lift / water / traffic                          | Drives additional checklist items and approvals.     |
| 6.14 | Method statement                          | attachment   | C (third-party, major works) | file present                                                                                                    | Statutory expectation (S-76).                        |
| 6.15 | Risk assessment                           | attachment   | C (as above)                 | file present                                                                                                    | As above.                                            |
| 6.16 | Safety approval required from             | ref          | S                            | derived from class + hazards                                                                                    | Routing.                                             |

---

## G8. Block 7 — Traction power block (conditional section)

Appears only when the work is on or near OHE, or when the requester ticks "power block
required".

| #    | Field                                    | Type      | Req | Validation                                                                    | Why it exists / what it changes                             |
| ---- | ---------------------------------------- | --------- | --- | ----------------------------------------------------------------------------- | ----------------------------------------------------------- |
| 7.1  | Power block required                     | bool      | M   | –                                                                             | Gates this whole section.                                   |
| 7.2  | Reason                                   | enum      | M   | work on OHE / work within danger zone / crane or height work / structure work | Determines isolation extent rules.                          |
| 7.3  | Requested isolation extent (map)         | geometry  | M   | –                                                                             | Input to minimal-isolation computation.                     |
| 7.4  | Computed minimal elementary sections     | multi-ref | S   | from traction graph                                                           | **Prevents grossly over-wide isolation** (S-57).            |
| 7.5  | Stations/sections going dead             | list      | S   | computed                                                                      | Shows the true footprint before approval.                   |
| 7.6  | Isolation type                           | enum      | M   | full isolation & earthing / partial / permit-to-work only                     | Safety procedure selection.                                 |
| 7.7  | Earthing points required                 | multi-ref | M   | must bound the worksite                                                       | The physical proof of a real power block (S-38).            |
| 7.8  | Authorised person to receive PTW         | ref       | M   | OHE competency valid                                                          | Grant gate.                                                 |
| 7.9  | TPC to be involved                       | ref       | S   | derived from feeder                                                           | Routing.                                                    |
| 7.10 | Traction supply implications             | text      | O   | –                                                                             | Grid/TSS coordination for large isolations.                 |
| 7.11 | Simultaneous traffic block required      | bool      | M   | –                                                                             | Links to the traffic block; combined-block creation (S-58). |
| 7.12 | Neutral section / phase break affected   | bool      | S   | computed                                                                      | Driver instructions.                                        |
| 7.13 | Electric traction diversion implications | text      | S   | computed                                                                      | Whether electric trains can be diverted at all.             |

---

## G9. Block 8 — Signalling and telecom (conditional section)

| #    | Field                                    | Type            | Req                   | Validation                                                  | Why it exists                                         |
| ---- | ---------------------------------------- | --------------- | --------------------- | ----------------------------------------------------------- | ----------------------------------------------------- |
| 8.1  | Signalling apparatus affected            | multi-ref       | M                     | must lie within extent                                      | Disconnection register (S-40).                        |
| 8.2  | Disconnection required                   | bool            | M                     | –                                                           | Gates the disconnection workflow.                     |
| 8.3  | Disconnection notice reference           | ref             | C                     | –                                                           | Statutory linkage.                                    |
| 8.4  | Working arrangement during disconnection | enum            | M                     | paper line clear / total suspension / alternative method    | Operating implications.                               |
| 8.5  | Interlocking alteration involved         | bool            | M                     | –                                                           | Escalates to major-works class if true.               |
| 8.6  | Testing required after work              | enum            | M                     | none / functional / correspondence / full interlocking test | **Testing time is the classic underestimate** (S-60). |
| 8.7  | Testing duration                         | duration        | C                     | –                                                           | Enters the duration decomposition.                    |
| 8.8  | Independent tester nominated             | ref             | C (interlocking work) | competency valid                                            | Assurance requirement.                                |
| 8.9  | Reversion plan                           | text/attachment | C (alteration)        | –                                                           | Mandatory for major works (S-61).                     |
| 8.10 | Point of no return time                  | time            | C (alteration)        | –                                                           | Go/no-go gate.                                        |
| 8.11 | Telecom circuits affected                | multi-ref       | C                     | –                                                           | Control communication continuity.                     |
| 8.12 | Effect on train detection                | text            | C                     | –                                                           | Safety implication for the operating method.          |

---

## G10. Block 9 — Resources

| #    | Field                           | Type            | Req            | Validation                    | Why it exists                                 |
| ---- | ------------------------------- | --------------- | -------------- | ----------------------------- | --------------------------------------------- |
| 9.1  | Machines required               | multi-ref + qty | C (mechanised) | must exist in resource master | Double-booking prevention (S-19).             |
| 9.2  | Machine current location        | ref             | S              | from resource tracking        | Mobilisation feasibility (S-20).              |
| 9.3  | Mobilisation time required      | duration        | S              | computed                      | Added to the block plan as an activity.       |
| 9.4  | Machine path required           | bool + path     | S              | computed                      | The machine's own movement must be pathed.    |
| 9.5  | Gang / unit assigned            | ref             | M              | roster check                  | Fatigue and loading rules (S-23).             |
| 9.6  | Number of workers               | int             | M              | –                             | Safety planning; cost.                        |
| 9.7  | Required competencies           | multi-enum      | S              | derived from work type        | Validation at grant (S-21).                   |
| 9.8  | Competency validation status    | status          | S              | computed                      | Blocks approval if invalid.                   |
| 9.9  | Key materials required          | multi-ref + qty | M              | –                             | Readiness gate (S-22).                        |
| 9.10 | Material availability confirmed | bool + date     | C              | must be true by T-24h         | Readiness gate.                               |
| 9.11 | Material at site by             | datetime        | C              | –                             | Readiness milestone.                          |
| 9.12 | Tower wagon / RRV required      | ref             | C              | –                             | Scarce resource; frequent conflict.           |
| 9.13 | Crane / heavy plant             | ref             | C              | –                             | Requires additional protection and approvals. |
| 9.14 | Contractor engaged              | ref             | C              | contract valid                | Contractual notice implications (S-65).       |
| 9.15 | Transport arrangement to site   | text            | O              | –                             | Late-arrival mitigation (S-27).               |
| 9.16 | Resource booking status         | status          | S              | computed                      | Approval gate.                                |

---

## G11. Block 10 — Dependencies and linkage

| #    | Field                               | Type             | Req         | Validation       | Why it exists                                                                  |
| ---- | ----------------------------------- | ---------------- | ----------- | ---------------- | ------------------------------------------------------------------------------ |
| 10.1 | Depends on request(s)               | multi-ref + type | O           | no cycles        | `must_follow` / `must_precede` / `simultaneous` / `mutually_exclusive` (S-08). |
| 10.2 | Related to programme milestone      | ref              | C (project) | –                | Slippage tracking.                                                             |
| 10.3 | Willing to combine with other works | bool             | M           | default **true** | **Explicit consent to bundling** — makes the shadow finder's job legitimate.   |
| 10.4 | Combination constraints             | text             | O           | –                | e.g. "cannot share with hot work".                                             |
| 10.5 | Preferred co-located works          | multi-ref        | O           | –                | Requester-initiated bundling.                                                  |
| 10.6 | Follows an earlier incomplete block | ref              | C           | –                | Continuity of partial work (S-32).                                             |
| 10.7 | Supersedes request                  | ref              | O           | –                | Duplicate resolution (S-03).                                                   |
| 10.8 | System-detected similar requests    | list             | S           | computed         | Duplicate warning at entry.                                                    |
| 10.9 | System-detected bundling candidates | list             | S           | computed         | Shown to requester before submission (S-05).                                   |

---

## G12. Block 11 — Commercial, financial and administrative

| #    | Field                                       | Type     | Req                   | Validation    | Why it exists                               |
| ---- | ------------------------------------------- | -------- | --------------------- | ------------- | ------------------------------------------- |
| 11.1 | Estimated cost of work                      | currency | C (project, contract) | –             | Programme financial tracking.               |
| 11.2 | Budget head / work order number             | ref      | C                     | –             | Financial attribution.                      |
| 11.3 | Sanction reference                          | ref      | C (project)           | –             | Administrative compliance.                  |
| 11.4 | Contract reference                          | ref      | C (contractor)        | –             | Notice-period and idle-charge terms (S-65). |
| 11.5 | Contractual notice period                   | duration | S                     | from contract | Warns when a change breaches terms.         |
| 11.6 | Deposit works / third-party payer           | ref      | C                     | –             | Cost recovery.                              |
| 11.7 | Cost of the block (indicative traffic cost) | currency | S                     | computed      | Makes the trade-off visible (S-56).         |

---

## G13. Block 12 — Attachments and evidence

| #    | Field                                  | Type     | Req                          | Why it exists                                                      |
| ---- | -------------------------------------- | -------- | ---------------------------- | ------------------------------------------------------------------ |
| 12.1 | Site photographs                       | files    | C (defect origin)            | Evidence of need; remote verification; prevents frivolous demands. |
| 12.2 | Sketch / layout plan                   | file     | C (alteration, project)      | Comprehension for approvers.                                       |
| 12.3 | Method statement                       | file     | C (third party, major works) | Statutory.                                                         |
| 12.4 | Risk assessment                        | file     | C                            | Statutory.                                                         |
| 12.5 | Previous inspection report             | file     | O                            | Justification of criticality.                                      |
| 12.6 | Test results (USFD, OMS, thermovision) | file/ref | O                            | Evidence-based criticality.                                        |
| 12.7 | Correspondence / directive             | file     | C (origin = directive/audit) | Traceability.                                                      |

---

## G14. Block 13 — System-computed decision support (read-only, always shown)

This panel is not "fields the user fills". It is **the system's answer**, rendered live as
the user edits, and it is the single most important part of the form for adoption: the
requester sees the consequences of their own ask before anyone else has to argue with them.

| #     | Shown                                                              | Source             |
| ----- | ------------------------------------------------------------------ | ------------------ |
| 13.1  | Derived unavailability set (what else becomes unusable)            | Topology expansion |
| 13.2  | Conflicting demands (spatial/temporal/resource)                    | Conflict engine    |
| 13.3  | Bundling opportunities ("3 other demands could share this window") | Shadow finder      |
| 13.4  | Affected trains, with a train-graph preview                        | Impact engine      |
| 13.5  | Estimated detention (train-minutes) and cancellations              | Impact engine      |
| 13.6  | Freight tonnage and terminal impact                                | Impact engine      |
| 13.7  | Indicative monetary cost                                           | Cost model         |
| 13.8  | Resource conflicts and competency exceptions                       | Resource engine    |
| 13.9  | Rule violations (hard) and warnings (soft), each citing its rule   | Rules engine       |
| 13.10 | Suggested better windows ("Tuesday 01:00 costs 78% less")          | Optimiser          |
| 13.11 | Confidence and data-quality caveats                                | All engines        |

---

## G15. The emergency form (minimum viable request)

Speed is safety. The emergency path must be completable in **under 30 seconds on a phone,
one-handed, in poor light, possibly offline.**

| #   | Field                   | Type                                                                               | Req |
| --- | ----------------------- | ---------------------------------------------------------------------------------- | --- |
| E.1 | Location                | map pin / nearest station + km (GPS pre-filled)                                    | M   |
| E.2 | Line                    | tap selection                                                                      | M   |
| E.3 | Nature                  | large icon buttons: rail fracture / OHE / signal / obstruction / structure / other | M   |
| E.4 | Trains must be stopped? | yes / no — single large toggle                                                     | M   |
| E.5 | Your name & number      | pre-filled from profile                                                            | S   |
| E.6 | Photo                   | optional single tap                                                                | O   |
| E.7 | Voice note              | optional                                                                           | O   |

Everything else — extent, duration, resources, protection plan — is **filled in
retrospectively** while the response is under way. The record is completed, never
back-dated silently: all late entries are timestamped as such.

---

## G16. Third-party request deltas

Third-party requests use the standard form plus:

- Mandatory railway **sponsoring officer** (1.7) who is accountable for the request.
- Mandatory **method statement** and **risk assessment** attachments.
- Mandatory **insurance/indemnity reference**.
- Mandatory **competency evidence** for all personnel who will be on railway land.
- A **separate approval chain** including Safety.
- **Longer default notice period** and a **restricted visibility** scope (they see only
  their own works).

---

## G17. Conditional logic map (progressive disclosure)

```
ALWAYS SHOWN (the "6-field open"):
   Block class · Location on map · Work type · Preferred date/time · Duration · Criticality

THEN, driven by what was chosen:

  work touches OHE  OR  power block ticked      → show Block 7 (Traction)
  work touches signalling assets                → show Block 8 (S&T)
  method = mechanised                           → show machine fields (9.1–9.4, 9.12–9.13)
  adjacent line = open                          → force 6.7 lookout/warning arrangement
  class ∈ {major works, commissioning}          → force reversion plan, go/no-go, testing
  class = third party                           → force sponsor, method statement, insurance
  class = project                               → show programme, budget, contract
  origin = statutory                            → force statutory due date, latest date
  criticality ≥ statutory-due                   → force consequence-of-deferral
  duration > 4h  OR  night                      → force deputy nominated person
  hazards include hot work/height/confined space→ show additional checklist + safety approval
  extent crosses divisional boundary            → force cross-division coordination fields
  weather sensitivity ≠ none                    → enable forecast check + standby linkage
  deviation from suggested duration > 30%       → force justification (4.11)
```

---

## G18. Validation rule catalogue (entry-time)

| ID   | Rule                                                                                                   | Severity                                                      |
| ---- | ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------- |
| V-01 | Chainage range must lie within the declared section                                                    | Block                                                         |
| V-02 | Selected line must exist between the declared stations                                                 | Block                                                         |
| V-03 | Requested date must respect the class notice period, or be explicitly marked "late" with justification | Block / Warn                                                  |
| V-04 | Duration components must sum to the requested duration                                                 | Block                                                         |
| V-05 | Minimum viable duration ≤ requested duration                                                           | Block                                                         |
| V-06 | Nominated person competency must be valid on the block date                                            | Block                                                         |
| V-07 | SLW proposed but no usable crossover outside the worksite                                              | Block                                                         |
| V-08 | Power block requested but no earthing points that bound the worksite                                   | Block                                                         |
| V-09 | Dependency graph must be acyclic                                                                       | Block                                                         |
| V-10 | Requested window falls in a configured embargo/peak window                                             | Block unless overridden by authorised role with justification |
| V-11 | Adjacent line "open" with no lookout/warning arrangement                                               | Block                                                         |
| V-12 | Statutory due date earlier than requested date                                                         | Block                                                         |
| V-13 | Machine already booked elsewhere in the window                                                         | Block                                                         |
| V-14 | Material availability unconfirmed within 24 h of block                                                 | Warn → escalates to Block at readiness gate                   |
| V-15 | Near-duplicate demand detected                                                                         | Warn (must acknowledge)                                       |
| V-16 | Bundling candidate exists that the requester has not considered                                        | Warn (must acknowledge)                                       |
| V-17 | Duration deviates > 30% from historical model                                                          | Warn (must justify)                                           |
| V-18 | Weather forecast adverse for a weather-sensitive work type                                             | Warn                                                          |
| V-19 | Description contains placeholder text ("NA", "as per rules", "-")                                      | Warn                                                          |
| V-20 | Gang would exceed consecutive-night limit                                                              | Block                                                         |
| V-21 | Contractual notice period would be breached by this date                                               | Warn                                                          |
| V-22 | Extent overlaps an existing approved block (may be a bundling opportunity)                             | Warn with bundle suggestion                                   |
| V-23 | Cross-divisional extent without the neighbouring division's coordination flag                          | Warn → Block at approval                                      |
| V-24 | Post-work speed restriction declared without extent/duration/review date                               | Block                                                         |

---

## G19. Post-block reporting form (the other half of the data)

Without this, the system has a plan but no memory. It must be completable from the field
in **under two minutes**.

| #    | Field                              | Type                                    | Req             | Feeds                                       |
| ---- | ---------------------------------- | --------------------------------------- | --------------- | ------------------------------------------- |
| R.1  | Actual block grant time            | datetime                                | S (event)       | Grant punctuality KPI (S-26)                |
| R.2  | Reason for late grant              | enum + text                             | C               | Controller/section KPI, root-cause analysis |
| R.3  | Party at site time                 | datetime                                | S (event)       | Mobilisation analysis (S-27)                |
| R.4  | Protection complete time           | datetime                                | S (checklist)   | Protection-time model (S-28)                |
| R.5  | Earthing confirmed time            | datetime                                | C (power block) | Safety record + power-block model           |
| R.6  | Work start time                    | datetime                                | S (event)       | Effective-work model                        |
| R.7  | Work end time                      | datetime                                | S (event)       | Effective-work model                        |
| R.8  | Protection removed time            | datetime                                | S (event)       | Hand-back model                             |
| R.9  | Actual hand-back time              | datetime                                | S (event)       | Overrun KPI                                 |
| R.10 | Quantum achieved                   | numeric + unit                          | M               | **Duration model calibration** (S-06)       |
| R.11 | % complete                         | numeric                                 | M               | Balance-work generation                     |
| R.12 | Balance work                       | text + auto-demand                      | C               | Continuity (S-32)                           |
| R.13 | Reason for shortfall / overrun     | enum + text                             | C               | Root-cause analytics (S-29)                 |
| R.14 | Resource issues encountered        | enum + text                             | C               | Resource model improvement                  |
| R.15 | Incidents / near misses            | structured                              | C               | Safety learning (S-44)                      |
| R.16 | Restriction imposed                | structured (value, extent, review date) | C               | Restriction register (S-34)                 |
| R.17 | Hand-back certification            | signature + fitness declaration         | M               | Safety record (S-33)                        |
| R.18 | Disconnections all restored        | bool                                    | M (if any)      | Safety gate (S-40)                          |
| R.19 | Site cleared and materials removed | bool                                    | M               | Housekeeping/safety                         |
| R.20 | Photographs of completed work      | files                                   | O               | Evidence, quality assurance                 |
| R.21 | Feedback on the plan               | free text                               | O               | Continuous improvement; user voice          |

**Reason-code taxonomies** (closed lists, because free text cannot be analysed):

```
LATE GRANT        : traffic priority · late running train · controller unavailable ·
                    protection delay · communication failure · site party not ready ·
                    power block delay · other

SHORTFALL/OVERRUN : machine breakdown · machine late arrival · material shortage ·
                    material late at site · manpower shortage · unexpected site condition ·
                    weather · additional defect found · testing took longer ·
                    protection took longer · block granted late · traffic interference ·
                    design/drawing issue · third-party delay · other
```

---

# Part H — Lifecycle, Rules and the Decision Engine

## H1. The demand lifecycle (planning phase)

```
                         ┌──────────┐
                         │  DRAFT   │  requester editing; live decision-support panel
                         └────┬─────┘
                              │ submit (validations V-01..V-24 pass)
                         ┌────▼─────┐
                         │SUBMITTED │  SLA clock starts
                         └────┬─────┘
                              │ departmental prioritisation
                         ┌────▼─────────┐
                         │DEPT_ENDORSED │  department stands behind it; competes for windows
                         └────┬─────────┘
                              │ enters planning pool
                         ┌────▼─────────┐        ┌─────────────────┐
                         │  IN_ANALYSIS │───────►│ RETURNED_FOR_INFO│──┐
                         └────┬─────────┘        └─────────────────┘  │
                              │ analysis complete                      │
                         ┌────▼─────────┐                              │
                         │ OPTIONS_READY│  ranked options + impact     │
                         └────┬─────────┘                              │
                              │ approval workflow                      │
                    ┌─────────▼──────────┐                             │
                    │    UNDER_REVIEW    │◄────────────────────────────┘
                    └────┬──────────┬────┘
              approve    │          │   refuse (+ mandatory reason)
                    ┌────▼────┐  ┌──▼─────────┐
                    │APPROVED │  │  REFUSED   │──► may be resubmitted with changes
                    └────┬────┘  └────────────┘
                         │ scheduled into the plan, notices issued
                    ┌────▼─────┐
                    │SCHEDULED │  acknowledged distribution; readiness milestones
                    └────┬─────┘
                         │  T-24h readiness gate
              ┌──────────┼─────────────┐
       ready  │          │ not ready   │
        ┌─────▼────┐  ┌──▼──────────┐  │
        │CONFIRMED │  │  AT_RISK    │──┘ ──► DEFERRED / SURRENDERED
        └─────┬────┘  └─────────────┘        (window offered to reserve queue)
              │
              ▼  (execution phase — see H2)
```

**Terminal / exceptional states:** `WITHDRAWN` (requester), `SUPERSEDED` (merged into
another block), `DEFERRED` (re-enters pool with history), `CANCELLED` (post-schedule),
`EXPIRED` (statutory date passed without execution — escalates automatically).

### H1.1 SLA clocks

| Transition                    | Routine         | Mega      | Major works | Emergency |
| ----------------------------- | --------------- | --------- | ----------- | --------- |
| SUBMITTED → DEPT_ENDORSED     | 3 d             | 5 d       | 7 d         | n/a       |
| DEPT_ENDORSED → OPTIONS_READY | 1 d (automated) | 1 d       | 2 d         | n/a       |
| OPTIONS_READY → decision      | 3 d             | 7 d       | 14 d        | minutes   |
| Decision → distribution       | immediate       | immediate | immediate   | immediate |

Breach triggers escalation up the ladder defined in configuration, with each escalation
recorded (S-85).

## H2. The execution lifecycle

This is a separate, tighter state machine, driven by **events**, each timestamped,
attributed and immutable.

```
 CONFIRMED
    │  T-2h  ── pre-block check: resources, people, materials, weather
    ▼
 READY_FOR_GRANT ──────────────────────────────────► (if not ready) SURRENDERED
    │  controller action
    ▼
 GRANTED_ON_LINE          [event: grant_time, granted_by, reason if late]
    │
    ├──► (power block) ISOLATION_REQUESTED → ISOLATION_GRANTED → EARTHING_CONFIRMED
    │                                                    │
    ▼                                                    │
 PROTECTION_IN_PROGRESS   [checklist items, each confirmed + timestamped]
    │                                                    │
    ▼                                                    │
 PROTECTED ◄─────────────────────────────────────────────┘  (both must be true
    │                                                        before work may start)
    ▼
 WORK_IN_PROGRESS         [progress reports, worksite position, incidents]
    │
    ├──► EXTENSION_REQUESTED ──► EXTENSION_APPROVED / EXTENSION_REFUSED
    │         (instant impact computation shown to the controller)
    │
    ▼
 WORK_COMPLETE            [quantum achieved, % complete, balance]
    │
    ▼
 PROTECTION_REMOVAL       [checklist reverse; disconnections restored]
    │
    ▼
 HANDBACK_CERTIFIED       [certifier, fitness, restriction imposed]
    │
    ▼
 LINE_CLEAR_RESTORED      [controller confirms; trains released]
    │
    ▼
 CLOSED                   [post-block report R.1–R.21 complete]
```

**Hard gates (cannot be bypassed):**

- `WORK_IN_PROGRESS` requires `PROTECTED` **and**, if a power block is involved,
  `EARTHING_CONFIRMED`. These are two separate facts (S-38).
- `HANDBACK_CERTIFIED` requires all `Disconnection` records paired (S-40).
- `LINE_CLEAR_RESTORED` requires a named certifier with valid competency (S-33, S-41).
- `CLOSED` requires the post-block report; blocks not closed within 48 h escalate.

## H3. Topology expansion — the derived unavailability engine

The most under-appreciated capability in the whole system. Given a set of blocked track
segments, compute everything else that becomes unusable or degraded.

**Algorithm sketch:**

```
INPUT : blocked_segments B, block window W, network graph G
OUTPUT: derived unavailability set D with reasons

1. Direct         : every segment in B is unavailable.
2. Isolation      : find segments whose ONLY connectivity to the operational network
                    passes through B (graph reachability from every entry point of the
                    section, with B removed). These become STRANDED.
3. Turnout loss   : any turnout physically inside B cannot be operated ⇒ every routing
                    option that requires it is withdrawn ⇒ mark dependent segments
                    ROUTE-LIMITED.
4. Crossover loss : if the crossovers needed for single-line working lie inside B, SLW is
                    infeasible ⇒ the section becomes COMPLETELY BLOCKED rather than SLW.
5. Platform loss  : platforms reachable only via B become UNUSABLE ⇒ passenger impact.
6. Siding loss    : freight sidings/terminals reachable only via B ⇒ placement impact.
7. LC effect      : level crossings inside B — gate working changes; road impact recorded.
8. Traction       : map B onto the traction graph; any elementary section that must be
                    isolated marks all segments under it as ELECTRICALLY DEAD ⇒ electric
                    traction cannot run even if the track is physically clear.
9. Signalling     : disconnected elements ⇒ affected signals/routes ⇒ degraded working
                    method for adjoining segments.
10. Capacity      : for every remaining usable segment, select the applicable
                    CapacityProfile (normal / SLW / single-direction / degraded-signalling)
                    for the window W.
11. Neighbours    : if B touches a divisional boundary, repeat 1–10 across the boundary
                    and flag cross-divisional coordination.

Return D with, for each element, the REASON it is unavailable — reasons are displayed,
never just the conclusion.
```

**Why the reason matters:** an operator who is told "UP Loop unavailable" argues. An
operator who is told "UP Loop unavailable — its only crossover (CO/14) lies inside the
worksite between km 412.300 and 412.800" agrees, or corrects the model. Both outcomes are
good.

## H4. Conflict detection

Run continuously over the open demand pool **and** the approved plan. Five conflict
families:

| Family               | Detection                                                                       | Example                                                              |
| -------------------- | ------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| **Spatial-temporal** | interval overlap on segment extents × time windows                              | Two demands on UP Main km 410–415 on the same Sunday                 |
| **Derived**          | overlap between one demand's extent and another's _derived unavailability set_  | A block that strands the very loop another block's machine must use  |
| **Resource**         | booking overlap on machine/gang/person/material, including mobilisation windows | One tamper, two blocks 60 km apart                                   |
| **Traffic**          | demand window × timetabled paths × capacity profile                             | Block across the path of a protected service                         |
| **Rule**             | demand attributes × rules engine                                                | Block inside a peak-hour embargo; adjacent line open without lookout |

**Output of detection is not a boolean.** Each conflict carries:
`{type, severity (hard/soft), the two objects, the overlapping extent, the overlapping
window, the rule or reason, and — critically — one or more suggested resolutions}`.

Suggested resolutions are what make the feature usable:
`shift by +2h` · `move to Tue 01:00` · `merge with demand D-1043` · `use tamper TM-07
instead` · `reduce extent to km 412–413` · `split into two blocks`.

## H5. The shadow finder — opportunity and bundling engine

Conflict detection asks _"what breaks?"_. The shadow finder asks _"what could be shared?"_
It is the single highest-value algorithm in the system, because it converts a conflict
(bad) into a bundle (good).

### H5.1 What can be shared

1. **The window** — two works on the same extent at the same time.
2. **The protection** — two works within one protected extent, even if not on the same
   metre of track.
3. **The isolation** — two OHE works within the same elementary section.
4. **The traffic disruption** — two works whose traffic cost is largely _the same trains_,
   so doing them together costs barely more than doing one.
5. **The mobilisation** — two works needing the same machine, at nearby locations, in
   sequence, saving one machine movement.
6. **The corridor** — many works along a corridor folded into one declared corridor block.

### H5.2 Algorithm

```
INPUT : open demands D, horizon H, network G, timetable T, resources R
OUTPUT: ranked bundle proposals

STEP 1  CANDIDATE GENERATION
  Group demands by spatial proximity:
    - same segment
    - same protection extent (within P metres, configurable, typically 1–3 km)
    - same elementary traction section
    - same station/yard
    - same corridor
  For each group, generate candidate windows from the union of members' acceptable
  windows (using 4.2 alternative dates and 4.4 flexibility).

STEP 2  COMPATIBILITY FILTER (hard)
  Reject a candidate bundle if ANY of:
    - a member declared "not willing to combine" (10.3 = false)
    - a combination constraint is violated (10.4), e.g. hot work + flammable
    - competing resource demands cannot both be met
    - dependency ordering (10.1) cannot be satisfied within the window
    - combined protection arrangement is not achievable
    - combined duration exceeds the class maximum or the traffic window
    - safety rule forbids simultaneity for those work types

STEP 3  DURATION SYNTHESIS
  Combined duration is NOT the sum. Model it as:
     protection_setup(bundle)            = max over members (shared)
   + isolation(bundle)                   = max over members (shared)
   + effective_work(bundle)              = f(parallelisable?, resource contention,
                                             physical interference)
   + testing(bundle)                     = max, or sum if sequential
   + protection_removal(bundle)          = max (shared)
  where parallelism is limited by:
     - number of independent work fronts the extent supports
     - machine/track-occupancy conflicts within the block
     - safety separation rules between simultaneous activities

STEP 4  IMPACT EVALUATION
  Compute traffic impact of the bundle (H6) and of each member executed separately.
  SAVING = Σ impact(separate) − impact(bundle)
  Also compute: block-hours saved, machine movements saved, protection setups saved.

STEP 5  RANKING
  Score = w1·traffic_saving + w2·block_hours_saved + w3·criticality_advanced
          + w4·resource_efficiency − w5·bundle_risk
  where bundle_risk grows with number of members, number of departments, and
  historical overrun rates of the member work types.

STEP 6  EXPLANATION
  For every proposed bundle emit:
    - members and their contributing demands
    - the shared elements (window / protection / isolation / mobilisation)
    - separate vs bundled impact, side by side
    - the risk factors
    - what would break the bundle (e.g. "if D-1043 slips, the bundle loses 60% of value")
```

### H5.3 Worked example

```
Open demands on the DOWN Main, km 410–416:

 D-1041  Engineering  through packing        km 411.0–413.5  4h  flexible ±3h  Sun/Tue
 D-1043  OHE          insulator replacement  km 412.4        2h  fixed night   Sun
 D-1047  S&T          axle counter alteration km 413.1       3h  flexible      any night
 D-1052  Engineering  drain clearing         km 415.0–415.6  2h  flexible      any

BUNDLE CANDIDATE B-07 : D-1041 + D-1043 + D-1047, Sunday 01:00–06:30
  Shared: one traffic block, one protection setup, one OHE isolation covering 412.4
  Duration synthesis:
      protection setup      0:25  (shared, was 3 × 0:25 = 1:15)
      isolation             0:20  (shared, was 0:20)
      effective work        4:00  (packing 4h; OHE 2h and S&T 3h run in parallel on
                                   separate fronts, both fit inside the packing window)
      testing               0:30  (S&T, sequential at the end)
      protection removal    0:20  (shared)
      TOTAL                 5:35  vs 11:20 if executed separately
  Traffic impact:
      bundled     1 block × 5:35 on a Sunday night =  92 train-minutes, 0 cancellations
      separately  3 blocks                          = 268 train-minutes, 1 cancellation
      SAVING      176 train-minutes, 1 cancellation, 5:45 of block time
  Risk factors:
      3 departments must all be ready simultaneously (historical joint-readiness 78%)
      D-1043 needs the tower wagon — currently booked elsewhere until Sat 22:00,
        mobilisation 1:40 ⇒ feasible but tight
  Excluded: D-1052 (km 415.0) lies outside the protection extent; bundling it would
      extend protection by 1.5 km and add 0:15 setup for only 2h of low-criticality work.
      Offered instead as a bundle with next month's corridor block.
```

That paragraph — automatically generated, in plain language, with numbers — is what a
block planning meeting should be looking at instead of a typed list.

## H6. The impact engine

### H6.1 Layered model

The impact engine answers "what does this block cost?" at three levels of fidelity, chosen
by context:

| Level             | Method                                                                                                                                                   | Latency        | Used for                                                    |
| ----------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- | ----------------------------------------------------------- |
| **L1 Screening**  | Count timetabled paths intersecting the extent × window; apply a per-path average detention factor by section and time band                              | < 100 ms       | Live feedback while the requester types                     |
| **L2 Analytical** | Apply capacity profiles; queueing model for offered vs available capacity; explicit regulation heuristics (loop, precedence, hold); first-order knock-on | 1–5 s          | Conflict detection, bundling ranking, approval screen       |
| **L3 Simulation** | Event-driven simulation of the timetable over the window with rake/crew links, platform occupancy and stochastic delay propagation, multiple runs        | 30 s – minutes | Mega blocks, major works, corridor strategy, disputed cases |

The level used is always displayed with the number. A figure from L1 must never be
presented with the same authority as a figure from L3.

### H6.2 What is computed

```
Affected services       : list of trains, with per-train delay estimate and confidence
Detention               : aggregate train-minutes, split passenger / freight
Cancellations           : services that cannot be pathed at all
Diversions              : services rerouted, with the diversion's own block check (S-47)
Short-termination       : services truncated
Regulation load         : number of crossings/precedences forced onto the controller
Platform impact         : platforms unusable; crowding risk at affected stations
Freight                 : tonnage delayed, terminal placements missed, demurrage exposure
Knock-on                : propagated delay via rake links and crew links, over horizon Hk
Passengers affected     : estimated headcount (from booking/occupancy data where available)
Cost                    : Σ (detention_minutes × unit_cost_by_class)
                          + (cancellations × cancellation_cost)
                          + (freight tonnage-hours × freight_unit_cost)
                          + (demurrage exposure)
Post-block penalty      : capacity cost of any speed restriction imposed after the work,
                          integrated over its expected life  ← frequently forgotten (S-34)
Confidence              : band, plus explicit listing of assumptions and data gaps
```

### H6.3 Comparison, always

An impact number in isolation is meaningless. Every impact is presented **against
alternatives**:

```
  Option                       Detention   Cancel   Freight t   Cost      Score
  ─────────────────────────────────────────────────────────────────────────────
  As requested Sun 10:00-14:00     340 min      3      1 200    ₹ x.xx    41
  Sun 01:00-05:00                   92 min      0        180    ₹ y.yy    88  ★
  Tue 01:00-05:00                   61 min      0          0    ₹ z.zz    94  ★★
  Bundled with D-1043,D-1047        92 min      0        180    ₹ y.yy    97  ★★★
  Do nothing (defer 1 month)          0 min      0          0    —        risk: statutory
```

## H7. Resource feasibility and the readiness gate

### H7.1 Resource model

Each resource carries: identity, type, capabilities, home base, **current location**,
availability calendar, existing bookings, mobilisation model (time as a function of
distance and whether it needs a path), and — for people — competencies with validity dates.

A booking is `(resource, block, from, to, purpose, status)` where `from` includes
mobilisation and `to` includes demobilisation. **The common failure (S-20) is booking only
the working window.**

### H7.2 The readiness gate at T-24h

An automated check, results published to a dashboard, with an owner for each red item:

```
  ☐ Machines confirmed available and positioned within reach       [auto + confirm]
  ☐ Machine path secured for its own movement                      [auto]
  ☐ Gang rostered; consecutive-night rule satisfied                [auto]
  ☐ Nominated person named; competency valid on the date           [auto]
  ☐ Contractor personnel competencies valid                        [auto]
  ☐ Key materials at site / confirmed en route                     [field confirm]
  ☐ Tools and protection equipment available                       [field confirm]
  ☐ Weather forecast acceptable for weather-sensitive work         [auto]
  ☐ Dependencies satisfied (predecessor blocks completed)          [auto]
  ☐ Traffic notices issued and acknowledged                        [auto]
  ☐ Passenger information published (if applicable)                [auto]
  ☐ Power block coordinated with TPC                               [auto + TPC confirm]
  ☐ Disconnection notice issued (if applicable)                    [auto]
  ☐ Site access arrangements confirmed                             [field confirm]
```

Any red item moves the block to `AT_RISK`, notifies the owner, and — this is the important
part — **offers the window to the reserve queue** (S-31) so that if the block is
surrendered, the capacity is not simply lost.

### H7.3 The reserve queue

A standing, ranked list of demands that are:

- **ready now** (resources and materials in place),
- **short** (fit inside a typical surrendered window),
- **flexible** (any date/time),
- **local** (within mobilisation reach of the freed extent).

When a block is surrendered or finishes early, the system immediately proposes the top
candidates to the controller. This converts wasted capacity into maintenance output and is
one of the fastest-payback features in the design.

## H8. The optimiser

### H8.1 Problem statement

> Given a set of demands, each with acceptable windows, durations, extents, resource needs,
> dependencies and criticality; a network with topology and capacity; a timetable; a
> resource pool; and a rule set — select **which demands to schedule, when, and in what
> bundles**, so as to maximise the objective while satisfying all hard constraints.

This is a rich vehicle-routing-flavoured scheduling problem: interval scheduling with
resource constraints, precedence, machine routing, and a non-linear (bundling) cost
structure. It is NP-hard. **We do not need optimality; we need consistently good,
explainable, fast answers.**

### H8.2 Hard constraints (never violated)

```
H-01  Safety rules from the rule engine marked as hard
H-02  No two blocks may claim conflicting exclusive access to the same segment/window
H-03  Resource capacity: no resource double-booked (including mobilisation)
H-04  Competency validity at the time of the block
H-05  Dependency ordering (must_precede / must_follow / simultaneous)
H-06  Statutory due dates
H-07  Configured embargo and peak windows (override requires authorised human action)
H-08  Class notice periods
H-09  Consecutive-night and rest rules for human resources
H-10  Adjacent-line protection requirement satisfied
H-11  Traction isolation feasibility (a valid minimal isolation must exist)
H-12  SLW feasibility (usable crossovers outside the worksite)
H-13  Section must not be rendered completely impassable beyond configured limits
H-14  Cross-divisional agreement present where required
```

### H8.3 Soft constraints (penalised)

```
S-01  Deviation from the requester's preferred date/time
S-02  Night work (staff welfare and productivity penalty)
S-03  Weekend/holiday work
S-04  Splitting a divisible work into multiple blocks
S-05  Bundling risk (multi-department joint readiness)
S-06  Machine deadheading distance
S-07  Proximity to a protected service's path
S-08  Consecutive blocks on the same section (passenger fatigue)
S-09  Deviation from the historical duration model
S-10  Contractual notice breaches
S-11  Weather risk for sensitive work
S-12  Concentration of blocks in one sub-division (equity across units)
```

### H8.4 Objective function

```
maximise
      W_maint  · Σ (criticality_weight(d) × completion(d) × urgency_factor(d))
    − W_traffic· Σ (detention_minutes × class_weight)
    − W_cancel · Σ (cancellations × cancellation_weight)
    − W_freight· Σ (freight_tonne_hours_delayed)
    − W_cost   · Σ (indicative_monetary_cost)
    + W_bundle · Σ (block_hours_saved_by_bundling)
    + W_resource·Σ (machine_utilisation_improvement)
    − W_soft   · Σ (soft_constraint_penalties)
    − W_restr  · Σ (post_block_restriction_capacity_penalty)

subject to  H-01 .. H-14
```

All `W_*` are **published configuration**, set by the Division within Zone-defined bounds,
versioned, and shown on every result screen. A department that dislikes an outcome can see
exactly which weight produced it and argue about the weight rather than about the machine.

### H8.5 Solution approach

A pragmatic three-stage pipeline, chosen for explainability as much as for quality:

```
STAGE 1  CONSTRUCT  (greedy, seconds)
  Sort demands by criticality × urgency × inflexibility.
  Place each into its best feasible window using the impact engine at L1/L2.
  Apply shadow finder opportunistically at each placement.
  → produces a feasible baseline quickly; ALWAYS available even if later stages time out.

STAGE 2  IMPROVE  (local search / LNS, tens of seconds)
  Neighbourhood moves:
     shift a block in time
     swap two blocks' windows
     merge two blocks into a bundle
     split a bundle
     reassign a machine
     move a block to an alternative acceptable date
     change SLW ↔ complete block configuration
  Accept by simulated annealing / large-neighbourhood search on the objective.
  → typically recovers most of the gap to good solutions.

STAGE 3  EXACT sub-problems  (CP/MIP, where it pays)
  Solve small, high-value sub-problems exactly:
     machine routing over a week for a scarce machine
     the corridor block composition for one weekend
     resolution of a tightly-coupled dependency cluster
  → exactness where it matters, heuristics where it does not.
```

**Determinism requirement:** the same inputs and the same weights must produce the same
output. Random seeds are fixed and recorded in the `PlanningRun` so any past
recommendation can be reproduced exactly for an audit (S-79).

### H8.6 Output: options, not an answer

The optimiser always returns **3–5 distinct options**, deliberately diversified:

```
 Option A  "Least traffic impact"      — optimises detention above all
 Option B  "Maximum maintenance output"— clears the most criticality-weighted backlog
 Option C  "Balanced"                  — the published default weights
 Option D  "Requester-preferred"       — honours stated preferences, shows what it costs
 Option E  "Minimum risk"              — avoids bundles and tight resource situations
```

Presenting a single "optimal" plan invites either blind acceptance (S-93) or rejection of
the whole system. Presenting the trade-off is both more honest and more persuasive.

## H9. Explainability — the non-negotiable layer

Every recommendation carries a machine-generated explanation with four parts:

1. **What is proposed** — plain language: _"Move D-1041 to Tuesday 01:00–06:35 and bundle
   with D-1043 and D-1047."_
2. **Why** — the binding factors: _"Sunday 10:00 conflicts with 3 protected services
   (248 train-minutes). Tuesday night has no protected services on this section. Bundling
   saves 5 h 45 m of block time and one tower-wagon movement."_
3. **What was rejected and why** — _"Sunday 01:00 was rejected: the tower wagon is
   committed at Y until 22:00 Saturday; mobilisation would arrive 00:40, leaving
   insufficient margin. Monday was rejected: gang would exceed the consecutive-night
   limit."_
4. **What would change the answer** — _"If the tower wagon were released 3 h earlier,
   Sunday 01:00 becomes feasible and scores 2 points higher. If D-1047 withdraws, the
   bundle loses 40% of its value and Option D becomes preferable."_

Part 4 is the most valuable and the most often omitted in optimisation products. It turns
the system from an oracle into a colleague.

## H10. The rules engine

### H10.1 Structure of a rule

```
Rule R-0142
  Title       : Adjacent line must be blocked for work involving machines on track
  Citation    : <manual / circular / enquiry recommendation reference>
  Class       : HARD
  Scope       : work_category IN (track renewal, geometry) AND method = mechanised
  Expression  : adjacent_line_status IN ('blocked','physically_separated')
  Message     : "Machine work requires the adjacent line to be blocked or physically
                 separated. Select an adjacent-line arrangement or request a combined block."
  Effective   : from 2026-xx-xx
  Version     : 3
  Approved by : Divisional Safety Officer, <date>
  Supersedes  : R-0142 v2
```

### H10.2 Properties

- **Cited.** Every rule names its source authority. A rule with no citation cannot be
  activated (prevents the system becoming an unaudited parallel rule book).
- **Versioned and dated.** Historical decisions are evaluated against the rule version in
  force at the time — essential for audit.
- **Classified.** `HARD` (blocks), `SOFT` (penalises), `WARN` (informs), `INFO`.
- **Testable.** Every rule ships with test cases proving it fires and does not over-fire.
- **Reportable.** _"Show me every rule derived from enquiry X"_ and _"show me every block
  refused by rule R-0142 in the last year"_ are first-class queries (S-44).
- **Safety-approved.** Changes to `HARD` rules require the safety authority's signature.

### H10.3 Rule families

```
SAFETY        protection, isolation, competency, adjacent line, hazards, separation
STATUTORY     inspection due dates, mandated intervals, regulatory sanction requirements
OPERATIONAL   notice periods, embargo windows, peak protection, capacity floors
RESOURCE      consecutive nights, rest, machine operating limits, competency validity
ENVIRONMENTAL rail temperature, wind limits for height work, visibility, noise
COMMERCIAL    contractual notice, freight commitment windows
PROCEDURAL    who may approve what, delegation limits, acknowledgement requirements
```

## H11. The learning loop

```
   ┌──────────────┐   plan     ┌──────────────┐  execute  ┌──────────────┐
   │  ESTIMATES   │───────────►│    BLOCKS    │──────────►│   ACTUALS    │
   │ duration     │            │              │           │ grant time   │
   │ impact       │            │              │           │ start time   │
   │ resources    │            │              │           │ work time    │
   └──────▲───────┘            └──────────────┘           │ handback     │
          │                                               │ quantum      │
          │                                               │ reason codes │
          │                                               └──────┬───────┘
          │                                                      │
          │            ┌──────────────────────────┐              │
          └────────────│  CALIBRATION & LEARNING  │◄─────────────┘
                       │  • duration models by    │
                       │    (work type, quantum,  │
                       │     method, resources,   │
                       │     season, unit)        │
                       │  • protection time models│
                       │  • grant-delay models    │
                       │  • overrun risk models   │
                       │  • delay-propagation     │
                       │    calibration           │
                       │  • bundle-success rates  │
                       └──────────────────────────┘
```

### H11.1 What is learned, and how it is used

| Learned quantity          | Method                                                                    | Used in                                       |
| ------------------------- | ------------------------------------------------------------------------- | --------------------------------------------- |
| Effective work duration   | Regression / quantile model on (work type, quantum, method, gang, season) | Field 4.10 suggestion; optimiser durations    |
| Protection setup time     | Empirical distribution by extent, method, location type                   | Duration decomposition                        |
| Grant delay               | Distribution by section, time band, controller shift                      | Realistic start-time planning; KPI            |
| Overrun probability       | Classification on plan attributes                                         | Bundle risk; contingency margin               |
| Delay propagation factor  | Calibration of the L2 analytical model against observed outcomes          | Impact engine accuracy                        |
| Bundle joint-readiness    | Frequency by department combination                                       | Bundle risk penalty                           |
| Requester estimation bias | Claimed vs actual per unit                                                | Scorecards; automatic de-biasing of estimates |

### H11.2 Guardrails on learning

- **Never let a learned model relax a safety rule.** Learning affects estimates and
  rankings only; hard constraints are human-authored.
- **Show the model's confidence.** A suggestion from 4 historical samples is presented
  differently from one based on 400.
- **Keep a human override with a reason.** The override itself becomes training data.
- **Detect drift.** If actuals diverge systematically from the model, raise it rather than
  silently re-fitting.

---

# Part I — Architecture and System Flow

## I1. Architectural drivers

The architecture is shaped by six forces, in priority order:

| #   | Driver                                                                                                             | Architectural consequence                                                                                 |
| --- | ------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------- |
| 1   | **Safety-relevant state must never be wrong or silently stale**                                                    | Explicit state confirmation, append-only event log, fail-safe defaults, staleness surfaced in the UI      |
| 2   | **Reads vastly outnumber writes, and read patterns differ wildly** (a map query is nothing like an approval query) | Separate the read model from the write model; optimise each independently                                 |
| 3   | **Analysis is expensive and asynchronous; the user must not wait**                                                 | Analysis runs continuously in the background, results are materialised, the UI reads pre-computed answers |
| 4   | **Many downstream consumers** (passenger info, caution orders, rosters, dashboards, neighbouring divisions)        | Publish domain events; let consumers subscribe rather than polling a database                             |
| 5   | **The field is offline and unreliable**                                                                            | Offline-first client with local durable store, idempotent sync, conflict resolution                       |
| 6   | **Everything must be auditable and reproducible**                                                                  | Event sourcing for the block lifecycle; snapshot every planning run's inputs and weights                  |

## I2. Logical architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  CLIENTS                                                                     │
│  ┌────────────┐ ┌─────────────┐ ┌──────────────┐ ┌───────────┐ ┌──────────┐  │
│  │ Planner    │ │ Control     │ │ Field app    │ │ Executive │ │ External │  │
│  │ workspace  │ │ room console│ │ (offline)    │ │ dashboard │ │ portal   │  │
│  └────────────┘ └─────────────┘ └──────────────┘ └───────────┘ └──────────┘  │
└──────────────────────────────┬───────────────────────────────────────────────┘
                               │  HTTPS / WebSocket / sync protocol
┌──────────────────────────────▼───────────────────────────────────────────────┐
│  EDGE  —  API gateway: authentication, authorisation, rate limiting,          │
│           request correlation, API versioning, schema validation              │
└───────────────┬──────────────────────────────────────┬───────────────────────┘
                │ commands (state change)              │ queries (read)
┌───────────────▼───────────────┐      ┌───────────────▼───────────────────────┐
│  COMMAND SIDE                 │      │  QUERY SIDE                           │
│  ┌─────────────────────────┐  │      │  ┌─────────────────────────────────┐  │
│  │ Demand service          │  │      │  │ Read models (materialised):     │  │
│  │ Block lifecycle service │  │      │  │  • map tiles / spatial index    │  │
│  │ Execution service       │  │      │  │  • forward block calendar       │  │
│  │ Approval service        │  │      │  │  • conflict & bundle views      │  │
│  │ Resource service        │  │      │  │  • train graph projection       │  │
│  │ Safety/protection svc   │  │      │  │  • dashboards & KPIs            │  │
│  │ Master data service     │  │      │  │  • search index                 │  │
│  └───────────┬─────────────┘  │      │  └─────────────────────────────────┘  │
│              │ writes         │      │              ▲ serves                 │
│  ┌───────────▼─────────────┐  │      │              │                        │
│  │ OPERATIONAL STORE       │  │      │  ┌───────────┴─────────────────────┐  │
│  │ (source of truth)       │  │      │  │ Cache (hot: live blocks,        │  │
│  │  relational + spatial   │  │      │  │ current positions, today's plan)│  │
│  │  + append-only event log│  │      │  └─────────────────────────────────┘  │
│  └───────────┬─────────────┘  │      └───────────────────────────────────────┘
└──────────────┼────────────────┘                      ▲
               │ domain events                         │ projections
┌──────────────▼───────────────────────────────────────┴───────────────────────┐
│  EVENT BACKBONE  (durable, ordered, replayable)                              │
│  topics: demand.* · block.* · execution.* · safety.* · resource.* ·          │
│          traffic.* · restriction.* · planning.* · notification.* · audit.*   │
└──┬────────────┬────────────┬────────────┬────────────┬───────────────────────┘
   │            │            │            │            │
┌──▼─────────┐┌─▼──────────┐┌▼──────────┐┌▼──────────┐┌▼─────────────────────┐
│ ANALYSIS   ││ OPTIMISER  ││NOTIFICATION││ PROJECTOR ││ INTEGRATION ADAPTERS │
│ • topology ││ • construct││ • channels ││ • builds  ││ • timetable          │
│ • conflict ││ • improve  ││ • ack      ││   read    ││ • train tracking     │
│ • bundling ││ • exact    ││   tracking ││   models  ││ • EAM / work orders  │
│ • impact   ││ • explain  ││ • escalate ││           ││ • freight ops        │
│ • rules    ││            ││            ││           ││ • weather            │
│ • learning ││            ││            ││           ││ • passenger info     │
└────────────┘└────────────┘└────────────┘└───────────┘└──────────────────────┘
```

## I3. Why this shape

**Command/query separation.** The approval screen needs consistency and transactional
integrity over a handful of records. The map needs to render thousands of geometries in
under a second. These are irreconcilable in a single model. Separating them lets each be
right.

**Event backbone.** Six independent consumers need to know that a block was approved:
notifications, the map projector, the caution-order generator, passenger information, the
roster system and the neighbouring division. Point-to-point integration between them is a
combinatorial mess. A published, versioned event is one write and N independent readers.

**Analysis as a subscriber, not a request handler.** Conflict detection over the whole
open demand set is expensive and must be continuous. Making it a synchronous API call
would make every form submission slow and would recompute the same thing repeatedly.
Instead it subscribes to changes, recomputes affected regions, and writes materialised
results that the UI reads instantly.

**Event sourcing for the block lifecycle only.** Full event sourcing everywhere is
overkill. But for blocks — where every state transition is a safety and accountability
record — the event log _is_ the requirement, not an implementation choice. State is a
projection; the log is the truth.

**Operational store is authoritative.** Caches expire, read models are rebuildable, event
topics have retention. Exactly one place holds the truth, and it is transactional.

## I4. Component responsibilities

| Component                   | Owns                                                                                                                  | Must not                                                                  |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| **API gateway**             | AuthN, coarse AuthZ, routing, versioning, rate limits, correlation IDs                                                | Contain domain logic                                                      |
| **Demand service**          | Demand creation, amendment, validation, templates, dependency graph                                                   | Decide approvals                                                          |
| **Block lifecycle service** | Block state machine, transitions, guards, scheduling into the plan                                                    | Perform analysis                                                          |
| **Execution service**       | Grant, protection checklist, progress, extension, hand-back, actuals                                                  | Approve extensions autonomously                                           |
| **Approval service**        | Workflow, roles, delegation, SLA clocks, escalation, decision records                                                 | Alter block content                                                       |
| **Resource service**        | Resource master, bookings, mobilisation, competency validation, readiness gate                                        | Own the roster system                                                     |
| **Safety service**          | Protection states, isolation states, disconnection register, competency gates, rules enforcement at transition points | Be bypassable                                                             |
| **Master data service**     | Topology, traction graph, assets, calendars, capacity profiles, rules, weights                                        | Be edited without audit                                                   |
| **Analysis workers**        | Topology expansion, conflict detection, shadow finder, impact, learning                                               | Write to the operational store directly (they publish results)            |
| **Optimiser**               | Planning runs, options, scores, explanations                                                                          | Commit a plan                                                             |
| **Notification service**    | Channel dispatch, delivery/acknowledgement tracking, escalation                                                       | Decide who is a stakeholder (that is domain logic, supplied in the event) |
| **Projector**               | Build and maintain read models from events                                                                            | Contain business rules                                                    |
| **Integration adapters**    | Translate external systems to/from domain events; handle their unreliability                                          | Leak external schemas into the domain                                     |

## I5. Principal flows

### I5.1 Demand submission (write path)

```
Field/Web client
  → API gateway            [authn, authz, correlation-id]
  → Demand service         [schema validation, V-01..V-24]
       ├─ synchronous: entry-time validation, duplicate check, L1 impact preview
       └─ persist Demand (versioned) in operational store
  → publish  demand.submitted
       ├─► Analysis workers   : topology expansion, conflict detection, bundling, L2 impact
       │        └─ publish analysis.completed  → Projector → read model
       ├─► Notification       : acknowledge to requester; notify dept officer
       ├─► Projector          : demand appears on calendar + map immediately
       └─► Audit              : immutable record
```

The requester gets an instant response (validation + L1 preview) and a richer answer
(conflicts, bundles, L2 impact) a few seconds later, pushed to the open screen.

### I5.2 Planning run and approval

```
Trigger: schedule (nightly), or planner action, or material change to the demand pool
  → Optimiser
       ├─ snapshot inputs (demands, network, timetable, resources, rules, weights)
       ├─ Stage 1 construct → Stage 2 improve → Stage 3 exact sub-problems
       ├─ produce 3–5 options with scores, component scores, explanations
       └─ persist PlanningRun (inputs hash, seed, weights version) — reproducible
  → publish planning.options_ready
       └─► Projector → planner workspace shows options side by side

Planner/approver
  → reviews options, impact, explanations; may adjust and re-run
  → Approval service: approve / modify / refuse  [+ mandatory justification if not top-ranked]
  → Block lifecycle service: blocks move to APPROVED → SCHEDULED
  → publish block.approved, block.scheduled
       ├─► Notification    : acknowledged distribution to all stakeholders
       ├─► Integration     : passenger information, caution order data, roster hints
       ├─► Analysis        : re-run conflict detection against the new baseline
       └─► Audit           : Decision record (options, chosen, decider, justification)
```

### I5.3 Execution day (event path)

```
T-24h  Resource service runs the readiness gate
         → publish block.at_risk (if any red) → Notification → owner
         → offer window to reserve queue if surrender likely

T-2h   Field app: pre-block check; party mobilising
         → execution.party_mobilising

T-0    Controller grants on line
         → execution.granted  {actual time, granted_by, late reason}
         → Projector: map turns the block from PLANNED to ACTIVE
         → KPI: grant punctuality

       TPC isolation (if power block)
         → safety.isolation_granted → safety.earthing_confirmed

       Field app: protection checklist items confirmed one by one
         → safety.protection_item_confirmed × n → safety.protected

       Gate: work may start only when protected (and earthed, if applicable)
         → execution.work_started

       Progress reports, worksite position
         → execution.progress {percent, position}
         → map updates the live work front

       Extension requested
         → execution.extension_requested
         → Impact engine (L2, seconds) → controller sees cost of granting
         → execution.extension_decided {granted/refused, reason, impact shown}

       Work complete → protection removed → disconnections restored
         → safety.protection_removed, safety.disconnections_restored

       Hand-back certified
         → execution.handback_certified {certifier, fitness, restriction imposed}
         → restriction.created (if any) → Restriction register + caution order data
         → execution.line_clear_restored
         → Projector: map clears the block; controller prompted to release held trains

T+     Post-block report
         → execution.closed {quantum, %, reasons, incidents}
         → Learning: recalibrate duration/protection/overrun models
```

### I5.4 Emergency flow

```
Field user (possibly offline)
  → minimal emergency form (G15) captured locally, queued
  → on first connectivity: emergency.raised  (or, if offline > threshold, the app
    instructs the user to use the voice fallback and records that it did so)
  → Control console: high-priority alarm; block appears on the map immediately as
    UNCONFIRMED EMERGENCY
  → Controller confirms and grants; trains stopped/regulated
  → Analysis: identify affected planned blocks → block.at_risk for each
                 → owners notified, items enter re-planning queue
  → Impact engine runs continuously and updates the projected recovery time
  → Formalisation of the full record continues in parallel, never blocking the response
```

### I5.5 Disruption / bulk re-planning

```
Authorised officer declares a disruption (weather, accident, security)
  → disruption.declared {extent, expected duration}
  → Block lifecycle: all blocks in extent × window → SUSPENDED (not cancelled)
  → all suspended demands enter the re-planning queue with their history intact
  → Optimiser runs in "recovery mode": relaxed soft constraints, restoration work
    given top criticality weight
  → Executive dashboard switches to incident view
```

## I6. Notification and acknowledgement fabric

A block's stakeholder set is **computed**, not typed:

```
stakeholders(block) =
    requester + department officer + sponsoring officer
  + nominated person + deputy + gang supervisor
  + section controller(s) on duty for the window + chief controller
  + TPC (if power block) + S&T supervisor (if disconnection)
  + station masters within extent + adjacent station masters
  + level crossing staff within extent
  + neighbouring division control (if cross-boundary)
  + machine operators of booked machines
  + contractor site representative
  + safety officer (if class or hazard requires)
  + passenger information desk (if services affected)
  + freight terminal (if placements affected)
```

Each notification carries: what changed, why, what the recipient must do, and by when.
Channels are tiered by urgency: in-app → push → SMS → voice call for safety-critical
changes within 12 hours of a block.

**Acknowledgement is tracked per recipient.** An "outstanding acknowledgements" panel is
visible to the planner and the controller. Non-acknowledgement within the configured
window escalates. A block whose safety-critical stakeholders have not acknowledged is
flagged at the readiness gate.

## I7. Integration landscape

| External system                                | Direction | Payload                                              | Failure mode & handling                                                     |
| ---------------------------------------------- | --------- | ---------------------------------------------------- | --------------------------------------------------------------------------- |
| Timetable / path planning                      | in        | Paths, formations, priority classes, planned changes | Cache last-known; mark impact figures as based on a stale timetable         |
| Train tracking / control                       | in        | Positions, actual times, delays                      | Degrade to last-reported-station; show position confidence on the map       |
| EAM / work order system                        | in/out    | Work orders as demands; execution actuals back       | Queue; reconcile on recovery; never lose an actual                          |
| Asset condition (USFD, TRC, OMS, thermovision) | in        | Measurements driving criticality                     | Optional enrichment; absence must not block                                 |
| Freight operations                             | in        | Rake positions, terminal placement schedules         | Impact figures degrade to "freight impact unknown" — stated explicitly      |
| Weather                                        | in        | Forecast, alerts                                     | Advisory only; absence produces a warning, not a block                      |
| Passenger information                          | out       | Service disruption payloads                          | Retry with backoff; alert if undelivered before the notice deadline         |
| Caution order system                           | out       | Restriction data from hand-back                      | Must be idempotent; duplicates are a safety nuisance                        |
| Roster / HR                                    | in        | Availability, competency validity                    | Absence ⇒ competency check cannot pass ⇒ manual override with justification |
| Identity provider                              | in        | Users, roles, org units                              | Cached with short TTL; emergency local fallback accounts for control rooms  |
| Neighbouring division instance                 | both      | Cross-boundary blocks and coordination               | Asynchronous; explicit agreement state                                      |

**Integration principles:**

1. **Adapters, not couplings.** External schemas never enter the domain model.
2. **Every integration must have a defined degraded behaviour**, and that behaviour must be
   _visible in the UI_, not silent.
3. **Idempotency everywhere.** Every outbound message carries a stable key.
4. **Pull the minimum, cache aggressively, timestamp everything.** The UI always shows
   "as at HH:MM" for externally-sourced data.

## I8. The API surface (indicative)

Grouped by intent rather than by table.

```
DEMAND
  POST   /demands                          create draft
  PATCH  /demands/{id}                     amend (creates a version)
  POST   /demands/{id}/submit
  POST   /demands/{id}/withdraw
  GET    /demands?filters                  list with facets
  GET    /demands/{id}/analysis            conflicts, bundles, impact, rule findings
  POST   /demands/preview                  unsaved draft → live decision support (L1)
  GET    /demands/templates
  POST   /demands/from-template/{tid}

PLANNING
  POST   /planning/runs                    trigger a run over a horizon
  GET    /planning/runs/{id}/options
  GET    /planning/runs/{id}/options/{oid}/explanation
  POST   /planning/runs/{id}/options/{oid}/adopt
  GET    /planning/calendar?from&to&scope  the forward access plan
  GET    /planning/bundles                 current bundling opportunities

BLOCK
  GET    /blocks?window&extent&status
  GET    /blocks/{id}
  POST   /blocks/{id}/approve | /refuse | /modify
  POST   /blocks/{id}/schedule
  POST   /blocks/{id}/cancel | /defer | /surrender
  GET    /blocks/{id}/stakeholders
  GET    /blocks/{id}/readiness
  GET    /blocks/{id}/timeline            full event history (audit view)

EXECUTION
  POST   /blocks/{id}/grant
  POST   /blocks/{id}/protection/items/{item}/confirm
  POST   /blocks/{id}/isolation/request | /granted | /earthed | /removed
  POST   /blocks/{id}/work/start | /progress | /complete
  POST   /blocks/{id}/extension/request | /decide
  POST   /blocks/{id}/handback
  POST   /blocks/{id}/report              post-block report
  POST   /blocks/{id}/incident

EMERGENCY
  POST   /emergency                        minimal payload, high priority
  POST   /disruptions                      declare bulk disruption

MAP & SITUATION
  GET    /map/state?bbox&at&layers         everything renderable at instant `at`
  GET    /map/tiles/{layer}/{z}/{x}/{y}    vector tiles for static-ish layers
  WS     /live                             subscription: positions, block states, alerts
  GET    /traingraph?section&from&to       time–distance projection
  GET    /conflicts?window&extent

RESOURCES
  GET    /resources?type&near&window
  POST   /resources/{id}/bookings
  GET    /resources/{id}/itinerary
  GET    /competency/{person}/validity

REFERENCE
  GET    /network/segments?bbox | /nodes | /turnouts | /elementary-sections
  POST   /network/expand                   derived unavailability for a given extent
  GET    /rules | /calendars | /weights
  GET    /restrictions?active&extent

ANALYTICS
  GET    /kpi/{metric}?scope&period
  GET    /scorecards/{unit}
  GET    /reports/{report}?params
```

**API conventions:** versioned (`/v1`), idempotency keys on all POSTs that create state,
correlation IDs propagated end to end, every response carrying `as_of` timestamps for any
derived or externally-sourced data, and explicit `confidence` on every computed figure.

## I9. Data architecture

| Store                                  | Purpose                                                     | Characteristics                                                                                                 |
| -------------------------------------- | ----------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| **Operational (relational + spatial)** | Source of truth for demands, blocks, resources, master data | ACID, constraints, spatial indexes on geometry and chainage ranges, temporal ranges indexed for overlap queries |
| **Event log (append-only)**            | Every block lifecycle and safety event                      | Immutable, ordered per aggregate, replayable, retained per statutory policy                                     |
| **Read models**                        | Map state, calendar, dashboards, conflict views, search     | Denormalised, rebuildable from events, optimised per query shape                                                |
| **Cache**                              | Today's plan, live block states, current positions          | Short TTL; never authoritative; every cached value carries its age                                              |
| **Analytics store**                    | Historical actuals, KPI time series, model training data    | Columnar; append-heavy; separated from the operational path                                                     |
| **Object store**                       | Photographs, method statements, sketches, certificates      | Content-addressed, virus-scanned, retention-tagged                                                              |

**Key modelling decisions:**

- **Dual location model.** Every spatial object carries _both_ a geographic geometry (for
  the map) and a linear reference (line + chainage range, for railway reasoning). Neither
  alone is sufficient: the map needs geometry; overlap detection, caution orders and asset
  linkage need chainage.
- **Temporal ranges are first-class.** Blocks, restrictions, bookings and paths are all
  intervals. Overlap queries are the most common operation in the system and must be
  indexed as such.
- **Everything safety-relevant is bitemporal.** We record both _when it happened_ and
  _when we learned it_, because late field synchronisation is normal and an audit must be
  able to distinguish the two.
- **Soft deletes are forbidden for safety records.** Corrections are new records that
  reference and supersede the old, with a reason.

## I10. Non-functional requirements

| Concern                              | Requirement                                                                                                                                                                         |
| ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Availability**                     | Control-room and field-critical functions: 99.9%; planning functions: 99.5%. Degraded mode must keep the _current day's_ block picture available even during a full backend outage. |
| **Map responsiveness**               | Initial situational view < 2 s; pan/zoom < 200 ms; live updates < 3 s from event.                                                                                                   |
| **Decision support latency**         | L1 preview < 300 ms; L2 analysis < 5 s; L3 simulation asynchronous with progress indication.                                                                                        |
| **Optimiser**                        | Feasible baseline within 30 s for a divisional horizon; improved solution within 5 min; always returns the best-so-far.                                                             |
| **Scale (per division, indicative)** | 10³–10⁴ track segments; 10³ demands per year; 10²–10³ trains per day; 10² concurrent users; 10¹–10² live blocks at peak.                                                            |
| **Field sync**                       | Must function with 0 connectivity for a full shift; sync completes within 60 s of connectivity restoration; conflicts surfaced, never silently resolved.                            |
| **Security**                         | Role and jurisdiction-scoped authorisation on every call; MFA for approval roles; full audit; third parties strictly sandboxed to their own works.                                  |
| **Data protection**                  | Personal data minimised; photographs scanned; retention policies enforced automatically.                                                                                            |
| **Accessibility**                    | Outdoor-readable contrast, large touch targets, multilingual, screen-reader support on office interfaces.                                                                           |
| **Observability**                    | Every decision, every integration call and every optimiser run traceable by correlation ID; alerting on stale integrations and projection lag.                                      |
| **Reproducibility**                  | Any past recommendation must be exactly reproducible from its recorded inputs, weights and seed.                                                                                    |

---

# Part J — Frontend and Experience Design

## J1. UX principles

1. **The map is the home page.** Railway people think in geography and time. Lists are for
   filtering; the map is for understanding.
2. **One screen per decision.** An approver should never need a second tab to decide. The
   demand, the impact, the options, the conflicts and the explanation are on one screen.
3. **Show the answer, then the working.** Headline number first; the derivation one click
   away; the assumptions always reachable.
4. **Colour means one thing, everywhere.** A single semantic palette across map, lists,
   timeline and dashboards. Never re-use a colour for a different meaning in a different view.
5. **Never hide uncertainty.** Stale data, low-confidence figures and unavailable
   integrations are shown, not smoothed over.
6. **Different users, radically different surfaces.** The field app and the executive
   dashboard share a backend and nothing else.
7. **Keyboard-first for the control room.** Controllers work under time pressure with a
   keyboard; every frequent action has a shortcut.
8. **Undo over confirm.** Reversible actions execute immediately with an undo affordance;
   only irreversible or safety-critical actions get a confirmation dialog. Confirmation
   fatigue is a safety hazard.

## J2. Semantic palette

| Meaning                           | Colour                                          | Used for                                                    |
| --------------------------------- | ----------------------------------------------- | ----------------------------------------------------------- |
| **Active block (in force now)**   | Red, solid                                      | Map segment, list row accent, timeline bar                  |
| **Granted, not yet protected**    | Red, hatched                                    | Transitional safety state                                   |
| **Approved / scheduled (future)** | Amber, solid                                    | Planned blocks                                              |
| **Requested / under review**      | Amber, dashed outline                           | Demands not yet approved                                    |
| **Proposed by optimiser**         | Violet, dotted                                  | System suggestions — visually distinct from human decisions |
| **Bundle candidate**              | Violet, with a connecting brace                 | Bundling opportunities                                      |
| **Conflict**                      | Magenta, pulsing outline                        | Anything requiring resolution                               |
| **Restriction (speed)**           | Orange, dashed line along track                 | TSR/PSR                                                     |
| **Emergency / incident**          | Red, flashing halo                              | Emergency blocks, incidents                                 |
| **Train (passenger)**             | Blue                                            | Position marker                                             |
| **Train (freight)**               | Green                                           | Position marker                                             |
| **Train (delayed > threshold)**   | Blue/green with red ring                        | Delay indication                                            |
| **Line available**                | Slate grey                                      | Normal track                                                |
| **Line unavailable (derived)**    | Grey, hatched                                   | Not blocked itself, but rendered unusable                   |
| **Electrically dead**             | Grey with a lightning-strike-through pattern    | Traction isolation footprint                                |
| **Stale / low confidence**        | Any of the above at 50% opacity + a clock badge | Honest degradation                                          |

Colour is never the _only_ channel: every state also has a pattern (solid/dashed/hatched)
and an icon, for accessibility and for greyscale printing.

## J3. Information architecture

```
┌─ SITUATION            (default landing for controllers and officers)
│    ├─ Live map
│    ├─ Train graph (time–distance)
│    ├─ Now panel: active blocks, alerts, extensions pending
│    └─ Shift handover pack
│
├─ PLAN
│    ├─ Forward calendar (day / week / month / corridor)
│    ├─ Planning workspace (options, comparison, adoption)
│    ├─ Bundling opportunities
│    ├─ Conflicts
│    └─ Corridor & mega-block strategy
│
├─ DEMANDS
│    ├─ My demands / My department / All (scoped)
│    ├─ New demand (map-first wizard)
│    ├─ Templates & recurring
│    └─ Reserve queue
│
├─ EXECUTION
│    ├─ Today's blocks (control view)
│    ├─ Readiness board (T-24h gate)
│    ├─ Live block console (per block)
│    └─ Post-block reports outstanding
│
├─ RESOURCES
│    ├─ Machines (itinerary & utilisation)
│    ├─ Gangs & competencies
│    ├─ Materials
│    └─ Contractors
│
├─ NETWORK
│    ├─ Topology browser & editor (master data)
│    ├─ Traction network
│    ├─ Assets & condition
│    └─ Restrictions register
│
├─ ANALYTICS
│    ├─ KPI dashboard (scoped)
│    ├─ Departmental scorecards
│    ├─ Backlog & ageing
│    └─ Reports & exports
│
└─ ADMIN
     ├─ Users, roles, delegation
     ├─ Rules (with citations & versions)
     ├─ Weights & calendars
     └─ Integrations health
```

## J4. Screen — Situation (the landing page)

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ ☰  RAILWAY ACCESS & BLOCK MANAGEMENT      Division: DLI ▾    🔔 4    👤 Sr.DOM      │
├──────────────────────────────────────────────────────────────────────────────────────┤
│ [SITUATION] [PLAN] [DEMANDS] [EXECUTION] [RESOURCES] [NETWORK] [ANALYTICS]           │
├───────────────┬──────────────────────────────────────────────────┬───────────────────┤
│ LAYERS        │                                                  │ NOW               │
│ ☑ Track       │                                                  │───────────────────│
│ ☑ Blocks      │                                                  │ ⚠ 2 EXTENSIONS    │
│   ☑ Active    │                                                  │   PENDING         │
│   ☑ Planned   │              [ M A P   C A N V A S ]             │  B-2291  +45 min  │
│   ☑ Requested │                                                  │   impact 62 min   │
│   ☑ Proposed  │        (see Part K for full map specification)   │   [Grant][Refuse] │
│ ☑ Restrictions│                                                  │  B-2288  +20 min  │
│ ☑ Trains      │                                                  │   impact  8 min   │
│   ☑ Passenger │                                                  │   [Grant][Refuse] │
│   ☑ Freight   │                                                  │───────────────────│
│ ☑ Conflicts   │                                                  │ ACTIVE BLOCKS  3  │
│ ☐ Traction    │                                                  │ ● B-2291 UP Main  │
│ ☐ Assets      │                                                  │   412.1–413.5     │
│ ☐ Resources   │                                                  │   ends 14:00 ⏱1:12│
│───────────────│                                                  │   ▓▓▓▓▓▓░░░ 68%   │
│ FILTERS       │                                                  │ ● B-2288 DN Loop  │
│ Dept  [All ▾] │                                                  │ ● E-0034 EMERGENCY│
│ Class [All ▾] │                                                  │   rail fracture   │
│ Status[All ▾] │                                                  │───────────────────│
│───────────────┤                                                  │ NEXT 6 HOURS   5  │
│ ◀◀ ◀ ▶ ▶▶     │                                                  │ 14:30 B-2295 …    │
│ ┌───────────┐ │                                                  │ 16:00 B-2301 …    │
│ │ TIME      │ │                                                  │───────────────────│
│ │ ●────────│ │                                                  │ ALERTS         4  │
│ │ -6h  NOW +6h│                                                  │ ⚠ B-2301 AT RISK  │
│ └───────────┘ │                                                  │   material uncfmd │
│ 10 Sep 12:48  │                                                  │ ⚠ 3 acks outstndg │
├───────────────┴──────────────────────────────────────────────────┴───────────────────┤
│ TRAIN GRAPH  ▾  (collapsible time–distance chart, synchronised to the time slider)   │
│  DLI ├──────────╲────────────╲──────────────────────────────────────────────────      │
│      │           ╲            ╲       ████ block B-2291                               │
│  SBB ├────────────╲────────────╲──────████──────────────────────────────────          │
│      │             ╲            ╲     ████                                            │
│  GZB ├──────────────╲────────────╲────████────────────────────────────────            │
│      └───────────────────────────────────────────────────────────────────────►        │
│       10:00    11:00    12:00    13:00    14:00    15:00    16:00    17:00            │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

**Key behaviours:**

- The **time slider** drives everything on the screen simultaneously — map, train graph and
  the Now panel. Dragging it into the future shows the _planned_ state; into the past shows
  the _recorded_ state. This single control is the most powerful idea in the interface.
- The **train graph** and the **map** are two projections of the same data and are
  cross-highlighted: hovering a train on the map highlights its line on the graph and
  vice versa.
- **Extensions pending** appear at the top of the Now panel with their computed impact
  already visible — the controller decides in one glance, not after a phone call (S-29).

## J5. Screen — New demand (map-first wizard)

The form is not a form. It is a map with a panel that fills itself in.

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ NEW BLOCK DEMAND                                          Step 1 of 4  ● ○ ○ ○       │
├────────────────────────────────────────────┬─────────────────────────────────────────┤
│                                            │ 1  WHERE                                │
│                                            │ ─────────────────────────────────────── │
│         [ MAP — draw the extent ]          │ Draw on the map, or:                    │
│                                            │  Between  [SBB ▾] and [GZB ▾]           │
│    ╭──────────────────────╮                │  Line     [UP Main ▾] [+ add line]      │
│    │ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ │ ← drawn extent │  From km  [412.100]  To km [413.500]    │
│    ╰──────────────────────╯                │  Length   1.400 km                      │
│         412.100      413.500               │                                         │
│                                            │ ▸ ALSO BECOMES UNAVAILABLE    (3)       │
│    ┌──── derived unavailability ────┐      │   • UP Loop — only crossover CO/14 lies │
│    │ ░░░░ UP Loop  (stranded)       │      │     inside the worksite                 │
│    │ ⚡⚡  OHE elementary section E-7│      │   • Platform 3 at SBB — reachable only  │
│    └───────────────────────────────┘       │     via the blocked extent              │
│                                            │   • Siding S/12 — placement not possible│
│                                            │                                         │
│                                            │ ▸ ELECTRICALLY DEAD IF POWER BLOCK      │
│                                            │   E-7 (SBB–GZB, 6.2 km, 2 stations)     │
│                                            │                                         │
│                                            │ ▸ NEARBY OPEN DEMANDS         (4)  ★     │
│                                            │   D-1043 OHE   412.4  2h  ← can bundle  │
│                                            │   D-1047 S&T   413.1  3h  ← can bundle  │
│                                            │   D-1052 Engg  415.0  2h    (outside)   │
│                                            │   [ Explore bundling → ]                │
│                                            │                                         │
│                                            │              [ Back ]  [ Next: WHAT → ] │
└────────────────────────────────────────────┴─────────────────────────────────────────┘
```

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ NEW BLOCK DEMAND                                          Step 3 of 4  ● ● ● ○       │
├────────────────────────────────────────────┬─────────────────────────────────────────┤
│ 3  WHEN                                    │  LIVE IMPACT  (updates as you choose)   │
│ ────────────────────────────────────────── │ ─────────────────────────────────────── │
│  Preferred date   [Sun 21 Sep]  📅          │  As chosen: Sun 21 Sep 10:00–14:00      │
│  Also acceptable  [Tue 23] [Wed 24] [+]    │                                         │
│  Start time       [10:00]                  │   Affected trains          14            │
│  Flexibility      ( ) Fixed                │   Detention            340 min  ▲ high   │
│                   (•) ±3 hours             │   Cancellations             3            │
│                   ( ) Any time             │   Freight delayed     1 200 t            │
│                   ( ) Night only           │   Indicative cost        ₹ x.xx          │
│                                            │   Confidence: L2 analytical              │
│  Duration                                  │                                         │
│   Protection setup   [0:25]                │  ⚠ 3 protected services affected         │
│   Effective work     [3:00]                │  ⚠ Sunday morning = high passenger load  │
│   Testing            [0:00]                │                                         │
│   Hand-back          [0:20]                │  ✦ BETTER WINDOWS                        │
│   ─────────────────────────                │   Sun 21 Sep 01:00–05:00                │
│   TOTAL              [3:45]                │      92 min · 0 cancel   −73%           │
│                                            │   Tue 23 Sep 01:00–05:00                │
│   System suggests 3:10 (±0:35)             │      61 min · 0 cancel   −82%  ★ best   │
│   based on 47 similar jobs        [use it] │   Bundled with D-1043, D-1047 on Tue    │
│                                            │      92 min total for 3 works  ★★★      │
│   Minimum viable     [2:30]                │      saves 5h45m of block time          │
│   Work divisible?    ( ) Yes  (•) No       │                                         │
│                                            │      [ Adopt Tuesday bundle → ]         │
│                                            │              [ Back ]  [ Next: HOW → ]  │
└────────────────────────────────────────────┴─────────────────────────────────────────┘
```

**Why this design works:** the requester sees the cost of their own request _before_
anyone argues with them, and is offered a better option with the reasoning attached. Most
of the negotiation that currently happens in a monthly meeting is pre-empted at the point
of entry. This is the single largest efficiency gain available in the whole system.

## J6. Screen — Planning workspace (options comparison)

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ PLANNING RUN #4821   Horizon: 21 Sep – 27 Sep   Weights: DLI-standard v4   [Re-run]  │
├──────────────────────────────────────────────────────────────────────────────────────┤
│                A: Least traffic  B: Max output  C: Balanced ★  D: As asked  E: Low risk│
│ Demands scheduled     38/52          49/52         45/52         41/52        40/52   │
│ Detention (min)        1 240          3 980         1 890         3 100        2 010   │
│ Cancellations              2             11             4            9            3   │
│ Freight delayed (t)    2 100          9 400         3 800        8 100        3 900   │
│ Block-hours used         112            168           134          161          130   │
│ Bundles formed             9              6            11            2            5   │
│ Block-hours SAVED         31             18            44            6           22   │
│ Statutory at risk          6              0            0            3            1   │
│ Machine utilisation      61%            88%          79%          64%          72%   │
│ Objective score           71             68            94           52           76   │
│                                                     ▲ recommended                     │
│ ─────────────────────────────────────────────────────────────────────────────────────│
│ [ Compare A vs C ]  [ View C on map ]  [ View C on calendar ]  [ Explain C ]          │
│                                                                                       │
│ WHY OPTION C                                                                          │
│  • Forms 11 bundles, saving 44 block-hours against executing every demand separately. │
│  • Schedules all 6 statutory-due items before their deadlines (A defers 6 — that is   │
│    why A's detention looks better; it is buying punctuality with statutory risk).     │
│  • Uses Tue/Wed nights for 68% of work; avoids all protected services.                │
│  • 7 demands unscheduled: 4 lack confirmed materials, 2 need a machine that is        │
│    committed to Programme P-11, 1 has an unresolved dependency on D-1039.             │
│  WHAT WOULD IMPROVE IT                                                                │
│  • Releasing tamper TM-07 two days earlier would allow 3 more demands (+9 block-hrs   │
│    saved, statutory risk unchanged).                                                  │
│  • If the Wed 24 embargo were lifted, detention falls a further 11%.                  │
│                                                                                       │
│                                     [ Adopt Option C ]  [ Adopt with modifications ]  │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

## J7. Screen — Approval

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ D-1041  Through packing  UP Main 411.000–413.500      Engineering / SBB sub-division  │
│ Criticality: CONDITION-BASED   Origin: TRC recording 14 Aug   SLA: 2 d 4 h remaining  │
├───────────────────────────────────────────┬──────────────────────────────────────────┤
│ REQUEST                                   │ IMPACT — Tue 23 Sep 01:00–06:35 (bundled)│
│  Quantum      1.4 km through packing      │  Affected trains            6            │
│  Method       mechanised (tamper)         │  Detention               92 min          │
│  Duration     5:35 (bundled)              │  Cancellations              0            │
│  Nominated    SSE/P.Way SBB  ✓ competent  │  Freight delayed         180 t           │
│  Adjacent line  BLOCKED  ✓                │  Passengers affected     ~1 400          │
│  Machines     TM-07 ✓ available           │  Indicative cost         ₹ y.yy          │
│  Materials    n/a                         │  Post-block restriction  30 kmph, 1.4 km,│
│  Gang         Gang-14  ✓ rested           │                          expected 5 days │
│                                           │  Confidence  L2 · timetable as at 09:12  │
│ BUNDLE B-07                               │                                          │
│  + D-1043 OHE insulator replacement       │ ALTERNATIVES                             │
│  + D-1047 S&T axle counter alteration     │  Separate execution   268 min · 1 cancel │
│  Shared: window, protection, isolation    │  Sunday as requested  340 min · 3 cancel │
│  Saves: 5h45m block time, 176 train-min   │  Defer 1 month        0 min · risk: none │
│                                           │                                          │
│ RULE FINDINGS                             │ EXPLANATION                    [expand]  │
│  ✓ R-0142 adjacent line — satisfied       │  Recommended because it forms the        │
│  ✓ R-0088 competency — valid              │  highest-value bundle in the horizon and │
│  ⚠ R-0203 3 depts in one bundle — joint   │  avoids all protected services…          │
│    readiness historically 78%             │                                          │
├───────────────────────────────────────────┴──────────────────────────────────────────┤
│ [ APPROVE as recommended ]  [ APPROVE with changes ]  [ REFUSE ]  [ RETURN for info ] │
│  Justification (required if not adopting the recommended option): ______________       │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

## J8. Screen — Live block console (control room)

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ B-2291   UP Main 412.100–413.500   Bundle: D-1041 + D-1043 + D-1047                  │
│ ● ACTIVE   Granted 01:07 (sanctioned 01:00, +7 min: "last goods clearance")          │
│ Sanctioned end 06:35        ⏱ 1 h 12 m remaining        Progress ▓▓▓▓▓▓▓░░░ 68%      │
├──────────────────────────────────────────────────────────────────────────────────────┤
│ SAFETY STATE                          │ WORK PACKAGES                                │
│  Traffic block   ● GRANTED  01:07     │  WP-1 Engg  packing   ▓▓▓▓▓▓▓▓░ 82%  on time │
│  Protection      ● COMPLETE 01:24     │        Site-in-charge: SSE/P.Way SBB          │
│  OHE isolation   ● GRANTED  01:15     │  WP-2 OHE   insulator ▓▓▓▓▓▓▓▓▓▓ 100% ✓ done │
│  Earthing        ● CONFIRMED 01:21    │  WP-3 S&T   axle cntr ▓▓▓▓░░░░░ 41%  ⚠ slow  │
│  Adjacent line   ● BLOCKED            │        testing not yet started (0:30 needed) │
│  Disconnections  2 open  ⚠            │                                              │
│                                       │ WORKSITE POSITIONS (live)                    │
│ PEOPLE ON SITE  23                    │  WP-1 at km 412.9 (moving)                   │
│ CONTACT  SSE/P.Way  9xxxxxxxxx        │  WP-3 at km 413.1 (static)                   │
├───────────────────────────────────────┴──────────────────────────────────────────────┤
│ ⚠ EXTENSION REQUESTED — WP-3 S&T, +45 min, reason: "cable termination fault found"    │
│   IF GRANTED:  4 trains affected · +62 detention-min · 0 cancellations                │
│                12045 held 22 min · 12046 held 18 min · 2 goods rerouted via loop      │
│   IF REFUSED:  work incomplete; axle counter must be restored to previous state       │
│                (0:20) ; a fresh 2 h block will be required within 7 days              │
│   [ GRANT +45 ]  [ GRANT +20 ]  [ REFUSE ]     Reason: ____________________           │
├──────────────────────────────────────────────────────────────────────────────────────┤
│ TIMELINE   01:00 sanctioned ─ 01:07 granted ─ 01:15 isolation ─ 01:21 earthed         │
│            ─ 01:24 protected ─ 01:26 work started ─ 04:52 WP-2 complete ─ …           │
│                                                        [ Full event log ]             │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

The controller is shown **both** consequences — grant and refuse — because refusing also
has a cost, and today that cost is invisible (S-29).

## J9. The field application

Designed for one hand, bright sunlight, gloves, poor signal, and a person whose primary
concern is not data entry.

```
┌───────────────────────────┐    ┌───────────────────────────┐
│ ≡   MY BLOCK      ⟳ 12s   │    │  PROTECTION CHECKLIST     │
├───────────────────────────┤    ├───────────────────────────┤
│                           │    │  B-2291   UP Main         │
│   ┌───────────────────┐   │    │  412.100 – 413.500        │
│   │                   │   │    │                           │
│   │   BLOCK GRANTED   │   │    │  ☑ Detonators — SBB end   │
│   │                   │   │    │     01:12  SSE/P.Way      │
│   │       ✓           │   │    │  ☑ Detonators — GZB end   │
│   │                   │   │    │     01:14  Gang-14        │
│   └───────────────────┘   │    │  ☑ Banner flag both ends  │
│                           │    │     01:16                 │
│   ┌───────────────────┐   │    │  ☑ Point clamped CO/14    │
│   │  OHE  EARTHED  ⚡  │   │    │     01:19                 │
│   │       ✓  01:21    │   │    │  ☐ Site safety briefing   │
│   └───────────────────┘   │    │     [ CONFIRM ]           │
│                           │    │  ☐ Adjacent line verified │
│   ┌───────────────────┐   │    │     [ CONFIRM ]           │
│   │ ADJACENT LINE     │   │    │                           │
│   │   ▓ BLOCKED ▓     │   │    │  2 of 6 remaining         │
│   └───────────────────┘   │    │                           │
│                           │    │  Work cannot start until  │
│   ENDS 06:35              │    │  all items are confirmed. │
│   ⏱  1 : 12 : 04          │    │                           │
│                           │    │                           │
│  ┌─────────────────────┐  │    │                           │
│  │   REPORT PROGRESS   │  │    │                           │
│  └─────────────────────┘  │    │                           │
│  ┌─────────────────────┐  │    │                           │
│  │  REQUEST EXTENSION  │  │    │                           │
│  └─────────────────────┘  │    │                           │
│  ┌─────────────────────┐  │    │                           │
│  │  🆘  EMERGENCY      │  │    │                           │
│  └─────────────────────┘  │    │                           │
├───────────────────────────┤    └───────────────────────────┘
│ Synced 12 s ago · online  │
└───────────────────────────┘
```

**Offline behaviour — the most safety-critical design in the system:**

```
Connectivity      Display                                     Behaviour
──────────────────────────────────────────────────────────────────────────────────────
Online            "Synced 12 s ago"  green                     Normal
< 5 min stale     "Last confirmed 3 min ago"  amber            Normal, banner shown
5–15 min stale    Large amber banner: "STATUS NOT CONFIRMED    Actions queued locally
                   FOR 8 MINUTES — verify by voice"
> 15 min stale    Screen turns amber; the tick becomes a "?";  All safety indications
                   "DO NOT RELY ON THIS DISPLAY —              downgraded to UNKNOWN
                   CONFIRM BY VOICE WITH CONTROL"
Block cancelled   Full-screen red takeover + sound + vibration Cannot be dismissed
while offline      as soon as connectivity returns              without acknowledgement
```

**The field app never says "granted" when it does not know.** Silence is treated as
danger, not as continuity. This directly addresses S-37 and S-89, the two scenarios that
can kill someone.

Other field screens: defect capture (photo + GPS + 3 taps), my forward assignments,
readiness confirmation, progress reporting (percentage slider + reason codes),
post-block report, and the emergency form (G15).

## J10. Executive dashboard

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ DIVISIONAL BLOCK PERFORMANCE — DLI            Period: Aug 2026   [Month ▾] [Export]   │
├──────────────────────────────────────────────────────────────────────────────────────┤
│  BLOCK UTILISATION      GRANT PUNCTUALITY      OVERRUN RATE      NON-UTILISATION      │
│      68%  ▲ 6           81%  ▲ 9              12%  ▼ 4            4%  ▼ 2            │
│   ▁▂▃▄▅▆▆▇             ▂▃▃▄▅▆▆▇             ▇▆▅▄▄▃▃▂           ▇▅▄▃▃▂▂▁            │
│                                                                                       │
│  DETENTION PER BLOCK-HOUR   BUNDLING RATIO    BACKLOG (stat. overdue)  EMERGENCY SHARE│
│      14.2 min  ▼ 3.1            37%  ▲ 12          23  ▼ 11              9%  ▼ 3     │
├──────────────────────────────────────────────────────────────────────────────────────┤
│  DEPARTMENTAL SCORECARD                                                               │
│  Dept   Demands  Sanctioned  Utilised  Grant-punct  Overrun  Asked/Used  Statutory OK │
│  Engg      184       171        71%        84%        9%      4.0/3.1h      96%       │
│  Elec       97        88        63%        79%       15%      3.0/2.2h      91%       │
│  S&T        76        69        58%        77%       21%      3.0/2.6h      88%       │
│  Project    31        28        81%        88%        7%      8.0/7.6h       —        │
├──────────────────────────────────────────────────────────────────────────────────────┤
│  TOP CAUSES OF LOST BLOCK TIME              WORST SECTIONS (detention/block-hour)     │
│  1 Late grant (traffic)          22%        1 SBB–GZB      28.4 min                   │
│  2 Machine late arrival          17%        2 GZB–MUT      19.1 min                   │
│  3 Protection took longer        14%        3 DLI–SBB      16.7 min                   │
│  4 Material not at site          11%                                                  │
│  5 Testing underestimated         9%        RESTRICTIONS OVERDUE FOR REVIEW      7    │
│                                             oldest: 30 kmph at 418.2 — 94 days        │
├──────────────────────────────────────────────────────────────────────────────────────┤
│  ⚠ REQUIRES YOUR ATTENTION                                                            │
│   • 3 statutory items will breach their due date within 21 days and are unscheduled   │
│   • Corridor block for 12 Oct has no bids from S&T — capacity likely to be wasted     │
│   • Tamper TM-07 utilisation 61% — 14 idle days next month; reserve queue has 9 jobs  │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

Every figure drills through to the underlying blocks. No number in this system is a
dead end.

## J11. Accessibility, language and field ergonomics

- **Multilingual** across at least the official languages of the zone, with the field app
  fully localised including reason-code lists.
- **Icon-led safety indication.** The three safety states (block, earthing, adjacent line)
  are recognisable without reading.
- **Contrast and size.** Field app designed for direct sunlight: high contrast, minimum
  44 px touch targets, no thin typography, no colour-only signalling.
- **Gloves and one-handed use.** Primary actions in the lower third of the screen.
- **Audible and haptic** alerts for safety-critical state changes.
- **Printable everything.** Every plan, notice, checklist and block sheet has a clean
  print layout, because paper remains the ultimate fallback (S-94).

---

# Part K — The Map

The map is the centrepiece of the system. It is the only artefact in which the five worlds
of [F2](#f2-conceptual-model--the-five-worlds) become simultaneously visible, and it is the
reason a controller, an engineer and a DRM can hold the same conversation.

## K1. Three view modes, one data model

Railway people use different spatial abstractions for different tasks. All three must be
available, and switching between them must preserve selection and time.

| Mode               | What it shows                                                             | Best for                                                                          |
| ------------------ | ------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| **Geographic**     | True coordinates on a base map; real curvature of the route               | Field context, third-party works, weather, regional awareness, executive briefing |
| **Schematic**      | Straightened, evenly-spaced line diagram — the classic control-room panel | Control room, block working, understanding line topology and crossovers           |
| **Linear (strip)** | One section as a horizontal chainage strip with lines stacked vertically  | Detailed block extent work, restriction placement, asset alignment                |

```
GEOGRAPHIC                    SCHEMATIC                      LINEAR (SBB–GZB)
                                                              km 410      415      420
    ╭─╮                       ○──────○──────○──────○         UP Main ──▓▓▓▓▓───────────
   ╭╯ ╰──╮                    │      │      │      │         DN Main ────────────░░░░░─
  ╭╯     ╰─╮   ○ SBB          ○──────○──────○──────○         UP Loop ──░░░░░───────────
 ╭╯        ╰──╮               SBB   JN12   GZB   MUT         Sidings ─────────○────────
○╯            ╰──○ GZB                                        Assets  │ │  ││   │  │ │
```

**Critical requirement:** all three are projections of the same objects. A block drawn in
one appears immediately in the others. Selection, filters and the time slider are shared.

## K2. Layer stack

Ordered bottom to top. Each layer independently toggleable, with sensible defaults per role.

```
z=0    BASE
        • Geographic: terrain / satellite / plain, at low saturation so railway data pops
        • Schematic: plain background
        • Administrative boundaries (division, section) as faint outlines

z=10   NETWORK
        10.1  Track segments (all lines, rendered with real curvature — see K3)
        10.2  Turnouts and crossovers (with normal/reverse indication at high zoom)
        10.3  Stations, yards, platforms
        10.4  Nodes: junctions, signals, level crossings, bridges, tunnels,
              neutral sections
        10.5  Chainage graduations (every km at mid zoom, every 100 m at high zoom)
        10.6  Line names and directions

z=20   TRACTION (off by default; essential for power blocks)
        20.1  Elementary sections as coloured bands along the track
        20.2  TSS / SP / SSP locations
        20.3  Feeder boundaries and neutral sections
        20.4  Live isolation state (energised / isolated / earthed)

z=30   ASSETS (off by default; on for engineering roles)
        30.1  Assets by class, clustered at low zoom
        30.2  Condition-coded (good / watch / defective / failed)
        30.3  Defect backlog heat (where is the pain concentrated)

z=40   RESTRICTIONS
        40.1  Speed restrictions as orange dashed overlay with value labels
        40.2  Permanent restrictions distinguished from temporary
        40.3  Ageing indication (restrictions past their review date pulse)

z=50   BLOCKS  ← the core layer
        50.1  Active blocks (red solid)
        50.2  Granted-not-yet-protected (red hatched)
        50.3  Approved / scheduled future blocks (amber solid)
        50.4  Requested / under review (amber dashed outline)
        50.5  Optimiser-proposed (violet dotted)
        50.6  Bundle groupings (violet brace connecting members)
        50.7  Derived unavailability (grey hatched — not blocked, but unusable)
        50.8  Electrically dead footprint (lightning hatch)
        50.9  Emergency blocks (red flashing halo)
        50.10 Worksite positions within a block (live markers)

z=60   TRAFFIC
        60.1  Train positions (blue passenger / green freight)
        60.2  Direction and speed indication
        60.3  Delay ring (red halo scaled to delay magnitude)
        60.4  Position confidence (solid = tracked; hollow = inferred from last report)
        60.5  Clustering at low zoom with count badges
        60.6  Trail (last N minutes of movement) on selection

z=70   CONFLICTS & ANALYSIS
        70.1  Conflict markers at the point of conflict (magenta, pulsing)
        70.2  Impact halo (which trains a selected block affects, drawn as links)
        70.3  Affected platforms / sidings / terminals
        70.4  Cross-divisional impact indicators at boundaries

z=80   RESOURCES (off by default)
        80.1  Machine current positions and itineraries
        80.2  Gang base locations
        80.3  Material stacking points
        80.4  Road access points for RRVs

z=90   ENVIRONMENT (off by default)
        90.1  Weather overlay (rain radar, temperature, wind)
        90.2  Flood-prone and vulnerable locations
        90.3  Active weather warnings

z=100  ANNOTATION & INTERACTION
        100.1 Drawing tools output (extent being drawn)
        100.2 Measurement tool
        100.3 Selection highlight and hover halo
        100.4 Labels and callouts
```

## K3. Rendering railway lines truthfully

A design detail that matters more than it appears: **track must not be drawn as straight
lines between stations.** Real alignments curve; a straight-line rendering makes the map
look like a schematic pretending to be a geography, and it misleads users about distance,
adjacency and site access.

Two sources of truth, in order of preference:

1. **Surveyed geometry.** Where GIS/survey data exists, render the actual polyline. This is
   the correct long-term answer and should be the master data goal.
2. **Interpolated geometry.** Where only endpoints and chainages exist, generate a
   plausible smooth alignment: place intermediate vertices along the chord and apply a
   small perpendicular deflection (a few percent of the chord length), seeded
   deterministically per segment so the rendering is stable across sessions and users.
   Render with rounded joins and caps.

**Rules for interpolated geometry:**

- It must be **deterministic** — the same segment must look identical to every user, every
  time, or the map loses credibility.
- It must be **labelled as approximate** in the layer legend and in any export.
- It must **never** be used for distance calculation, extent computation or caution orders —
  those always use chainage, never rendered geometry.
- Parallel lines (UP/DN/loops) must be rendered with a consistent perpendicular offset so
  they remain visually distinguishable at all zooms without overlapping.

## K4. Block visualisation

### K4.1 The visual grammar

```
  ACTIVE (in force now)          ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓   solid red, full width
  GRANTED, NOT YET PROTECTED     ▨▨▨▨▨▨▨▨▨▨▨▨▨▨▨▨   hatched red
  APPROVED / SCHEDULED           ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒   solid amber
  REQUESTED / UNDER REVIEW       ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈   dashed amber outline only
  OPTIMISER-PROPOSED             ⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯   dotted violet
  DERIVED UNAVAILABLE            ░░░░░░░░░░░░░░░░   grey hatch, thinner
  ELECTRICALLY DEAD              ⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡   lightning hatch band alongside
  EMERGENCY                      ▓▓▓▓▓▓▓ + pulsing halo
  CONFLICT                       magenta pulsing outline around the overlapping extent
```

Each block carries an **end-cap marker** at each extremity showing the protection type
(detonators / banner flag / stop board), so a controller can see at a glance how the site
is protected.

### K4.2 Block detail on selection

Selecting a block opens a docked panel (never a modal — the map must stay visible):

```
┌─────────────────────────────────────────┐
│ B-2291  ● ACTIVE                    ✕   │
│ UP Main  412.100 – 413.500  (1.400 km)  │
│ SBB – GZB · DLI Division                │
├─────────────────────────────────────────┤
│ Window   01:00 – 06:35   granted 01:07  │
│ Remaining  1 h 12 m      progress 68%   │
│ Class    Routine (bundled)              │
│ Bundle   D-1041 + D-1043 + D-1047       │
├─────────────────────────────────────────┤
│ SAFETY                                  │
│  Traffic  ● granted   Protection ● done │
│  OHE      ● earthed   Adjacent  ▓ blocked│
│  Disconnections  2 open  ⚠              │
├─────────────────────────────────────────┤
│ ALSO UNAVAILABLE (derived)              │
│  UP Loop (stranded via CO/14)  [show]   │
│  Platform 3 SBB                [show]   │
├─────────────────────────────────────────┤
│ IMPACT NOW                              │
│  6 trains · 92 detention-min · 0 cancel │
│  [ Show affected trains on map ]        │
├─────────────────────────────────────────┤
│ Site-in-charge  SSE/P.Way SBB  📞        │
│ 23 persons on site                      │
├─────────────────────────────────────────┤
│ [Timeline] [Work packages] [Documents]  │
│ [Request extension] [Open console]      │
└─────────────────────────────────────────┘
```

### K4.3 Drawing a block on the map

Block creation is a **map gesture**, not a form field. This is the interaction that makes
the whole system feel native to railway thinking.

```
Step 1  Select the tool          → cursor becomes a chainage-snapping crosshair
Step 2  Click the start point    → snaps to the nearest track segment and chainage;
                                   a live readout shows "UP Main km 412.100"
Step 3  Drag along the line      → the extent grows; it follows the track, not the
                                   straight line between the two clicks
Step 4  Click the end point      → extent fixed; chainages editable numerically
Step 5  Choose lines             → if multiple parallel lines exist at that chainage,
                                   a small selector appears: [UP Main] [DN Main] [UP Loop]
Step 6  Immediately, the map shows:
          • the drawn extent in "draft" styling
          • the DERIVED UNAVAILABILITY set, in grey hatch, appearing live
          • the ELECTRICALLY DEAD footprint if OHE work is indicated
          • CONFLICT markers against existing blocks and demands
          • BUNDLE candidates highlighted in violet with a connecting brace
          • affected trains flashing briefly on the traffic layer
Step 7  A floating draft card appears next to the extent with the essential asks:
          date, time, duration, work type, criticality — and the live impact figure
Step 8  [ Continue to full request ]  →  opens the wizard (J5) pre-filled
        [ Save as draft ]             →  appears on the calendar as a draft
        [ Discard ]
```

**Snapping and precision:**

- Snap to: track segment centreline, chainage graduations, existing block boundaries,
  turnouts, signals, station limits, asset locations.
- Numeric override always available — a PWI who knows the exact chainage should be able to
  type it.
- Extent must be **validated live**: an extent that crosses a divisional boundary, or that
  cannot be protected, is flagged as it is drawn, not after submission.

### K4.4 Editing an existing block on the map

- Drag either end-cap to change the extent → live re-computation of derived unavailability,
  conflicts and impact.
- Drag the whole block along the time slider → live re-computation of traffic impact,
  with the delta shown ("moving 3 h earlier saves 178 detention-minutes").
- Right-click → split, merge with an adjacent block, convert to bundle, extend to the
  adjacent line, propose as a corridor block.
- **All edits are proposals until saved**, and edits to an approved block route back
  through approval with the change highlighted.

## K5. Train visualisation

### K5.1 Rendering

```
   ▶ 12045          passenger, on time, tracked precisely
   ▶ 12045 ⭕        passenger, delayed (ring thickness/colour ∝ delay)
   ▷ 12045          hollow = position inferred from last station report, not live
   ▶ GDS-4471       freight (green)
   ⬤ 14            cluster at low zoom, 14 trains
   ▶ 12045 ⚠        train projected to be affected by a block
```

- **Direction** shown by the marker's orientation along the track.
- **Speed** optionally shown as a short motion trail.
- **Position confidence is never hidden.** A train whose position is interpolated between
  reporting points is drawn hollow, and its tooltip says "last reported SBB 12:31,
  position estimated".
- **Selection** shows: number, type, origin/destination, current delay, next reporting
  point, ETA, formation, and — critically — **which blocks will affect it and by how much**.

### K5.2 Train–block interaction (the point of the whole map)

When a block is selected, the map draws **impact links** to the trains it affects, each
labelled with the estimated detention. When a train is selected, the map highlights the
blocks that will affect it along its remaining path.

```
        ●━━━━━━━━━━━━━━━━━━━━━━━●
        │   ▓▓▓▓ B-2291 ▓▓▓▓    │
        │        ╱ │ ╲          │
        │   ▶12045 ▶12046 ▶GDS4471
        │   +22m   +18m   +31m
```

This single visual answers the question that today takes a phone call and ten minutes.

### K5.3 Projected positions in the future

When the time slider is moved into the future, trains are drawn at their **timetabled
projected positions**, in a visually distinct style (outlined, semi-transparent), with a
clear "PROJECTED" badge on the time control. Confusing a projection with a live position
would be a serious usability failure, so the distinction is emphatic.

## K6. The time slider — past, present and future in one control

```
┌───────────────────────────────────────────────────────────────────────────────┐
│  ⏮   ⏪   ▐▐   ⏩   ⏭      ● LIVE      Speed: [1× ▾]   [Jump to… ▾]          │
│                                                                               │
│  ├────────┼────────┼────────┼────●────┼────────┼────────┼────────┤            │
│  06:00   08:00   10:00   12:00  NOW  14:00   16:00   18:00   20:00           │
│         ▓▓▓▓▓▓         ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒          ▒▒▒▒▒▒▒▒                    │
│         B-2288          B-2291 (active)           B-2295 (scheduled)          │
│                    ┈┈┈┈┈┈┈┈ D-1052 (requested)                                │
│                                    ⋯⋯⋯⋯⋯⋯ proposed alternative                │
│  Tue 10 Sep 2026 · 12:48                                    [ Reset to LIVE ] │
└───────────────────────────────────────────────────────────────────────────────┘
```

Behaviours:

- **Past:** shows the recorded state — actual block times, actual train positions, actual
  restrictions. This is the audit and enquiry view (_"show me 04:17 on 3 August"_).
- **Now:** live, auto-refreshing, with a prominent LIVE indicator.
- **Future:** shows the planned state — approved blocks, requested demands, proposed
  options, and projected train positions.
- **Playback:** scrub or play at 1×/10×/60× to watch a block's day unfold — extremely
  effective for post-incident review and for training.
- **Snap points:** jumping to "next block start", "start of my shift", "the moment of the
  extension request" and similar named instants.
- The time context is **shared with every other view on screen** — train graph, lists,
  panels — so the whole application is a coherent snapshot of one instant.

## K7. Conflict and opportunity visualisation

```
 CONFLICT                                    BUNDLE OPPORTUNITY
 ══════════════════════════════════════      ══════════════════════════════════════
      ▒▒▒▒▒▒▒▒▒▒▒▒  D-1041 Sun 10:00              ⋯⋯⋯⋯⋯⋯⋯⋯ D-1041
           ╳ overlapping extent + window          ⋯⋯⋯ D-1043    ⎫
      ▒▒▒▒▒▒▒▒▒▒▒▒  D-1099 Sun 11:00              ⋯⋯⋯⋯ D-1047   ⎬ violet brace
      ┌──────────────────────────────┐            ─────────────  ⎭
      │ ⚠ CONFLICT                   │            ┌──────────────────────────────┐
      │ Same extent, overlapping     │            │ ✦ BUNDLE OPPORTUNITY          │
      │ window, different depts      │            │ 3 demands can share one window│
      │ RESOLUTIONS:                 │            │ Saves 5h45m block time and    │
      │  • Merge into one block ★    │            │ 176 detention-minutes         │
      │  • Move D-1099 to Tue 01:00  │            │ [ Preview bundled block ]     │
      │  • Reduce D-1041 to 411–412  │            │ [ Propose to all owners ]     │
      │ [ Apply ]                    │            └──────────────────────────────┘
      └──────────────────────────────┘
```

Conflicts are never presented as bare errors. Every conflict marker carries at least one
concrete, applicable resolution, and applying it is a single action that re-runs the
analysis live.

## K8. Traction (power block) visualisation

Selecting "power block required" while drawing switches the map into traction mode:

```
   Elementary sections along the route:
   ├─── E-5 ───┼──────── E-6 ────────┼──────── E-7 ────────┼─── E-8 ───┤
                                      ▲                    ▲
                                    SP/12                SSP/13

   Worksite at km 412.4  ⇒  MINIMAL ISOLATION = E-7 only
   ┌────────────────────────────────────────────────────────────────┐
   │ ⚡ ISOLATION FOOTPRINT                                          │
   │ Elementary section E-7  ·  SP/12 to SSP/13  ·  6.2 km          │
   │ Stations going dead: SBB, JN12                                 │
   │ Earthing points: EP/412.0 and EP/414.5 (both bound the site) ✓ │
   │ Electric traction cannot run on ANY line under E-7             │
   │ ⚠ 4 electric services affected — diesel diversion not available│
   │ [ Show wider isolation options ]  [ Confirm minimal isolation ]│
   └────────────────────────────────────────────────────────────────┘
```

Showing the **footprint before approval** is the direct answer to S-57. The person asking
for the power block sees exactly how much of the railway they are about to switch off.

## K9. Corridor and strategic views

For zonal and Board-level users, a corridor view collapses the geography into a single
long strip covering multiple divisions:

```
 CORRIDOR: A ──── B ──── C ──── D ──── E        Sep 2026
 Div:      │◄── DLI ──►│◄── UMB ──►│◄── FZR ──►│
 Week 1    ▒▒▒        ▒▒▒▒▒▒            ▒▒
 Week 2         ▒▒▒▒▒        ▒▒     ▒▒▒▒▒▒▒▒▒▒     ← overlapping = corridor cut ⚠
 Week 3    ▒▒▒▒▒▒▒▒▒▒ (declared corridor block — bids open)
 Week 4              ▒▒      ▒▒▒
```

This view exists to catch S-15 (adjacent divisions independently closing the same
corridor) and to manage declared corridor blocks as a strategic instrument.

## K10. Map performance and technical approach

| Concern              | Approach                                                                                                                                                              |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Volume**           | Static-ish layers (network, assets, traction) served as pre-generated vector tiles; dynamic layers (blocks, trains, conflicts) served as live GeoJSON/binary deltas   |
| **Viewport scoping** | Only fetch what is visible plus a margin; subscribe to live updates only for the visible extent                                                                       |
| **Train updates**    | Delta updates over a persistent connection; client-side interpolation between reports for smooth motion, clearly marked as interpolated                               |
| **Clustering**       | Trains and assets cluster below a configured zoom; blocks never cluster (a hidden block is a safety risk) — instead they aggregate into a labelled corridor indicator |
| **Time travel**      | Past states served from the event log via a snapshot + replay projection, cached per (instant, extent); future states computed from the plan                          |
| **Offline (field)**  | Pre-cached tiles for the user's section; last-known block state persisted locally with explicit staleness                                                             |
| **Determinism**      | Interpolated geometry seeded per segment so every user sees an identical map                                                                                          |
| **Degradation**      | If the live channel drops, the map dims, a banner appears, and the last-update time is displayed prominently. It never silently shows stale data as current.          |

## K11. Map interaction summary

| Action                 | Result                                                                             |
| ---------------------- | ---------------------------------------------------------------------------------- |
| Click segment          | Segment info: line, chainage, assets, restrictions, blocks past/future             |
| Click block            | Block panel (K4.2)                                                                 |
| Click train            | Train panel with affecting blocks                                                  |
| Hover anything         | Lightweight tooltip; cross-highlight in train graph and lists                      |
| Draw tool              | New block extent (K4.3)                                                            |
| Drag block end-cap     | Change extent, live impact delta                                                   |
| Drag block on timeline | Change window, live impact delta                                                   |
| Right-click block      | Split / merge / bundle / propose corridor / duplicate                              |
| Shift-select multiple  | Bulk actions; bundle proposal for the selection                                    |
| Measure tool           | Chainage distance between two points                                               |
| Time slider            | Whole application moves to that instant                                            |
| Layer toggles          | Show/hide; per-role defaults; saved as personal presets                            |
| Search                 | Jump to station, chainage, block ID, train number, asset ID                        |
| Keyboard               | `B` draw block · `T` time to now · `1-9` layer toggles · `/` search · `Esc` cancel |

---

# Part L — Operations, Assurance and Rollout

## L1. Security and access control

### L1.1 Authorisation model

Authorisation is a function of **three dimensions**, not one:

```
   permitted(user, action, object) =
        role_grants(user.roles, action)
     ∧  jurisdiction_covers(user.scope, object.location)
     ∧  department_permits(user.department, object.department, action)
     ∧  delegation_valid_at(now)
```

- **Role** — what kind of action (raise, endorse, approve, grant, certify, administer).
- **Jurisdiction** — which section/division/zone the user is responsible for.
- **Department scope** — a Signal officer may endorse S&T demands, not Engineering ones.

A DOM of one division must not be able to approve a block in another; an engineer must not
be able to grant a block on line; a contractor must see only their own works. These are
enforced server-side on every call, never in the UI alone.

### L1.2 Elevated actions

| Action                          | Requirement                                                                |
| ------------------------------- | -------------------------------------------------------------------------- |
| Approve a block                 | Role + jurisdiction + MFA                                                  |
| Override an embargo/peak window | Senior role + mandatory justification + notification to Safety             |
| Override a competency exception | Safety role + justification; recorded as a safety exception                |
| Modify a HARD rule              | Safety authority signature + version + effective date                      |
| Change objective weights        | Divisional authority within Zone-set bounds; versioned and published       |
| Backdate any record             | Prohibited. Late entries are recorded with both event time and entry time. |
| Delete anything safety-relevant | Prohibited. Supersede with a reason.                                       |

### L1.3 Threat considerations

- **Insider misuse** is the realistic threat, not external attack: a user granting
  themselves a block, or altering a record after an incident. Countered by immutability,
  append-only logs, and separation of duties (the person who requests cannot grant).
- **Availability attack** on a safety-adjacent system: rate limiting, isolation of the
  control-room path from public-facing surfaces, and the degraded-mode design (L5).
- **Third-party portal** is the largest external surface: strict sandboxing, no access to
  network or traffic data beyond their own works, mandatory railway sponsorship.
- **Field devices** are lost and shared: device enrolment, short session lifetimes for
  approval capability, and no cached credentials for elevated actions.

## L2. Data governance

| Domain                                          | Owner                       | Change control                                                                                              |
| ----------------------------------------------- | --------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Topology (segments, nodes, turnouts, chainages) | Engineering                 | Reviewed change with effective dates; versioned; never edited retrospectively without a supersession record |
| Traction graph (elementary sections, feeders)   | Electrical                  | As above                                                                                                    |
| Signalling assets                               | S&T                         | As above                                                                                                    |
| Timetable and paths                             | Operating                   | Synchronised from the timetable system; local edits prohibited                                              |
| Capacity profiles                               | Operating                   | Reviewed periodically against observed throughput                                                           |
| Calendars (embargo, peak, festival)             | Operating                   | Published in advance; changes notified                                                                      |
| Rules                                           | Safety                      | Formal approval; versioned; test cases required                                                             |
| Objective weights                               | Division within Zone bounds | Published; versioned; shown on every result                                                                 |
| Competency register                             | HR / Training               | Integrated; expiry drives hard gates                                                                        |

**Master data quality is the project's principal risk.** A topology that is 90% correct
produces derived-unavailability results that are wrong often enough to destroy trust. The
rollout plan (L6) therefore treats topology validation as a first-class workstream with its
own acceptance criteria, not as a data-loading task.

## L3. Audit and reconstruction

Every state-changing action produces an `AuditRecord`:
`{actor, role, action, entity, before, after, timestamp, correlation_id, client, reason?}`

Beyond generic auditing, the system must support three specific reconstructions:

1. **"What was the state of the railway at instant T?"** — served from the event log by
   snapshot + replay; rendered on the map via the time slider. This is the enquiry view.
2. **"Why was this block approved?"** — the `Decision` record: options presented, their
   scores, the weights and rule versions in force, who decided, and the justification.
3. **"Would the system make the same recommendation today?"** — the `PlanningRun` records
   its input snapshot hash, weight version, rule versions and random seed, so any past
   recommendation is exactly reproducible.

Retention follows the statutory period for safety records; nothing safety-relevant is ever
hard-deleted within that period.

## L4. Observability

| Signal                           | Why it matters here                                                                                                                                                   |
| -------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Projection lag**               | If the map is behind the truth, the controller is looking at a lie. Lag > threshold must raise an operational alert and dim the map.                                  |
| **Integration freshness**        | Every external feed has a "last successful" timestamp surfaced in the UI and alerted on.                                                                              |
| **Field sync health**            | Devices that have not synced within a shift are flagged to the controller _before_ a block starts.                                                                    |
| **Optimiser health**             | Run duration, gap to bound, options produced, timeouts.                                                                                                               |
| **Rule firing rates**            | A rule that suddenly fires 10× more often usually indicates a data problem, not a behaviour change.                                                                   |
| **SLA breaches and escalations** | Process health.                                                                                                                                                       |
| **Data quality**                 | Placeholder text rate, mandatory-field override rate, post-block report completeness. Falling data quality is the leading indicator of adoption failure (S-83, S-88). |

## L5. Degraded modes — designing for the day it breaks

| Failure                   | Behaviour                                                                                                                                                                                                                                                                                         |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Live channel down**     | Map dims, banner shows last-update time, polling fallback; no silent staleness                                                                                                                                                                                                                    |
| **Analysis workers down** | Existing materialised results still served, clearly stamped with their computation time; new demands accepted but marked "analysis pending"                                                                                                                                                       |
| **Optimiser down**        | Manual planning fully available; the system is a workflow and record even with no intelligence                                                                                                                                                                                                    |
| **Timetable feed down**   | Impact figures marked "based on timetable as at …"; L1 only; approvals still possible with the caveat recorded                                                                                                                                                                                    |
| **Train tracking down**   | Map shows scheduled positions only, prominently badged; no inferred positions presented as live                                                                                                                                                                                                   |
| **Field device offline**  | Offline-first behaviour per J9; safety states degrade to UNKNOWN, never to "granted"                                                                                                                                                                                                              |
| **Full backend outage**   | **Continuously refreshed offline artefacts:** every control room holds an auto-generated, printable "next 24 hours block sheet" regenerated hourly and cached locally; documented voice-based fallback procedure; on recovery, a reconciliation workflow captures what happened during the outage |

The degraded-mode artefacts are a **delivery requirement with acceptance tests**, not
documentation. A system that has never been tested with its backend switched off is not
ready for a control room.

## L6. Rollout strategy

### Phase 0 — Foundations (before any user sees anything)

- Build the topology model for the pilot division and **validate it against reality**:
  every segment, chainage, turnout, crossover and elementary section walked or verified
  against records. Acceptance: derived-unavailability results reviewed and accepted by the
  section engineers and controllers for a sample of 50 representative extents.
- Establish master data ownership and change control.
- Integrate timetable and train tracking; measure feed quality.

### Phase 1 — See (read-only, 3 months, one division)

- The map, the calendar, the train graph, the restriction register.
- No workflow. Blocks are entered by a small team mirroring the existing process.
- **Goal:** everyone agrees the picture is true. Trust before workflow.
- Exit criteria: controllers voluntarily use the map during their shift.

### Phase 2 — Request and record (4 months)

- Structured demand intake, workflow, approval, notifications with acknowledgement.
- Field app for execution events and post-block reporting.
- Conflict detection (no optimisation yet).
- **Goal:** one system of record; parallel registers retired.
- Exit criteria: ≥ 90% of demands raised in the system; post-block reporting ≥ 80%.

### Phase 3 — Analyse (4 months)

- Derived unavailability, impact engine L1/L2, resource model, readiness gate,
  reserve queue.
- Shadow finder in **advisory** mode: it suggests bundles, humans decide.
- **Goal:** demonstrable capacity savings from bundling and from the reserve queue.
- Exit criteria: bundling ratio ≥ 20%; measurable improvement in utilisation.

### Phase 4 — Optimise (6 months)

- Full optimiser with options, scoring and explanations.
- Learning loop active; data-derived duration suggestions.
- L3 simulation for mega blocks.
- Exit criteria: planners adopt an optimiser option (possibly modified) for ≥ 60% of
  routine demands.

### Phase 5 — Scale (12 months+)

- Additional divisions, then the zone; corridor and cross-divisional coordination.
- Third-party portal; programme/project portfolio management.
- National KPI comparison; corridor strategy at Board level.

**Sequencing principle:** _see → record → analyse → optimise._ Attempting optimisation
before the picture is trusted and the actuals are captured guarantees rejection.

## L7. Change management

The technical risk is manageable. The organisational risk is not, and it is where such
programmes usually fail.

1. **Give the data-entry burden back as value immediately.** The field user who logs a
   defect must see it on the map within seconds, and must see its status without asking
   anyone. (S-88)
2. **Make transparency symmetric.** Publish Operating's grant punctuality alongside
   Engineering's utilisation. A system that only measures one side will be resisted by that
   side, correctly. (S-84)
3. **Never let the system be blamed for a human decision.** Every refusal carries a named
   human and a reason. "The system said no" must be impossible.
4. **Train on the map, not on the forms.** The map sells itself; forms never do.
5. **Identify and empower local champions** in each department; give them configuration
   authority over their own templates.
6. **Retire the parallel register formally, with a date and a directive.** Dual running
   beyond a defined period is worse than no system.
7. **Publish the weights and let departments argue about them.** An argument about weights
   is a healthy institutional conversation; an argument about whether the machine is fair
   is not.

## L8. Test strategy

### L8.1 Test levels

| Level          | Focus                                                            | Notes                                                                                                                |
| -------------- | ---------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| Unit           | Rules, duration synthesis, interval overlap, chainage arithmetic | Chainage and interval maths are deceptively error-prone; test exhaustively                                           |
| Property-based | Topology expansion, conflict detection                           | Generate random networks and extents; assert invariants (e.g. a block never makes an unaffected segment unavailable) |
| Contract       | Every integration adapter                                        | Both directions, including malformed and stale inputs                                                                |
| Scenario       | The 94 scenarios of Part B                                       | Each scenario becomes an executable acceptance test                                                                  |
| Simulation     | Optimiser and impact engine                                      | Replay historical periods; compare recommendations against what actually happened                                    |
| Safety         | Every hard gate                                                  | Attempt to bypass each gate through every entry point, including the API                                             |
| Resilience     | Degraded modes (L5)                                              | Kill each dependency in turn; assert the UI degrades visibly and safely                                              |
| Field          | Offline behaviour                                                | Airplane-mode testing on real devices in real locations                                                              |
| Usability      | Control room under load                                          | Timed tasks with real controllers during a busy period                                                               |
| Load           | Map, live channel, optimiser                                     | Peak concurrency with realistic data volumes                                                                         |

### L8.2 Critical test cases (illustrative)

```
SAFETY GATES
  T-S01  Work cannot start when protection is incomplete — via UI, via API, via field app
  T-S02  Work cannot start when a power block is required and earthing is unconfirmed
  T-S03  Hand-back rejected while any disconnection is open
  T-S04  Block grant rejected when the nominated person's competency expired yesterday
  T-S05  Field app shows UNKNOWN, never GRANTED, after the staleness threshold
  T-S06  Block cancellation while the device is offline produces an undismissable alert
         on reconnection
  T-S07  Adjacent line "open" without a lookout arrangement is blocked at submission

TOPOLOGY
  T-T01  Blocking the only crossover renders SLW infeasible and the section fully blocked
  T-T02  Blocking a segment strands the loop reachable only through it
  T-T03  A platform reachable only via the blocked extent is reported as unusable
  T-T04  Traction isolation for a point worksite selects exactly one elementary section
  T-T05  Cross-divisional extent triggers the coordination requirement

CONFLICT & BUNDLING
  T-C01  Two demands on overlapping extents and windows are detected and offered a merge
  T-C02  A bundle is rejected when a member declined combination
  T-C03  Bundle duration is less than the sum of member durations and respects
         parallelism limits
  T-C04  Machine double-booking including mobilisation windows is detected
  T-C05  Dependency cycle is rejected at entry

IMPACT
  T-I01  L1 and L2 agree within tolerance on a set of historical cases
  T-I02  Diversion route with its own block is detected (no "diversion into a wall")
  T-I03  Post-block restriction capacity penalty is included in the block's cost
  T-I04  Impact figures carry an explicit staleness stamp when the timetable feed is old

OPTIMISER
  T-O01  Same inputs + weights + seed produce identical output (reproducibility)
  T-O02  No hard constraint is ever violated in any returned option
  T-O03  Options are meaningfully diverse (not five near-identical plans)
  T-O04  Explanation names the actual binding constraints
  T-O05  Timeout returns the best-so-far feasible solution, never nothing

EXECUTION
  T-E01  Late grant records a mandatory reason code
  T-E02  Extension request shows impact within 5 s
  T-E03  Early hand-back immediately prompts release of held trains
  T-E04  Surrendered block offers the window to the reserve queue
  T-E05  Post-block report generates a follow-up demand for balance work

RESILIENCE
  T-R01  With the optimiser down, manual planning and approval work end to end
  T-R02  With the train feed down, the map badges scheduled positions and refuses to
         present them as live
  T-R03  With the full backend down, the printed 24-hour block sheet is current to
         within one hour
  T-R04  Recovery reconciliation captures events that occurred during an outage

ACCOUNTABILITY
  T-A01  The map at an arbitrary past instant matches the recorded event log
  T-A02  A past recommendation is exactly reproduced from its recorded run
  T-A03  Approving against the recommendation without justification is impossible
  T-A04  No user can delete or backdate a safety record through any interface
```

---

# Part M — Traceability: Scenario → Solution

Every scenario from Part B, mapped to the mechanism that addresses it. This table is the
acceptance backbone: nothing may be descoped without an explicit decision recorded against
the scenario it abandons.

| S    | Scenario (short)                          | Addressed by                                                                    |
| ---- | ----------------------------------------- | ------------------------------------------------------------------------------- |
| S-01 | Need never formally requested             | Field defect capture (J9); demand ageing clocks; EAM ingestion                  |
| S-02 | Demand raised too late                    | Class notice periods (F5); live lead-time indicator (G5 4.16); V-03             |
| S-03 | Same work requested twice                 | Asset-bound demands (G3 2.10); duplicate detection (G14 13.2, V-15)             |
| S-04 | Vague description                         | Structured schema (Part G); V-19 placeholder detection                          |
| S-05 | Requester blind to existing plan          | Forward calendar; map-first wizard showing nearby demands (J5)                  |
| S-06 | Duration guessed                          | Learning loop (H11); suggested duration + confidence (G5 4.10)                  |
| S-07 | Quantum not stated                        | Mandatory quantum + unit (G4 3.4/3.5)                                           |
| S-08 | Dependencies invisible                    | Typed dependency links (G11 10.1); H8.2 H-05                                    |
| S-09 | No criticality differentiation            | Mandatory criticality + consequence of deferral (G4 3.7/3.8); objective weights |
| S-10 | Recurring work re-typed                   | Recurrence templates (G5 4.15); statutory due tracking                          |
| S-11 | Two depts block same track different days | Continuous conflict detection (H4); shadow finder (H5)                          |
| S-12 | First-come-first-served processing        | Set-based optimisation over a horizon (H8)                                      |
| S-13 | Adjacent/dependent track effects unknown  | Topology expansion (H3); derived unavailability on the map (K4.1)               |
| S-14 | Impact computed after approval            | Impact engine on the approval screen (H6, J7)                                   |
| S-15 | No cross-division visibility              | Corridor view (K9); cross-divisional flags (G3 2.16); H-14                      |
| S-16 | Five inconsistent copies of the plan      | Single system of record; all artefacts generated (F1.11)                        |
| S-17 | Late changes don't reach everyone         | Computed stakeholder set + notification fabric (I6)                             |
| S-18 | Acknowledgement assumed                   | Per-recipient acknowledgement tracking + escalation (I6)                        |
| S-19 | Resource conflicts on the day             | Resource bookings + H-03; readiness gate (H7.2)                                 |
| S-20 | Machine positioning time ignored          | Mobilisation model; booking includes mobilisation (H7.1)                        |
| S-21 | Competent person unavailable              | Competency register + validity gate (G7 6.2, H-04)                              |
| S-22 | Material not on site                      | Readiness gate material confirmation (H7.2, V-14)                               |
| S-23 | Fatigue / gang overload                   | Consecutive-night rules (H-09, V-20)                                            |
| S-24 | Seasonal/event constraints ignored        | Calendars (F4.5, H-07)                                                          |
| S-25 | Plans not comparable                      | Published objective function; option comparison (H8.4, J6)                      |
| S-26 | Block granted late                        | Grant event with reason code (H2, R.2); grant-punctuality KPI                   |
| S-27 | Work party arrives late                   | Party-at-site event (R.3); mobilisation planning                                |
| S-28 | Protection time unmodelled                | Duration decomposition (G5 4.6–4.9); learned protection times                   |
| S-29 | Overrun / extension chaos                 | In-system extension with instant impact (J8, I5.3)                              |
| S-30 | Early completion wasted                   | Hand-back event pushed live; prompt to release trains (I5.3, T-E03)             |
| S-31 | Block taken but unused                    | Readiness gate + reserve queue (H7.2, H7.3)                                     |
| S-32 | Partial completion unrecorded             | Post-block quantum reporting; auto follow-up demand (R.10–R.12)                 |
| S-33 | Informal hand-back                        | Digital hand-back certificate (H2, R.17)                                        |
| S-34 | Forgotten speed restriction               | Restriction register with review dates and ageing dashboard (F4.2, K2 z=40)     |
| S-35 | Rolling block front unknown               | Live worksite position reporting (G/K4.1 50.10)                                 |
| S-36 | Multiple worksites in one block           | Work packages with individual readiness (F4.2, J8)                              |
| S-37 | Party on track without a valid block      | Field app positive state + fail-safe offline behaviour (J9)                     |
| S-38 | OHE not actually earthed                  | Separate earthing state as a hard gate (H2)                                     |
| S-39 | Adjacent line risk                        | Mandatory adjacent-line declaration + lookout rule (G3 2.11, G7 6.7, V-11)      |
| S-40 | Disconnection not restored                | Disconnection register; hand-back gate (H2, T-S03)                              |
| S-41 | Competency unverified at grant            | Competency gate at grant (H-04, T-S04)                                          |
| S-42 | Protection not actually placed            | Per-item protection checklist with timestamps (J9)                              |
| S-43 | Emergency at site uncommunicable          | Offline emergency path + documented voice fallback (G15, J9)                    |
| S-44 | Safety lessons not encoded                | Rules engine with citations to enquiry recommendations (H10)                    |
| S-45 | Late passenger notice                     | Class notice periods; disruption payload on approval (I5.2, I7)                 |
| S-46 | Detention misattributed                   | Structured attribution to cause objects (F4.3)                                  |
| S-47 | Diversion route also blocked              | Diversion validated against the block picture (H6.2, T-I02)                     |
| S-48 | SLW without capacity analysis             | Capacity profiles per configuration (H3 step 10, H6)                            |
| S-49 | Knock-on delay ignored                    | Propagation modelling in L2/L3 (H6.1, H6.2)                                     |
| S-50 | Premium services unprotected              | Service priority classes; S-07 soft constraint / hard where configured          |
| S-51 | Suburban peak destroyed                   | Peak windows as hard constraints with senior override (H-07, V-10)              |
| S-52 | Inconsistent passenger information        | Single disruption output stream (I7)                                            |
| S-53 | Freight windows collide                   | Terminal schedules as constraints; tonnage impact (H6.2)                        |
| S-54 | Yard congestion                           | Holding capacity modelling; warning on projected holds                          |
| S-55 | Perishables not prioritised               | Consignment sensitivity in the impact model                                     |
| S-56 | Revenue cost never calculated             | Cost model (H6.2); indicative cost on every option                              |
| S-57 | Over-wide traction isolation              | Traction graph + minimal isolation computation (H3 step 8, K8)                  |
| S-58 | Traffic and power blocks separate         | Combined block object with linked sub-blocks (G8 7.11, H2)                      |
| S-59 | Whole activity requested as a block       | Phases requiring block (G4 3.11); restriction alternative (G4 3.10)             |
| S-60 | Testing time underestimated               | Separate testing duration (G5 4.8, G9 8.6/8.7); learned testing times           |
| S-61 | No reversion plan                         | Mandatory reversion plan + point of no return (G9 8.9/8.10)                     |
| S-62 | Low machine utilisation                   | Joint machine/block optimisation; machine itinerary view (H8, J3)               |
| S-63 | Machine breakdown mid-block               | In-block incident event → recomputed hand-back and impact (I5.3)                |
| S-64 | Gangs idle                                | Personal "my blocks" view with clear status (J9)                                |
| S-65 | Contractor notice breached                | Contract terms modelled; warning on change (G12 11.5, V-21)                     |
| S-66 | Rain washes out the block                 | Weather sensitivity + forecast checks + standby (G4 3.12, H7.2)                 |
| S-67 | Temperature/wind constraints              | Environmental rules family (H10.3)                                              |
| S-68 | Mass disruption invalidates the plan      | Disruption declaration + bulk re-planning (I5.5)                                |
| S-69 | External events                           | External constraint calendar (F4.5)                                             |
| S-70 | Emergency block                           | 30-second emergency path (G15, I5.4)                                            |
| S-71 | Emergency collides with planned work      | Automatic at-risk marking and re-planning queue (I5.4)                          |
| S-72 | Asset failure attention                   | Failure objects spawning blocks; asset reliability history                      |
| S-73 | Accident restoration                      | Restoration block class + incident dashboard (F5, I5.5)                         |
| S-74 | Security blocks                           | Security class with restricted visibility (F5)                                  |
| S-75 | Project needs recurring access            | Programme portfolio object (F4.2, G2 1.10)                                      |
| S-76 | Third-party works                         | External portal with sponsorship and method statements (G16)                    |
| S-77 | Contractor competency                     | Contractor competency records + grant gate (G10 9.14, H-04)                     |
| S-78 | Project vs maintenance conflict           | Single demand pool in one optimisation (H8)                                     |
| S-79 | Decision unreconstructable                | Decision records + reproducible planning runs (L3)                              |
| S-80 | Manual, unreliable statistics             | All KPIs derived automatically with drill-through (J10)                         |
| S-81 | Data captured, never analysed             | Analytics layer with standing questions (J10, H11)                              |
| S-82 | Shift handover loses context              | Auto-generated handover pack (J3, J4)                                           |
| S-83 | Burdensome entry degrades quality         | Progressive disclosure, templates, computed fields (G1, G17)                    |
| S-84 | Departmental mistrust                     | Symmetric transparency in scorecards (J10, L7.2)                                |
| S-85 | Escalation is personal                    | SLA clocks + defined ladder (H1.1)                                              |
| S-86 | Approval bottleneck                       | Role-based approval with recorded delegation (L1.1)                             |
| S-87 | Transfers destroy knowledge               | Asset and section dossiers (J3 NETWORK)                                         |
| S-88 | Staff resist added work                   | Immediate value per role (F1.9, L7.1)                                           |
| S-89 | Low connectivity                          | Offline-first field app with fail-safe staleness (J9)                           |
| S-90 | Language and literacy                     | Multilingual, icon-led, high-contrast design (J11)                              |
| S-91 | Training and turnover                     | In-app guidance + sandbox environment (L7)                                      |
| S-92 | Gaming the system                         | Claimed-vs-actual tracking on scorecards (J10, H11.1)                           |
| S-93 | Over-reliance on the optimiser            | Mandatory explainability; options not answers (H9, H8.6)                        |
| S-94 | System as single point of failure         | Degraded modes + printable artefacts + reconciliation (L5)                      |

---

# Part N — Risks, Open Questions and Further Work

## N1. Principal risks

| #   | Risk                                                                         | Likelihood | Impact   | Mitigation                                                                                                                                                   |
| --- | ---------------------------------------------------------------------------- | ---------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| R1  | **Topology data is incomplete or wrong**, so derived unavailability misleads | High       | Critical | Phase 0 validation workstream with engineer sign-off; confidence flags on segments with unverified data; never present low-confidence derivations as certain |
| R2  | **Adoption failure** — parallel registers persist                            | High       | Critical | Value-first sequencing (see→record→analyse→optimise); immediate value per role; formal retirement directive                                                  |
| R3  | **Optimiser output distrusted**                                              | Medium     | High     | Explainability as a first-class feature; options not answers; published weights; advisory-only mode for the first year                                       |
| R4  | **Automation complacency** — staff stop thinking                             | Medium     | Critical | UI framing as proposals; mandatory justification on approval; periodic manual-mode exercises                                                                 |
| R5  | **The system becomes a safety dependency it was never designed to be**       | Medium     | Critical | Explicit red lines (C4) restated in every field UI; degraded-mode testing; physical protection remains primary                                               |
| R6  | **Integration feeds unreliable**, so impact figures are wrong                | High       | High     | Explicit staleness on every derived figure; defined degraded behaviour per feed; never present stale data as current                                         |
| R7  | **Data entry burden degrades quality**                                       | High       | High     | Ruthless field minimisation; computed fields; templates; monitor placeholder-text rate as a KPI                                                              |
| R8  | **Departmental gaming** of criticality and duration                          | High       | Medium   | Claimed-vs-actual scorecards; automatic de-biasing; transparency                                                                                             |
| R9  | **Scope creep into EAM / timetabling / control**                             | High       | Medium   | Explicit scope boundaries (A1.2); integrate rather than absorb                                                                                               |
| R10 | **Performance collapse of the map at scale**                                 | Medium     | High     | Tiling, viewport scoping, delta updates, clustering; load testing at 2× expected volume                                                                      |
| R11 | **Change of leadership kills the programme**                                 | Medium     | High     | Early, visible, quantified wins (reserve queue and bundling produce savings within months)                                                                   |
| R12 | **Field devices unavailable or unsupported**                                 | Medium     | High     | Progressive web app; low-end device support; SMS fallback for critical notifications                                                                         |
| R13 | **Rules become an unaudited parallel rule book**                             | Medium     | Critical | Citation mandatory; safety approval for hard rules; versioning; rule-firing analytics                                                                        |
| R14 | **Cross-division rollout stalls** on inconsistent master data                | High       | Medium   | Central schema, federated ownership, conformance testing before onboarding                                                                                   |

## N2. Open questions requiring decisions before build

1. **Granularity of the blockable unit.** Is the atomic unit the track segment between
   nodes, or a chainage range within a line? The former is cleaner for graph reasoning;
   the latter matches how blocks are actually described. _Recommendation: model chainage
   ranges, index them against segments, and support both in the UI._
2. **How microscopic must the impact model be?** Blocking-time-theory-level fidelity is
   expensive to build and to maintain. _Recommendation: L1/L2 in-house, L3 by integration
   with an existing simulation capability where one exists._
3. **Where does the train position feed come from, and at what quality?** This determines
   whether the map is a live operational tool or a planning tool with a delayed picture.
4. **Is the timetable stable enough to plan against at T-21 days?** If paths change
   frequently, impact figures computed at planning time will be wrong by execution time;
   re-computation cadence must be defined.
5. **Who owns the objective weights?** Division, Zone, or Board? This is a policy question
   with real consequences for how the railway trades punctuality against maintenance.
6. **Statutory status of digital records.** Can a digital hand-back certificate stand in
   place of the current paper instrument, and under what conditions? Requires a formal
   determination before Phase 2.
7. **Emergency block formalisation.** How much may be recorded retrospectively, and what
   is the maximum permissible delay before the record is considered deficient?
8. **Third-party access model.** Portal, or sponsored entry by a railway officer only?
   Security and accountability argue for the latter; scale argues for the former.
9. **Relationship to existing control-room systems.** Side-by-side screens, or embedded?
   Controllers have finite screen real estate and finite attention.
10. **Offline safety indication liability.** What exactly may the field app assert when it
    has been offline for 20 minutes? This needs a formal safety determination, not a
    design opinion.

## N3. Further work

- **Predictive maintenance integration.** Condition data driving demand generation, so the
  system asks for a block before the asset fails rather than after.
- **Capacity-aware annual planning.** Corridor possession strategy set a year ahead, with
  departments bidding into declared windows — the mature end-state of the corridor block
  concept.
- **Automated caution order generation** end to end, from hand-back certificate to driver
  instruction.
- **Delay attribution automation** using the block record plus the running record, removing
  a large manual and contentious workload.
- **Cross-zone corridor optimisation** — the national view, once divisional data quality
  is proven.
- **What-if studio** for planners: model the effect of a policy change (e.g. "what if we
  declared a weekly 4-hour corridor block on this route?") before adopting it.
- **Machine learning on overrun risk** to set contingency margins automatically.
- **Digital twin ambitions** should be resisted until the basics are solid; a truthful
  topology and honest actuals are worth more than a sophisticated model built on bad data.

## N4. Closing note

The instinct in a programme like this is to begin with the optimiser, because that is the
interesting part. That instinct should be resisted.

The optimiser is worth nothing without a truthful topology, and the topology is worth
nothing if nobody records what actually happened, and none of it is worth anything if the
gangman on the track cannot tell, with certainty, whether he is protected.

Build in that order: **truth first, then memory, then intelligence.**

The prize is substantial and measurable — a quarter more maintenance output from the same
sanctioned block-hours, a third less deferred work, fewer emergencies, and, for the first
time, an institutional answer to the question the railway has never been able to answer
about its own most contested resource:

> _What did we actually get for the hours we took the railway away from the public — and
> did we get it safely?_

---

# Part O — Implementation Blueprint

## _How this paper becomes running software (optimisation service excluded)_

---

## O0. How to read this Part

### O0.1 Purpose

Parts A–N described **what the railway needs and why**. Part O describes **how we build
it**, on the stack that this repository has already committed to, in the order we will
build it, with the concrete files, endpoints, schemas and acceptance gates for each piece.

It is written for the person who has to open an editor tomorrow morning.

### O0.2 Deliberate exclusion — the optimisation service

**Nothing in Part O describes the optimisation service.** No solver, no objective
function implementation, no ranked-plan generation, no bundling search, no
`optimization-service` internals.

That work is being deferred and will be authored separately. Part O therefore:

- treats the optimiser as an **external module behind a frozen interface** (O25);
- builds everything the optimiser will eventually need — truthful topology, structured
  demand, actuals capture, conflict facts, impact inputs — **without building the
  optimiser itself**;
- makes every screen and API work in an **"advisory-off" mode**, so the product is
  complete, demonstrable and useful before any optimisation exists.

This is not a compromise. It is the sequencing argued for in [N4](#n4-closing-note):
**truth first, then memory, then intelligence.**

### O0.3 What this Part deliberately does NOT repeat

To keep this document a *build guide* and not a third copy of the same material, the
following live elsewhere and are **referenced, not restated**:

| Already documented in                              | Covers                                                                        | Part O's relationship                                                            |
| -------------------------------------------------- | ----------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| `docs/plan.md`                                     | Phase 0–15 delivery plan, confirmed stack decisions, backlog                  | Part O **adopts** the stack verbatim and adds the OPUS-5 delta as new phases      |
| `docs/application_architecture_flow.md`            | Service decomposition, CQRS write/read split, event-driven loop                | Part O **assumes** it; only extensions are described                              |
| `docs/database_schema.md`                          | Existing MVP tables                                                            | Part O lists **only the new/changed tables** OPUS-5 requires                      |
| `docs/frontend-plan.md`                            | Next.js routes, design system, component inventory, forms strategy             | Part O adds **only the OPUS-5 screens and the map chapter**                       |
| `docs/MAP_VISUALIZATION_ARCHITECTURE.md`           | 3D (X,Y,Time) tiling, delta transfer, base-graph endpoint, Maplibre choice     | Part O **builds on the tiling contract** and specifies the *dynamism and clarity* layer above it |
| OPUS-5 [Part I](#part-i--architecture-and-system-flow) | Logical architecture, principal flows, API surface (indicative)           | Part O turns the indicative API into a **concrete, versioned endpoint catalogue**  |
| OPUS-5 [Part J](#part-j--frontend-and-experience-design) | Screen designs, UX principles, field app                                | Part O gives the **component/file plan and state ownership** for those screens     |
| OPUS-5 [Part K](#part-k--the-map)                  | Map visual grammar, view modes, layer semantics                                | Part O gives the **rendering implementation, LOD tables, label engine, perf budget** |

> **Rule for contributors:** if a statement in Part O contradicts one of the documents
> above, Part O wins for *implementation detail*; the referenced document wins for
> *intent*. Raise the contradiction rather than silently choosing.

### O0.4 Reading order for a new contributor

```
1. plan.md §1 (stack)                        — what we build with
2. OPUS-5 Part C (problem) + Part F (design) — why it exists
3. OPUS-5 Part O0–O3 (this Part, start)      — the shape of the codebase
4. The chapter for your work package:
      backend data      → O4, O5
      write path        → O6, O7
      derived facts     → O8, O9
      read path         → O10, O11, O12, O13
      frontend          → O14
      the map           → O15   ← the largest chapter, read fully before touching the map
      field app         → O16
      platform          → O17–O21
5. O22 (sequence) to find what is unblocked right now
6. O23 if you are blocked on something only the product owner can answer
```

---

## O1. Implementation stance

### O1.1 Five stances that govern every decision below

1. **Additive, never destructive.** The repository already runs end-to-end (Phases 0–12
   of `plan.md`). OPUS-5 is implemented as *additive migrations, additive endpoints and
   additive screens*. Nothing existing is deleted until its replacement is proven.
2. **Truth before intelligence.** Topology fidelity, actuals capture and honest staleness
   are built first because every later capability is worthless without them.
3. **Deterministic before heuristic.** Everything that can be computed exactly — topology
   expansion, overlap detection, capacity lookup, rule evaluation — is built now as plain
   deterministic code. Only search/ranking is deferred to the optimiser.
4. **Every screen works with zero optimiser.** If the optimiser never ships, the product
   is still a coherent, useful, demonstrable system. The optimiser adds *ranking*, not
   *function*.
5. **The map is the product.** For this domain, the map is not a feature — it is the
   primary comprehension surface for controllers, planners and management. It gets the
   largest chapter, the strictest performance budget and the hardest acceptance tests.

### O1.2 Honest inventory — what exists in the repository today

| Area                | State                                                                                                | Verdict           |
| ------------------- | ---------------------------------------------------------------------------------------------------- | ----------------- |
| Monorepo scaffold   | `/services/{api-gateway,command-service,query-service,optimization-service}`, `/db`, `/contracts`, `/frontend`, `/infra` | **Keep**          |
| Operational DB      | SQLAlchemy models + Alembic; org, network, planning, requests, events, identity                      | **Extend** (O4.1) |
| Read Store          | Separate Postgres DB, four projections + map projections, own Alembic                                | **Extend** (O4.3) |
| Contracts           | Envelope, typed payloads, topic map, JSON Schemas                                                    | **Extend** (O5)   |
| Command Service     | `POST/PATCH /block-requests`, validation, Kafka publish                                              | **Extend** (O6)   |
| Query Service       | `/plans /blocks /tracks /trains /basegraph /trainpositions`, Redis cache-aside                       | **Extend** (O10)  |
| API Gateway         | Reverse proxy, correlation ID, stub auth, CORS                                                       | **Extend** (O11)  |
| ETL                 | Polling full-refresh + tile version bumping                                                          | **Extend** (O12)  |
| Frontend            | Next.js App Router, Tailwind + shadcn/ui, TanStack Query, Zustand, Maplibre map, time slider          | **Extend** (O14, O15) |
| Optimisation service| Shadow finder + interval-union merge (MVP placeholder)                                               | **Frozen** (O25)  |

### O1.3 The OPUS-5 gap register

Everything OPUS-5 demands that does not exist yet, with its verdict. `BUILD` = in scope
for Part O. `DEFER-OPT` = belongs to the optimisation service, out of scope here.
`DEFER-P2` = a later phase, interface reserved now.

| #   | Capability (OPUS-5 ref)                             | Verdict    | Where in Part O |
| --- | --------------------------------------------------- | ---------- | --------------- |
| G01 | Chainage-addressed extents (N2.1)                   | BUILD      | O4.1            |
| G02 | Topology graph with turnouts/crossovers (M2)        | BUILD      | O4.1            |
| G03 | Traction elementary-section graph (M2, G8)          | BUILD      | O4.1            |
| G04 | Derived unavailability engine (H3)                  | BUILD      | O8              |
| G05 | Full structured demand schema (Part G)              | BUILD      | O6.2            |
| G06 | Entry-time validation catalogue V-01…V-24 (G18)     | BUILD      | O6.4            |
| G07 | Demand lifecycle + SLA clocks (H1)                  | BUILD      | O6.5            |
| G08 | Execution lifecycle with hard safety gates (H2)     | BUILD      | O6.6            |
| G09 | Protection / disconnection / isolation registers    | BUILD      | O4.1, O6.7      |
| G10 | Hand-back certificate + restriction register (H2)   | BUILD      | O6.8            |
| G11 | Post-block actuals R.1–R.20 (G19)                   | BUILD      | O6.9            |
| G12 | Resource model + readiness gate (H7)                | BUILD      | O4.1, O6.10     |
| G13 | Competency register + grant gate (H-04)             | BUILD      | O4.1, O6.10     |
| G14 | Rules engine, config-driven, cited (H10)            | BUILD      | O7              |
| G15 | Conflict detection (H4) — deterministic             | BUILD      | O9.1            |
| G16 | Impact engine L1 (capacity/detention arithmetic)    | BUILD      | O9.2            |
| G17 | Impact engine L2/L3 (propagation, simulation)       | DEFER-P2   | O9.3            |
| G18 | Shadow finder / bundling search (H5)                | DEFER-OPT  | O25             |
| G19 | Objective function + ranked options (H8)            | DEFER-OPT  | O25             |
| G20 | Explainability rendering (H9)                       | BUILD (shell) | O9.4, O15.11 |
| G21 | Learning loop / duration model (H11)                | DEFER-OPT  | O25             |
| G22 | Notification + acknowledgement fabric (I6)          | BUILD      | O17             |
| G23 | Live block console (J8)                             | BUILD      | O14.6           |
| G24 | Offline-first field PWA (J9)                        | BUILD      | O16             |
| G25 | Dynamic, information-rich map (Part K)              | BUILD      | **O15**         |
| G26 | Time travel past↔future on the map (K6)             | BUILD      | O15.8           |
| G27 | Map-first demand drawing (K4.3)                     | BUILD      | O15.15          |
| G28 | Train graph (time–distance) linked to map           | BUILD      | O15.17          |
| G29 | RBAC + delegation (L1)                              | BUILD      | O18             |
| G30 | Immutable audit + reconstruction (L3)               | BUILD      | O19.2           |
| G31 | Degraded modes + printable artefacts (L5)           | BUILD      | O19.4           |
| G32 | Multilingual UI (J11, S-90)                         | BUILD      | O14.9           |

---

## O2. Confirmed stack and the rules for using it

### O2.1 The stack (adopted verbatim from `plan.md` §1)

| Layer                | Technology                                              | Version pin        | Non-negotiable because                                       |
| -------------------- | ------------------------------------------------------- | ------------------ | ------------------------------------------------------------ |
| Language (backend)   | Python                                                  | 3.12               | Existing services; consistent tooling                        |
| Web framework        | FastAPI + Uvicorn                                       | latest 0.1x        | Async, Pydantic-native, OpenAPI for free                     |
| Validation/DTO       | Pydantic v2                                             | 2.x                | Shared with `/contracts`                                     |
| ORM                  | SQLAlchemy 2.0 (declarative, typed)                     | 2.x                | Single source of truth for schema                            |
| Migrations           | Alembic                                                 | 1.13+              | Versioned, reviewable, reversible                            |
| Operational DB       | PostgreSQL                                              | 16                 | Transactions, JSONB, ranges, recursive CTEs                  |
| Read Store           | PostgreSQL (separate database `block_planning_read`)     | 16                 | Read/write isolation per CQRS                                |
| Broker               | Redpanda (Kafka API)                                    | latest             | Kafka semantics, no Zookeeper, light in Compose              |
| Cache                | Redis                                                   | 7                  | Cache-aside, short TTL, pub/sub for SSE fan-out              |
| Frontend framework   | Next.js (App Router) + React 18 + TypeScript (strict)   | 14/15              | Existing; RSC where useful, client islands for the map       |
| Styling              | Tailwind CSS + shadcn/ui + lucide-react                 | current            | Existing design system                                       |
| Server state         | TanStack Query v5                                       | 5.x                | Caching, polling, invalidation                               |
| Client state         | Zustand                                                 | 4.x                | Map/time/tile stores already exist                           |
| Map engine           | Maplibre GL JS                                          | 5.x                | Open, vector, GPU, no licence cost                           |
| Local persistence    | Dexie (IndexedDB) + localStorage                        | 4.x                | Offline field app + base-graph cache                         |
| Charts               | Recharts                                                | 2.x                | Already used for Gantt/KPIs                                  |
| Forms                | react-hook-form + zod                                   | current            | Existing forms strategy                                      |
| Container            | Docker + Docker Compose                                 | current            | One-command local stack                                      |
| Lint/format          | ruff + black (py), eslint + prettier (ts)               | current            | Existing                                                     |

**Additions Part O introduces** (small, justified, no new paradigm):

| Addition                        | Purpose                                                              | Alternative rejected because                    |
| ------------------------------- | -------------------------------------------------------------------- | ----------------------------------------------- |
| `networkx` (backend)            | Topology expansion (H3) — reachability, articulation, path search     | Hand-rolled BFS is fine but loses free algorithms |
| `shapely` (backend)             | Chainage↔geometry interpolation, extent clipping for map geometry     | Manual linear referencing is error-prone        |
| `sse-starlette` (backend)       | Server-Sent Events for live block console (O13)                       | WebSocket is heavier; polling is laggy          |
| `@turf/turf` (frontend, subset) | `along`, `lineSlice`, `bearing` for train/worksite placement           | Reimplementing linear referencing on the client |
| `next-intl` (frontend)          | Multilingual UI (S-90)                                                | Hand-rolled i18n loses pluralisation/format     |
| `maplibre-gl-inspect`-style dev overlay (dev only) | Layer/feature debugging                            | —                                               |

> No GIS server, no PostGIS requirement in the MVP. Geometry is stored as GeoJSON in
> JSONB with a chainage index; PostGIS is a **future** upgrade recorded in O4.6, not a
> prerequisite.

### O2.2 Backend conventions (binding)

```
Module layout inside every service:
  app/
    main.py          — FastAPI app, lifespan, middleware wiring ONLY
    config.py        — pydantic-settings; every env var declared with a default
    db.py            — session dependency
    cache.py         — Redis wrapper (best-effort; degrades to no-cache)
    kafka.py         — publisher/consumer wrapper (best-effort; never blocks a request)
    schemas.py       — API DTOs (never ORM models on the wire)
    domain/          — pure functions, no I/O, unit-testable without a database
    services/        — orchestration: domain + repositories + events
    repositories/    — all SQL lives here; nothing else imports SQLAlchemy queries
    routers/         — thin; parse → call service → serialise
```

Rules:

1. **No business logic in routers.** A router is ≤ 20 lines.
2. **No I/O in `domain/`.** Everything in `domain/` is a pure function taking plain data.
   This is what makes topology expansion, conflict detection and rule evaluation testable.
3. **Never return ORM objects.** Always a Pydantic response model.
4. **All timestamps are timezone-aware UTC** at the boundary; local time is a *display*
   concern only. Store `timestamptz`. This has already bitten the tiling code once.
5. **Every write emits an event** through the transactional outbox (O5.4). No
   fire-and-forget Kafka publish inside a request transaction.
6. **Every mutating endpoint accepts `Idempotency-Key`** and is safe to retry.
7. **Errors are structured**: `{code, message, field?, rule_id?, correlation_id}`. A
   validation failure must name the rule that failed (V-nn) so the UI can explain it.
8. **Nothing safety-relevant is inferred.** If a fact is unknown, it is `UNKNOWN`, and
   `UNKNOWN` renders as unsafe. There is no defaulting to "probably fine".

### O2.3 Frontend conventions (binding)

1. **TypeScript strict.** `any` requires a comment naming the reason.
2. **Server state → TanStack Query. Client state → Zustand.** Never duplicate server data
   into Zustand; store *selection, viewport, filters, time offset* only.
3. **One hook per resource** in `lib/hooks/use-*.ts`; components never call `fetch`.
4. **Every list/detail screen implements four states**: loading (skeleton), empty
   (`EmptyState`), error (`ErrorState` with retry + correlation id), stale
   (`FreshnessIndicator`).
5. **Colour is never the only signal.** Every semantic colour is paired with an icon,
   pattern or label (accessibility + sunlight readability, S-90).
6. **The map is a client island.** `'use client'`, dynamic import, `ssr: false`.
7. **No layout shift on data refresh.** Polling must not cause the map or tables to jump.

### O2.4 Naming conventions

| Thing              | Convention                                | Example                                  |
| ------------------ | ----------------------------------------- | ---------------------------------------- |
| Table              | `snake_case`, singular                    | `block_demand`, `track_segment`          |
| Column             | `snake_case`; times end `_at`; flags `is_`| `granted_at`, `is_emergency`             |
| Enum values (DB)   | `UPPER_SNAKE`                             | `HANDBACK_CERTIFIED`                     |
| Event type         | `domain.entity.past_tense`                | `block.demand.submitted`                 |
| Kafka topic        | `dot.separated.plural`                    | `plan.commands`, `block.execution.events`|
| REST path          | `kebab-case`, plural                      | `/block-demands/{id}/extension-requests` |
| Rule id            | `V-nn` (validation), `H-nn` (hard), `S-nn` (soft) | `V-11`, `H-04`                    |
| Map layer id       | `layer-domain-role`                       | `layer-block-fill`, `layer-train-label`  |
| Map source id      | `src-domain`                              | `src-trains`, `src-blocks`               |
| Zustand store      | `*.store.ts` exporting `use*Store`        | `map.store.ts` → `useMapStore`           |

---

## O3. Repository layout after this implementation

Only **new or materially changed** paths are shown. Everything else stays as-is.

```
team-waypoints/
├── contracts/
│   └── events/
│       ├── schemas.py                # + demand, execution, safety, notification payloads
│       ├── events.py                 # + ~30 new event classes in EVENT_REGISTRY
│       ├── topics.py                 # + block.execution.events, safety.events,
│       │                             #   notification.commands, map.invalidation
│       └── json_schemas/             # + one .json per new event
│
├── db/
│   ├── models/
│   │   ├── network.py                # + Node, TrackSegment, Turnout, Crossover,
│   │   │                             #   LevelCrossing, Structure, Platform, Siding
│   │   ├── traction.py               # NEW  TractionFeeder, ElementarySection, EarthPoint
│   │   ├── signalling.py             # NEW  SignallingElement, Interlocking
│   │   ├── demand.py                 # NEW  BlockDemand (full Part G schema), DemandLink
│   │   ├── execution.py              # NEW  Block, WorkPackage, Worksite, ProtectionItem,
│   │   │                             #      Disconnection, Isolation, HandbackCertificate
│   │   ├── restriction.py            # NEW  Restriction, RestrictionReview
│   │   ├── resource.py               # NEW  Machine, Gang, Person, Competency, Material,
│   │   │                             #      Contractor, ResourceBooking
│   │   ├── rules.py                  # NEW  Rule, RuleVersion, RuleFiring
│   │   ├── governance.py             # NEW  Decision, ApprovalStep, Delegation, AuditRecord
│   │   └── notification.py           # NEW  Notification, Recipient, Acknowledgement
│   │
│   ├── domain/                       # NEW — pure, importable by any service
│   │   ├── chainage.py               #   linear referencing helpers
│   │   ├── topology.py               #   H3 derived-unavailability engine
│   │   ├── conflicts.py              #   H4 deterministic conflict detection
│   │   ├── capacity.py               #   capacity profile selection
│   │   ├── impact_l1.py              #   deterministic detention arithmetic
│   │   ├── rules_engine.py           #   H10 evaluator
│   │   └── lifecycle.py              #   H1/H2 state machines as data
│   │
│   ├── readstore/
│   │   ├── models.py                 # + BlockView2, WorksiteView, RestrictionView,
│   │   │                             #   ConflictView, DemandView, ResourceView,
│   │   │                             #   NetworkGeometry, SectionCapacityView
│   │   ├── tiling.py                 # + block/restriction tiling, multi-layer versions
│   │   └── etl.py                    # + incremental sync, per-entity version bumps
│   │
│   └── migrations/versions/          # + 0003…00NN (one concern per migration)
│
├── services/
│   ├── command-service/app/
│   │   ├── domain/                   # NEW  validation, gates, state transitions
│   │   ├── routers/
│   │   │   ├── demands.py            # NEW  full Part G intake
│   │   │   ├── execution.py          # NEW  grant/protect/start/extend/handback
│   │   │   ├── safety.py             # NEW  disconnections, isolations, competency checks
│   │   │   ├── resources.py          # NEW  bookings, readiness gate
│   │   │   ├── restrictions.py       # NEW  register + review
│   │   │   └── event_injection.py    # existing (demo/testing)
│   │   └── outbox.py                 # NEW  transactional outbox + relay
│   │
│   ├── query-service/app/
│   │   ├── routers/
│   │   │   ├── map.py                # NEW  /map/snapshot, /map/tiles, /map/inspect/*
│   │   │   ├── demands.py            # NEW  list/detail/timeline
│   │   │   ├── conflicts.py          # NEW  conflict + derived-unavailability reads
│   │   │   ├── restrictions.py       # NEW
│   │   │   ├── resources.py          # NEW
│   │   │   ├── traingraph.py         # NEW  time–distance series for the mini graph
│   │   │   └── stream.py             # NEW  SSE fan-out from Redis pub/sub
│   │   └── cache_keys.py             # NEW  single place defining every cache key + TTL
│   │
│   ├── api-gateway/app/
│   │   ├── auth.py                   # NEW  JWT verify, role/scope extraction
│   │   ├── rate_limit.py             # NEW  per-identity token bucket (Redis)
│   │   └── routers/stream.py         # NEW  SSE passthrough (no buffering)
│   │
│   └── optimization-service/         # FROZEN — see O25. Do not modify in this work.
│
└── frontend/
    ├── app/
    │   ├── situation/                # NEW  the landing "situation" screen (J4)
    │   ├── demands/                  # NEW  list, detail, wizard (map-first)
    │   ├── console/                  # NEW  live block console (J8)
    │   ├── field/                    # NEW  field PWA routes (J9)
    │   └── infrastructure/map/       # EXTENDED — the dynamic map (O15)
    │
    ├── components/map/               # EXTENDED — see O15.21 for the full file plan
    ├── components/inspector/         # NEW  progressive detail panel
    ├── components/timeline/          # NEW  time slider + playback + train graph
    ├── lib/map/                      # NEW  layer specs, style tokens, label engine
    ├── lib/offline/                  # NEW  Dexie schema, queue, sync
    └── stores/                       # + inspector.store.ts, filter.store.ts, playback.store.ts
```

---

## O4. Data layer implementation

### O4.1 Operational schema — new tables

Only the **new** tables are specified. Column lists are indicative but the keys,
constraints and index notes are binding, because they are what makes the map and the
conflict engine fast enough.

#### O4.1.1 Network / topology

```
node
  id PK, code, name, node_type ENUM(STATION|JUNCTION|SIGNAL|LC|BRIDGE|NEUTRAL_SECTION|
                                    BLOCK_HUT|YARD_ENTRY|SIDING_ENTRY|BOUNDARY)
  section_id FK, lat, lon, chainage_m INT, is_block_station BOOL
  attributes JSONB
  INDEX (section_id, chainage_m)

track_segment                                    -- THE atomic blockable unit
  id PK, line_id FK, from_node_id FK, to_node_id FK
  chainage_start_m INT, chainage_end_m INT       -- CHECK end > start
  length_m INT GENERATED, geometry JSONB          -- GeoJSON LineString, WGS84
  schematic_geometry JSONB                        -- pre-computed straightened variant
  max_speed_kmph INT, gauge, is_electrified BOOL
  direction ENUM(UP|DN|BIDIRECTIONAL)
  confidence ENUM(VERIFIED|IMPORTED|ESTIMATED)    -- R1 mitigation, surfaced in the UI
  INDEX (line_id, chainage_start_m), INDEX (from_node_id), INDEX (to_node_id)

turnout      id PK, node_id FK, facing_segment_id FK, normal_segment_id FK,
             reverse_segment_id FK, max_speed_reverse_kmph, is_motor_operated BOOL
crossover    id PK, name, turnout_ids JSONB, line_a_id FK, line_b_id FK,
             node_id FK, chainage_m
level_crossing  id PK, segment_id FK, chainage_m, lc_type, road_class, is_manned
structure       id PK, segment_id FK, chainage_from_m, chainage_to_m,
                structure_type ENUM(MAJOR_BRIDGE|MINOR_BRIDGE|TUNNEL|ROB|RUB|CULVERT)
platform        id PK, station_node_id FK, number, length_m, reachable_via JSONB
siding          id PK, node_id FK, customer, capacity_wagons, reachable_via JSONB
```

#### O4.1.2 Traction graph (enables the *minimal isolation set*, G8 7.4)

```
traction_feeder      id PK, code, tss_node_id FK, phase, nominal_kv
elementary_section   id PK, code, feeder_id FK,
                     start_node_id FK, end_node_id FK,       -- SP/SSP boundaries
                     covered_segment_ids JSONB,              -- denormalised for speed
                     is_switchable_independently BOOL
earth_point          id PK, elementary_section_id FK, node_id FK, chainage_m, type
```

> **Why denormalise `covered_segment_ids`:** the minimal-isolation computation runs on
> every keystroke in the demand wizard. A JSONB array with a GIN index answers
> "which elementary sections cover these segments?" in one query.

#### O4.1.3 Signalling

```
signalling_element  id PK, element_type ENUM(SIGNAL|POINT_MACHINE|AXLE_COUNTER|
                        TRACK_CIRCUIT|LC_GATE|BLOCK_INSTRUMENT|PANEL),
                    node_id FK NULL, segment_id FK NULL, chainage_m,
                    interlocking_id FK, identifier
interlocking        id PK, station_node_id FK, type ENUM(RRI|PI|EI|SSI), commissioned_on
```

#### O4.1.4 Demand (the Part G schema, made physical)

```
block_demand
  id PK, reference TEXT UNIQUE,                    -- human handle, e.g. BD-2026-004821
  version INT NOT NULL DEFAULT 1,                  -- amendments create versions
  supersedes_id FK NULL,
  block_class ENUM(...F5...), status ENUM(...H1...),
  department_id FK, unit_id FK, requester_id FK, sponsor_id FK NULL,
  origin_type ENUM, origin_ref TEXT, programme_id FK NULL,
  -- extent
  from_node_id FK, to_node_id FK, line_ids JSONB, segment_ids JSONB,
  chainage_from_m INT, chainage_to_m INT, direction ENUM,
  occupancy ENUM(COMPLETE|PARTIAL_WIDTH|SLW),
  adjacent_line_status ENUM(OPEN|CAUTIONED|BLOCKED|PHYSICALLY_SEPARATED|NOT_APPLICABLE),
  adjacent_line_speed_kmph INT NULL,
  -- work
  work_category, work_type, description TEXT, quantum NUMERIC, quantum_unit,
  method ENUM, criticality ENUM, deferral_consequence TEXT,
  statutory_due_on DATE NULL, restriction_alternative JSONB,
  weather_sensitivity ENUM, expected_output TEXT,
  -- timing
  preferred_start TIMESTAMPTZ, alt_windows JSONB, flexibility ENUM,
  duration_total_min INT,
  dur_protection_min INT, dur_work_min INT, dur_testing_min INT, dur_handback_min INT,
  min_viable_min INT, is_divisible BOOL, latest_acceptable_on DATE NULL,
  recurrence JSONB NULL,
  -- safety / traction / s&t sub-documents (sparse, conditional sections)
  protection JSONB, traction JSONB, signalling JSONB, resources JSONB,
  commercial JSONB, attachments JSONB,
  -- system-computed snapshots (recomputed, never trusted as input)
  computed JSONB,                                  -- derived unavailability, conflicts, L1 impact
  combinable BOOL NOT NULL DEFAULT TRUE,           -- G11 10.3
  created_at, submitted_at, decided_at, sla_due_at
  INDEX (status, preferred_start), INDEX GIN (segment_ids), INDEX (department_id, status)

demand_link   id PK, from_demand_id FK, to_demand_id FK,
              link_type ENUM(MUST_PRECEDE|MUST_FOLLOW|SIMULTANEOUS|MUTUALLY_EXCLUSIVE|
                             DUPLICATE_OF|SUPERSEDES|BALANCE_OF)
              -- acyclicity enforced in the service layer (V-09), tested by a recursive CTE
```

> **Why JSONB for the conditional sections:** G7–G12 are sparse — a P.Way demand has no
> traction section. Fully normalising them creates a dozen near-empty tables. They are
> validated by Pydantic on the way in (so they are *not* free-form) and indexed only where
> queried. The **non-sparse, always-queried** fields stay as real columns.

#### O4.1.5 Execution

```
block                       -- the sanctioned access event; one demand → 0..1 block,
                            -- but one block ← many demands (bundling, later)
  id PK, reference UNIQUE, block_class ENUM, status ENUM(...H2...),
  planned_start TIMESTAMPTZ, planned_end TIMESTAMPTZ,
  actual_grant_at, actual_start_at, actual_handback_at, actual_line_clear_at,
  grant_delay_reason ENUM NULL, grant_delay_note TEXT,
  segment_ids JSONB, chainage_from_m, chainage_to_m, occupancy ENUM,
  traffic_state ENUM(NOT_REQUESTED|REQUESTED|GRANTED|SURRENDERED|RESTORED),
  power_state   ENUM(NOT_REQUIRED|REQUESTED|ISOLATED|EARTHED|RESTORED),
  adjacent_line_status ENUM,
  nominated_person_id FK, controller_id FK, plan_id FK NULL,
  created_at, closed_at
  INDEX (status, planned_start), INDEX GIN (segment_ids)

work_package  id PK, block_id FK, demand_id FK, party_id FK, status ENUM,
              chainage_from_m, chainage_to_m, progress_pct INT, readiness JSONB
worksite      id PK, work_package_id FK, chainage_m INT, lat, lon,
              reported_at TIMESTAMPTZ, reported_by FK      -- rolling block front (S-35)
protection_item  id PK, block_id FK, item ENUM(DETONATORS|BANNER_FLAG|HAND_SIGNAL|
                     CLAMP_PADLOCK|STOP_BOARD|DISCONNECTION|LOOKOUT|POINT_CLAMP),
                 position ENUM(APPROACH_UP|APPROACH_DN|SITE), required BOOL,
                 confirmed_at, confirmed_by FK, photo_ref
disconnection    id PK, block_id FK, signalling_element_id FK,
                 disconnected_at, disconnected_by, reconnected_at, reconnected_by,
                 notice_ref                                -- PAIRING ENFORCED (S-40)
isolation        id PK, block_id FK, elementary_section_ids JSONB,
                 requested_at, granted_at, earthed_at, earth_removed_at, restored_at,
                 tpc_id FK, ptw_ref, authorised_person_id FK
handback_certificate id PK, block_id FK, certifier_id FK, certified_at,
                 fitness ENUM(FIT_NORMAL|FIT_WITH_RESTRICTION|NOT_FIT),
                 restriction_id FK NULL, signature_ref, notes
block_actuals    id PK, block_id FK, quantum_achieved, percent_complete,
                 shortfall_reason ENUM, resource_issue ENUM, balance_demand_id FK NULL,
                 reported_at, reported_by
```

#### O4.1.6 Restrictions (S-34 — first-class, aged, reviewed)

```
restriction  id PK, restriction_type ENUM(SPEED|BLOCKAGE|ADHESION|CAUTION|NO_STOPPING),
             value_kmph INT NULL, segment_ids JSONB,
             chainage_from_m, chainage_to_m, direction ENUM,
             imposed_at, imposed_by FK, origin_block_id FK NULL, reason TEXT,
             expected_relaxation_on DATE, review_due_on DATE, owner_id FK,
             relaxed_at NULL, status ENUM(ACTIVE|RELAXED|SUPERSEDED),
             INDEX (status, review_due_on), INDEX GIN (segment_ids)
restriction_review  id PK, restriction_id FK, reviewed_at, reviewed_by, outcome, note
```

#### O4.1.7 Resources and competency

```
machine       id PK, code, machine_type ENUM(TAMPER|BCM|REGULATOR|TOWER_WAGON|RRV|CRANE|
                  USFD|OMS|OTHER), home_base_node_id FK,
              current_node_id FK, current_reported_at, mobilisation_model JSONB
gang          id PK, code, unit_id FK, strength INT, base_node_id FK
person        id PK, name, designation, department_id FK, phone, unit_id FK
competency    id PK, person_id FK, competency_code, valid_from, valid_to, evidence_ref
              INDEX (person_id, competency_code, valid_to)
material      id PK, code, description, uom
material_stock id PK, material_id FK, node_id FK, quantity, reserved_for_demand_id FK
contractor    id PK, name, contract_ref, notice_period_hours, idle_charge_terms JSONB
resource_booking id PK, resource_kind ENUM(MACHINE|GANG|PERSON|CONTRACTOR|MATERIAL),
              resource_id UUID, demand_id FK NULL, block_id FK NULL,
              from_at, to_at, includes_mobilisation BOOL,
              status ENUM(TENTATIVE|CONFIRMED|RELEASED|CONSUMED)
              EXCLUDE constraint on (resource_kind, resource_id, tstzrange(from_at,to_at))
              WHERE status IN ('CONFIRMED')          -- DB-level double-booking prevention
```

> **The `EXCLUDE` constraint is the point.** S-19 (resource conflicts discovered on the
> day) is eliminated at the database level, not by application politeness. Requires
> `btree_gist`; the migration must `CREATE EXTENSION IF NOT EXISTS btree_gist`.

#### O4.1.8 Rules, governance, notification

```
rule           id PK, code UNIQUE, family ENUM(SAFETY|CAPACITY|RESOURCE|ENVIRONMENT|
                   PROCEDURAL|COMMERCIAL), severity ENUM(HARD|SOFT|WARN),
               citation TEXT NOT NULL,               -- L1: no uncited rule may exist
               is_active BOOL, scope JSONB
rule_version   id PK, rule_id FK, version INT, expression JSONB, message_template TEXT,
               effective_from, effective_to, approved_by FK, safety_approved_at
rule_firing    id PK, rule_version_id FK, subject_type, subject_id, fired_at,
               outcome ENUM(BLOCKED|WARNED|PASSED|OVERRIDDEN),
               override_by FK NULL, override_reason TEXT
decision       id PK, subject_type, subject_id, options JSONB, chosen JSONB,
               decider_id FK, decided_at, justification TEXT, correlation_id
approval_step  id PK, subject_type, subject_id, sequence INT, role_code,
               assignee_id FK NULL, delegated_from FK NULL,
               status ENUM(PENDING|APPROVED|REJECTED|ESCALATED|SKIPPED),
               due_at, acted_at, comment
delegation     id PK, from_person_id FK, to_person_id FK, role_code,
               valid_from, valid_to, reason, created_by
audit_record   id PK, actor_id, action, entity_type, entity_id,
               before JSONB, after JSONB, at TIMESTAMPTZ, correlation_id, ip, user_agent
               -- APPEND ONLY: revoke UPDATE/DELETE for the application role
notification   id PK, event_type, subject_type, subject_id, payload JSONB,
               created_at, priority ENUM(INFO|ACTION|URGENT|SAFETY)
notification_recipient id PK, notification_id FK, person_id FK, role_code,
               channel ENUM(IN_APP|PUSH|SMS|EMAIL|VOICE_FALLBACK),
               sent_at, delivered_at, acknowledged_at, escalated_at
```

### O4.2 Migration strategy

Rules for every Alembic revision in this work:

1. **One concern per revision.** `0003_topology`, `0004_traction`, `0005_demand`,
   `0006_execution`, `0007_restrictions`, `0008_resources`, `0009_rules_governance`,
   `0010_notifications`. Never a "misc" migration.
2. **Enums are created explicitly and referenced by name.** The duplicate `CREATE TYPE`
   bug already found in Phase 10a came from letting SQLAlchemy auto-create enums twice.
   Use `sa.Enum(..., name='...', create_type=False)` in the table and an explicit
   `op.execute("CREATE TYPE ...")` guarded by `IF NOT EXISTS` logic.
3. **Every revision has a working `downgrade()`.** Tested once in CI on a scratch DB.
4. **Data backfill is a separate revision** from the DDL that enables it, so a failed
   backfill does not block the schema.
5. **No `NOT NULL` without a default on an existing table** — add nullable, backfill,
   then tighten in a third revision.
6. **`alembic check` runs in CI**; model drift fails the build.

### O4.3 Read Store projections (map-first)

The Read Store exists so the map and dashboards never touch the operational database. New
projections, all denormalised, all carrying `synced_at` and a `version`:

| Projection            | Grain                          | Feeds                                            |
| --------------------- | ------------------------------ | ------------------------------------------------ |
| `network_geometry`    | one row per track segment      | base graph, both geographic and schematic        |
| `node_view`           | one row per node               | station labels, junction markers                 |
| `block_view`          | one row per block              | map block layer, console, Gantt                  |
| `block_extent_view`   | one row per (block, segment)   | **map rendering without a join** — the hot path  |
| `worksite_view`       | one row per worksite report    | live work-front marker                           |
| `restriction_view`    | one row per active restriction | restriction overlay, ageing dashboard            |
| `demand_view`         | one row per demand             | demand lists, planning board, map "proposed" layer|
| `conflict_view`       | one row per detected conflict  | conflict layer + conflict inbox                  |
| `derived_unavail_view`| one row per (block, segment, reason) | "what else dies" shading                   |
| `train_position`      | existing, extended             | train layer (+ delay, confidence, next stop)     |
| `train_graph_series`  | one row per (train, time, chainage) | mini time–distance graph                    |
| `section_capacity_view`| one row per (section, config) | capacity badge on the map and impact panel       |
| `resource_view`       | one row per booking            | resource timeline, readiness panel               |
| `kpi_daily`           | one row per (scope, date, kpi) | executive dashboard                              |

Binding rules:

- **No cross-database foreign keys.** IDs are carried as plain UUID columns.
- **Every projection row carries `source_updated_at` and `synced_at`.** The UI shows the
  older of the two as the freshness stamp. Honest staleness (F1.10) is a requirement.
- **Projections are idempotent.** Re-running the ETL must produce byte-identical rows;
  this is what makes the version-bump-on-change logic correct.

### O4.4 The tiling and versioning contract (extended)

The existing (X, Y, Time) tiling for train positions is proven. Part O generalises it so
**every dynamic map layer** participates in delta transfer.

```
tile_id  =  "{layer}:{z}:{x}:{y}:{tbucket}"

  layer    ∈ {trains, blocks, restrictions, worksites, conflicts}
  z        = tiling zoom band (fixed set: 8, 11, 14) — NOT the map zoom
  x, y     = tile indices at that band
  tbucket  = UTC epoch minutes floored to the layer's time granularity
             trains 15 min · blocks 60 min · restrictions 240 min ·
             worksites 15 min · conflicts 60 min
```

`data_tile` table (Read Store) gains `layer` and `signature`:

```
data_tile
  tile_id PK, layer, z, x, y, tbucket,
  version UUID,            -- new UUID whenever signature changes
  signature TEXT,          -- stable hash of the tile's serialised content
  entity_count INT, last_updated TIMESTAMPTZ
```

Rules that were learned the hard way and must not be re-broken:

1. **Time bucketing is UTC on both sides.** Frontend `roundToInterval` and backend
   `time_bucket` must produce identical values for identical instants. There is a shared
   test vector file for this (`db/readstore/testdata/tile_vectors.json`).
2. **An entity spanning multiple buckets is written to every bucket it spans.** A block
   from 22:00 to 02:00 appears in five 60-minute buckets. This was bug #2 of Phase 10a.
3. **Delta responses are grouped by tile, never a flat list.** A flat list caused the
   client to wipe unchanged tiles (bug #4). The response shape is:
   ```json
   {
     "tiles": { "trains:11:1042:701:29234100": { "version": "…", "entities": [ … ] } },
     "meta": { "businessClock": "…", "unchanged": ["trains:11:1042:702:29234100"] }
   }
   ```
4. **`unchanged` is explicit.** The client must be told "this tile is still valid", not
   left to infer it from absence.
5. **Version bump is content-derived, not time-derived.** If nothing changed, the version
   must not change, or delta transfer degenerates into full transfer.

### O4.5 Seed and synthetic network requirements

`db/network_gen.py` already generates a demo network. It must be extended to produce a
network rich enough to *exercise the map*, because a 6-node network hides every clarity
and density problem the map has.

| Property                     | Minimum for demo | Minimum for load test |
| ---------------------------- | ---------------- | --------------------- |
| Stations                     | 24               | 200                   |
| Track segments               | 300              | 4 000                 |
| Turnouts / crossovers        | 60 / 20          | 600 / 200             |
| Elementary sections          | 20               | 150                   |
| Trains in a 24 h window      | 150              | 1 500                 |
| Simultaneous live blocks     | 12               | 120                   |
| Active restrictions          | 25               | 300                   |
| Curved, organic geometry     | required         | required              |
| Multi-line sections (2–4)    | required         | required              |
| One cross-division boundary  | required         | required              |

The generator must also emit **deliberately awkward cases**, because these are what the
map has to survive:

- two blocks whose extents overlap partially on the same line;
- a block whose only crossover for SLW lies *inside* the worksite (makes SLW infeasible);
- a station where six trains are within 300 m of each other (label collision);
- a restriction 8 months past its review date (ageing visual);
- a segment with `confidence = ESTIMATED` (must render differently);
- a train with no position for 20 minutes (stale marker, not a hidden marker).

### O4.6 Indexing, performance and the PostGIS question

| Query                                          | Index                                              | Budget  |
| ---------------------------------------------- | -------------------------------------------------- | ------- |
| Segments in a viewport                         | `network_geometry(bbox_minx, bbox_miny, …)` btree   | < 30 ms |
| Blocks overlapping a window                    | `block_view` GiST on `tstzrange(start, end)`        | < 30 ms |
| Blocks on a segment                            | `block_extent_view(segment_id, start_at)`           | < 20 ms |
| Demands overlapping extent+window (conflicts)  | GIN on `segment_ids` + GiST on range                | < 50 ms |
| Tile fetch by ids                              | `data_tile(tile_id)` PK, batched `= ANY($1)`        | < 25 ms |
| Train positions in tiles                       | `train_position(tile_id, at)`                       | < 40 ms |

**PostGIS is not required for the MVP.** Segment geometry is GeoJSON in JSONB plus a
pre-computed bounding box in four numeric columns, which answers every viewport query we
have. PostGIS becomes worthwhile only when we need true spatial joins (e.g. "which
demands are within 500 m of this point"), and that is recorded as a future upgrade with a
clean migration path: add `geometry(LineString, 4326)`, backfill from JSONB, add GiST.

---

## O5. Contracts and events

### O5.1 Envelope (unchanged, restated for completeness of the catalogue)

Every event carries: `event_id`, `event_type`, `event_version`, `occurred_at`,
`correlation_id`, `causation_id`, `actor`, `payload`. Consumers **must** ignore unknown
payload fields (forward compatibility) and **must** be idempotent on `event_id`.

### O5.2 New topics

| Topic                     | Produced by      | Consumed by                          | Retention |
| ------------------------- | ---------------- | ------------------------------------ | --------- |
| `demand.events`           | Command          | ETL, Notification, (Optimiser later) | 7 d       |
| `block.execution.events`  | Command          | ETL, Notification, SSE fan-out       | 7 d       |
| `safety.events`           | Command          | ETL, Notification, Audit             | 90 d      |
| `resource.events`         | Command          | ETL, Notification                    | 7 d       |
| `restriction.events`      | Command          | ETL, Notification                    | 30 d      |
| `notification.commands`   | Command, ETL     | Notification worker                  | 3 d       |
| `map.invalidation`        | ETL              | Query Service (Redis pub/sub bridge) | 1 h       |
| `plan.commands`           | existing         | Optimiser (frozen)                   | 7 d       |
| `optimization.results`    | Optimiser        | ETL — **consumed but not produced by us** | 7 d  |

### O5.3 New event catalogue

| Event type                          | Emitted when                                   | Key payload                                  |
| ----------------------------------- | ---------------------------------------------- | -------------------------------------------- |
| `block.demand.drafted`              | draft saved                                    | demand_id, requester                         |
| `block.demand.submitted`            | submitted for scrutiny                         | full demand snapshot, computed facts         |
| `block.demand.amended`              | new version created                            | demand_id, version, diff                     |
| `block.demand.withdrawn`            | requester withdraws                            | reason                                       |
| `block.demand.validated`            | entry validation completed                     | V-rule outcomes                              |
| `block.demand.conflict_detected`    | conflict engine finds a conflict               | conflict list with types                     |
| `block.demand.approved` / `.rejected` | approval step completes                      | decider, justification                       |
| `block.scheduled`                   | block object created from demand(s)            | block_id, window, extent                     |
| `block.grant.requested`             | field/site requests the block on line          | block_id, requested_at                       |
| `block.granted`                     | controller grants                              | granted_at, delay_reason                     |
| `block.protection.item_confirmed`   | one checklist item confirmed                   | item, position, by, photo_ref                |
| `block.protected`                   | all required protection confirmed              | protected_at                                 |
| `block.isolation.requested/granted/earthed/restored` | power block progression      | elementary sections, TPC                     |
| `block.work.started`                | work start declared                            | started_at, party count                      |
| `block.worksite.moved`              | rolling front reported                         | chainage, lat/lon                            |
| `block.progress.reported`           | progress % update                              | percent, note                                |
| `block.extension.requested`         | extension asked from the field                 | requested_minutes, progress, reason          |
| `block.extension.decided`           | controller approves/refuses                    | decision, impact snapshot                    |
| `block.incident.reported`           | machine failure/injury/near-miss               | type, severity                               |
| `block.work.completed`              | work declared complete                         | quantum achieved                             |
| `block.handback.certified`          | certificate issued                             | certifier, fitness, restriction              |
| `block.line_clear.restored`         | controller restores traffic                    | at                                           |
| `block.closed`                      | post-block report complete                     | actuals                                      |
| `block.surrendered`                 | sanctioned block not used                      | reason → triggers reserve-queue notification |
| `restriction.imposed` / `.reviewed` / `.relaxed` | restriction register changes      | value, extent, review date                   |
| `resource.booked` / `.released` / `.conflicted` | booking lifecycle                   | resource, window                             |
| `readiness.gate.evaluated`          | T-24 h gate runs                               | pass/fail per criterion                      |
| `safety.competency.rejected`        | grant blocked by invalid competency            | person, competency, expiry                   |
| `disruption.declared` / `.cleared`  | mass disruption mode                           | scope, affected blocks                       |
| `map.tiles.invalidated`             | ETL bumped tile versions                       | tile ids + layer                             |

### O5.4 Transactional outbox (mandatory)

The current best-effort publish can lose events if Kafka is unavailable mid-request. That
is acceptable for a demo and unacceptable for a safety-adjacent record.

```
outbox_message
  id PK, topic, key, payload JSONB, headers JSONB,
  created_at, published_at NULL, attempts INT, last_error TEXT
  INDEX (published_at) WHERE published_at IS NULL
```

Flow: the service writes the domain rows **and** the outbox row in one transaction; a
relay task (async loop in the Command Service, or a small worker) polls unpublished rows,
publishes, and marks them. Consequences:

- A write either fully happens with its event, or not at all.
- Kafka downtime degrades to latency, not data loss.
- Replay is trivial: reset `published_at`.

### O5.5 Versioning discipline

- Additive payload fields → same `event_version`.
- Removing/retyping a field → new `event_version`, both emitted for one release cycle.
- JSON Schemas in `contracts/events/json_schemas/` are the contract; a CI test validates
  every emitted example against its schema.

---

## O6. Command Service — the write path

### O6.1 Responsibility boundary

The Command Service owns **every state change** in the operational database. It does not
read for display, does not compute rankings, and does not talk to the optimiser except by
publishing events the optimiser may later consume.

### O6.2 Endpoint catalogue

Demand intake:

| Method | Path                                        | Purpose                                   | Emits                        |
| ------ | ------------------------------------------- | ----------------------------------------- | ---------------------------- |
| POST   | `/demands`                                  | create draft                              | `block.demand.drafted`       |
| PATCH  | `/demands/{id}`                             | edit draft (autosave)                     | —                            |
| POST   | `/demands/{id}/validate`                    | run V-rules without submitting            | `block.demand.validated`     |
| POST   | `/demands/{id}/submit`                      | submit for scrutiny                       | `.submitted`, `.conflict_detected` |
| POST   | `/demands/{id}/amend`                       | create a new version of a submitted demand| `.amended`                   |
| POST   | `/demands/{id}/withdraw`                    | withdraw                                  | `.withdrawn`                 |
| POST   | `/demands/{id}/links`                       | add dependency/duplicate link             | —                            |
| POST   | `/demands/emergency`                        | 7-field emergency path (G15)              | `.submitted` (priority)      |
| POST   | `/demands/{id}/approvals/{step}/decide`     | approve/reject a step                     | `.approved` / `.rejected`    |
| POST   | `/demands/{id}/attachments`                 | upload evidence                           | —                            |

Execution (the live block console and the field app):

| Method | Path                                          | Purpose                                    |
| ------ | --------------------------------------------- | ------------------------------------------ |
| POST   | `/blocks/{id}/grant-request`                  | site asks for the block on line            |
| POST   | `/blocks/{id}/grant`                          | controller grants (reason code if late)    |
| POST   | `/blocks/{id}/protection/{itemId}/confirm`    | confirm one protection item                |
| POST   | `/blocks/{id}/isolation/request|grant|earth|restore` | power block progression             |
| POST   | `/blocks/{id}/disconnections`                 | record disconnection                       |
| POST   | `/blocks/{id}/disconnections/{id}/restore`    | record reconnection                        |
| POST   | `/blocks/{id}/work/start`                     | declare work started (gated)               |
| POST   | `/blocks/{id}/worksite`                       | report rolling front position              |
| POST   | `/blocks/{id}/progress`                       | progress %                                 |
| POST   | `/blocks/{id}/extension-requests`             | request extension (+ instant impact)       |
| POST   | `/blocks/{id}/extension-requests/{id}/decide` | approve/refuse                             |
| POST   | `/blocks/{id}/incidents`                      | incident/near-miss                         |
| POST   | `/blocks/{id}/work/complete`                  | work complete + quantum                    |
| POST   | `/blocks/{id}/handback`                       | certificate (certifier, fitness, TSR)      |
| POST   | `/blocks/{id}/line-clear`                     | controller restores traffic                |
| POST   | `/blocks/{id}/surrender`                      | block not used (reason)                    |
| POST   | `/blocks/{id}/close`                          | post-block report R.1–R.20                 |

Supporting:

| Method | Path                                  | Purpose                                     |
| ------ | ------------------------------------- | ------------------------------------------- |
| POST   | `/restrictions`                       | impose (usually auto from handback)         |
| POST   | `/restrictions/{id}/review`           | review outcome                              |
| POST   | `/restrictions/{id}/relax`            | relax                                       |
| POST   | `/resource-bookings`                  | book a machine/gang/person/material         |
| DELETE | `/resource-bookings/{id}`             | release                                     |
| POST   | `/readiness/{blockId}/evaluate`       | run the T-24 h gate on demand               |
| POST   | `/disruptions`                        | declare mass disruption (bulk re-plan)      |
| POST   | `/delegations`                        | time-bounded approval delegation            |

### O6.3 Request/response shape rules

- Request bodies mirror the Part G structure **section by section**, so the wizard can
  `PATCH` one section at a time without sending the whole document.
- Every response includes `computed` — the system's current answer (derived
  unavailability, conflicts, L1 impact, rule outcomes). The wizard renders this live
  (G14). This is the single highest-value feedback loop in the product.
- `409 Conflict` is reserved for **state machine violations** and carries the current
  state and the legal transitions. The UI uses this to disable the right buttons.

### O6.4 The validation engine (V-01 … V-24)

Implemented in `db/domain/rules_engine.py` + `command-service/app/domain/validation.py`
as **pure functions over a `DemandContext`**:

```python
@dataclass(frozen=True)
class DemandContext:
    demand: DemandData            # the submitted document
    network: NetworkSlice         # segments, turnouts, crossovers in/near the extent
    traction: TractionSlice
    calendars: CalendarSet        # embargo, peak, festival, statutory
    bookings: list[BookingData]   # existing resource bookings in the window
    competencies: list[CompetencyData]
    neighbours: list[DemandData]  # open demands overlapping in space or time
    history: DurationStats | None # from actuals; None when we have no history yet

def validate(ctx: DemandContext) -> list[Finding]: ...

@dataclass(frozen=True)
class Finding:
    rule_id: str        # "V-11"
    severity: Literal["BLOCK", "WARN", "INFO"]
    message: str        # already localised key + params
    field_path: str | None   # "protection.lookout" → the UI focuses this field
    citation: str       # the authority; never empty for BLOCK
    fix_hint: str | None
    data: dict          # what the UI needs to render the explanation
```

Mapping (every rule from G18 gets a home; none is dropped silently):

| Rule | Implementation note |
| ---- | ------------------- |
| V-01 | chainage within section extent — pure arithmetic on `NetworkSlice` |
| V-02 | line exists between stations — graph edge lookup |
| V-03 | notice period from block class config; produces WARN + `is_late` flag or BLOCK |
| V-04 | duration components sum — arithmetic |
| V-05 | `min_viable_min ≤ duration_total_min` |
| V-06 | competency validity on the block date — index lookup, expiry compared to `preferred_start` |
| V-07 | SLW requires a usable crossover **outside** the worksite — graph query |
| V-08 | earthing points must bound the worksite — traction graph query |
| V-09 | dependency acyclicity — recursive CTE + in-memory check |
| V-10 | embargo/peak calendar — interval intersection; override requires role + justification |
| V-11 | adjacent line OPEN without lookout/warning → BLOCK |
| V-12 | statutory due date before requested date |
| V-13 | machine double booking — the DB `EXCLUDE` constraint is the backstop; this is the friendly pre-check |
| V-14 | material unconfirmed → WARN now, BLOCK at the readiness gate |
| V-15 | near-duplicate demand — same asset/segment overlap + similar work type within ±30 d |
| V-16 | bundling candidate exists → WARN, must acknowledge. **Detection of overlap is deterministic and in scope; ranked bundling proposals are not (O25).** |
| V-17 | duration deviates >30 % from history — skipped with INFO when `history is None` |
| V-18 | adverse weather forecast for a weather-sensitive type |
| V-19 | placeholder text detection — regex list, configurable |
| V-20 | consecutive-night limit for the gang |
| V-21 | contractual notice period breach |
| V-22 | extent overlaps an approved block → WARN with "join this window" affordance |
| V-23 | cross-divisional extent without coordination flag → WARN then BLOCK at approval |
| V-24 | post-work restriction declared without extent/duration/review date |

Testing: each rule gets a **table-driven test** with at least one passing and one failing
fixture. This suite is the regression net for the whole write path.

### O6.5 Demand lifecycle and SLA clocks

The H1 lifecycle is expressed as **data**, not `if`-chains, in `db/domain/lifecycle.py`:

```python
DEMAND_TRANSITIONS: dict[Status, list[Transition]] = {
  Status.DRAFT:      [T(to=SUBMITTED, action="submit", guards=["no_blocking_findings"],
                        roles=["REQUESTER"])],
  Status.SUBMITTED:  [T(to=UNDER_SCRUTINY, action="accept", roles=["PLANNER"]),
                      T(to=RETURNED, action="return", roles=["PLANNER"],
                        requires=["reason"])],
  ...
}
```

Benefits: the same table drives (a) the API guard, (b) the UI's enabled buttons via
`GET /demands/{id}/transitions`, (c) the generated state diagram in the docs, (d) tests.

SLA clocks are rows, not cron logic: each stage entry writes `sla_due_at`; a periodic
sweeper emits `sla.breached` and creates the escalation approval step. Pausing rules
(e.g. clock stops while returned to the requester) are configuration.

### O6.6 Execution state machine and the hard gates

The H2 gates are implemented as **guard functions that cannot be bypassed by any role**:

```python
def guard_work_start(block: Block) -> None:
    if block.traffic_state != TrafficState.GRANTED:
        raise Gate("H-G1", "Traffic block is not granted")
    if not all_required_protection_confirmed(block):
        raise Gate("H-G2", "Protection checklist incomplete")
    if block.requires_power and block.power_state != PowerState.EARTHED:
        raise Gate("H-G3", "OHE is not confirmed earthed")   # S-38
    if not competency_valid(block.nominated_person_id, block.work_class, now()):
        raise Gate("H-G4", "Nominated person competency invalid/expired")  # S-41
```

and:

```python
def guard_handback(block) -> None:
    if open_disconnections(block):                      # S-40
        raise Gate("H-G5", "Disconnections not restored")
    if not certifier_competent(block):                  # S-33
        raise Gate("H-G6", "Certifier competency invalid")
```

> There is **no override role** for H-G1…H-G6. An override facility on these gates would
> convert the system from an aid into a hazard. If an exceptional situation arises, the
> answer is the documented manual procedure, recorded afterwards — not a button.

### O6.7 Protection, disconnection and isolation registers

- Protection items are **generated from the work type + block class template** when the
  block is created, so the field user sees a pre-built checklist, not a blank form.
- Each confirmation captures `confirmed_at`, `confirmed_by`, optional photo, and
  (if available) device GPS. Offline confirmations are queued with their **original**
  timestamp and marked `recorded_late = true` on sync — never silently back-dated.
- Disconnections enforce pairing at the database level with a partial unique index and at
  the API level with the hand-back gate.
- Isolation progression is strictly ordered: `REQUESTED → GRANTED → EARTHED → …`; skipping
  a step is a `409` with the expected next step named.

### O6.8 Hand-back and the restriction register

`POST /blocks/{id}/handback` with `fitness = FIT_WITH_RESTRICTION` **must** carry a
restriction sub-document (value, extent, direction, expected relaxation, review date,
owner). The service creates the `restriction` row in the same transaction and emits
`restriction.imposed`. This closes S-34 by construction: it is impossible to impose a
restriction without a review date.

A daily sweeper flags restrictions past `review_due_on`, emits notifications to the owner,
and drives the ageing dashboard and the map's restriction styling (O15.13).

### O6.9 Post-block actuals

`POST /blocks/{id}/close` accepts R.1–R.20. Rules:

- `quantum_achieved` and `percent_complete` are mandatory.
- If `percent_complete < 100`, a **balance demand is auto-created as a draft**, pre-filled
  from the parent, and linked with `BALANCE_OF` (S-32). The user only confirms it.
- Blocks not closed within 48 h escalate to the department officer.
- The record feeds `DurationStats` — which is *stored* now and *used by the optimiser
  later*. Storing it is in scope; learning from it is not (O25).

### O6.10 Resource booking and the readiness gate

Booking is a first-class endpoint with the DB exclusion constraint as the backstop. The
readiness gate is a scheduled evaluation at **T-24 h** (configurable per class) producing
a structured result:

| Criterion              | Source                                | Failure effect                |
| ---------------------- | ------------------------------------- | ----------------------------- |
| Resources confirmed    | `resource_booking.status = CONFIRMED`  | BLOCK (block goes AT_RISK)    |
| Material at site       | explicit confirmation                  | BLOCK                         |
| Competency valid       | competency register                    | BLOCK                         |
| Weather acceptable     | forecast feed (or manual override)     | WARN                          |
| Acknowledgements       | notification acknowledgement state     | WARN → escalate               |
| Machine reachable      | mobilisation time vs current location  | WARN                          |

A failed gate does not cancel the block; it marks it `AT_RISK`, notifies the owner and
the controller, and surfaces it on the map and console with a distinct visual. Cancelling
remains a human decision.

---

## O7. The rules engine

### O7.1 Why it is a separate component

Safety learning must become enforceable without a software release (S-44), and every
enforced constraint must cite its authority (C4.5). That means rules are **data**.

### O7.2 Rule representation

```json
{
  "code": "H-11",
  "family": "SAFETY",
  "severity": "HARD",
  "citation": "Enquiry recommendation 2024/17, para 6.3",
  "scope": { "work_categories": ["OHE_STRUCTURES"], "divisions": ["*"] },
  "expression": {
    "all": [
      { "field": "traction.power_block_required", "op": "eq", "value": true },
      { "field": "adjacent_line_status", "op": "in", "value": ["OPEN"] }
    ]
  },
  "outcome": "BLOCK",
  "message_template": "OHE structure work with the adjacent line open requires {required}",
  "effective_from": "2026-04-01"
}
```

- **Expressions are a small, safe, whitelisted DSL** — `all`, `any`, `not`, and leaf
  predicates over declared field paths. **No `eval`, no arbitrary code.** This is both a
  security requirement (OWASP A03 injection) and an auditability requirement.
- Field paths are validated against a published schema at rule-save time, so a typo fails
  at authoring, not at 03:00 during a block.

### O7.3 Evaluation and observability

- The evaluator is pure and returns `Finding`s identical in shape to the V-rules, so the
  UI has one rendering path for all constraint feedback.
- Every evaluation writes a `rule_firing` row. This gives us "which rules actually fire,
  how often, and how often are they overridden" — the input to periodic rule review, and
  the answer to "show me all rules derived from enquiry X" (S-44).
- Rules with `HARD` severity require a recorded safety approval before activation; the API
  refuses to activate an unapproved hard rule.

---

## O8. Topology expansion — the derived unavailability engine

### O8.1 Placement

`db/domain/topology.py`. Pure, deterministic, no I/O. Called by the Command Service (to
populate `computed` on a demand), by the Query Service (to answer map queries), and by the
ETL (to build `derived_unavail_view`).

> **This is not optimisation.** It is graph reachability. It is in scope.

### O8.2 Interface

```python
def expand(blocked: set[SegmentId],
           window: TimeWindow,
           graph: NetworkGraph,
           traction: TractionGraph,
           signalling: SignallingIndex) -> Unavailability: ...

@dataclass(frozen=True)
class UnavailabilityItem:
    segment_id: SegmentId
    effect: Literal["BLOCKED", "STRANDED", "ROUTE_LIMITED",
                    "ELECTRICALLY_DEAD", "DEGRADED_SIGNALLING", "CAPACITY_REDUCED"]
    reason_code: str          # "ONLY_ACCESS_VIA_BLOCK", "TURNOUT_INSIDE_WORKSITE", …
    explanation: str          # human sentence for the map tooltip
    evidence: list[str]       # node/turnout ids that produced this conclusion
    confidence: Literal["VERIFIED", "IMPORTED", "ESTIMATED"]
```

The `evidence` and `confidence` fields are not decoration: the map must be able to answer
"*why* is this segment shaded?" and "*how sure* are you?" in one hover (H9, R1).

### O8.3 Algorithm implementation notes

Following H3's eleven steps, with the practical details that matter:

1. **Direct** — trivial.
2. **Stranded** — build the graph with blocked edges removed, then check reachability from
   the set of *operational entry points* of the affected sections. `networkx` connected
   components on the residual graph; anything in a component with no entry point is
   stranded. Cache the graph per `(section, version)`; it changes rarely.
3. **Turnout loss** — a turnout physically inside a blocked segment cannot be operated;
   mark every route requiring it withdrawn. Routes are precomputed per interlocking.
4. **Crossover loss for SLW** — the key check: for SLW between A and B, there must be a
   usable crossover at or beyond each end, *outside* the blocked extent. If not, SLW is
   infeasible and the section is COMPLETELY blocked. This single check prevents a very
   expensive class of day-of surprise (S-13).
5. **Platform / siding loss** — reachability from the platform/siding node.
6. **LC effects** — geometric containment by chainage.
7. **Traction** — map blocked segments to elementary sections; compute the minimal set
   whose isolation covers the worksite plus statutory clearance; mark all segments under
   those sections electrically dead.
8. **Signalling** — disconnected elements → affected routes → degraded working method.
9. **Capacity** — select the `CapacityProfile` per remaining segment for the window.
10. **Neighbours** — repeat across a divisional boundary; flag coordination.

Performance: the whole expansion for a typical extent must complete in **< 150 ms** so the
demand wizard can call it on every meaningful edit. Achieved by (a) slicing the graph to
the affected section plus one hop, (b) caching the section subgraph, (c) precomputing
routes and elementary-section coverage.

### O8.4 Honesty requirements

- If any input segment has `confidence != VERIFIED`, every derived conclusion inherits the
  lowest confidence in its evidence chain, and the UI must render it as provisional.
- If the graph is disconnected because of *missing data* rather than the block, the engine
  must say `DATA_INCOMPLETE` rather than `STRANDED`. Silently converting a data gap into
  an operational conclusion is exactly the failure mode R1 warns about.

---

## O9. Conflicts and impact — what is in scope now

### O9.1 Conflict detection (deterministic, in scope)

`db/domain/conflicts.py`:

```python
def detect(subject: DemandOrBlock,
           others: Iterable[DemandOrBlock],
           bookings: Iterable[BookingData],
           graph: NetworkGraph,
           calendars: CalendarSet) -> list[Conflict]
```

Conflict types, each with a distinct visual on the map (O15.11):

| Type                  | Test                                                                 |
| --------------------- | -------------------------------------------------------------------- |
| `SPATIO_TEMPORAL`     | segment sets intersect **and** time ranges intersect                 |
| `ADJACENCY`           | extents are on adjacent lines with incompatible adjacent-line status |
| `DERIVED`             | one demand's derived unavailability set hits another's extent        |
| `RESOURCE`            | same resource, overlapping windows                                   |
| `DEPENDENCY`          | ordering link violated by the proposed dates                         |
| `CALENDAR`            | window intersects an embargo/peak/statutory constraint               |
| `CAPACITY`            | offered traffic exceeds the capacity profile for the configuration   |
| `CROSS_DIVISION`      | corridor-level clash across a boundary                               |

Every conflict carries `severity`, `explanation`, `evidence`, and `suggested_actions`
(e.g. "shift 90 min later", "join block B-1042"). **Suggestions here are simple,
rule-derived hints — not search results.** Ranked alternatives are the optimiser's job.

### O9.2 Impact — Level 1 only (in scope)

`db/domain/impact_l1.py` computes, using the timetable and the capacity profile:

- **Affected trains**: paths whose (segment, time) footprint intersects the block.
- **Detention minutes**: for each affected train, `max(0, earliest_feasible_pass - booked_pass)`
  under the applicable configuration (complete block → hold until hand-back; SLW → queue
  through reduced capacity using a simple deterministic server model).
- **Cancellations / diversions**: rule-based (a train held beyond `X` minutes with no path
  is proposed for cancellation; a train with an alternative route is proposed for
  diversion, validated against the block picture on that route — S-47).
- **Freight tonnage delayed** and **indicative cost** via the configurable cost model.

Every figure is returned with its **assumptions** attached:

```json
{ "value": 342, "unit": "train_minutes", "method": "L1_DETERMINISTIC",
  "assumptions": ["capacity profile SLW_2TPH", "no propagation beyond section",
                  "timetable snapshot 2026-09-10T18:00Z"],
  "confidence": "MEDIUM" }
```

This is what makes the number defensible on the approval screen, and it is what stops a
planner from over-trusting it.

### O9.3 Impact Levels 2 and 3 (deferred, interface reserved)

- **L2 (propagation via rake/crew links)** and **L3 (microscopic simulation)** are out of
  scope for this work.
- The response schema already carries `method` and `confidence`, so upgrading L1 → L2
  changes a value and a label, not a contract.

### O9.4 Explainability shell (in scope) vs ranked options (deferred)

We build the **rendering and data contract** for explanations now:

```json
{ "subject": "demand:BD-2026-004821",
  "binding_constraints": [ { "rule": "H-07", "text": "Peak window 07:00–11:00" } ],
  "facts": [ { "label": "Affected trains", "value": 14, "drill": "…" } ],
  "alternatives_considered": [],           // ← always empty until the optimiser exists
  "what_would_change_it": [ "Start after 11:00", "Reduce extent to 412/1–412/4" ] }
```

The UI renders `alternatives_considered` as an explicit "no ranked alternatives available
— optimiser not enabled" state rather than hiding the panel. When the optimiser arrives,
the panel fills in with no frontend change.

---

## O10. Query Service — the read path

### O10.1 Principles

1. **Never touch the operational database.** Read Store only.
2. **One endpoint per screen need**, not per table. A screen that needs five joins gets
   one endpoint returning one shaped payload. Chatty frontends are the main cause of a
   sluggish map.
3. **Cache-aside with a single key registry.** All keys and TTLs live in
   `cache_keys.py`; nothing constructs a key inline.
4. **Every response carries freshness.** `meta.dataAsOf`, `meta.businessClock`,
   `meta.degraded[]`.

### O10.2 Endpoint catalogue (new)

Map and situational:

| Method | Path                          | Returns                                                        | TTL   |
| ------ | ----------------------------- | -------------------------------------------------------------- | ----- |
| GET    | `/basegraph`                  | nodes + segments + schematic geometry (existing, extended)     | 1 h   |
| GET    | `/basegraph/version`          | cheap etag probe so clients avoid re-downloading               | 60 s  |
| POST   | `/map/tiles`                  | multi-layer delta transfer (trains, blocks, restrictions, worksites, conflicts) | 5 s |
| GET    | `/map/snapshot?at=…&bbox=…`   | one-shot full picture at an instant (used for print/degraded)  | 30 s  |
| GET    | `/map/inspect/segment/{id}?at=…` | everything true about one segment at one instant             | 15 s  |
| GET    | `/map/inspect/block/{id}`     | full block dossier for the inspector panel                     | 10 s  |
| GET    | `/map/inspect/train/{id}?at=…`| train dossier: delay, next stops, blocks ahead, restrictions   | 5 s   |
| GET    | `/traingraph?section=…&from=…&to=…` | time–distance series for the mini graph                  | 30 s  |
| GET    | `/legend?layers=…`            | server-driven legend so colours never drift from data          | 1 h   |

Domain reads:

| Method | Path                                  | Notes                                      |
| ------ | ------------------------------------- | ------------------------------------------ |
| GET    | `/demands`                            | filters: status, dept, class, date, section, criticality |
| GET    | `/demands/{id}`                       | full document + `computed` + timeline      |
| GET    | `/demands/{id}/timeline`              | lifecycle events with actors               |
| GET    | `/blocks`                             | existing, extended with execution state    |
| GET    | `/blocks/{id}`                        | dossier incl. work packages and protection |
| GET    | `/conflicts`                          | conflict inbox                             |
| GET    | `/restrictions`                       | + `?overdue=true` for the ageing view      |
| GET    | `/resources/timeline`                 | machine/gang itinerary (S-62 visibility)   |
| GET    | `/readiness?date=…`                   | readiness board for the next 48 h          |
| GET    | `/handover-pack?shift=…&section=…`    | auto-generated shift handover (S-82)       |
| GET    | `/kpis?scope=…&period=…`              | dashboard series                           |
| GET    | `/scorecards?dept=…`                  | claimed-vs-actual (S-92)                   |
| GET    | `/audit?entity=…&at=…`                | reconstruction view                        |

### O10.3 Cache key registry (shape)

```python
KEYS = {
  "basegraph":        ("bg:v{ver}",                       3600),
  "map_tiles":        ("mt:{layer}:{tile_id}",               5),
  "map_snapshot":     ("ms:{bbox_hash}:{at_bucket}",        30),
  "inspect_segment":  ("is:{segment_id}:{at_bucket}",       15),
  "traingraph":       ("tg:{section}:{from}:{to}",          30),
  "demand_list":      ("dl:{filter_hash}:{page}",           15),
  "kpi":              ("kpi:{scope}:{period}",             300),
}
```

Invalidation: the ETL publishes `map.invalidation` → a small bridge in the Query Service
subscribes and deletes affected keys. **Never** rely solely on TTL for safety-relevant
data such as block state; TTL is the backstop, invalidation is the mechanism.

### O10.4 Degradation behaviour

| Failure              | Behaviour                                                          |
| -------------------- | ------------------------------------------------------------------ |
| Redis down           | serve from Read Store, set `meta.degraded += ["cache"]`, log once   |
| Read Store lagging   | serve, set `meta.dataAsOf` honestly; UI shows amber freshness       |
| Read Store down      | `503` with `Retry-After`; the frontend falls back to its IndexedDB snapshot and marks the whole map STALE |
| Tile missing         | return the tile as `null` with `reason: "NOT_BUILT"` — never an empty success, which the client would read as "nothing there" |

That last row matters: **absence of data and emptiness of data must never look the same**
on a safety-adjacent map.

---

## O11. API Gateway

### O11.1 What it gains

1. **Real authentication** replacing the stub: JWT (RS256) verification, `sub`, `roles`,
   `scopes`, `division`, `department` claims extracted into a request context and
   forwarded as signed internal headers.
2. **Authorisation at the edge for coarse checks** (is this role allowed to call this
   path at all); fine-grained checks stay in the services where the data lives.
3. **Rate limiting** per identity via a Redis token bucket, with generous limits for
   read endpoints and strict limits for write and auth endpoints.
4. **SSE passthrough** with buffering disabled and correct headers.
5. **Request/response size limits** and a strict CORS allow-list from config (the
   permissive dev CORS must not reach any shared environment).
6. **Correlation ID** (already present) plus `X-Request-Start` for latency attribution.

### O11.2 Security checklist (OWASP-aligned, binding)

| Risk                      | Control                                                                 |
| ------------------------- | ----------------------------------------------------------------------- |
| Broken access control     | Deny-by-default route table; every route declares required scopes        |
| Injection                 | Parameterised SQL only; rule DSL is whitelisted, never `eval`            |
| Insecure design           | Safety gates are non-overridable (O6.6); no auto-approval anywhere       |
| Security misconfiguration | CORS/hosts/secrets from env; no defaults that are safe only in dev       |
| Vulnerable components     | Pinned versions; dependency audit in CI                                  |
| Auth failures             | Short-lived access tokens, refresh rotation, lockout on repeated failure |
| Data integrity            | Outbox + append-only audit; signed internal headers between services     |
| Logging failures          | Structured logs with correlation id; **never log tokens or PII payloads**|
| SSRF                      | The gateway proxies only to a fixed, configured upstream list            |
| File upload               | Type/size validation, virus scan hook, stored outside the web root, served via signed URLs |

---

## O12. ETL / projection pipeline

### O12.1 From full-refresh to incremental

The current polling ETL does a full refresh. That is fine at demo scale and quadratically
wrong at network scale. Target design, still without Debezium:

1. **Watermark per source table** (`max(updated_at)` seen), stored in a `etl_watermark`
   table.
2. Each cycle: select rows changed since the watermark, transform, upsert into the
   projection, recompute the affected tiles' signatures, bump versions where the signature
   changed, publish `map.invalidation` for those tiles.
3. **Ordering**: network → traction → demands → blocks → worksites → restrictions →
   conflicts → tiles → KPIs. A projection never reads another projection built later in
   the same cycle.
4. **Idempotent**: re-running a cycle produces identical output.
5. **Cycle budget**: 2 s at demo scale, 10 s at load-test scale. If a cycle exceeds its
   budget three times in a row, the ETL emits a degradation event that the UI surfaces as
   an amber freshness state rather than silently lagging.

### O12.2 Event-driven nudge

The ETL additionally consumes `block.execution.events` and `safety.events` so that a
grant, a hand-back or an earthing confirmation is projected within **≤ 1 s** rather than
waiting for the next poll. Execution state is the one place where polling latency is
operationally visible.

### O12.3 Backfill and rebuild

A `--rebuild [projection]` mode drops and rebuilds a single projection from scratch. This
is the recovery procedure when a projection bug is found, and it is exercised in testing —
an unrehearsed rebuild is not a recovery plan.

---

## O13. Real-time transport

Three tiers, adopted in order, with a shared client abstraction so screens do not care
which is active:

| Tier | Mechanism                              | Used for                                        | Latency |
| ---- | -------------------------------------- | ----------------------------------------------- | ------- |
| 1    | TanStack Query polling (existing)      | lists, dashboards, map tiles                    | 2–15 s  |
| 2    | **SSE** `GET /stream?topics=…&scope=…` | live block console, field app state, map deltas | < 1 s   |
| 3    | WebSocket (future)                     | bidirectional needs (collaborative planning)    | < 1 s   |

SSE implementation:

- Query Service exposes `/stream`; the ETL/Command publish to Redis pub/sub channels; the
  stream endpoint subscribes per client scope and forwards.
- Event shape mirrors the Kafka envelope so the client has one decoder.
- The client auto-reconnects with `Last-Event-ID`, and on reconnect **performs a full
  re-sync of the affected scope** rather than assuming continuity.
- **The map keeps polling as a safety net even when SSE is connected**, at a reduced rate
  (every 30 s). A silent dead stream must not present a frozen picture as a live one — the
  freshness indicator is driven by the *last successful data timestamp*, not by the socket
  state.

---

## O14. Frontend implementation

### O14.1 Route map (additions to `frontend-plan.md` §3)

```
/situation                    ← new landing: map + live blocks + alerts + handover
/demands                      list, filters, saved views
/demands/new                  map-first wizard (O14.4)
/demands/[id]                 document + computed panel + timeline + decision record
/planning                     planning board (calendar + conflicts + readiness)
/console                      live block console (controller)
/console/[blockId]            single block execution view
/restrictions                 register + ageing
/resources                    machine/gang timelines
/network/[segmentId]          section dossier (survives transfers, S-87)
/analytics                    KPIs, scorecards, backlog
/field                        field PWA shell (separate, minimal chrome)
/field/blocks/[id]            the safety screen (O16)
/infrastructure/map           the dynamic map (O15)
```

### O14.2 State ownership matrix

| State                         | Owner                | Persisted           |
| ----------------------------- | -------------------- | ------------------- |
| Server data (all)             | TanStack Query       | memory + IndexedDB for the base graph |
| Map viewport                  | `map.store`          | localStorage        |
| Layer visibility + filters    | `filter.store`       | localStorage + URL  |
| Time offset / playback        | `time.store`, `playback.store` | localStorage (offset only) |
| Tile versions                 | `tile.store`         | session only        |
| Inspector selection + history  | `inspector.store`    | session             |
| Wizard draft                  | server draft + RHF   | server (autosave)   |
| Field queue (offline)         | Dexie                | IndexedDB           |

**URL is state.** Viewport, time offset, layer filters and selection are reflected in the
query string so a controller can paste a link into a message and the recipient sees
*exactly* the same picture. This one decision removes an entire class of miscommunication.

### O14.3 Data hooks

One hook per resource, colocated types, all returning `{data, isLoading, isError, meta}`:

```
use-demands.ts          use-demand.ts           use-demand-transitions.ts
use-blocks.ts           use-block.ts            use-block-stream.ts
use-map-tiles.ts        use-base-graph.ts       use-map-inspect.ts
use-train-graph.ts      use-conflicts.ts        use-restrictions.ts
use-resources.ts        use-readiness.ts        use-handover-pack.ts
use-kpis.ts             use-scorecards.ts       use-legend.ts
```

Conventions: `staleTime` matches the server TTL; `refetchInterval` only where the data is
genuinely live; `placeholderData: keepPreviousData` everywhere a filter changes, so the
map and tables never blank out.

### O14.4 The map-first demand wizard

Six-field open (G17), then progressive disclosure. Implementation notes:

1. Step 1 is **the map**: the user draws the extent (O15.15). Chainage, line, segments,
   division, LCs, structures and the derived unavailability are all computed and shown.
2. The `computed` panel is **always visible on the right**, updating on every debounce
   (400 ms). It shows: what else dies, who conflicts, affected trains, detention estimate,
   rule findings. This is the single most important adoption feature — the requester sees
   the consequence of their own ask before submitting.
3. Conditional sections mount/unmount from a declarative config derived from G17, not from
   nested JSX conditionals.
4. Autosave to a server draft every 5 s and on blur; the wizard is resumable across
   devices.
5. Blocking findings disable submit and **focus the offending field** on click.

### O14.5 The planning board

Calendar/Gantt of demands and blocks with a conflict rail underneath, a readiness column
and drag-to-reschedule that immediately re-runs conflict detection and L1 impact.
Explicitly **no ranked suggestions** — the "Suggested plans" panel exists but renders the
"optimiser not enabled" state (O9.4).

### O14.6 The live block console

Three panes: map (scoped to the section), block list ordered by urgency, and the selected
block's execution timeline with the action buttons the controller's role permits.
Extension requests arrive as a modal with the L1 impact pre-computed and a countdown.
Every action requires one confirmation and records a reason where the model demands it.

### O14.7 Accessibility, language and field ergonomics

- All interactive elements keyboard reachable; the map has a keyboard mode (O15.19).
- `next-intl` with English + Hindi + one regional language in the first release; safety
  strings are translated first and reviewed by a native speaker.
- Minimum 44 px touch targets on field screens; a high-contrast "sunlight" theme toggle.
- Colour + icon + text for every state; verified against deuteranopia simulation.

### O14.8 Performance budget (frontend)

| Screen              | First contentful paint | Interaction latency | Bundle (route) |
| ------------------- | ---------------------- | ------------------- | -------------- |
| Situation           | < 1.5 s                | < 100 ms            | < 250 kB       |
| Map                 | < 2.5 s                | < 16 ms per frame   | < 350 kB       |
| Demand wizard       | < 1.5 s                | < 100 ms            | < 220 kB       |
| Field block screen  | < 1.0 s (cached)       | < 100 ms            | < 120 kB       |

### O14.9 Component additions

`components/inspector/*` (progressive detail panel), `components/timeline/*` (time slider,
playback, train graph), `components/explain/*` (constraint findings, evidence chips),
`components/safety/*` (state pills for traffic/power/adjacent line, used identically on
console, map and field app — one component, one truth).

---

## O15. The Dynamic Map — implementation

> This is the largest chapter in Part O, deliberately. The map is how a controller,
> a planner and a DRM each understand the same railway at the same moment. Part K defined
> the *grammar*. `MAP_VISUALIZATION_ARCHITECTURE.md` defined the *transport* (tiling).
> This chapter defines the **behaviour, legibility and code**.

### O15.0 The two requirements this chapter must satisfy

**Requirement 1 — the map must be much more dynamic.**
It must feel like a living instrument, not a picture that occasionally refreshes.
Concretely, "dynamic" is decomposed into twelve measurable behaviours (O15.1).

**Requirement 2 — the information on the map must be much clearer.**
More data must not mean more noise. Clarity is decomposed into a doctrine (O15.2), a
level-of-detail contract (O15.3), a token system (O15.4) and a label engine (O15.5).

These two requirements pull against each other. Everything in this chapter is the
negotiated settlement between them.

### O15.1 What "dynamic" means, concretely

| #   | Behaviour                        | Definition of done                                                                                   |
| --- | -------------------------------- | ----------------------------------------------------------------------------------------------------- |
| D1  | **Continuous motion**            | Trains move smoothly between position updates by interpolation at 60 fps — never teleport every 2 s.  |
| D2  | **Live state, not stale paint**  | A grant, an earthing, a hand-back changes the map within 1 s (SSE) with an animated state transition. |
| D3  | **Time travel**                  | Scrubbing the time slider re-renders the entire map at that instant, past or future, in < 200 ms.     |
| D4  | **Playback**                     | Play/pause/×1/×5/×20/×60 animates the picture through a window; scrub-while-playing is supported.     |
| D5  | **Viewport-reactive detail**     | Zoom and pan change *what is shown*, not just its size — a declared LOD contract (O15.3).             |
| D6  | **Progressive inspection**       | Hover → 3 facts; click → 12 facts; expand → full dossier. No modal wall.                              |
| D7  | **Direct manipulation**          | Extents can be drawn, dragged and trimmed on the map, with live recomputation of consequences.        |
| D8  | **Reactive consequence**         | Changing anything (time, extent, filter) immediately restyles everything it affects — no "Apply".     |
| D9  | **Focus and dimming**            | Selecting an entity dims unrelated data instead of hiding it; context is never lost.                  |
| D10 | **Honest liveness**              | Every element carries an age; stale data visibly decays rather than lying.                            |
| D11 | **Linked views**                 | Map ↔ train graph ↔ block list ↔ timeline all highlight the same entity simultaneously.               |
| D12 | **Smooth under load**            | 1 500 trains, 120 blocks, 300 restrictions: pan/zoom stays ≥ 50 fps.                                  |

### O15.2 The clarity doctrine

Seven rules. They are enforced in review; a PR that breaks one is rejected.

1. **Answer the four questions first.** At any moment, without clicking, the map must
   answer: *Where is track unavailable? Which trains are affected? What is unsafe or
   unknown? What is about to change?* Everything else is secondary and may be hidden.
2. **One meaning per visual channel.**
   - **Hue** = domain state (block, restriction, conflict, train).
   - **Saturation/opacity** = certainty and recency.
   - **Pattern (dash/hatch)** = provisional vs actual.
   - **Stroke width** = importance/priority class.
   - **Motion** = live change only.
   Nothing else may be encoded. Two meanings on one channel is how maps become unreadable.
3. **Never more than five simultaneous colour meanings in the viewport.** If a sixth is
   needed, something must collapse into a summary badge.
4. **Label budget.** At most 40 text labels on screen at once, priority-ranked (O15.5).
   Above that, labels collapse into counts.
5. **Nothing important is hover-only.** Hover reveals *detail*; it never reveals
   *existence*. A safety-relevant fact is always visible without interaction.
6. **Unknown is a state, and it is loud.** Grey-with-question-hatch, never "clean".
7. **Every colour on the map is explained by the legend, and the legend is generated from
   the same tokens the renderer uses** (`GET /legend`). Legend drift is a documented
   failure mode; this makes it structurally impossible.

### O15.3 Level-of-detail contract

`lib/map/lod.ts` exports a single table. Layers read from it; no component invents its own
zoom thresholds.

| Zoom  | Scale sense       | Base network                        | Blocks                          | Trains                                   | Restrictions              | Labels                        |
| ----- | ----------------- | ----------------------------------- | ------------------------------- | ---------------------------------------- | ------------------------- | ----------------------------- |
| 4–7   | Zone / corridor   | corridors as single lines           | aggregated count badge per section | aggregated count per section          | count badge               | division names only           |
| 8–10  | Division          | sections, major junctions           | one bar per block, no extent detail | clustered (radius 60 px)              | one marker per group      | station codes, major only     |
| 11–12 | Section           | individual lines, stations          | true extent, state colour       | clustered (radius 45 px) + individuals   | true extent               | all stations, block refs      |
| 13–14 | Station area      | + loops, platforms, crossovers      | + work packages, worksite front | individual, with direction chevrons      | + value labels            | + train numbers               |
| 15–17 | Yard / worksite   | + turnouts, signals, LCs, structures| + protection markers, isolation | + speed/delay chips                      | + extent handles          | + chainage ticks, asset names |
| 18+   | Engineering       | + chainage every 100 m, asset ids   | + per-item protection status    | + exact chainage                         | + review dates            | full detail                   |

Rules:

- **A layer must not simply "get bigger".** Each zoom band adds *information*, not size.
- **Transitions are cross-faded over 150 ms**, never hard-switched, so the eye keeps
  continuity.
- **The count badge is clickable** at every aggregated level and zooms to fit the group.

### O15.4 Semantic token system

`lib/map/tokens.ts` is the single source of truth, imported by the renderer, the legend
endpoint fixture, the inspector and the field app.

| Token                      | Meaning                              | Light      | Dark       | Pattern        | Icon        |
| -------------------------- | ------------------------------------ | ---------- | ---------- | -------------- | ----------- |
| `track.available`          | normal, usable                       | slate-400  | slate-500  | solid          | —           |
| `track.unverified`         | topology confidence ≠ VERIFIED       | slate-400  | slate-500  | fine dot       | `?`         |
| `block.proposed`           | demand, not approved                 | violet-400 | violet-400 | dashed         | `pencil`    |
| `block.approved`           | sanctioned, not yet live             | amber-500  | amber-400  | solid, hollow  | `calendar`  |
| `block.live`               | granted and in force                 | amber-600  | amber-500  | solid, glowing | `shield`    |
| `block.overrun`            | past sanctioned end                  | red-600    | red-500    | solid + pulse  | `alert`     |
| `block.at_risk`            | readiness gate failed                | amber-600  | amber-500  | dashed + `!`   | `alert`     |
| `block.handed_back`        | complete, awaiting close             | emerald-600| emerald-500| solid, thin    | `check`     |
| `unavailable.derived`      | consequence of another block         | amber-300  | amber-700  | diagonal hatch | `link`      |
| `power.isolated`           | OHE dead                             | sky-600    | sky-400    | double line    | `zap-off`   |
| `power.earthed`            | dead **and** earthed                 | sky-700    | sky-300    | double + tick  | `zap-off`   |
| `power.live_adjacent`      | live OHE next to a worksite          | red-600    | red-500    | double + bolt  | `zap`       |
| `restriction.speed`        | TSR/PSR in force                     | orange-500 | orange-400 | dash-dot       | `gauge`     |
| `restriction.overdue`      | past review date                     | orange-700 | orange-300 | dash-dot + `!` | `clock`     |
| `conflict.hard`            | infeasible clash                     | red-600    | red-500    | zigzag         | `x-octagon` |
| `conflict.soft`            | penalised clash                      | yellow-600 | yellow-400 | zigzag thin    | `alert`     |
| `train.ontime`             | ≤ 5 min late                         | emerald-600| emerald-400| —              | chevron     |
| `train.delayed`            | 6–30 min                             | amber-600  | amber-400  | —              | chevron     |
| `train.severely_delayed`   | > 30 min                             | red-600    | red-400    | —              | chevron     |
| `train.stale`              | no position for > 3 min              | slate-400  | slate-500  | 50 % opacity   | `wifi-off`  |
| `train.projected`          | future/estimated position            | current hue| current hue| hollow outline | `dashed`    |
| `state.unknown`            | any unknown safety fact              | zinc-500   | zinc-400   | question hatch | `help`      |

**Binding rule:** no hex value appears anywhere in a component. Every colour reference is
a token. This is what allows the theme, the sunlight mode and the colour-blind mode to be
real rather than aspirational.

### O15.5 The label engine

Uncontrolled labels are the fastest way to ruin a dense railway map. Maplibre's collision
detection is used, but it is not sufficient alone because it does not know what *matters*.

`lib/map/labels.ts`:

```ts
type LabelPriority =
  | 'safety'      // 100  live block, unknown state, overrun, live OHE adjacency
  | 'selection'   //  90  the currently selected/hovered entity and its relations
  | 'conflict'    //  80  conflicts in view
  | 'operational' //  60  train numbers, block references
  | 'context'     //  40  station names
  | 'detail';     //  20  chainage ticks, asset ids
```

Implementation:

1. Every text layer sets `symbol-sort-key` from the priority, so Maplibre drops low
   priority labels first under collision.
2. `text-allow-overlap: false`, `icon-allow-overlap: true` — the *marker* always survives,
   only its *text* is dropped. Existence is never hidden (doctrine rule 5).
3. When a label is dropped, its marker gains a subtle "has hidden label" affordance so the
   user knows detail is available on hover.
4. **Leader lines** for dense station areas: when ≥ 4 labels compete within 80 px, they
   are stacked in a small callout box anchored to the cluster with a leader line, rather
   than fighting for space.
5. **A hard cap of 40 visible labels** is enforced by a post-render pass; beyond that,
   `context` and `detail` tiers are suppressed and a "labels reduced" chip appears in the
   map chrome with a one-click override.

### O15.6 The inspector — progressive detail

`components/inspector/` replaces ad-hoc popups. One panel, three depths, driven by
`inspector.store`.

| Depth       | Trigger        | Content                                                             | Latency |
| ----------- | -------------- | ------------------------------------------------------------------- | ------- |
| **Peek**    | hover / focus  | 3 facts max: identity, state, one number that matters               | instant (from tile data, no fetch) |
| **Card**    | click          | ~12 facts + primary actions + "why" chip                            | < 150 ms (cached fetch) |
| **Dossier** | expand / `→`   | full record: timeline, protection, resources, impact, audit, history | < 500 ms |

Rules:

- **Peek never fetches.** If the data is not already in the tile, the peek shows what it
  has and says so. A hover that triggers a network request is a hover that feels broken.
- The inspector is **stackable with breadcrumbs**: block → its work package → the machine
  → the machine's next block. Back navigation preserves the map view.
- Every fact that is *derived* carries a `?` chip opening the explanation (evidence chain
  from O8.2 / O9.2). This is where H9 explainability actually lands for the user.
- The inspector is **keyboard-first**: `↑↓` moves between entities in the current
  selection set, `→` deepens, `←` returns, `Esc` clears.

### O15.7 Hover, selection and focus

Three distinct states, three distinct visuals, never conflated:

| State       | Cause                     | Visual                                                        | Persistence   |
| ----------- | ------------------------- | ------------------------------------------------------------- | ------------- |
| **Hover**   | pointer / keyboard focus  | 1 px halo + peek                                              | transient     |
| **Selected**| click                     | 2 px halo + card + URL updated                                | until cleared |
| **Focused** | "focus" action on selected| everything unrelated dimmed to 25 % opacity; related highlighted | explicit toggle |

**Focus mode is the clarity release valve.** When a controller focuses a block, the map
dims every train not affected by it, every restriction not in its extent, and every other
block — while keeping them faintly visible so the context is not lost (doctrine rule: dim,
never hide). One keystroke (`F`) toggles it.

Related-entity computation for focus is served by `GET /map/inspect/*`, which returns a
`related` array of `{kind, id}` so the client can restyle without extra queries.

### O15.8 Time: the slider, the clock and playback

The existing time slider is extended into a full temporal controller.

**Model** (`time.store` + `playback.store`):

```ts
interface TimeState {
  mode: 'live' | 'custom';
  businessClockAt: string;     // last server-confirmed "now"
  offsetMs: number;            // custom offset from business clock
  windowMs: number;            // visible window for the graph/gantt (default 4 h)
}
interface PlaybackState {
  playing: boolean;
  rate: 1 | 5 | 20 | 60;
  fromAt: string; toAt: string;
}
```

**Behaviours:**

1. **Live mode** follows the server's business clock (never the browser clock — a wrong
   laptop clock must not shift the railway).
2. **Custom mode** is entered by dragging the slider or typing a time; the map header
   changes colour and shows "VIEWING 14:35 (+22 min)" so nobody mistakes a forecast for
   reality. This is a safety requirement, not a nicety.
3. **Range**: −6 h to +12 h by default, configurable. Past is *recorded*; future is
   *projected* and every projected element renders with the `train.projected` /
   `block.approved` hollow style.
4. **Scrubbing** is debounced at 80 ms for fetches but re-renders instantly from data
   already in tiles, so dragging feels continuous even before new tiles arrive.
5. **Playback** advances the display clock by `rate × wallclock`, requesting tiles ahead
   of the playhead (pre-fetch 2 buckets). Pausing snaps to the current instant.
6. **Keyboard**: `space` play/pause, `←/→` ±1 min, `shift+←/→` ±15 min, `home` back to
   live.
7. **The time control is shared** by the map, the Gantt and the train graph — one clock,
   three views (D11).

### O15.9 Train rendering

**Position and motion (D1).** Positions arrive every 2 s. Between updates the client
interpolates along the segment geometry using `@turf/along` with the reported speed and
heading, capped so a train never overshoots the next reported point. On a correction, the
marker **eases** to the true position over 300 ms rather than jumping — jumping reads as a
data error to the user even when it is not.

**Projected positions.** In future time, positions come from the timetable path, rendered
hollow with a dashed halo, and the inspector labels them "projected from WTT, not
observed".

**Encoding, in priority order:**

| Fact              | Channel                                     |
| ----------------- | ------------------------------------------- |
| Identity          | label (train number), priority `operational`|
| Direction         | chevron rotation along the line             |
| Delay             | hue (`train.*` tokens) + minutes chip ≥ z14 |
| Position quality  | opacity + `wifi-off` icon when stale        |
| Priority class    | stroke width (premium thicker)              |
| Selection         | halo                                        |

**Clustering.** Below z13, `cluster: true`, radius 45, with a count label. Cluster colour
is the **worst** delay state in the cluster, not the average — the map must surface
problems, not dilute them. Clicking a cluster zooms to its bounds; `alt+click` opens a
list in the inspector without moving the map.

**Density guard.** If more than 400 individual train symbols would render, the layer
switches to clustered mode regardless of zoom and shows a chip: "clustered for legibility
— zoom in or filter".

### O15.10 Block rendering

**Geometry.** A block is drawn along the *actual track geometry* for its chainage extent,
using `lineSlice` over the segment geometries — never as a straight line between two
points and never as a rectangle. A block that does not follow the rails is a block nobody
trusts.

**The visual grammar** (tokens from O15.4):

```
proposed      ── ── ──   violet dashed, thin, 60 % opacity
approved      ─────────   amber hollow (outline only)
live          ━━━━━━━━━   amber solid, 6 px, soft outer glow
live+overrun  ━━━━━━━━━   red solid with a 1 Hz pulse (the ONLY pulsing element on the map)
at risk       ━ ━ ━ ━ ━   amber dashed with a corner "!" badge
handed back   ─────────   emerald thin
derived unavail ╱╱╱╱╱╱   amber diagonal hatch at 35 % opacity
```

**Layered composition per block** (four Maplibre layers, in order):

1. `layer-block-casing` — dark casing for contrast on any basemap.
2. `layer-block-fill` — the state colour/pattern.
3. `layer-block-endcaps` — perpendicular tick marks at each chainage limit, so the *extent
   boundary* is unambiguous. (Without endcaps, users misread where a block stops — this
   was a repeated finding in similar tools.)
4. `layer-block-symbols` — state icon at the midpoint, work-package markers at z≥13,
   protection markers at z≥15.

**Work packages and the live front.** At z≥13, each work package renders as a sub-segment
inside the block with its own progress fill (0–100 %). The reported worksite position
(S-35) renders as a distinct chevron marker that **moves as reports arrive**, with a faint
trail of its last three reported positions so the direction of progress is visible.

**Countdown.** A live block shows remaining sanctioned time as a small ring around its
midpoint icon at z≥13 — filling as it runs, turning red in the last 10 %, and continuing
past 100 % into overrun. It is the single most-watched number in the control room and it
should be visible without opening anything.

### O15.11 Conflict and opportunity visualisation

Conflicts are the reason the map exists. They must be impossible to miss and trivial to
understand.

**On the map:**

- A conflict renders as a **zigzag overlay on the intersection extent only** — not on the
  whole of either entity. The user must see *where* they clash, not merely *that* they do.
- A **conflict badge** sits at the intersection midpoint showing the count when several
  conflicts coincide.
- Off-screen conflicts produce **edge indicators**: a small arrow on the viewport border
  pointing toward the conflict, with distance. Clicking flies to it. Without this, a
  controller can be unaware of a conflict simply because they panned away.

**In the inspector**, a conflict card states, in this order:

```
WHAT   Demand BD-…4821 overlaps Block B-…1042 on UP Main, 412/3–412/7
WHEN   Sunday 10:00–12:20 (2 h 20 m of overlap)
WHY    Same segments, intersecting windows            [hard]
COST   14 trains affected · ~342 train-minutes · SLW infeasible (no crossover outside)
NEXT   • Shift demand to 12:30 (removes overlap)
       • Join the existing window (extent already covered)
       • Reduce extent to 412/3–412/5
```

`NEXT` items here are **deterministic, rule-derived hints**, and the panel says so:
"suggestions are rule-based; ranked plan options require the optimiser (not enabled)".
This keeps the promise of O9.4 honest and avoids implying intelligence we have not built.

**Opportunity (bundling) hint.** Overlap *detection* is deterministic and in scope, so the
map may show a "shared window possible" chip where two compatible demands sit close in
space and time. It states the fact and stops there; it does not rank, cost-optimise or
propose a merged plan. That is the optimiser's territory.

### O15.12 Traction / power overlay

Toggleable overlay, rendered **above** the track but **below** blocks:

- Elementary sections drawn as a parallel double line offset 4 px above the track.
- `power.isolated` and `power.earthed` are visually distinct — earthed adds a tick glyph
  at each earth point. The difference between "switched off" and "proved dead and earthed"
  is the difference between a safe worksite and a fatality (S-38), and the map must never
  blur it.
- When a block requires a power block and the OHE is **not** confirmed earthed, the block
  renders with a `state.unknown` hatch overlay until earthing is confirmed. Unknown is
  loud (doctrine rule 6).
- Live OHE immediately adjacent to a worksite renders in `power.live_adjacent` with a bolt
  glyph. This is one of the few things allowed to be visually aggressive.
- Selecting a proposed isolation shows the **minimal isolation set** computed in O8.3,
  with everything that goes dead shaded, plus a count: "isolating 2 elementary sections →
  4 stations dark, 11 km of OHE".

### O15.13 Restriction overlay

- Rendered as a dash-dot line offset 4 px *below* the track (mirroring traction above), so
  three concerns can coexist on one corridor without overlapping strokes.
- Speed value labelled at z≥13 with a small speed-plate glyph.
- **Ageing is encoded**: as a restriction passes its review date, its hue shifts toward
  `restriction.overdue` and it gains a clock glyph. A restriction eight months overdue
  looks visibly wrong on the map. Making decay visible is how S-34 stops recurring.
- The restriction layer has its own filter chip: `all / active / overdue / imposed by this
  block`.

### O15.14 Derived unavailability visualisation

The output of O8 is one of the highest-value things the map can show, and one of the
easiest to render confusingly.

- Rendered as **diagonal hatch** (never a solid fill, which would be mistaken for a block).
- **Only shown when a block or demand is selected or hovered**, because it is a
  *consequence of something*, and showing consequences without their causes is noise.
- Each hatched segment's peek states the reason in one sentence:
  "Unusable: only access is via the blocked UP Main between 412/3 and 412/7."
- Confidence is respected: an `ESTIMATED` conclusion renders at lower opacity with a `?`
  and the peek says "provisional — topology unverified".

### O15.15 Drawing and editing extents on the map

Direct manipulation (D7), implemented in `components/map/ExtentDrawTool.tsx`.

**Draw flow:**

1. User picks a line (click) → the line highlights and chainage ticks appear.
2. Click sets the start; move shows a live extent with a floating readout
   `412/300 → 414/750 · 2.45 km`; click sets the end.
3. The extent **snaps** to meaningful features within 25 px: node, turnout, crossover,
   signal, structure, LC, existing block boundary. Snapping is what makes drawn extents
   operationally sane rather than arbitrary.
4. On release, the client calls the wizard's compute endpoint and the map immediately
   shows derived unavailability, conflicts and affected trains **on the map itself**, not
   only in a side panel.

**Edit flow:** a selected extent shows draggable endcap handles and a whole-extent drag.
Every drag re-runs the computation on a 300 ms debounce. An edit that introduces a hard
rule violation snaps back with an inline explanation naming the rule.

**Guard rails:** extents cannot be drawn across a division boundary without an explicit
confirmation (V-23), cannot be zero-length, and cannot span discontinuous geometry.

### O15.16 Geographic ↔ schematic morph

Both view modes are supported (Part K1). Implementation:

- Every segment carries **two geometries** (`geometry`, `schematic_geometry`), the second
  precomputed by the ETL using a straightening pass.
- Switching modes **animates between them over 600 ms** with `easeInOutCubic` on the
  coordinate arrays. Morphing rather than swapping preserves the user's mental map — a
  hard swap forces re-orientation every time and users stop switching.
- All overlays are recomputed against the active geometry; nothing is positioned in
  absolute pixels.
- Mode is per-user, persisted, and reflected in the URL.

### O15.17 The linked train graph (time–distance)

A collapsible bottom panel (30 % height) showing the classic controller's graph: chainage
on Y, time on X, train paths as lines, blocks as shaded horizontal bands.

- **Linked selection**: hovering a train on the map highlights its line in the graph and
  vice versa (D11).
- The **time slider's playhead** is a vertical line on the graph; dragging either moves
  both.
- Blocks appear as bands so a planner can see, in one glance, which paths pass through the
  proposed window — the exact judgement the approval screen requires.
- Rendered with Recharts for axes and a custom canvas layer for the paths (hundreds of
  polylines are too many for SVG at interactive frame rates).

### O15.18 Density management and the performance budget

| Metric                                   | Budget                    | Enforcement                          |
| ---------------------------------------- | ------------------------- | ------------------------------------ |
| Frame time while panning (1 500 trains)  | ≤ 20 ms (≥ 50 fps)        | perf test in CI with a synthetic feed|
| Time-scrub re-render                     | ≤ 200 ms                  | measured, logged as a map metric     |
| Tile response (95th percentile)          | ≤ 120 ms                  | server metric                        |
| Delta payload per 2 s poll (typical)     | ≤ 40 kB                   | server metric                        |
| Initial map interactive                  | ≤ 2.5 s cold, ≤ 1 s warm  | Lighthouse + IndexedDB cache         |
| Memory after 30 min live                 | ≤ 400 MB                  | soak test                            |
| Visible labels                           | ≤ 40                      | post-render pass (O15.5)             |
| Distinct colour meanings in viewport     | ≤ 5                       | review rule + dev overlay warning    |

Techniques, in the order they are applied:

1. **GeoJSON sources updated by `setData` with pre-built feature collections** — never
   per-feature mutation.
2. **Feature-state for hover/selection/dim** — restyling via `setFeatureState` costs
   nothing; rebuilding sources costs everything.
3. **Data-driven styling expressions** so state changes need no JS per frame.
4. **Interpolation in a `requestAnimationFrame` loop** that writes to a single source,
   throttled to the display refresh.
5. **Tile-scoped data only.** Nothing outside the viewport tiles is ever in memory.
6. **Web Worker** for tile-boundary computation and GeoJSON assembly at load-test scale
   (Phase 10c in `plan.md`; the interface is designed for it now — all builders are pure
   functions taking plain data, so moving them to a worker is a transport change only).
7. **Cluster below z13**, density guard above (O15.9).

### O15.19 Empty, stale and degraded states on the map

| Situation                    | Rendering                                                                    |
| ---------------------------- | ---------------------------------------------------------------------------- |
| No data yet                  | skeleton network in slate with a "loading network" chip — never a blank void  |
| Tile not built               | that area is **cross-hatched grey with "no data"**, not shown as empty track  |
| Positions stale > 3 min      | trains fade to `train.stale`, banner: "train positions stale — last update HH:MM" |
| SSE dropped                  | amber chip "live updates reconnecting — polling at 30 s"                      |
| Read Store down              | map switches to the IndexedDB snapshot, full-width red banner with the snapshot time, all actions disabled |
| Viewing custom time          | persistent coloured header "VIEWING 14:35 — not live"                         |
| Unverified topology in view  | those segments render with the `track.unverified` dot pattern + legend note   |

**The rule behind this table:** the map may be wrong about the future, but it must never
be *quietly* wrong about the present.

### O15.20 Map keyboard and accessibility mode

- `Tab` cycles entities in the viewport by priority (live blocks → conflicts → trains).
- Arrow keys pan, `+/-` zoom, `[`/`]` step zoom bands, `F` focus, `L` legend,
  `T` time panel, `G` train graph, `Esc` clear.
- The current selection is announced via an `aria-live` region in plain language:
  "Live block B-1042, UP Main 412/3 to 412/7, 38 minutes remaining, protection complete,
  OHE earthed."
- A **table view toggle** presents the same viewport contents as an accessible data table.
  This is both an accessibility feature and the degraded-mode print artefact (L5).

### O15.21 File plan for the map

```
frontend/components/map/
  MapContainer.tsx          existing — becomes a thin composition root
  MapStyle.ts               NEW  basemap style + token→paint compilation
  layers/
    baseNetwork.layer.ts    NEW  casing, line, chainage ticks, node symbols
    block.layer.ts          REPLACES BlockLayer.ts — casing/fill/endcaps/symbols
    train.layer.ts          REPLACES TrainLayer.ts — cluster/point/label/chevron
    restriction.layer.ts    NEW
    traction.layer.ts       NEW
    conflict.layer.ts       NEW
    unavailability.layer.ts NEW
    worksite.layer.ts       NEW
    selection.layer.ts      NEW  halo/dim via feature-state
  tools/
    ExtentDrawTool.tsx      NEW  draw/snap/edit
    MeasureTool.tsx         NEW  chainage measurement
  chrome/
    MapLegend.tsx           NEW  server-driven legend
    MapFilters.tsx          NEW  layer + semantic filters (URL-synced)
    MapStatusBar.tsx        NEW  freshness, degraded chips, counts
    EdgeIndicators.tsx      NEW  off-screen conflict/live-block arrows
    ViewModeToggle.tsx      NEW  geographic ↔ schematic morph
  TimeControls.tsx          existing — extended with playback
  MapSidebar.tsx            existing — becomes entity lists + filters
  PartKMap.tsx              existing prototype — fold in, then delete

frontend/lib/map/
  tokens.ts       lod.ts        labels.ts       interpolate.ts
  geometry.ts     snapping.ts   featureState.ts telemetry.ts
```

**Deletion is part of the work.** `PartKMap.tsx` and the old layer builders must be
removed once folded in; two map implementations is how the clarity doctrine dies.

### O15.22 Map data contracts (feature properties)

Every rendered feature carries a flat, stable property set — Maplibre expressions cannot
read nested objects.

```ts
interface TrainFeatureProps {
  id: string; number: string; kind: 'PASSENGER'|'FREIGHT'|'SPECIAL'|'ENGINEERING';
  priorityClass: number; delayMin: number; delayState: 'ONTIME'|'DELAYED'|'SEVERE';
  bearing: number; speedKmph: number; trackId: string; chainageM: number;
  positionQuality: 'OBSERVED'|'INFERRED'|'PROJECTED'; ageSec: number;
  nextStop?: string; etaAt?: string;
}

interface BlockFeatureProps {
  id: string; ref: string; state: 'PROPOSED'|'APPROVED'|'LIVE'|'AT_RISK'|'OVERRUN'|'HANDED_BACK';
  trafficState: string; powerState: string; adjacentLine: string;
  startAt: string; endAt: string; remainingMin: number; progressPct: number;
  department: string; workType: string; packages: number;
  hasUnknownSafetyFact: boolean; conflictCount: number;
}

interface RestrictionFeatureProps {
  id: string; kind: string; valueKmph?: number; imposedAt: string;
  reviewDueOn: string; overdueDays: number; originBlockRef?: string;
}

interface UnavailFeatureProps {
  segmentId: string; effect: string; reasonCode: string;
  causeBlockId: string; confidence: 'VERIFIED'|'IMPORTED'|'ESTIMATED';
}
```

Rule: **anything the renderer needs must be a top-level primitive**; anything the
inspector needs may be fetched. This split is what keeps the peek instant (O15.6).

### O15.23 Map telemetry

`lib/map/telemetry.ts` records (locally, and optionally to the backend) frame time
percentiles, tile fetch latency, delta payload size, label suppression count, time-scrub
latency, and interaction counts per tool. Two purposes: proving the performance budget in
CI, and learning which map affordances are actually used so the next iteration removes
what is not.

### O15.24 Map acceptance tests

Each is a definition of done, not a suggestion.

| ID    | Test                                                                                              |
| ----- | ------------------------------------------------------------------------------------------------- |
| M-01  | With 1 500 trains and 120 blocks, panning sustains ≥ 50 fps for 30 s                             |
| M-02  | Scrubbing the slider ±6 h re-renders in < 200 ms per step with no flicker                        |
| M-03  | A grant event appears on the map within 1 s via SSE, with an animated state transition            |
| M-04  | Stopping the position feed makes trains visibly stale within 3 min and shows the banner           |
| M-05  | Selecting a block shades its derived unavailability, and every hatched segment explains itself    |
| M-06  | A power block without confirmed earthing renders `unknown` hatch and never `earthed`              |
| M-07  | Drawing an extent snaps to a crossover and reports SLW infeasibility when the crossover is inside |
| M-08  | Two overlapping demands produce a zigzag on the intersection only, plus an edge indicator when off-screen |
| M-09  | Geographic ↔ schematic morph animates and keeps all overlays correctly positioned                 |
| M-10  | At most 40 labels render at any zoom; the "labels reduced" chip appears beyond that               |
| M-11  | Full keyboard traversal reaches every visible entity and announces it via `aria-live`             |
| M-12  | With Redis and the Read Store stopped, the map shows the IndexedDB snapshot with a red banner and disabled actions |
| M-13  | Delta transfer: an unchanged tile returns `unchanged` and the client does not clear it            |
| M-14  | Colour-blind simulation: every state remains distinguishable by icon or pattern alone             |
| M-15  | A restriction 8 months overdue is visually distinct from a fresh one without interaction          |

---

## O16. The field application

### O16.1 Form factor decision

**A Progressive Web App inside the same Next.js project**, under `/field`, with its own
minimal shell, its own service worker scope, and its own bundle budget.

Rationale: one codebase, one auth, one deployment; installable on Android without a store;
works on low-end devices; no native build pipeline to maintain for an MVP. A native app is
justified only if we later need background location or hardware integration — recorded as
a future decision, not taken now.

### O16.2 The safety screen (the most important screen in the system)

Requirements, all non-negotiable:

1. **Three facts, huge, above the fold**: is the block granted; is OHE earthed; is the
   adjacent line open. Each is a full-width pill with an icon, a word, and a colour.
2. **A staleness clock is always visible**: "Confirmed 14:32 · 41 s ago". When the app has
   been offline beyond the threshold, the pills **degrade to `UNKNOWN`** and the screen
   says, in plain language, "Cannot confirm protection — treat the line as open."
3. **Never infer.** No cached "granted" state may be shown as current beyond the
   configured freshness window. This is the single most important line of code in the
   product.
4. **A standing disclaimer**: physical protection remains primary; this app records and
   informs, it does not protect (C4.2).
5. Large touch targets, high contrast, sunlight mode, one-handed reachability, and the
   whole screen readable at arm's length.

### O16.3 Offline architecture

```
lib/offline/
  db.ts        Dexie schema: assignments, blocks, checklists, queue, media, sync_meta
  queue.ts     append-only outbound queue with monotonic client sequence
  sync.ts      background sync: drain queue → pull scope → reconcile
  conflict.ts  resolution policy
```

Policies:

- **Writes are queued locally with their true timestamp** and marked `recorded_late` when
  they sync after the fact. No silent back-dating (O6.7).
- **Reads are cached per assignment scope**, refreshed opportunistically.
- **Conflict policy**: server wins for state; client wins for *observations* (a protection
  confirmation made at 10:14 is a fact and is preserved as such, even if it arrives at
  10:40). Anything unresolvable is surfaced to the user, never silently dropped.
- **Media** (photos) are compressed client-side, queued separately, and uploaded on
  Wi-Fi/good signal; the record is not blocked waiting for the photo.
- **Emergency path works fully offline** and queues at the front, plus a `tel:` fallback
  to the control office presented immediately when the network is unavailable (S-43).

### O16.4 Field screens

`/field` (my assignments), `/field/blocks/[id]` (safety screen + checklist + progress +
extension + hand-back), `/field/defects/new` (60-second capture with camera + GPS, S-01),
`/field/emergency` (the 7-field form, G15).

---

## O17. Notifications and acknowledgement

### O17.1 Design

A worker service (or a Command Service background task in the MVP) consumes
`notification.commands` and fans out per recipient and channel.

- **Recipient computation is server-side and rule-based**: for a block, the stakeholder set
  is derived from the demand owner, the department officer, the controller of the section,
  the nominated person, resource owners, and any subscriber to the section. Nobody
  maintains a distribution list by hand — that is how S-17 happens.
- **Channels** are attempted in priority order per notification priority; `SAFETY` and
  `URGENT` escalate to SMS/voice fallback.
- **Acknowledgement is explicit**, tracked per recipient, and drives a dashboard of
  outstanding acknowledgements plus automatic escalation before the block date (S-18).
- **Idempotency**: a notification for an `event_id` is created once, regardless of
  redelivery.

### O17.2 In-app surface

A notification centre with severity grouping, plus non-modal toasts for live events on
the console and map. Safety notifications are the only ones permitted to interrupt.

---

## O18. Security and access control

### O18.1 Model

**RBAC with scope**: `role × scope` where scope is `zone | division | section |
department | project`. A permission check answers "may this identity perform this action on
this entity in this scope".

Roles (initial): `FIELD_USER`, `NOMINATED_PERSON`, `DEPT_OFFICER`, `PLANNER`,
`CONTROLLER`, `CHIEF_CONTROLLER`, `OPS_MANAGER`, `SAFETY_OFFICER`, `TPC`, `DRM`,
`PROJECT_MANAGER`, `CONTRACTOR`, `AUDITOR` (read-only, everything), `ADMIN`.

### O18.2 Rules

1. **Deny by default.** Every endpoint declares its required permission; a missing
   declaration fails the build via a test that enumerates routes.
2. **Delegation is a record**, time-bounded, with the delegator named on every action
   taken under it (S-86).
3. **Elevated actions** (peak override, embargo override, restricted-visibility classes)
   require re-authentication and a mandatory justification, and always emit an audit
   record and a notification to the safety officer.
4. **Contractors and third parties** see only their own sponsored works.
5. **Auditors** get a read-only role that can query historic state (O19.2) but cannot
   mutate anything.

### O18.3 Practical hardening checklist

- Access tokens ≤ 15 min, refresh rotation, revocation list in Redis.
- Passwords (if local auth is used at all) hashed with Argon2id; prefer SSO/OIDC.
- Every write endpoint requires `Idempotency-Key` and is rate limited.
- File uploads: extension + MIME + magic-byte validation, size cap, stored with generated
  names outside the web root, served via short-lived signed URLs.
- No secret in the repository; `.env.example` documents every variable with a safe default
  that fails closed.
- Structured logs exclude tokens, phone numbers and free-text safety notes.

---

## O19. Observability, audit and degraded modes

### O19.1 Observability

- **Structured JSON logs** with `correlation_id`, `actor`, `entity`, `event`.
- **Metrics** (Prometheus-format endpoint per service): request latency histograms, ETL
  cycle time and lag, tile hit/miss, event publish/consume lag, outbox backlog, SSE
  connections, rule firing counts, map frame-time percentiles from the client.
- **Health endpoints**: `/healthz` (liveness), `/readyz` (dependencies with per-dependency
  status, used by Compose healthchecks).
- **Golden signals dashboard** for the demo: write latency, ETL lag, tile latency, live
  block count, stale-position count.

### O19.2 Audit and reconstruction

- `audit_record` is append-only; the application database role has no `UPDATE`/`DELETE`
  on it.
- **Time-travel reconstruction**: `GET /audit/state?entity=block:B-1042&at=…` replays
  events up to an instant and returns the state as it was known then. This answers the
  enquiry question "what did the controller actually see at 10:15?" — which is different
  from "what do we now know was true", and both must be answerable.
- Every `Decision` stores the options presented and the justification. When the optimiser
  arrives, its options land here; until then, the array is empty and the justification is
  the human's own — the record shape does not change.

### O19.3 Correlation across the stack

The gateway's `X-Correlation-Id` is carried into events (`correlation_id`), into ETL
processing, into cache keys' invalidation messages, and into the frontend's error toasts
(`CorrelationIdBadge`, already built). A user can read an id off the screen and an
engineer can trace the entire path.

### O19.4 Degraded modes (L5, made concrete)

| Failure                    | Automatic behaviour                                                    | Artefact                             |
| -------------------------- | ---------------------------------------------------------------------- | ------------------------------------ |
| Kafka down                 | outbox accumulates; API keeps working; alarm on backlog                | —                                    |
| Optimiser absent           | normal operation; "optimiser not enabled" states                       | —                                    |
| Read Store lag > 60 s      | amber freshness everywhere; approvals warn that impact figures are stale| —                                    |
| Query Service down         | frontend serves IndexedDB snapshot, read-only, red banner              | snapshot                             |
| Whole system down          | pre-generated PDFs                                                     | **daily block sheet** per section, regenerated hourly and pushed to field devices |
| Field device offline       | queued writes, `UNKNOWN` safety states after the freshness window      | cached assignment card               |

The **daily block sheet** is a deliverable, not an afterthought: an A4 PDF per section
listing every sanctioned block for the next 24 h with extents, times, nominated persons,
contact numbers and protection requirements. It is what the railway falls back to, and it
is generated from the same system of record, so it cannot drift (F1.11).

---

## O20. Testing and acceptance

### O20.1 Test pyramid

| Level          | Scope                                                                 | Tooling            |
| -------------- | --------------------------------------------------------------------- | ------------------ |
| Unit (pure)    | `db/domain/*` — topology, conflicts, rules, capacity, impact L1, lifecycle | pytest, table-driven |
| Unit (service) | validation, gates, state transitions with a fake repository            | pytest             |
| Contract       | every event validated against its JSON Schema; API responses vs OpenAPI| pytest + schemathesis |
| Integration    | Command → outbox → Kafka → ETL → Read Store → Query                    | pytest + testcontainers/Compose |
| Frontend unit  | hooks, tile math, label engine, interpolation, tokens                  | vitest             |
| Frontend E2E   | wizard, console, map behaviours M-01…M-15                              | Playwright         |
| Performance    | map frame time, tile latency, ETL cycle at load-test scale             | Playwright + k6    |
| Safety         | the gate suite below                                                   | pytest, mandatory  |

### O20.2 The safety test suite (must never be skipped)

| ID    | Assertion                                                                              |
| ----- | -------------------------------------------------------------------------------------- |
| SAF-1 | Work cannot start without traffic block granted                                        |
| SAF-2 | Work cannot start without every required protection item confirmed                     |
| SAF-3 | Work near OHE cannot start without `EARTHED`, even if `ISOLATED`                        |
| SAF-4 | Grant is refused when the nominated person's competency expires before the block date  |
| SAF-5 | Hand-back is refused with any open disconnection                                        |
| SAF-6 | Adjacent line `OPEN` without a lookout/warning arrangement is refused at entry (V-11)   |
| SAF-7 | No role can override SAF-1…SAF-6                                                        |
| SAF-8 | Field app shows `UNKNOWN` (not the cached state) after the offline freshness window     |
| SAF-9 | An emergency demand is accepted with the 7 minimum fields and never blocked by validation |
| SAF-10| Restriction cannot be imposed without extent, value and review date (V-24)              |

### O20.3 Definition of done (per work package)

Code + tests + migration (with downgrade) + OpenAPI/schema updated + seed data covering
the new case + a screenshot or short clip for UI work + the relevant acceptance rows
passing + no new lint errors.

---

## O21. Local development and deployment

### O21.1 One-command local stack

```powershell
docker compose -f infra/docker-compose.yml up -d
python infra/bootstrap_topics.py
python -m db.seed --profile demo          # 24 stations / 300 segments / 150 trains
python -m db.readstore.etl --rebuild all
# frontend: http://localhost:3004   gateway: http://localhost:8000
```

Additions needed to Compose: the notification worker, the ETL as a long-running service
(currently run by hand), and a `seed` one-shot profile so a fresh clone is demo-ready in
one command.

### O21.2 Environment variables (new)

| Variable                          | Service        | Default (dev)               | Notes                          |
| --------------------------------- | -------------- | --------------------------- | ------------------------------ |
| `AUTH_MODE`                       | gateway        | `stub`                      | `stub` \| `oidc`               |
| `OIDC_ISSUER` / `OIDC_AUDIENCE`   | gateway        | —                           | required when `oidc`           |
| `CORS_ALLOWED_ORIGINS`            | gateway        | `http://localhost:3004`     | strict list, no `*` outside dev|
| `RATE_LIMIT_WRITES_PER_MIN`       | gateway        | `60`                        |                                |
| `SSE_ENABLED`                     | query          | `true`                      |                                |
| `TILE_TIME_BUCKET_MIN_TRAINS`     | query/etl      | `15`                        | must match the frontend        |
| `ETL_MODE`                        | etl            | `incremental`               | `full` \| `incremental`        |
| `ETL_INTERVAL_SEC`                | etl            | `2`                         |                                |
| `READINESS_GATE_HOURS_BEFORE`     | command        | `24`                        |                                |
| `FIELD_FRESHNESS_WINDOW_SEC`      | frontend/field | `300`                       | **safety-relevant**            |
| `NEXT_PUBLIC_MAP_STYLE_URL`       | frontend       | local style                 | basemap source                 |
| `NEXT_PUBLIC_DEFAULT_LOCALE`      | frontend       | `en`                        |                                |
| `WEATHER_PROVIDER` / `_API_KEY`   | command        | `none`                      | optional; degrades to manual   |

### O21.3 Deployment posture (beyond local)

Not in scope to build now, but the shape is fixed so nothing has to be undone: stateless
services behind a load balancer, Postgres managed with PITR, Redpanda/Kafka managed or
3-node, Redis with persistence off (cache only), object storage for attachments, and the
frontend on any Node host or static+edge runtime. Everything is already containerised, so
this is a configuration exercise, not a rewrite.

---

## O22. Delivery sequence

Work packages, ordered by dependency. **No package here contains optimiser work.**
Each has an exit criterion that can be demonstrated.

| WP  | Package                          | Depends on | Exit criterion                                                        |
| --- | -------------------------------- | ---------- | --------------------------------------------------------------------- |
| W1  | Topology & traction schema + seed| —          | 24-station network with curves, turnouts, elementary sections, loads in the map |
| W2  | Chainage & geometry utilities    | W1         | Any chainage range renders on the true track geometry                 |
| W3  | Topology expansion engine (O8)   | W1, W2     | Selecting a block shades a correct, explained unavailability set      |
| W4  | Demand schema + wizard intake    | W1         | Full Part G demand can be created, saved, versioned                   |
| W5  | Validation + rules engine        | W4         | All V-01…V-24 fire correctly with citations                           |
| W6  | Conflict detection + L1 impact   | W3, W4     | Two clashing demands produce explained conflicts and detention figures|
| W7  | Read Store projections + tiling  | W1–W6      | All map layers delta-transfer correctly                               |
| W8  | Query endpoints + cache registry | W7         | Every screen served by one call each, within latency budget           |
| W9  | **Dynamic map — core**           | W7, W8     | M-01, M-02, M-05, M-13 pass                                           |
| W10 | **Dynamic map — clarity**        | W9         | M-08, M-10, M-14, M-15 pass                                           |
| W11 | Execution lifecycle + gates      | W4         | SAF-1…SAF-7 pass                                                      |
| W12 | Live console + SSE               | W11, W8    | M-03, M-04 pass; grant→map latency < 1 s                              |
| W13 | Field PWA + offline              | W11        | SAF-8, SAF-9 pass; full offline block execution                       |
| W14 | Restrictions + resources + readiness | W11    | SAF-10 passes; readiness board works                                   |
| W15 | Notifications + acknowledgement  | W11        | Stakeholder set computed; acknowledgement dashboard live              |
| W16 | RBAC + audit + degraded modes    | W11        | M-12 passes; audit reconstruction answers "what was known at T"       |
| W17 | Map extras: draw, morph, graph   | W9, W10    | M-07, M-09 pass; train graph linked                                   |
| W18 | Analytics, scorecards, KPIs      | W7, W11    | Claimed-vs-actual visible per department                              |
| W19 | i18n, accessibility, print       | W9–W13     | M-11 passes; block sheet PDF generated hourly                         |
| W20 | Hardening, perf, docs, demo      | all        | Full budget table met; demo script runs unassisted                    |

Parallelisation: W4/W5 (write path) and W7/W8/W9 (read path + map) can run concurrently
once W1–W3 land. W13 (field) can start as soon as W11's endpoints exist.

---

## O23. What is needed from you — the requirements guide

This chapter exists so that work is never silently blocked waiting for an answer. It lists
everything only you (the product owner) can decide or provide, states the **default that
will be applied if you say nothing**, and marks whether it blocks work.

> **How to use it:** answer the fast questionnaire in O23.7 first (ten minutes). Everything
> else can be answered as the relevant work package approaches.

### O23.1 Decisions — product and scope

| #    | Decision                                                     | Options                                                                 | Default if silent                        | Blocks   |
| ---- | ------------------------------------------------------------ | ----------------------------------------------------------------------- | ---------------------------------------- | -------- |
| D-01 | Target audience for the first demo                           | judges/evaluators · railway SMEs · internal only                        | judges/evaluators                        | W20      |
| D-02 | Scope of the first release                                    | full Part O · map + read path only · write path only                    | map + execution lifecycle + demand intake| W22 plan |
| D-03 | Is the field PWA in the first release?                       | yes · no                                                                | yes, minimal (safety screen + checklist) | W13      |
| D-04 | Real auth or stub for the demo                                | OIDC · local users · stub                                               | local users with seeded roles            | W16      |
| D-05 | Multi-tenancy (multiple divisions visible at once)            | yes · single division                                                   | single division, schema ready for more   | W1       |
| D-06 | Emergency block path in scope                                 | yes · no                                                                | yes (it is cheap and it is the headline) | W4       |
| D-07 | Third-party/contractor portal                                 | yes · no                                                                | no (schema reserved)                     | W4       |
| D-08 | Which languages                                               | list                                                                    | English + Hindi                          | W19      |
| D-09 | Do we need printable artefacts (block sheet PDF)?             | yes · no                                                                | yes                                      | W19      |
| D-10 | Optimiser interface stub visible in the UI?                   | show "not enabled" · hide entirely                                      | show "not enabled" (honest)              | W9       |

### O23.2 Decisions — domain policy (defaults are guesses; your answers make them real)

| #    | Question                                                                  | Default applied                                   | Blocks |
| ---- | ------------------------------------------------------------------------- | ------------------------------------------------- | ------ |
| P-01 | Notice period per block class                                             | Routine 14 d, Mega 30 d, Major 60 d, Short 24 h   | W5     |
| P-02 | Peak / embargo windows to enforce                                         | 07:00–11:00 and 17:00–21:00 on the demo section   | W5     |
| P-03 | Approval chain per class (who signs what)                                 | Dept officer → Planner → Ops manager; Safety for high-risk | W11 |
| P-04 | SLA per lifecycle stage                                                   | scrutiny 2 d, analysis 1 d, approval 3 d          | W5     |
| P-05 | Criticality levels and their exact definitions                            | the six in G4 3.7                                 | W4     |
| P-06 | Competency codes required per work type                                   | a small demo set                                  | W11    |
| P-07 | Cost model (₹ per train-minute, per cancellation, per tonne-hour)          | placeholder values, clearly labelled              | W6     |
| P-08 | Capacity profiles (trains/hour) for normal, SLW, degraded                 | 12 / 5 / 8 on the demo section                    | W6     |
| P-09 | Freshness window before the field app declares `UNKNOWN`                   | 300 s                                             | W13    |
| P-10 | Maximum consecutive night blocks per gang                                 | 3                                                 | W5     |
| P-11 | Restriction review period after imposition                                | 30 days                                           | W14    |
| P-12 | Who may override an embargo/peak window                                   | `OPS_MANAGER` and above, with justification       | W16    |
| P-13 | Retention period for audit and safety records                             | 7 years (configurable)                            | W16    |
| P-14 | Emergency record completion deadline                                      | 24 h                                              | W4     |

### O23.3 Data you need to provide (or approve synthetic substitutes)

| #    | Data                                       | Ideal format                                     | If unavailable                                          | Blocks |
| ---- | ------------------------------------------ | ------------------------------------------------ | ------------------------------------------------------- | ------ |
| N-01 | Track topology for the demo section        | CSV/GeoJSON: nodes, segments, chainage, line ids | synthetic generator (O4.5) — **fully sufficient for a demo** | W1  |
| N-02 | Station list with codes and coordinates    | CSV                                              | synthetic                                               | W1     |
| N-03 | Turnouts / crossovers                      | CSV                                              | synthetic                                               | W1     |
| N-04 | Traction elementary sections + earth points| CSV                                              | synthetic                                               | W1     |
| N-05 | Working timetable / paths                  | CSV or GTFS-like                                 | synthetic 150-train day                                 | W6     |
| N-06 | Live train positions feed                  | API or sample dump                               | simulated feed driven by the timetable                  | W9     |
| N-07 | Work-type taxonomy actually used           | list                                             | the G4.1 taxonomy                                       | W4     |
| N-08 | Real (redacted) block request examples     | scans/photos/spreadsheets                        | invented but plausible                                  | W4     |
| N-09 | Machine/gang inventory                     | CSV                                              | synthetic                                               | W14    |
| N-10 | Rule sources (circulars, enquiry findings) | text + citation                                  | placeholder citations, clearly marked                   | W5     |
| N-11 | Basemap preference                         | style URL or "generic"                           | a neutral open style; railway drawn from our own data   | W9     |

> **Important:** none of N-01…N-11 blocks progress. The synthetic generator is designed to
> be a credible stand-in. Real data improves realism; it is not a prerequisite.

### O23.4 Accounts, credentials and infrastructure

| #    | Item                                     | Needed for                        | If unavailable                      |
| ---- | ---------------------------------------- | --------------------------------- | ----------------------------------- |
| A-01 | Map tile/style provider (if not self-hosted) | basemap                       | self-hosted neutral style           |
| A-02 | Weather API key                          | V-18, readiness gate               | weather checks disabled, marked N/A |
| A-03 | SMS/push provider                        | notification escalation            | in-app only, escalation simulated   |
| A-04 | OIDC/SSO details                         | real auth                          | seeded local users                  |
| A-05 | Object storage bucket                    | attachments/photos                 | local volume in Compose             |
| A-06 | Deployment target (if any)               | beyond local                       | local Docker Compose only           |

None of these block local development; each degrades to a clearly-labelled stub.

### O23.5 Design and branding inputs

| #    | Item                                    | Default if not provided                          |
| ---- | --------------------------------------- | ------------------------------------------------ |
| B-01 | Logo / wordmark                         | text wordmark                                    |
| B-02 | Brand colours                           | the existing token palette (already accessible)  |
| B-03 | Any mandated government UI standard     | none applied                                     |
| B-04 | Terminology preferences (block vs possession, etc.) | Indian Railways terminology as used in Part A2 |
| B-05 | Demo narrative you want the UI to tell  | the S-11 → bundling → execution story            |

### O23.6 People and time from your side

| #    | Ask                                                     | How much                       | Why it matters                                   |
| ---- | ------------------------------------------------------- | ------------------------------ | ------------------------------------------------ |
| T-01 | One review of the demand form fields                    | 45 min                         | Prevents building a form nobody will fill (S-83) |
| T-02 | One walkthrough of the map with a controller mindset    | 45 min after W9                | Clarity cannot be validated by the builder       |
| T-03 | Sign-off on the safety-state wording (field app)        | 20 min                         | The exact words matter more than the code        |
| T-04 | Answers to the O23.7 questionnaire                      | 10 min                         | Unblocks defaults becoming decisions             |
| T-05 | Confirmation of the demo script and running order       | 30 min before W20              | Demo failures are usually sequencing failures    |

### O23.7 The fast questionnaire (copy, answer inline, paste back)

```
1.  Primary audience for the first demo?                       →
2.  Must the field/mobile app be in the first release?          →
3.  Real login, or seeded demo users?                           →
4.  Do you have ANY real topology/timetable data?               → yes / no / partial
5.  If no real data: is a synthetic 24-station network OK?       → yes / no
6.  Languages needed in the first release?                       →
7.  Which single screen must be flawless on demo day?            → map / console / wizard / dashboard
8.  Peak windows to enforce on the demo section?                 →
9.  Are placeholder cost figures (₹/train-minute) acceptable?    → yes / no
10. Anything from Parts B–N you want explicitly DROPPED?         →
11. Anything from Parts B–N you want explicitly PRIORITISED?     →
12. Deadline or milestone date I should sequence against?        →
```

### O23.8 Blocking vs non-blocking summary

| Truly blocking (work stops without an answer) | Non-blocking (default applied, revisit later)        |
| --------------------------------------------- | ---------------------------------------------------- |
| D-02 scope of the first release               | every item in O23.2 (policy defaults exist)          |
| D-08 languages, only at W19                   | every item in O23.3 (synthetic data exists)          |
| P-09 field freshness window, at W13           | every item in O23.4 (stubs exist)                    |
| A-04 only if real auth is mandatory           | every item in O23.5 (defaults exist)                 |

**Everything else proceeds on documented defaults**, which are recorded in O24 so that no
assumption is invisible.

---

## O24. Assumptions register

Applied where no instruction exists. Each is cheap to reverse if challenged early.

| #    | Assumption                                                                        | Reversal cost |
| ---- | --------------------------------------------------------------------------------- | ------------- |
| AS-1 | A synthetic network is acceptable for demonstration and load testing               | none          |
| AS-2 | One division, one corridor, in the first release                                   | low           |
| AS-3 | Train positions are simulated from the timetable, with realistic jitter and gaps   | low           |
| AS-4 | Impact stays at Level 1 (deterministic); no propagation modelling                  | medium        |
| AS-5 | No optimiser in this work; all ranked-suggestion UI shows "not enabled"            | none          |
| AS-6 | Attachments are stored locally in dev, object storage later                        | low           |
| AS-7 | Notifications are in-app only unless a provider is supplied                        | low           |
| AS-8 | Auth is seeded local users with real RBAC enforcement                              | low           |
| AS-9 | English + Hindi, with safety strings translated first                              | low           |
| AS-10| PostGIS is not used; JSONB geometry + bbox columns are sufficient                   | medium        |
| AS-11| Polling + SSE only; no WebSocket in this work                                       | low           |
| AS-12| Cost figures are placeholders and are labelled as such in the UI                    | none          |
| AS-13| The map's basemap is a neutral open style; all railway detail is our own data       | low           |
| AS-14| Curved, organic track geometry is required (a straight-line network hides real problems) | none     |

---

## O25. The optimisation service boundary

### O25.1 Why it is excluded here

By explicit instruction, and by the sequencing argument of [N4](#n4-closing-note). The
optimiser is the last thing to build, not the first: it consumes truthful topology,
structured demand, resource facts and actuals — all of which this work produces.

### O25.2 What is emphatically NOT built in Part O

- Objective function implementation, weights, or tuning (H8.4).
- Search, heuristics, CP/MIP models, solver integration (H8.5).
- Shadow finder / bundling **search and ranking** (H5). *(Overlap **detection** is built —
  it is deterministic set intersection, not search.)*
- Ranked plan options and their comparison scoring (H8.6).
- Learned duration models and estimate calibration (H11).
- Automatic re-planning proposals after disruption (only the *queueing* of affected blocks
  is built; proposing the new plan is the optimiser's job).

### O25.3 The frozen interface

The optimiser, when it arrives, plugs in without changing anything built here.

**It consumes** (already produced by this work):

| Source                        | Content                                                    |
| ----------------------------- | ---------------------------------------------------------- |
| `plan.commands` (Kafka)       | planning-run requests                                       |
| `demand.events`               | the full structured demand set                              |
| Operational DB (read)         | demands, network, traction, resources, bookings, calendars  |
| `db.domain.topology.expand()` | derived unavailability (deterministic, shared)              |
| `db.domain.conflicts.detect()`| conflict facts (deterministic, shared)                      |
| `db.domain.impact_l1`         | detention arithmetic                                        |
| `block_actuals` + `DurationStats` | history for calibration                                 |

**It produces** (already consumed by this work):

```json
// topic: optimization.results
{ "planning_run_id": "…", "horizon": {"from": "…", "to": "…"},
  "weights_version": "…",
  "options": [
    { "option_id": "…", "score": 0.82,
      "components": {"detention": …, "backlog": …, "utilisation": …},
      "blocks": [ { "demand_ids": ["…"], "window": {"from":"…","to":"…"},
                    "segments": ["…"], "rationale": "…" } ],
      "binding_constraints": [ {"rule": "H-07", "text": "…"} ],
      "rejected_alternatives": [ {"summary": "…", "reason": "…"} ] } ] }
```

The Read Store already has a place for these (`PlanSummary`, `Decision.options`), the
approval screen already has the panel, and the map already has a "proposed" style. When
the optimiser ships, those surfaces light up with **no changes to the write path, the read
path, the map or the field app**.

### O25.4 The rule that keeps this honest

Until an optimiser exists, **no screen may imply that one does**. Empty option lists render
as "optimiser not enabled — suggestions below are rule-based only". Overstating machine
intelligence is precisely the failure mode S-93 warns about, and it is easier to avoid at
the start than to walk back later.

---

## O26. Closing note on Part O

Part O adds nothing to the argument of Parts A–N. It only makes them buildable.

Three things are worth restating, because they are the ones most likely to be traded away
under time pressure and most expensive to recover afterwards:

1. **Truthful topology with honest confidence flags.** Every derived conclusion the system
   presents — what else becomes unusable, whether single-line working is possible, how
   wide the isolation must be — is only as good as the graph beneath it. A confident
   answer from an unverified graph is worse than no answer.
2. **Actuals capture that costs the field user nothing.** If reporting what happened takes
   more than two minutes, it will not happen, and the system will never learn. Every other
   ambition depends on this one unglamorous screen.
3. **A map that is dynamic and clear at the same time.** Dynamism without clarity is a
   light show; clarity without dynamism is a printout. The settlement between them —
   the level-of-detail contract, the token system, the label budget, focus-not-hide, and
   loud honesty about staleness — is the difference between a map a controller trusts at
   03:00 and one they close.

Build in that order, and the optimiser — when it is finally written — will have something
true to reason about.

---
# block-planner backend — handoff for frontend integration

This document explains what's been built so far, why it's shaped the way it
is, and everything you need to start wiring a frontend against it. It's a
snapshot, not a living doc — for anything that changes after this is
written, `CLAUDE.md` at the repo root is the authoritative, continuously
updated source (it has the full decision history, every verification run,
and every gotcha discovered along the way). Read this first for the shape
of the system; go to `CLAUDE.md` when you need the "why" behind a specific
design choice or a deeper dive into the scheduling algorithms themselves.

## 1. What this system does

SIH 26027: railway maintenance blocks. Three departments (Engineering,
S&T, Traction) need to close sections of track to do maintenance work.
Today they each grab track time independently, which wastes capacity. This
project demonstrates that a shared, coordinated schedule — computed by a
constraint solver — beats the uncoordinated status quo, on a synthetic but
realistic 100km double-track railway section over a 30-day planning
horizon.

Concretely, the backend:
1. **Generates** a synthetic problem instance (track layout, train
   timetable, a backlog of maintenance jobs) from a seed.
2. **Schedules** it three different ways — a greedy uncoordinated baseline,
   and two variants of a CP-SAT solver that coordinates across departments
   (one using ground-truth job priorities, one using an ML-predicted
   priority).
3. **Validates** every schedule independently against physical feasibility
   rules (no double-booked track, no train/maintenance conflicts, etc.).
4. **Persists** everything to Postgres and serves it over a REST API.

The frontend's job is to let a user pick a scenario, kick off runs, watch
them complete, and visualize/compare the resulting schedules — most
importantly as a Gantt-style chart of possessions and jobs, plus
side-by-side metric comparisons against the baseline.

## 2. Repo layout

```
src/            the scheduling pipeline itself (pure Python + pandas + OR-Tools + LightGBM)
  config.py       every tunable constant -- single source of truth
  data_gen.py     synthetic section/trains/jobs/windows generator
  baseline.py     greedy uncoordinated scheduler
  solver.py       CP-SAT coordinated scheduler
  model.py        LightGBM job-priority classifier
  check.py        independent feasibility validator (runs against ANY schedule)

api/            FastAPI backend exposing src/ over HTTP + Postgres persistence
  main.py         app entry point, CORS, /health
  config.py       env vars (DATABASE_URL, SOLVE_TIME_LIMIT, MODEL_PATH)
  schemas.py      Pydantic request/response models
  routers/        thin HTTP layer (scenarios.py, runs.py)
  services/       real logic (persistence.py, solve_runner.py, transform.py)
  models/         SQLAlchemy ORM (tables.py, database.py) + Alembic migrations
                  -- NOT the same as the repo-root models/ dir below

scripts/
  run.py          batch CLI: run data_gen -> baseline/solver -> check over many seeds
  seed_demo.py    provisions fixed named demo scenarios, pre-solved (see §7)

models/         joblib artifact for the trained priority classifier (mounted into the container)
tests/          pytest suite for src/
docker-compose.yml, Dockerfile   the whole stack: api + postgres
CLAUDE.md       full project history / decisions / verified findings (long, detailed)
```

**Important distinction**: `api/models/` is SQLAlchemy ORM code
(`tables.py`, `database.py`). The repo-root `models/` is a directory
holding the trained ML model's `.joblib` file. Same word, unrelated
things — don't confuse them when navigating.

## 3. Domain concepts you need to know

- **Job**: one maintenance task. Belongs to a department (Engineering /
  S&T / Traction), sits on one `segment` (of 20, each 5km) and one `line`
  (Up/Down), has an `estimated_duration_min`, and a `priority_class`
  (`Critical` / `High` / `Medium` / `Low`).
- **Backlog vs in-horizon jobs**: the job list isn't a clean slate. Some
  jobs are already overdue at day 0 (`day < 0`, id prefix `BKL-`); others
  arrive during the 30-day horizon (`day >= 0`).
- **Window**: maintenance can only happen inside two daily permitted
  windows — a 180-minute night window and a shorter 90-minute midday
  window, same clock times every day, section-wide.
- **Possession**: the actual unit that gets granted. A possession blocks
  one line over a contiguous range of segments for the full span of one
  window instance — no train can enter that range for that whole span.
  Multiple jobs can share one possession if they're on different segments
  within its range. **This is the central coordination mechanism**: the
  uncoordinated baseline gives every job its own possession (wasteful —
  it blocks a whole window slot for just one job's segment); the solver
  packs multiple jobs into shared possessions. The demonstrated win is
  mostly "far fewer possessions for the same work," not "faster
  scheduling."
- **Approach**: one of three ways to produce a schedule for a given
  scenario —
  - `baseline`: greedy, each department schedules independently, no
    coordination.
  - `solver_gt`: CP-SAT solver, using each job's true `priority_class` as
    the optimization weight.
  - `solver_ml`: CP-SAT solver, using an ML-predicted `priority_class`
    instead of the ground truth (the realistic case — in production you
    wouldn't have ground-truth priority, you'd have a model's guess).
- **Scenario**: a named, reproducible problem instance — a seed plus
  `backlog_size`/`jobs_per_day` parameters. The same scenario can have
  multiple runs (one per approach) so they're directly comparable.

## 4. Data model (Postgres, via SQLAlchemy)

Three tables, `Scenario` (1) → `Run` (many) → `Result` (1:1):

```python
class Scenario:
    id, name, seed, backlog_size, jobs_per_day, horizon_days, created_at

class Run:
    id, scenario_id, approach, status, solve_time_limit, solve_time_actual,
    solver_status, error_message, created_at, completed_at

class Result:
    id, run_id, schedule_json, possessions_json, metrics_json,
    validation_violations_json, unscheduled_json   # all JSONB
```

```python
Approach = "baseline" | "solver_gt" | "solver_ml"
RunStatus = "pending" | "running" | "complete" | "failed"
```

A `Scenario` row alone is just parameters — no schedule exists until a
`Run` is created and solved. A `Run` moves through
`pending -> running -> complete` (or `-> failed`) and only gets a `Result`
row once it reaches `complete`. **The frontend never queries the ORM
directly — this is just useful background for understanding the JSON
shapes the API hands back.**

## 5. How a run actually executes (background jobs, no task queue)

There's deliberately no Celery/Redis/worker process here — it's a
single-node hackathon demo. `POST /scenarios/{id}/runs` creates the `Run`
row (`status: pending`) and hands the actual work to FastAPI's
`BackgroundTasks`, which runs it in a worker thread automatically (since
the background function is a plain synchronous function, not `async def`)
— so the API keeps responding to other requests (including polling the
very run you just started) while a CP-SAT solve is in flight for up to 60
seconds.

The background function (`api/services/solve_runner.py::run_scenario`)
does, in order: set status to `running` → regenerate the scenario's data
from its stored seed/params → run the requested approach → validate the
result → save schedule/possessions/metrics/violations → set status to
`complete`. If *anything* in that chain throws, it's caught and the run is
marked `failed` with the exception message — a run can never be left
stuck in `running`.

**This means the frontend must poll.** There is no websocket/SSE push.
Flow for the frontend:
1. `POST /scenarios/{id}/runs` → get back `{id, status: "pending"}` immediately.
2. Poll `GET /runs/{id}` (cheap, metadata-only) until `status` is
   `complete` or `failed`. A sensible interval is 1-2s; a `solver_gt`/
   `solver_ml` run can take up to `SOLVE_TIME_LIMIT` (60s by default),
   `baseline` finishes in well under a second.
3. Once `complete`, fetch `GET /runs/{id}/schedule` and/or
   `GET /runs/{id}/metrics` for the actual payload.
4. If `failed`, `GET /runs/{id}` includes `error_message`.

## 6. API reference

Base URL when running via docker-compose: `http://localhost:8000`. CORS is
open to `http://localhost:*` and `http://127.0.0.1:*` (any port) — a
frontend dev server on any local port will work without extra config; no
other origins are allowed (no auth either — this is demo-scope only, don't
build in front of it as if it were production-hardened).

### `GET /health`
Liveness + whether the ML model actually loaded.
```json
{"status": "ok", "version": "0.1.0", "model_loaded": true}
```

### `GET /scenarios`
List every scenario with each approach's most recent run status. Cheap,
no payloads — good for a scenario picker's initial load.
```json
[
  {
    "id": 3,
    "name": "Standard section",
    "seed": 42,
    "runs": {"baseline": "complete", "solver_gt": "complete", "solver_ml": "complete"}
  }
]
```
`runs` always has all three approach keys; value is `null` if that
approach has never been run on this scenario.

### `POST /scenarios`
Create a scenario (parameters only — **no data is generated yet**, that
happens lazily the first time a run against it executes).
```json
// request
{"name": "My scenario", "seed": 123, "backlog_size": 240, "jobs_per_day": 2.5}
// backlog_size / jobs_per_day are optional, default from src/config.py
// name and seed are required

// response  200
{"id": 6}
```

### `POST /scenarios/{scenario_id}/runs`
Kick off a run. Returns immediately — does not wait for the solve.
```json
// request
{"approach": "solver_ml", "solve_time_limit": 60}
// approach: "baseline" | "solver_gt" | "solver_ml"  (required)
// solve_time_limit: optional seconds, ignored for baseline, defaults to
// SOLVE_TIME_LIMIT (60) if omitted for a solver approach

// response  200
{"id": 17, "status": "pending"}
```
`404 {"detail": "scenario not found"}` if `scenario_id` doesn't exist.

### `GET /runs/{run_id}`
Status metadata only — never the schedule payload (poll this, not
`/schedule`, while waiting).
```json
{"status": "complete", "solver_status": "FEASIBLE", "solve_time_actual": 60.09, "error_message": null}
```
`status`: `pending` | `running` | `complete` | `failed`.
`solver_status`: OR-Tools status string (`"FEASIBLE"`/`"OPTIMAL"`/etc.) for
solver approaches, literal `"N/A"` for baseline, `null` before completion.
`404` if `run_id` doesn't exist.

### `GET /runs/{run_id}/schedule`
The full Gantt data source. **404** if the run doesn't exist, **409**
`{"detail": "run is <status>, not complete"}` if it exists but hasn't
finished — use this to distinguish "wrong id" from "still solving" in the
UI.
```json
{
  "possessions": [
    {"id": "POSS-001-primary-Down-5", "line": "Down", "start_segment": 5, "end_segment": 8, "start_min": 1500, "end_min": 1680}
  ],
  "jobs": [
    {
      "id": "BKL-0001", "possession_id": "POSS-004-primary-Down-6", "segment": 6, "line": "Down",
      "department": "Engineering", "priority_class": "Medium",
      "start_min": 5920, "end_min": 6000, "wait_days": 4, "duration_min": 80
    }
  ],
  "unscheduled": [
    {"id": "BKL-0000", "segment": 14, "department": "Traction", "priority_class": "High"}
  ]
}
```
Notes for rendering:
- `start_min`/`end_min` are integer minutes from horizon start (day 0,
  minute 0) — divide by 1440 for day index, mod 1440 for clock time within
  the day.
- Every scheduled job's `possession_id` always points at an entry in
  `possessions` (verified: 0 unmatched in every test run) — a job's
  segment always falls inside its possession's `[start_segment,
  end_segment]` range and its time window inside the possession's.
  Multiple jobs can share one `possession_id`.
- `unscheduled` jobs have no `start_min`/`end_min`/`line`/`possession_id`
  at all — they never got placed. Show them separately (e.g. a "did not
  fit" list), not on the Gantt timeline.
- `wait_days` is how many days the job waited to start, relative to when
  it became actionable (report day, floored at horizon start) — the
  metric this project treats as the fair scheduler-behavior signal (see
  §8 for why, vs. the more naively-obvious `delay_days`, which isn't
  exposed per-job on this endpoint, only aggregated in `/metrics`).
- Response sizes are real payloads: ~60-70KB for a full scenario (hundreds
  of jobs/possessions). Fast though — verified 20-40ms server-side.
  Fine to fetch whole and render client-side; no pagination.

### `GET /runs/{run_id}/metrics`
Just the metrics dict, small and fast — poll/fetch this independently of
the schedule if you just need summary numbers. Same 404/409 rules as
`/schedule`.
```json
{
  "jobs_unscheduled": 76,
  "n_possessions": 83,
  "line_blocked_min": 68490.0,
  "total_job_duration_min": 22075.0,
  "weighted_wait": 8550.89,
  "wait_days": {"Critical": 7.47, "High": 9.38, "Medium": 13.28, "Low": 10.09},
  "mean_delay_days": {"Critical": 71.53, "High": 57.12, "Medium": 40.86, "Low": 24.8}
}
```
`wait_days`/`mean_delay_days` are keyed by `priority_class`. This exact
key set is a contract other code relies on — don't expect fields to
disappear, new ones may be added over time without a version bump.

### `GET /scenarios/{scenario_id}/comparison`
Metrics for every **complete** run on a scenario, keyed by approach, plus
`baseline`-relative percentage differences.
```json
{
  "scenario_id": 3,
  "metrics": {
    "baseline":  { "...": "full metrics dict, same shape as /metrics" },
    "solver_gt": { "...": "..." },
    "solver_ml": { "...": "..." }
  },
  "comparison_to_baseline": {
    "solver_gt": {
      "n_possessions": -59.53,
      "weighted_wait": -1.95,
      "wait_days": {"Critical": -0.84, "High": -9.78, "Medium": 15.06, "Low": -5.38},
      "...": "one entry per metric key, recursing into dict-valued ones"
    },
    "solver_ml": { "...": "..." }
  }
}
```
Percentage diff sign convention: **negative = lower than baseline**
(no "good"/"bad" judgment baked in — e.g. a negative `n_possessions` is an
improvement, a negative `weighted_wait` is an improvement, but a negative
`total_job_duration_min` wouldn't necessarily be — the frontend/consumer
decides what "better" means per metric). A metric entry is `null` if the
baseline value was `0`/`NaN` (percentage change against nothing is
undefined). **If `baseline` was never run on this scenario**,
`comparison_to_baseline` for every solver approach is the literal string
`"baseline has not been run for this scenario"` instead of a number —
check for a string vs. an object before rendering. `404` for an unknown
`scenario_id`; no 409 here (it just reports whatever complete runs exist,
possibly none).

### `GET /scenarios/{scenario_id}/summary`
Scenario parameters + everything `/comparison` returns, in one call — use
this for a scenario-picker/detail view instead of two round trips.
Verified fast: 16-98ms.
```json
{
  "id": 3, "name": "Standard section", "seed": 42,
  "backlog_size": 240, "jobs_per_day": 2.5, "horizon_days": 30,
  "metrics": { "...": "same as /comparison" },
  "comparison_to_baseline": { "...": "same as /comparison" }
}
```

## 7. Demo data already seeded — use this to start building today

You don't have to create scenarios or wait 60 seconds for anything —
`scripts/seed_demo.py` has already pre-solved three fixed, named
scenarios against the live stack (all 9 runs `complete`, 0 validation
violations). As of this writing:

| scenario_id | name             | seed | backlog_size | notes |
|---|---|---|---|---|
| 3 | Standard section | 42 | 240 | the main demo case |
| 4 | Heavy backlog    | 42 | 480 | worse maintenance debt |
| 5 | Light load       | 42 | 60  | lighter load |

Each has three `complete` runs (`baseline`, `solver_gt`, `solver_ml`) —
try e.g. `GET /scenarios/3/summary` or `GET /runs/8/schedule` (scenario
3's `baseline` run) right now. Run ids for scenario 3 are 8/9/10
(baseline/solver_gt/solver_ml respectively) as of this writing, but
**don't hardcode run ids in the frontend** — always resolve them via
`GET /scenarios/{id}` or `/summary`'s parent list, since re-running or
reseeding will create new ones. If this data ever looks stale or
inconsistent, `docker compose exec api python -m scripts.seed_demo` is
idempotent and safe to rerun (it skips anything already `complete`).

## 8. Things worth knowing before you build the UI

- **Not every solver run beats baseline.** This is a real, measured
  finding (see `CLAUDE.md`), not a bug: across a 30-seed batch,
  `n_possessions` improves in 30/30 seeds (the reliable win — lead with
  this), but `weighted_wait` only improves in ~21/30 seeds. Don't build a
  UI that assumes green-across-the-board; a comparison view should be
  able to show a metric getting worse without looking broken.
- **Solver `solver_status` is usually `"FEASIBLE"`, not `"OPTIMAL"`** —
  CP-SAT runs out of its time budget before proving optimality at this
  problem size. That's expected, not an error state.
- **`wait_days` vs `mean_delay_days`**: `wait_days` isolates scheduler
  behavior (relative to when a job became actionable); `mean_delay_days`
  is relative to the job's original report day, which confounds
  scheduler behavior with how overdue the job already was at day 0. If
  you show only one of these two in a headline UI, use `wait_days`.
- **Runs aren't bit-for-bit reproducible** for `solver_gt`/`solver_ml`
  (parallel search, wall-clock cutoff) — rerunning the same scenario/
  approach can give slightly different numbers. `baseline` is fully
  deterministic.
- **`jobs_unscheduled`** isn't a failure — jobs can legitimately not fit
  in the horizon given gang/window capacity. It's a first-class metric to
  display, and the specific unscheduled jobs are in `/schedule`'s
  `unscheduled` list.

## 9. Running the stack locally

```
docker compose up -d --build        # starts api (:8000) + postgres (:5432)
curl localhost:8000/health          # sanity check
docker compose exec api python -m alembic -c api/alembic.ini upgrade head   # if migrations aren't applied yet
docker compose exec api python -m scripts.seed_demo   # populate the 3 demo scenarios (idempotent)
```
`src/`, `models/`, and `scripts/` are volume-mounted into the container —
editing them locally takes effect without a rebuild. `api/` is baked into
the image at build time, so changes there need `docker compose up -d --build`.

## 10. Where the source of truth actually lives

This document is a snapshot for onboarding. For anything authoritative —
exact function signatures, every verified numeric finding, the full
reasoning behind design decisions, migration history — go to `CLAUDE.md`
at the repo root. It's organized chronologically by feature phase and is
kept in sync with the code as it changes; this document is not
guaranteed to be.
