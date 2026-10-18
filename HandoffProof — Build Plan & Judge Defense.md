# HandoffProof — Build Plan & Judge Defense

Oct 17, 2026 · @Mohammed Omar Siddiqui

## Overview

HandoffProof is an AI-powered **incident intelligence and accountability** prototype: it links related resident reports, retains the original evidence, makes ownership and acceptance explicit, follows up with consenting callers, and surfaces dangerous changes to a human supervisor. Assigning a person does **not** mean that person has acknowledged, accepted, or resolved the work. A timer advances unanswered handoffs; physical-danger priority requires evidence or a defined high-risk safety rule.

**Tagline:** An incident isn't handled until someone accepts responsibility — and the evidence is still visible.

**Track and seat:** Communication (Retell AI) · an **illustrative, non-emergency** LA storm-response service desk and its overnight supervisor. **Hackathon demonstration only; not affiliated with or operating for the City of Los Angeles.**

**The problem.** Reports get passed between departments, closed without the work being done, or stall because everyone assumes someone else has them. During the January 2023 storms, a City Council motion described MyLA311 tickets [closed or cancelled while the problem was still unresolved, and residents unsure whether their request reached the right department](https://cd1.lacity.gov/press-releases/councilmember-hernandez-introduces-motion-address-storm-related-city-service). In March 2026 a council committee [approved a motion asking for reports on ongoing MyLA311 problems, completion rates and backlogs](https://cityclerk.lacity.org/onlinedocs/2026/26-0162_rpt_pw_3-25-26.pdf).

**The product in one breath.** Retell captures messy resident calls, and the backend connects related reports without erasing any witness account. Each incident shows a debt list and a visible handoff: **assigned → acknowledged → accepted → human-verified resolution/closure**. Unaccepted cases are nudged or offered a *consent-gated* callback. A newly reported danger or independently high-risk unanswered case reaches a human supervisor; a missed call creates uncertainty, **not proof of physical deterioration**. The dashboard shows both a ranked top 10 and an always-visible critical-alert lane.

**Bigger vision / dual use.** Handoffs fail both on ordinary weekdays and under crisis pressure. The MVP serves fictional municipal 311-style reports and a storm-night surge. The same **software** pattern could later apply to shipping/port logistics, utility restoration, and public-safety or defense support workflows where an accountable human must accept an evidence-backed handoff. Those integrations are future uses, **not features demonstrated as deployed**. **No wireless sensing, ESP32s, sensors, or autonomous dispatch in this MVP.**

|  | Who | Their day |
| --- | --- | --- |
| Crisis customer | Overnight supervisor, city call line | Storm night: hundreds of drain, flood and road reports, too few staff |
| Ordinary-day customer | City 311 / service-request manager | Any weekday: pothole and drain tickets bounced between departments |
| Third customer | Utility or property manager after-hours line | Outage and leak calls that must not stall between teams |

## How it works

The handoff ladder can advance on time, but **physical-danger prioritization is evidence-based**. A named on-call contact may be assigned by configuration, yet their acknowledgment/acceptance must still be recorded; an unknown on-call contact remains an explicit ownership debt and needs human attention. Silence never resolves a case or proves new danger.

&#91;embedded content: case flow · 6 steps, 2 decisions\]

Related reports become one incident **with separate, auditable original reports**. The engine tracks missing information and ownership transitions. An unattended handoff gets a reminder and a configured on-call assignment. An outbound callback requires a recorded `callback_ok=true`, an appropriate number, and approved live-call configuration. Worsening evidence or a previously high-risk, unreachable caller triggers a reasoned human-review alert.

**The escalation ladder (one case)**

| Step | Trigger | What happens |
| --- | --- | --- |
| 1. Assigned | Incident created | Route to a department; log `assigned_at` and any configured named contact. **Not accepted yet** |
| 2. Nudge | Not acknowledged/accepted within X minutes | Remind queue; log when a human acknowledges receipt (`acknowledged_at`) |
| 3. Default on-call contact | Still unaccepted | Assign configured on-call person; if none exists, keep `no_owner` debt and flag for human attention |
| 4. Consent-gated callback | Still unaccepted **and** the caller agreed | Retell checks "worse / same / better?" and "anyone in danger?"; without consent, do not place a call |
| 5. Supervisor review | New danger, confirmed worsening, or *existing high-risk* case with unresolved contact/ownership | Pin critical safety items separately from the ranked top 10; provide a one-line evidence-based reason |

**Why tickets don't pile up at the top**

- Unaccepted low-danger cases can continue through operational nudges without being mislabeled a high-danger emergency.
- A default contact is **proposed ownership**, not acceptance. Missing on-call configuration remains a visible blocker.
- Related reports combine into one incident **with each report, timestamp and transcript preserved**, so 20 calls can appear as one incident with 20 sources.
- The supervisor sees a ranked top 10 **plus a separate persistent critical-alert lane**; critical safety flags are never hidden by the ranking cap.
- A silent department produces one grouped department alert **without hiding genuinely critical incident alerts**.
- A failed call creates `caller_unreachable` / follow-up uncertainty, not an automatic assertion that flooding worsened.

**Never automated**

- Automatically closing a case, asserting work was completed, or calling an assignment "accepted" before explicit human acceptance. Resolution requires human evidence and an authorized human close action (or verified resident confirmation reviewed by a human).
- Deciding a resident is safe, or that conditions worsened, solely because they did not answer.
- Calling someone who did not explicitly authorize a follow-up or who opted out.
- Dispatching emergency services, replacing 911, promising city response, or issuing/lifting official orders.
- Presenting this fictional LA demonstration as an official city service; both agents identify themselves as a **prototype demo**.
- Treating a model-generated extraction as verified fact when the transcript is ambiguous; preserve an `unknown`/review path.

### Scope decision register (Oct 17, 2026)

| Decision | Current MVP commitment | Implementation status |
| --- | --- | --- |
| Evidence-linked incident intelligence | Retain every original call/report and show why linked | **Implemented (B4):** each report kept as its own row; link reason logged |
| Verifiable accountability | Assignment ≠ acknowledgment ≠ acceptance ≠ human-verified resolution | **Implemented** in engine and dashboard (Acknowledge, Accept, human-only Close) |
| Consented voice follow-up | Persist `callback_ok` and prohibit outbound requests without true consent | **Implemented and tested in simulation**; live outbound call not yet run |
| Safe triage | Worsening / reported danger is evidence; missed calls mean unknown; critical alerts never hidden by top 10 | **Implemented:** evidence-only risk, uncapped critical-alert lane |
| Software-only | No wireless sensing, sensors, ESP32, autonomous 911/dispatch | **Explicitly excluded** |
| Three people in parallel | PC-A voice; PC-B engine; PC-C dashboard; shared contract approval required | **Unchanged** |

### Accountability state semantics

- **Assigned:** a department or configured on-call person is nominated; no guarantee they have seen it.
- **Acknowledged:** a named human confirms receipt; **not equivalent to accepting responsibility**.
- **Accepted:** a named human explicitly takes responsibility via a recorded action.
- **Resolved:** evidence suggests corrective work is done; **only an authorized human** records resolution and closes the case. Existing `status=closed` remains the implementation representation until the team agrees on additional fields.
- **Unknown:** missing consent, missing location, unanswered call, or absent on-call mapping must remain visible as a debt, not silently interpreted as safe/resolved.

**Contract migration note:** Approved and implemented: `ReportIn.callback_ok`, `Assignment.acknowledged_at/by` and `accepted_by`, `POST /api/incidents/{id}/acknowledge`, `StateView.critical_alerts[]`, event `actor`/`evidence`, and masked phone numbers. Backend, TypeScript types, fixtures and contract tests were changed together. Live status by task is tracked in the *Parallel Build Plan* progress section.

## Architecture and tech stack

Retell handles every phone call; a small backend owns linking, the debt list and escalation, so every decision is transparent and auditable.

&#91;embedded content: architecture · voice layer, backend, two views\]

Demo callers speak to Retell; **verified** webhooks submit structured report data to the backend. The engine links evidence, computes explainable operational/risk signals, and records accountable transitions; humans acknowledge, accept, and close. The dashboard displays department queues, a ranked supervisor top 10, **and persistent critical alerts**. All calls use consenting test participants and fictional incident data.

**Stack (pick what the team already knows)**

| Layer | Choice | Why |
| --- | --- | --- |
| Voice | Retell AI: one inbound intake agent, one outbound callback agent | Sponsor tool; free credit covers the demo |
| Backend | Python 3.11 + FastAPI | Existing scaffold; deterministic event/audit engine, APIs and timers |
| Database | SQLModel + SQLite | Existing local demo; explicit reports, assignments, callbacks and audit history |
| AI | Retell post-call extraction; optional LLM for ambiguous text and linking candidates | AI proposes interpretations; deterministic safety checks and human review remain authoritative |
| Frontend | Vite + React, 1-second polling | Existing two-queue dashboard; add visible acknowledgment and critical-alert indicators |
| Hosting | Local + optional tunnel (ngrok / Cloudflare Tunnel) | Expose live webhook only **after signature verification**; otherwise use simulation |
| Development | VS Code/Codex or existing team tools | IBM Bob evidence only if pursuing the Bob award; verify award rules with organizers |
| Hardware | **None in MVP** | Wireless sensing, ESP32 and other physical sensors explicitly excluded |

**Data model**

| Table | Key fields |
| --- | --- |
| reports | id, call_id, phone (restricted), **callback_ok**, location_text, lat/lng, hazard_type, danger_words, transcript, created_at; report IDs remain distinct after linking |
| incidents | id, area, hazard_type, risk_score, status (open / accepted / escalated / closed), evidence-based review flags; linked reports remain separate rows |
| debts | incident_id, kind (location, caller_unreachable, no_owner, no_update, consent_unknown), opened_at, cleared_at |
| assignments | incident_id, department, owner, assigned_at, **acknowledged_at**, accepted_at, default_owner_at; a default owner is not an acceptance |
| callbacks | incident_id, phone (restricted), attempt_no, outcome (worse / same / better / no_answer), called_at, consent decision / delivery state |
| events | incident_id, type, reason, at, actor/source, evidence references — append-only "why it's here" trail |
| closure evidence | existing human-only close event plus who, when and verified note; any new schema requires shared-contract approval |

**Retell integration (verify each against Retell's current docs)**

1. **Phase 0 completed in Retell dashboard (manual/browser-level):** draft Intake and Callback agents and their 5 + 3 post-call extraction fields were tested. **This does not prove webhook or outbound API integration.**
2. Intake agent says it is a **hackathon demo**, asks location, hazard, anyone in danger, and explicitly requests callback permission (`callback_ok`). On immediate danger, directs callers to 911 rather than promising response.
3. A verifies the `x-retell-signature` on the **raw request body** before trusting any public `call_analyzed` webhook; check the live payload names and add replay/duplicate protection.
4. B must persist consent in the report/contract and gate any `request_callback()` call. No consent / unclear consent / missing number → no outbound call and an auditable reason.
5. Callback agent uses `{{location}}` and `{{hazard}}`, asks worse/same/better and safety questions, never claims a city response; its post-call outcome is saved with evidence source.
6. A maps no-answer/voicemail/dial-failure to `no_answer`; B treats it as **unknown status and contact debt**, not physical worsening. Retry only under the agreed consent and frequency limits.
7. Use synthetic numbers for seeds. Use real test-participant numbers only with permission; do not expose keys or full phone numbers in logs or demo screenshots.

**Escalation rules (start here, tune on seed data)**

- **Linking candidate:** within ~300 m and 60 minutes, compatible hazard groups; normalize speech variants (e.g. "Avenue fifty two") and retain the original reports. Never discard evidence because it was merged.
- **Physical-risk score, v1 candidate:** base hazard + verified danger phrases (+25) + corroborating independent reports (+5 each, capped at +25) + explicit worsening (+30); an explicit `same` adds no danger points. A confirmed improvement may reduce score only with evidence and never auto-close the case. Tune thresholds on seeds and test false positives.
- **Separate operational follow-up debt:** an unanswered call or unaccepted handoff increases *need for review*, but is **not evidence that physical conditions worsened**. Danger-word extraction must distinguish direct quotes and uncertain paraphrase.
- **Human supervisor:** keep top 10 ranked items plus **persistent critical safety alerts** that remain visible even outside the top 10; require a reason line and source evidence for each alert.
- **High-risk unanswered exception:** already-dangerous situations with failed contact remain critical due to their known risk and unresolved uncertainty, not because no-answer proves deterioration.
- **Safety gate:** no automatic emergency dispatch or official response; prompt directs people in immediate danger to 911.

## Build plan

The MVP remains **one fictional storm night in one LA neighborhood**: three intake reports, one linked incident with three retained sources, one visible unanswered handoff, one **consented** follow-up, and one human supervisor alert. Separately demonstrate that ordinary-day potholes/drains use the same software. Keep the three-person architecture and exclude wireless sensing/hardware and real city operations.

**MVP scope (must work live on stage)**

1. Retell Intake returns `location_text`, `hazard_type`, `danger_words`, `anyone_in_danger`, and **`callback_ok`**. Unclear/declined consent remains no-call.
2. Backend links compatible reports (area, hazard, time) **without losing individual reports**, timestamps, sources or original text.
3. Each incident tracks location/contact/ownership debts and an **evidence trail** explaining AI suggestions and human actions.
4. Department queue tracks **assigned → acknowledged → accepted** separately; a default on-call assignment does not equal acknowledgment.
5. Retell Callback contacts **only consenting test callers** when unresolved/unaccepted; worse/same/better/no-answer updates evidence and uncertainty without auto-closing.
6. Supervisor dashboard shows a ranked **top 10 plus always-visible critical alerts**, each with a plain-language reason and evidence source.
7. Department-silence detector groups operational handoff failures: "Street Services accepted 0 of 12 in the last hour."
8. Human-only closure with recorded actor and confirmation; neither model nor silence can close or declare safety.
9. Twist toggles support surge, department silence, phones down and a *simulated* second-domain handoff; none dispatches real services.

**Team roles (assumes 3 people)**

| Person | Owns | First deliverable |
| --- | --- | --- |
| A — Voice + pitch | Retell prompts, extraction fields, webhook verification, consent-aware callback API integration; demo and slides | A verified, idempotent test call creates a report with consent captured |
| B — Engine | Report/incident linking, consent persistence and gates, distinct ownership transitions, auditable evidence, escalation and seeds | Three storm reports → one incident; missing consent blocks callbacks; acceptance requires human action |
| C — Dashboard + evidence | Department and supervisor UI, acknowledgment/acceptance distinction, persistent critical alerts, twists, recording | Live dashboard shows incidents, evidence, ownership and critical alerts without refresh |

Everyone rehearses Q&A on Sunday morning; A leads the pitch, B answers technical questions, C drives the demo.

**Weekend schedule (adjust to the event's actual deadline)**

- [ ] Phase 0: three machines cloned; backend and frontend verified; coordinate shared consent/acknowledgment/critical-alert contract changes; retain Retell browser-test evidence and IDs privately; verify phone availability separately. *(Contracts ✅; two of three machines verified; phone number unconfirmed.)*
- [ ] Sat by noon: verified incoming call creates a consent-tagged report and live dashboard card (using simulated calls until the webhook is authenticated). *(Signed synthetic webhook ✅; real Retell call not yet.)*
- [x] Sat afternoon: linking preserves all source reports; debts, human Accept, acknowledgment state, and critical alert pane work.
- [ ] Sat evening: consent-gated real callback to an opted-in teammate; explicit `worse` escalates and `no_answer` never implies the hazard worsened. *(Engine rules ✅ in simulation; real callback not yet.)*
- [ ] Sat night: department-silence / surge / phones-down twists; first dry run; collect fallback recording. *(Twists ✅; dry run and recording not yet.)*
- [ ] Sun morning: fix glitches only, rehearse Q&A, freeze code 2 hours before judging.
- [ ] Before judging: three full rehearsals of the 3-minute demo. Verify the actual event schedule with organizers.

**Cut list (only if time remains, in this order)**

1. Multilingual callback (Spanish first).
2. Map view of incidents (illustrative locations only).
3. Second-domain scenario (ports or energy handoff) using **synthetic data and the same software engine**.

**Explicitly excluded from this hackathon MVP:** wireless sensing, ESP32s, sensor ingestion, autonomous dispatch, integration with official municipal systems, and a full predictive emergency platform.

**Rules of thumb:** build on seeded data first, then wire live calls; never let the demo depend on something you have not run three times.

## Demo script

The 3-minute demo climaxes on an **opted-in teammate's test call** saying "it's worse". The incident gains a visible critical alert with an evidence reference; the case is still unaccepted until a human taps Accept. No real city ticket or dispatch occurs.

| Time | On screen | What we say |
| --- | --- | --- |
| 0:00–0:20 | Prototype title + documented LA storm-report problem | "A sent ticket isn't an accepted handoff. This is a demonstration, not a live city service." |
| 0:20–0:50 | Three fictional intake reports: drain, road water, stalled car | "Three witnesses describe one emerging incident. We keep every original report." |
| 0:50–1:20 | Debt list + assigned / acknowledged / accepted states | "Assigning an on-call contact does not mean someone has accepted the case." |
| 1:20–2:00 | Callback to consenting teammate (or clearly labeled simulation) | "They agreed to a follow-up. We ask what changed and whether anyone is in danger." |
| 2:00–2:30 | Critical alert pinned above ranked top 10; source sentence visible | "The resident says it's worse. That's the evidence, not the elapsed timer or a missed call." |
| 2:30–3:00 | Department-silent twist and human-only Accept action | "One department-level failure alert, persistent safety alerts, and an auditable human handoff." |

**Twist toggles to pre-build**

- **Department goes silent** — acceptance rate drops to zero; create one grouped operational alert, preserve critical case alerts.
- **Call surge** — 50 synthetic reports collapse into a few linked incidents with all original report references intact.
- **Phones down** — callback failure creates contact uncertainty and optional *existing-high-risk* human attention; it does not prove worsening or close anything.
- **New domain** — optional synthetic port/utility handoff scenario; same workflow, no claimed integrations.
- **Consent declined** — add a simple synthetic test: no outbound call is placed; audit explains why (safety gate).

**Fallbacks (have all three ready)**

1. A recorded video of the full demo, captured Saturday night.
2. A "simulate callback" button that plays a recorded answer if the live call fails.
3. Seeded data so the dashboard tells the story even with no calls at all.

## Pitch and funding pathway

The pitch has six beats and leads with the LA story, not the technology.

1. **Hook** — "Disasters get worse at handoffs, where everyone thinks someone else has it."
2. **LA evidence** — 2023 storm tickets closed unresolved; 2026 council committee still asking about MyLA311 backlogs.
3. **Insight** — Status is not accountability: assigned, acknowledged, accepted and human-verified resolution are different events. Risk uses reported evidence, not silent assumptions.
4. **Live demo** — the 3-minute consent-safe, synthetic incident script above.
5. **Dual use** — everyday service requests and storm-night surge now; port/grid/logistics handoffs as future **software adaptations**, not deployed integrations.
6. **Path forward** — show potential (unverified) funding pathways and invite a prospective agency to explore a **permissioned pilot**, not a claim of an approved LA district pilot.

**Federal funding pathway (slide for the twist)**

| Stage | Federal source | Who applies | Status |
| --- | --- | --- | --- |
| Research and prototype (possible) | NSF SBIR Phase I | A qualifying company, after incorporation | Verify current solicitation, eligibility, budget limits and dates before presenting |
| City partner / procurement (possible) | FEMA HSGP / UASI / SHSP-related local projects | Eligible city/county grantee; company only as an authorized vendor | Not a direct company grant or award; program alignment and actual purchasing authority require verification |
| Alternative R&D (possible) | DHS S&T SBIR / solicitations | Eligible applicant only where a matching open topic exists | Verify availability and deadlines; no funding is secured |

**How to frame it for each source**

- **NSF:** the research question is "verifiable, calibrated escalation from noisy, multilingual resident evidence" — how a system decides what deserves a human when reports are partial and callers drop.
- **City (UASI):** fits "public information and warning" and "operational communications"; strictly non-emergency side, never a 911 replacement.
- **Say "potential pathway subject to eligibility," never "funded" or "guaranteed."**

## Judge Q&A defense

Every answer is one or two sentences; practise them out loud until each takes under 15 seconds.

**Novelty and prior art**

- **"Isn't this just PagerDuty or ServiceNow?"** — They provide sophisticated service workflows; our demo centers on resident evidence, explicit **assigned versus accepted** ownership, a consent-gated follow-up, and persistent safety alerts. We do not claim those other tools cannot be configured similarly.
- **"Cities already have AI 311 agents."** — Yes (Citibot, Polimorphic, Salesforce). They answer the call. We handle what happens after it: making sure someone accepts it.
- **"Isn't linking calls already done?"** — Grouping identical calls exists in 911 (Carbyne). We link related-but-different reports — a drain, a road, a stalled car — into one emerging incident, and then require an owner for it.

**Safety and what's never automated**

- **"What if the AI misclassifies a real emergency?"** — It is a non-emergency **hackathon demo**, not a live response service; the agent tells people in immediate danger to call 911. We preserve raw evidence, flag uncertain extraction for review, and never dispatch.
- **"What does the AI never do?"** — It cannot accept responsibility for a human, claim verified safety, place calls without consent, close work automatically, dispatch services, or issue official orders.
- **"What if the resident doesn't pick up?"** — Their condition is **unknown**, not worse or better. We log a contact debt and only elevate independently high-risk cases for review. No repeated calls without an agreed consent and retry policy.
- **"What if the caller did not consent?"** — We do not call. `callback_ok` is extracted, persisted and checked before the outbound API action; the reason is auditable.

**Escalation design**

- **"Won't everything pile up at the supervisor?"** — No. The ranked top 10 is capped, but **critical safety alerts remain visible independently**. Duplicate reports are linked and routine failures are grouped.
- **"What if nobody accepts anything?"** — One department-level operational alert highlights the systemic handoff failure while per-incident critical alerts remain visible. Reassignment stays a human decision.
- **"Who is the default owner?"** — A **fictional** configured on-call roster in the demo; assignment is not acknowledgment/acceptance. Missing roster mapping is flagged, never invented.
- **"What does 'resolved' mean?"** — A human records evidence of the fix, and an authorized human records closure. A better callback alone never auto-closes.

**Feasibility and adoption**

- **"Would LA actually adopt this?"** — We have **no city integration or purchasing commitment**. A future pilot would require agency sponsorship, authorization, procurement and safety/privacy review.
- **"Who pays?"** — Hypothetically an agency or infrastructure operator, subject to procurement. Government grants are **potential** research/procurement pathways, not money already committed to HandoffProof.
- **"Privacy of residents' numbers?"** — We use opt-in test participants, synthetic numbers in seed files, access-restricted phone fields, no exposed keys or full numbers in demo logs, and a documented retention/deletion plan before any real deployment.
- **"Isn't Retell an odd fit for government?"** — The voice layer is swappable, and the ownership engine is the product. Any future government use would require an independent vendor-security, data handling, accessibility and procurement review; do not treat a vendor marketing claim as approval.

**Dual use and twists**

- **"Who uses this on an ordinary day?"** — A non-emergency service-request manager reviewing unresolved pothole/drain cases; the same software supports simulated storm-night pressure.
- **"How does this handle the twists?"** — The workflow persists under surge, lost communications and a silent department. A **synthetic** logistics handoff can illustrate future dual use without hardware or live external integration.
- **"Where is wireless sensing?"** — Explicitly outside this MVP. Our evidence comes from calls and recorded follow-ups.

**Technical**

- **"Where's the AI, really?"** — Retell extracts structured facts from calls and callbacks. Optional AI can suggest related reports or clean up ambiguous language, but deterministic checks and humans control consent, ownership, closure and safety escalations. The explanation links back to source reports.
- **"How did you use IBM Bob?"** — If we pursue a Bob-specific award, only show actual Bob sessions/evidence. Otherwise, accurately state the development tools used (e.g. VS Code/Codex); do not claim Bob usage that did not occur.

## Do not claim, open questions, sources

The fastest way to lose credibility is one claim a judge can disprove; keep to these limits.

**Do not claim**

- "Nobody has ever built this" or "no competitors" — do not assert an exhaustive prior-art search. Describe **our specific prototype combination** and what we demonstrated.
- That LA's current 311 system still has the exact 2023 problem — say the 2026 committee is still asking about MyLA311 performance.
- "FEMA will fund us" or any 911 / Next Generation 911 grant money — none is available to us.
- That we replace, connect to, or touch 911, or that we operate a City of LA phone line — this is a simulated non-emergency workflow.
- That we deployed a wireless sensor, connected municipal systems, or have real-world prevention/prediction data — none is in MVP.
- That `no_answer` proves risk increased, that default owner means accepted, or that a top-10 limit includes all critical alerts.
- That real caller data can be collected/called without explicit consent.
- Any accuracy number we have not measured ourselves.
- That the west Altadena evacuation orders were late — a May 2026 review found they were not delayed.

**Open questions to answer Saturday**

- [x] Retell browser tests: Intake (5 fields) and Callback (3 fields) produced expected structured extraction; **not yet live integration**.
- [ ] Verify webhook signature, event mapping, deduplication and sandbox/live Retell API behavior using the latest provider docs. *(Signature check and deduplication ✅; event mapping still unchecked against a real payload.)*
- [ ] Decide who may authorize outbound test calls, consent retention, retry rate and test-participant contact policy. *(Engine caps retries at 2; the people/policy decision is open.)*
- [x] Team agrees how to migrate shared `ReportIn`/SQLModel/TypeScript contracts for consent, acknowledgment and persistent critical flags.
- [ ] Check actual available Retell number/credit; do not assume purchasing or live outbound test completed.
- [ ] Confirm IBM Bob prize rules **only if entering that prize**, plus any required evidence.
- [ ] Confirm each developer's ownership, demo roles and who rehearses each Q&A category.

**Sources**

- [LA City Council District 1: motion on storm-related 311 service (Jan 2023)](https://cd1.lacity.gov/press-releases/councilmember-hernandez-introduces-motion-address-storm-related-city-service)
- [LA City Clerk 26-0162: Public Works Committee report on MyLA311 (Mar 2026)](https://cityclerk.lacity.org/onlinedocs/2026/26-0162_rpt_pw_3-25-26.pdf)
- [SBIR/STTR reauthorized after six-month lapse (Mondaq, Apr 2026)](https://www.mondaq.com/unitedstates/government-contracts-procurement-ppp/1774902/sbirsttr-programs-reauthorized-after-six-month-lapse)
- [Citibot AI voice agents](https://www.citibot.io/voice) · [Polimorphic AI for 311](https://www.polimorphic.com/use-cases/ai-for-smarter-311-services)
- Team research reports: *Open federal grants by track*, *Novel winning hackathon ideas* (UASI FY2026 amounts, NSF SBIR terms, Carbyne, Retell features).
