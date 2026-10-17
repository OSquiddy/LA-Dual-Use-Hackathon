# HandoffProof — Build Plan & Judge Defense

Oct 17, 2026 · @Mohammed Omar Siddiqui

## Overview

HandoffProof makes sure every resident report in a crisis has an owner: a case is not handled until a named person accepts it, and evidence of danger — not a timer — decides what reaches the supervisor.

**Tagline:** An emergency isn't handled until someone accepts responsibility.

**Track and seat:** Communication (Retell AI) · the overnight supervisor of a city call line during a storm.

**The problem.** Reports get passed between departments, closed without the work being done, or stall because everyone assumes someone else has them. During the January 2023 storms, a City Council motion described MyLA311 tickets [closed or cancelled while the problem was still unresolved, and residents unsure whether their request reached the right department](https://cd1.lacity.gov/press-releases/councilmember-hernandez-introduces-motion-address-storm-related-city-service). In March 2026 a council committee [approved a motion asking for reports on ongoing MyLA311 problems, completion rates and backlogs](https://cityclerk.lacity.org/onlinedocs/2026/26-0162_rpt_pw_3-25-26.pdf).

**The product in one breath.** Related resident calls are linked into one emerging incident. Each case shows what is still missing (its "debt list"). It is sent to a department that must tap Accept. If nobody accepts, a Retell voice agent calls the resident back to ask whether it is getting worse. Worsening, unowned cases jump to the supervisor; silence never closes a case.

**Bigger vision.** Disasters get worse at handoffs. The same engine applies to a container passed between carrier, customs and terminal, a battery alert passed between fleet and utility, or a harbor contact passed from robot to watch officer.

|  | Who | Their day |
| --- | --- | --- |
| Crisis customer | Overnight supervisor, city call line | Storm night: hundreds of drain, flood and road reports, too few staff |
| Ordinary-day customer | City 311 / service-request manager | Any weekday: pothole and drain tickets bounced between departments |
| Third customer | Utility or property manager after-hours line | Outage and leak calls that must not stall between teams |

## How it works

A case climbs only on evidence of danger, never on age alone; every case gets an owner by default, and silence raises priority instead of closing it.

&#91;embedded content: case flow · 6 steps, 2 decisions\]

Related reports become one incident with a debt list; if no one accepts it, a default owner is assigned and the resident is called back, and only a worsening or unanswered case reaches the supervisor.

**The escalation ladder (one case)**

| Step | Trigger | What happens |
| --- | --- | --- |
| 1. Assigned | Incident created | Sent to the department, which must tap Accept |
| 2. Nudge | Not accepted within X minutes | Reminder to the department queue |
| 3. Default owner | Still not accepted | Assigned to that department's on-call person for the area |
| 4. Callback | Still not acted on | Retell agent calls the resident: "Is it worse? Is anyone in danger?" |
| 5. Supervisor | Answer is worse, danger words, or no answer on a high-risk case | Ranked into the supervisor's top 10 with a one-line reason |

**Why tickets don't pile up at the top**

- Only risk climbs; a pothole nobody accepted stays at steps 2–3.
- Every case has a named default owner by step 3.
- Related reports merge into one incident, so 20 calls become one item with 20 witnesses.
- The supervisor sees a ranked, capped list, not the whole backlog.
- If a whole department stops accepting, one department-level alert replaces hundreds of ticket alerts.

**Never automated**

- Closing a case — only the person who did the work, or the resident confirming it's fixed.
- Deciding someone is safe because they didn't answer.
- Dispatching emergency services or replacing 911.
- Issuing or lifting any official order.

## Architecture and tech stack

Retell handles every phone call; a small backend owns linking, the debt list and escalation, so every decision is transparent and auditable.

&#91;embedded content: architecture · voice layer, backend, two views\]

Residents talk only to Retell; call results arrive as webhooks, the escalation engine decides, and departments accept cases from their queue while the supervisor sees the ranked list.

**Stack (pick what the team already knows)**

| Layer | Choice | Why |
| --- | --- | --- |
| Voice | Retell AI: one inbound intake agent, one outbound callback agent | Sponsor tool; free credit covers the demo |
| Backend | Python FastAPI (or Node/Express) | Fast to write webhooks and timers |
| Database | SQLite (or Supabase if the team prefers hosted) | Zero setup; enough for a demo |
| AI | LLM call for extraction cleanup and report linking; Retell post-call analysis for structured fields | Keeps AI where the input is messy |
| Frontend | React or Next.js with polling or websockets | Live queue without refresh |
| Hosting | Local + a tunnel (ngrok or Cloudflare Tunnel) for Retell webhooks | Retell needs a public URL |
| Build tool | IBM Bob for all coding sessions | Required evidence for the Bob prize |

**Data model**

| Table | Key fields |
| --- | --- |
| reports | id, call\_id, phone, location\_text, lat/lng, hazard\_type, danger\_words, transcript, created\_at |
| incidents | id, area, hazard\_type, report\_ids, risk\_score, status (open / accepted / escalated / closed) |
| debts | incident\_id, kind (location, caller\_unreachable, no\_owner, no\_update), opened\_at, cleared\_at |
| assignments | incident\_id, department, owner, assigned\_at, accepted\_at, default\_owner\_at |
| callbacks | incident\_id, phone, attempt\_no, outcome (worse / same / better / no\_answer), called\_at |
| events | incident\_id, type, reason, at — the audit trail shown in "why it's here" |

**Retell integration (verify each against Retell's current docs)**

1. Intake agent: prompt asks for location, what's happening, anyone in danger; post-call analysis returns those as structured fields.
2. Webhook on call completion posts the fields and transcript to the backend, which creates a report and runs the linker.
3. Callback: the backend starts an outbound call with the case's location and hazard passed as dynamic variables.
4. The callback agent asks one question set (worse / same / better / danger); its post-call result updates the case.
5. No answer or voicemail detected = outcome no\_answer; our own timer handles retries rather than relying on warm transfer.

**Escalation rules (start here, tune on seed data)**

- Link two reports if within about 300 m and 60 minutes with a compatible hazard.
- Risk score rises with danger words, number of linked reports, "worse" answers and failed callbacks; it never falls because of silence.
- Supervisor queue = top 10 by risk score among unaccepted or worsening incidents.

## Build plan

The MVP is one storm night in one LA neighborhood, end to end: three intake calls, one linked incident, one unaccepted handoff, one live callback, one supervisor alert. Everything else is cut until that works.

**MVP scope (must work live on stage)**

1. Retell inbound agent takes a resident report and returns structured fields (location, hazard, danger words, callback number).
2. Backend links related reports into one incident (same area + compatible hazard within a time window).
3. Each incident keeps a debt list: missing location detail, caller unreachable, no owner yet.
4. Department queue with an Accept button and a default on-call owner after a timeout.
5. Retell outbound callback to the resident when a case sits unaccepted; the answer (worse / same / better / no answer) updates the case.
6. Supervisor queue: top 10 by danger, each with a one-line "why it's here."
7. Department-silence detector: "Street Services accepted 0 of 12 in the last hour."
8. Twist toggles panel (see Demo script).

**Team roles (assumes 3 people)**

| Person | Owns | First deliverable |
| --- | --- | --- |
| A — Voice + pitch | Retell agents (intake + callback), webhooks, phone numbers; then demo script, slides, funding slide | A test call that lands as JSON in the backend |
| B — Engine | Case model, linking rules, debt list, escalation ladder, timers, seed scenario | Escalation rules passing on seeded data |
| C — Dashboard + Bob evidence | Supervisor + department views, twist toggles, IBM Bob session screenshots and usage statement | Live queue that updates without refresh |

Everyone rehearses Q&A on Sunday morning; A leads the pitch, B answers technical questions, C drives the demo.

**Weekend schedule (adjust to the event's actual deadline)**

- [ ] Sat first 2 hours — repo set up in IBM Bob; Retell account, number and free credit; data model agreed; seed scenario written.
- [ ] Sat by noon — inbound intake call lands in the backend; cases render on the dashboard.
- [ ] Sat afternoon — linking, debt list, Accept button, default owner, supervisor queue.
- [ ] Sat evening — outbound callback loop working end to end; escalation on "worse" and on no-answer.
- [ ] Sat night — department-silence detector; twist toggles; first full dry run.
- [ ] Sun morning — polish, fallback recordings, rehearse Q&A, freeze code 2 hours before judging.
- [ ] Sun before judging — three full rehearsals of the 3-minute demo.

**Cut list (only if time remains, in this order)**

1. Multilingual callback (Spanish first).
2. Map view of incidents.
3. Second-domain demo for a twist (ports or energy handoff).
4. Physical water-level sensor — skip unless someone has already used an ESP32.

**Rules of thumb:** build on seeded data first, then wire live calls; never let the demo depend on something you have not run three times.

## Demo script

The demo is 3 minutes and climaxes on one live phone call where a resident says "it's worse" and an unowned case turns red on the supervisor's screen.

| Time | On screen | What we say |
| --- | --- | --- |
| 0:00–0:20 | Title slide, LA 2023 storm headline | "In the 2023 storms, LA residents saw 311 tickets closed while the problem was still there. Nobody failed to answer — nobody accepted." |
| 0:20–0:50 | Three intake calls (one live, two pre-seeded): blocked drain, water across the road, car stalled | "Three different reports. HandoffProof links them into one emerging flood on one street." |
| 0:50–1:20 | Incident card with its debt list; sent to Street Services; Accept timer running | "It shows what's still missing: exact location, one caller dropped, and no owner yet." |
| 1:20–2:00 | Timer expires; live Retell callback on speaker; resident (teammate) says the water is at the curb and rising | "Nobody accepted, so we ask the person who's there. Silence never closes a case." |
| 2:00–2:30 | Case jumps to the top of the supervisor queue, red, with its reason line | "Unowned, worsening, caller unreachable. The supervisor sees one case, not 500." |
| 2:30–3:00 | Toggle a twist: Street Services goes silent; one department-level alert appears | "When a whole department goes quiet, we flag the department, not every ticket. Same engine works for any handoff." |

**Twist toggles to pre-build**

- **Department goes silent** — acceptance rate drops to zero; the department alert fires.
- **Call surge** — 50 seeded calls arrive; linking collapses them into a few incidents.
- **Network or phones down** — callbacks fail; failed attempts raise priority instead of closing.
- **New domain** — swap the seed file so the "case" is a container or a battery alert; the ladder runs unchanged.

**Fallbacks (have all three ready)**

1. A recorded video of the full demo, captured Saturday night.
2. A "simulate callback" button that plays a recorded answer if the live call fails.
3. Seeded data so the dashboard tells the story even with no calls at all.

## Pitch and funding pathway

The pitch has six beats and leads with the LA story, not the technology.

1. **Hook** — "Disasters get worse at handoffs, where everyone thinks someone else has it."
2. **LA evidence** — 2023 storm tickets closed unresolved; 2026 council committee still asking about MyLA311 backlogs.
3. **Insight** — Systems track status (sent, closed). We track ownership (accepted by whom) and evidence (is it getting worse).
4. **Live demo** — the 3-minute script above.
5. **Dual use** — ordinary weekday 311 tickets; storm night surge; any handoff (ports, grid, harbor).
6. **Path forward** — funding slide, then a pilot ask: one LA council district during the next storm season.

**Federal funding pathway (slide for the twist)**

| Stage | Federal source | Who applies | Status |
| --- | --- | --- | --- |
| Research and prototype (primary) | NSF SBIR Phase I, up to $305K | Our company, after incorporating | Project Pitch first; realistic full-proposal deadline Mar 4, 2027 |
| City purchase and rollout | FEMA Homeland Security Grant Program (UASI / SHSP) | City or County of LA buys us as a vendor | FY2026 LA/Long Beach UASI about $28.1M, spendable to Aug 31, 2029 |
| Alternative R&D | DHS S&T SBIR, or DHS S&T Long Range BAA white paper | Our company | DHS SBIR topics expected Nov–Jan; LRBAA status unverified |

**How to frame it for each source**

- **NSF:** the research question is "verifiable, calibrated escalation from noisy, multilingual resident evidence" — how a system decides what deserves a human when reports are partial and callers drop.
- **City (UASI):** fits "public information and warning" and "operational communications"; strictly non-emergency side, never a 911 replacement.
- **Say "eligible pathway," not "funded."**

## Judge Q&A defense

Every answer is one or two sentences; practise them out loud until each takes under 15 seconds.

**Novelty and prior art**

- **"Isn't this just PagerDuty or ServiceNow?"** — Those escalate on a timer for IT staff who already own the system. We escalate on evidence from the public — a resident callback saying it's worse — and silence raises priority instead of closing the case.
- **"Cities already have AI 311 agents."** — Yes (Citibot, Polimorphic, Salesforce). They answer the call. We handle what happens after it: making sure someone accepts it.
- **"Isn't linking calls already done?"** — Grouping identical calls exists in 911 (Carbyne). We link related-but-different reports — a drain, a road, a stalled car — into one emerging incident, and then require an owner for it.

**Safety and what's never automated**

- **"What if the AI misclassifies a real emergency?"** — Danger words always escalate, we over-flag on purpose, and we are the non-emergency side; anyone in immediate danger is told to call 911.
- **"What does the AI never do?"** — It never closes a case, never decides someone is safe because they didn't answer, never dispatches emergency services, and never issues or lifts an order.
- **"What if the resident doesn't pick up?"** — Retry, then text, then the case rises in priority. No answer is treated as more urgent, never as resolved.

**Escalation design**

- **"Won't everything pile up at the supervisor?"** — No. Only risk climbs, not age. Every case gets a default on-call owner, duplicates merge, and the supervisor sees a ranked top 10.
- **"What if nobody accepts anything?"** — That is a broken department, not 500 broken tickets. We raise one department-level alert and let the supervisor reassign in batches.
- **"Who is the default owner?"** — The department's named on-call person for that area, configured by the city. We don't invent owners.

**Feasibility and adoption**

- **"Would LA actually adopt this?"** — It sits beside MyLA311 as a layer reading tickets and writing acceptances; a pilot is one council district during storm season.
- **"Who pays?"** — The city, from homeland security grant money it already holds (spendable to 2029), with NSF SBIR funding our R&D.
- **"Privacy of residents' numbers?"** — We only call back the number the resident called from, about their own report, and store the minimum needed to close the case.
- **"Isn't Retell an odd fit for government?"** — Retell lists SOC 2 and HIPAA; the voice layer is swappable, and the ownership engine is the product.

**Dual use and twists**

- **"Who uses this on an ordinary day?"** — The 311 service-request manager whose pothole and drain tickets bounce between departments every weekday.
- **"How does this handle the twists?"** — Any new situation is a new kind of handoff. We swap the seed data and the same ladder runs — we can show it on a container or a battery alert.

**Technical**

- **"Where's the AI, really?"** — Extracting structured reports from messy speech, linking related reports, and reading the callback answer. The escalation rules are deliberately transparent so a human can audit every decision.
- **"How did you use IBM Bob?"** — Show the session summaries and the files Bob helped write.

## Do not claim, open questions, sources

The fastest way to lose credibility is one claim a judge can disprove; keep to these limits.

**Do not claim**

- "Nobody has ever built this" — say "we found no product that combines ownership tracking with evidence-based callbacks."
- That LA's current 311 system still has the exact 2023 problem — say the 2026 committee is still asking about MyLA311 performance.
- "FEMA will fund us" or any 911 / Next Generation 911 grant money — none is available to us.
- That we replace or touch 911 — we are the non-emergency side.
- Any accuracy number we have not measured ourselves.
- That the west Altadena evacuation orders were late — a May 2026 review found they were not delayed.

**Open questions to answer Saturday**

- [ ] Ask the Retell rep: has anyone used outbound callbacks to re-check unresolved city tickets?
- [ ] Confirm Retell outbound call, webhook and post-call analysis setup works on the free credit.
- [ ] Retell warm transfer has a known issue when the transfer hits voicemail — build our own timeout instead.
- [ ] Confirm the IBM Bob prize rules with the organizers (repo, session screenshots, usage statement).
- [ ] Decide team roles and who rehearses each Q&A category.

**Sources**

- [LA City Council District 1: motion on storm-related 311 service (Jan 2023)](https://cd1.lacity.gov/press-releases/councilmember-hernandez-introduces-motion-address-storm-related-city-service)
- [LA City Clerk 26-0162: Public Works Committee report on MyLA311 (Mar 2026)](https://cityclerk.lacity.org/onlinedocs/2026/26-0162_rpt_pw_3-25-26.pdf)
- [SBIR/STTR reauthorized after six-month lapse (Mondaq, Apr 2026)](https://www.mondaq.com/unitedstates/government-contracts-procurement-ppp/1774902/sbirsttr-programs-reauthorized-after-six-month-lapse)
- [Citibot AI voice agents](https://www.citibot.io/voice) · [Polimorphic AI for 311](https://www.polimorphic.com/use-cases/ai-for-smarter-311-services)
- Team research reports: *Open federal grants by track*, *Novel winning hackathon ideas* (UASI FY2026 amounts, NSF SBIR terms, Carbyne, Retell features).
