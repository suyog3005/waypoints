# AI-Powered Automatic Block Planning System

## Final System Architecture — Component & Flow Specification

> This document explains the finalized architecture shown in the system diagram.
> The Data Lake / Object Store is intentionally excluded from the implementation explanation.

---

## 1. Purpose

1. The system is an AI-powered railway block planning platform.
2. Its primary purpose is to help plan railway blocks intelligently.
3. A block represents a period during which a railway track or related resource is unavailable for normal operations.
4. Multiple departments may request blocks for different maintenance or operational reasons.
5. Requests may overlap in time.
6. Requests may also affect other tracks.
7. Different requests may have dependencies on the same railway resources.
8. The system must identify these dependencies.
9. The system must combine compatible requests when possible.
10. The system must minimize unnecessary blocking time.
11. The system must consider train operations while planning blocks.
12. The system must consider restrictions and operational constraints.
13. The system must consider maintenance dependencies.
14. The system must support real-time changes.
15. Kafka provides the event-driven communication layer.
16. The AI and optimization service produces improved block plans.
17. The Operational DB remains the source of truth.
18. The Read Store is optimized for read-heavy workloads.
19. Redis provides fast access to frequently requested data.
20. The Query Service provides the normal read interface to the frontend.
21. The Command Service handles state-changing operations.
22. The API Gateway provides controlled access to backend services.
23. The frontend provides the user-facing planning and monitoring interface.
24. The architecture separates reads from writes.
25. This separation allows each path to be optimized independently.

---

## 2. Final High-Level Architecture

26. The frontend communicates with the API Gateway.
27. The API Gateway routes read requests to the Query Service.
28. The API Gateway routes write requests to the Command Service.
29. The Query Service communicates directly with Redis.
30. The Query Service also communicates directly with the Read Store.
31. Kafka is not part of the normal read path.
32. The Command Service publishes commands or events to Kafka.
33. Kafka distributes events to interested consumers.
34. The AI Optimization Service consumes relevant Kafka events.
35. The AI Optimization Service creates optimized planning results.
36. The optimized plan is written to the Operational DB.
37. Operational DB changes are propagated to the Read Store.
38. CDC or ETL can be used for this synchronization.
39. Redis can then be updated or invalidated.
40. The Query Service can retrieve the latest read model.
41. The frontend receives the final response through the API Gateway.
42. Real-time events can trigger another optimization cycle.
43. The system therefore forms a feedback loop.
44. The feedback loop allows plans to adapt to changing railway conditions.
45. The architecture is event-driven mainly on the write and real-time side.

---

## 3. Frontend

46. The frontend is the primary user interface.
47. It can be implemented using React or Next.js.
48. Users interact with railway planning information through the frontend.
49. The frontend can show trains.
50. The frontend can show tracks.
51. The frontend can show blocks.
52. The frontend can show restrictions.
53. The frontend can show maintenance information.
54. The frontend can show asset status.
55. The frontend can show optimized plans.
56. The frontend can show utilization metrics.
57. The frontend can show alerts.
58. The frontend can show operational dashboards.
59. The frontend can provide planning controls.
60. The frontend can provide what-if planning controls.
61. The frontend can provide department-specific forms.
62. The frontend can provide technical block-request forms.
63. The frontend can provide operational block-request forms.
64. Users should not directly access the database.
65. Users should not directly access Kafka.
66. Users communicate through APIs.
67. The frontend sends GET-style requests for normal reads.
68. The frontend sends POST, PUT, PATCH, or DELETE requests for state changes.
69. The frontend should handle loading states.
70. The frontend should handle API errors.
71. The frontend should show optimization status.
72. The frontend should show the latest confirmed plan.
73. The frontend should distinguish proposed and active plans.
74. The frontend should display relevant validation messages.
75. The frontend should refresh or receive updates when important state changes occur.

---

## 4. API Gateway

76. The API Gateway is the controlled entry point for the frontend.
77. It prevents the frontend from knowing internal service topology.
78. It routes requests to the correct backend service.
79. Read requests are routed to the Query Service.
80. Write requests are routed to the Command Service.
81. Authentication can be handled at the gateway.
82. Authorization can be enforced at the gateway or service layer.
83. Rate limiting can be applied at the gateway.
84. Request logging can be applied at the gateway.
85. Correlation IDs can be generated at the gateway.
86. Correlation IDs help trace requests across services.
87. The gateway should not contain complex railway business logic.
88. Business validation belongs primarily in backend services.
89. The gateway should remain lightweight.
90. It can also handle common HTTP concerns.
91. It can reject malformed requests.
92. It can route API versions.
93. It can expose a stable external API.
94. Internal service changes therefore do not necessarily affect the frontend.
95. This creates a clean service boundary.

---

## 5. Query Service

96. The Query Service handles read operations.
97. It is the backend entry point for dashboard queries.
98. It handles requests for plans.
99. It handles requests for blocks.
100.  It handles requests for trains.
101.  It handles requests for tracks.
102.  It handles requests for restrictions.
103.  It handles requests for assets.
104.  It handles utilization metrics.
105.  It handles reports.
106.  It handles alerts.
107.  It can provide aggregated dashboard information.
108.  It should not publish normal queries to Kafka.
109.  It should not use Kafka as a database.
110.  It should directly communicate with Redis.
111.  It should directly communicate with the Read Store.
112.  Redis should be checked first for cacheable requests.
113.  A cache hit can return data quickly.
114.  A cache miss should cause the Query Service to access the Read Store.
115.  The result from a cache miss can be stored in Redis.
116.  The result can then be returned to the frontend.
117.  The Query Service should not normally query the Operational DB.
118.  This protects the transactional database from heavy dashboard traffic.
119.  The Query Service can contain read-specific transformations.
120.  It can combine data from read-optimized tables.
121.  It can apply pagination.
122.  It can apply filtering.
123.  It can apply sorting.
124.  It can validate query parameters.
125.  It can return standardized API responses.

---

## 6. Correct Read Path

126. The normal read path starts at the frontend.
127. The frontend sends a query.
128. The query reaches the API Gateway.
129. The API Gateway routes it to the Query Service.
130. The Query Service checks Redis first.
131. If Redis contains a valid value, it is a cache hit.
132. The Query Service returns the cached result.
133. The result travels back through the API Gateway.
134. The frontend displays the result.
135. If Redis does not contain the requested value, it is a cache miss.
136. The Query Service then directly queries the Read Store.
137. The Read Store returns the required data.
138. The Query Service may transform the data.
139. The Query Service can place the result into Redis.
140. The Query Service returns the result to the frontend.
141. This is the intended direct read flow.
142. The read flow does not pass through Kafka.
143. Kafka is therefore isolated from normal synchronous queries.
144. This keeps dashboard queries fast.
145. It also avoids unnecessary asynchronous complexity.
146. Redis provides low-latency access.
147. The Read Store provides durable read-optimized data.
148. The Query Service controls the read contract.
149. The API Gateway controls external access.
150. The frontend remains independent of storage details.

---

## 7. Redis Cache

151. Redis is a fast cache.
152. Redis is not the source of truth.
153. Data in Redis can expire.
154. Data in Redis can be invalidated.
155. The Operational DB remains authoritative.
156. The Read Store contains the read model.
157. Redis is useful for frequently requested information.
158. Current active plans are good cache candidates.
159. Current train status can be cached.
160. Current block information can be cached.
161. Active restrictions can be cached.
162. Dashboard KPIs can be cached.
163. Frequently requested network information can be cached.
164. Session-related information can also be cached where appropriate.
165. Cache keys should be deterministic.
166. Cache entries should have suitable TTLs.
167. Frequently changing data needs careful invalidation.
168. Stale data must not be used where safety or operational correctness is critical.
169. The system should define which data can tolerate eventual consistency.
170. The system should define which data requires immediate freshness.

---

## 8. Read Store / Analytics DB

171. The Read Store is optimized for reading.
172. It is separate from the transactional Operational DB.
173. It can contain denormalized representations.
174. It can contain materialized views.
175. It can contain precomputed aggregations.
176. It can contain dashboard-specific projections.
177. It can contain historical read data.
178. It should support efficient frontend queries.
179. It should reduce expensive joins during normal dashboard operations.
180. It should be populated from authoritative operational changes.
181. CDC can capture changes from the Operational DB.
182. ETL can also be used where appropriate.
183. The choice depends on MVP complexity and required freshness.
184. The Read Store should not become the authoritative write database.
185. Writes should not normally originate from the Query Service.
186. The Query Service reads from the Read Store.
187. The Read Store can be optimized independently.
188. This is an important benefit of the architecture.
189. Reporting workloads can be separated from transactional workloads.
190. Dashboard performance becomes easier to manage.

---

## 9. Operational DB

191. The Operational DB is the source of truth.
192. PostgreSQL is the primary database technology.
193. TimescaleDB can be used for suitable time-series data.
194. The Operational DB stores current operational state.
195. It stores trains.
196. It stores tracks.
197. It stores blocks.
198. It stores assets.
199. It stores schedules.
200. It stores restrictions.
201. It stores maintenance information.
202. It stores constraints.
203. It stores department requests.
204. It stores plans.
205. It stores events or event references.
206. It stores optimization results.
207. It stores plan status.
208. It stores timestamps.
209. It stores ownership information where required.
210. It stores relationships between railway entities.
211. Database constraints protect data integrity.
212. Indexes support important transactional queries.
213. Transactions should protect multi-step state changes.
214. The Operational DB should be carefully protected from direct frontend access.
215. Only trusted backend services should access it.

---

## 10. Database Entities

216. A Train entity represents a train.
217. A Track entity represents a railway track or network segment.
218. A Block entity represents a requested or planned blocking interval.
219. An Asset entity represents infrastructure or operational equipment.
220. A Restriction entity represents an operational restriction.
221. A Maintenance entity represents planned or required maintenance.
222. A Department entity represents the requesting organization.
223. A Block Request represents a department's submitted requirement.
224. A Technical Request stores technical parameters.
225. An Operational Request stores operational parameters.
226. A Plan represents an overall block plan.
227. A Plan Item represents a scheduled block within a plan.
228. A Constraint represents a planning rule.
229. An Event represents an important state or operational occurrence.
230. An Optimization Run represents one optimizer execution.
231. An Optimization Result represents the result of an optimization run.
232. Affected Track relationships can identify secondary track impacts.
233. Train schedules should be related to relevant tracks and blocks.
234. Maintenance requirements should be linked to affected resources.
235. Restrictions should contain validity intervals.
236. Block requests should retain their original requested windows.
237. The optimized plan should preserve traceability to source requests.
238. This traceability is important for explaining optimizer decisions.
239. Database design should avoid losing the original user request.
240. Proposed and approved plans should be distinguishable.

---

## 11. Technical Block Request

241. A department submits a technical block request.
242. The request contains multiple railway parameters.
243. Train stops can be included.
244. Railway line can be included.
245. Direction can be included.
246. Restriction type can be included.
247. Block date can be included.
248. Train type information can be included.
249. The request can indicate additional affected tracks.
250. Finance-related submission information can be included.
251. The responsible maintenance department can be included.
252. Other technical parameters can be captured.
253. These fields become inputs to planning.
254. They should not be treated as simple display fields.
255. Relevant fields should become optimizer constraints.
256. Some fields can determine affected resources.
257. Some fields can determine operational risk.
258. Some fields can determine eligibility.
259. Some fields can determine schedule feasibility.
260. The backend must validate these fields before publishing an event.

---

## 12. Operational Block Request

261. The operational form captures why the block is needed.
262. A bridge can be a reason.
263. An underpass can be a reason.
264. A road crossing can be a reason.
265. Tree work can be a reason.
266. Cable maintenance can be a reason.
267. Track maintenance can be a reason.
268. Other operational reasons can be supported.
269. Operational reasons can determine required resources.
270. Operational reasons can determine expected duration.
271. Operational reasons can determine safety constraints.
272. Operational reasons can determine affected assets.
273. The optimizer can use these attributes.
274. Different reasons may require different blocking procedures.
275. The reason therefore becomes planning metadata.
276. It can also help estimate required work duration.
277. Historical durations can later improve estimates.
278. The operational form and technical form complement each other.
279. Both should ultimately feed the block-planning model.
280. The system should maintain a clear relationship between both forms.

---

## 13. Command Service

281. The Command Service handles state-changing operations.
282. It receives validated commands from the API Gateway.
283. It can create block requests.
284. It can update block requests.
285. It can add restrictions.
286. It can modify assets.
287. It can trigger optimization.
288. It can activate plans.
289. It can cancel or modify eligible requests.
290. It applies business validation.
291. It creates the appropriate command/event payload.
292. It publishes the message to Kafka.
293. It should not contain the optimizer itself.
294. It should not become the main analytics service.
295. It should keep command handling focused.
296. Commands should have IDs.
297. Commands should contain timestamps.
298. Commands should identify the requesting user or department where appropriate.
299. Commands should have versioned schemas.
300. Commands should be traceable through the system.

---

## 14. Kafka Event Bus

301. Kafka provides asynchronous event communication.
302. Kafka decouples producers from consumers.
303. The Command Service can publish commands.
304. External railway systems can publish operational events.
305. The AI Optimization Service consumes relevant events.
306. Other future services can consume the same events.
307. Kafka provides durable event streaming.
308. Topics should be designed around meaningful event domains.
309. Example topic: plan.commands.
310. Example topic: train.events.
311. Example topic: track.events.
312. Example topic: asset.events.
313. Example topic: restriction.events.
314. Example topic: maintenance.events.
315. Example topic: optimization.requests.
316. Example topic: optimization.results.
317. Example topic: alerts.
318. Exact topics should be finalized during architecture/contracts work.
319. Event payloads must be versioned.
320. Consumers must be able to handle failures safely.

---

## 15. Event Contract

321. Every important event needs a defined schema.
322. The schema should contain an event ID.
323. The schema should contain an event type.
324. The schema should contain an event version.
325. The schema should contain a timestamp.
326. The schema should contain the relevant entity ID.
327. The schema should contain the producer or source where required.
328. The payload should contain domain-specific information.
329. Required fields must be clearly documented.
330. Optional fields must be clearly documented.
331. Consumers should not depend on undocumented fields.
332. Schema changes should be backward-compatible where possible.
333. Invalid events should be rejected or routed to an error mechanism.
334. Duplicate event handling should be considered.
335. Idempotency should be considered for important consumers.
336. Correlation IDs should help trace related operations.
337. The event contract is part of the system architecture.
338. Event schemas should be documented before integration.
339. Event schemas should have automated validation where practical.
340. Kafka should carry events, not arbitrary unstructured messages.

---

## 16. AI + Optimization Service

341. This service is the intelligence layer.
342. It consumes relevant events from Kafka.
343. It can receive new block requests.
344. It can receive schedule changes.
345. It can receive train delay events.
346. It can receive track status changes.
347. It can receive maintenance events.
348. It can receive restriction changes.
349. It can receive asset availability changes.
350. It can retrieve additional planning data when required.
351. It performs prediction where ML is appropriate.
352. It performs optimization using explicit constraints.
353. ML should not be confused with the optimizer.
354. ML can predict delay or demand.
355. The optimizer decides feasible block allocations.
356. The optimizer should use deterministic constraints where safety requires them.
357. The optimizer can use mathematical programming.
358. Constraint programming can also be considered.
359. The optimization objective should be explicitly defined.
360. The output should be explainable enough for operators.

---

## 17. Shadow Finder Concept

361. Shadow Finder is an important planning concept.
362. It identifies overlapping or dependent block requests.
363. Suppose Department A requests Track 1 from 10:00 to 12:00.
364. Department B requests Track 1 from 11:00 to 14:00.
365. These requests overlap.
366. Processing them independently can create inefficient scheduling.
367. The optimizer should identify the overlap.
368. It should determine whether the work can be merged.
369. It should consider the full requested duration.
370. It should consider whether one combined block is feasible.
371. It should identify other tracks affected by the block.
372. It should identify maintenance opportunities on those tracks.
373. It should identify train movement consequences.
374. It should identify restrictions.
375. It should identify dependencies between requests.
376. The objective is not simply to merge every request.
377. A merge is valid only when operational constraints allow it.
378. Safety constraints always take priority.
379. The optimizer should minimize unnecessary repeated blocking.
380. Shadow Finder therefore becomes a key input to optimization.

---

## 18. Schedule Merging

381. Multiple departments may request different times.
382. The optimizer receives all relevant requests.
383. It groups requests by affected resources.
384. It identifies overlapping time windows.
385. It identifies compatible adjacent windows where applicable.
386. It checks whether requests can share a block.
387. It checks the required work duration.
388. It checks dependencies.
389. It checks train schedules.
390. It checks restrictions.
391. It checks affected tracks.
392. It checks maintenance requirements.
393. It checks operational feasibility.
394. It calculates candidate merged windows.
395. It compares candidate plans.
396. It selects the best feasible plan.
397. The goal is minimum disruption.
398. The goal is also high asset utilization.
399. The optimizer should avoid unnecessary block repetition.
400. Every merge should remain traceable to its source requests.

---

## 19. Track Dependency Analysis

401. A block on one track may affect other tracks.
402. The request should identify known affected tracks.
403. The system can also derive dependencies from network relationships.
404. Track dependencies can affect train routing.
405. Track dependencies can affect block feasibility.
406. A secondary track may also require maintenance.
407. The optimizer should check whether that maintenance can be combined.
408. This can turn one planned block into a larger coordinated maintenance window.
409. The system should avoid blindly blocking unrelated resources.
410. Dependency rules must be explicit.
411. Track topology can be represented in the domain model.
412. Track direction should be considered where relevant.
413. Train movement constraints should be considered.
414. The optimizer should calculate the impact of candidate blocks.
415. The result should include affected resources.
416. Operators should be able to inspect those dependencies.
417. The frontend can visualize affected tracks.
418. This makes the optimization result easier to understand.
419. The system can later learn from historical dependencies.
420. The dependency engine and optimizer should remain logically separable.

---

## 20. Optimization Objective

421. The optimizer should find a feasible plan first.
422. Among feasible plans, it should improve the objective.
423. One objective is minimizing block duration.
424. Another objective is minimizing train delay.
425. Another objective is minimizing operational disruption.
426. Another objective is maximizing track utilization.
427. Another objective is reducing repeated blocking.
428. Another objective is combining maintenance activities.
429. Another objective is reducing rescheduling.
430. Safety constraints override optimization preferences.
431. Hard constraints must never be violated.
432. Soft constraints can be penalized.
433. Penalty weights should be configurable.
434. The optimization result should expose major metrics.
435. Metrics can include total block duration.
436. Metrics can include affected trains.
437. Metrics can include expected delay.
438. Metrics can include utilization.
439. Metrics can include number of merged requests.
440. Metrics can include affected tracks.

---

## 21. Write Path

441. The write path starts when a user performs a state-changing action.
442. The frontend sends the command to the API Gateway.
443. The API Gateway routes the command to the Command Service.
444. The Command Service validates the command.
445. The Command Service creates a command/event.
446. The Command Service publishes it to Kafka.
447. Kafka stores and distributes the message.
448. The AI Optimization Service consumes relevant messages.
449. The optimizer evaluates the current planning state.
450. It generates an optimized plan.
451. The optimized plan is persisted in the Operational DB.
452. The Operational DB becomes the authoritative state.
453. The database change is propagated through CDC or ETL.
454. The Read Store receives the updated read model.
455. Redis can be updated or invalidated.
456. Future queries therefore see the updated information.
457. This completes the write-to-read propagation cycle.
458. The write path is asynchronous after Kafka publication.
459. The frontend should therefore support processing states.
460. The frontend should distinguish submitted from optimized/confirmed state.

---

## 22. Read Path

461. The read path starts with a frontend query.
462. The query reaches the API Gateway.
463. The API Gateway routes it to the Query Service.
464. The Query Service checks Redis.
465. A cache hit returns quickly.
466. A cache miss causes a direct query to the Read Store.
467. The Query Service can transform the read-model data.
468. The result is placed into Redis where appropriate.
469. The response is returned through the API Gateway.
470. The frontend displays the result.
471. Kafka is not required for this synchronous read.
472. The Read Store is optimized for this workload.
473. Redis reduces repeated database queries.
474. The Query Service owns the external read contract.
475. This path is intentionally simple.

---

## 23. Real-Time Event Flow

476. Railway conditions can change after a plan is created.
477. A train can become delayed.
478. A track can become unavailable.
479. An asset can fail.
480. A maintenance requirement can change.
481. A restriction can be added.
482. Such changes can generate operational events.
483. Operational events enter Kafka.
484. The AI Optimization Service consumes the relevant event.
485. It loads the affected planning context.
486. It identifies impacted blocks.
487. It recalculates the relevant schedule.
488. It can invoke Shadow Finder logic.
489. It can merge compatible blocks.
490. It can identify newly affected tracks.
491. It can generate a new feasible plan.
492. The new plan is written to the Operational DB.
493. CDC or ETL updates the Read Store.
494. Redis is updated or invalidated.
495. The Query Service serves the latest information.
496. The frontend displays the updated plan.
497. This creates a real-time adaptive planning loop.
498. The loop is driven by events rather than repeated manual replanning.
499. The system can therefore react to disruptions.
500. The final architecture is: WRITE through Command Service and Kafka, READ directly through Query Service to Redis/Read Store, with AI Optimization producing the intelligent block plan and Operational DB remaining the source of truth.

---

## 24. Component Responsibility Summary

### Frontend

- Provides the planning UI.
- Displays railway state.
- Collects user input.
- Displays optimized results.
- Displays alerts and metrics.

### API Gateway

- Provides one API entry point.
- Routes requests.
- Handles authentication and common API controls.

### Query Service

- Handles reads.
- Checks Redis.
- Reads from Read Store on cache miss.
- Returns frontend-ready data.

### Command Service

- Handles writes.
- Validates commands.
- Publishes events to Kafka.
- Keeps state-changing logic separate from reads.

### Kafka

- Provides event streaming.
- Decouples services.
- Carries commands and operational events.
- Triggers asynchronous processing.

### AI + Optimization Service

- Consumes planning events.
- Performs prediction.
- Finds feasible block plans.
- Merges compatible requests.
- Uses Shadow Finder concepts.
- Considers track dependencies.
- Minimizes block time and disruption.

### Operational DB

- Stores authoritative operational state.
- Stores requests and plans.
- Stores constraints and railway entities.
- Stores optimization results.

### Read Store

- Provides read-optimized data.
- Supports dashboards.
- Supports analytics.
- Supports reports.
- Receives synchronized operational changes.

### Redis

- Provides low-latency cached responses.
- Reduces repeated read-store queries.
- Accelerates dashboards and frequent requests.

---

## 25. Final Flow

### Write

```text
Frontend
  -> API Gateway
  -> Command Service
  -> Kafka
  -> AI + Optimization
  -> Operational DB
  -> CDC / ETL
  -> Read Store
  -> Redis
```

### Read

```text
Frontend
  -> API Gateway
  -> Query Service
  -> Redis
       |-- Cache Hit -> Response
       |
       |-- Cache Miss -> Read Store
                         -> Redis
                         -> Response
```

### Real-Time

```text
Railway Event
  -> Kafka
  -> AI + Optimization
  -> Operational DB
  -> CDC / ETL
  -> Read Store
  -> Redis
  -> Query Service
  -> Frontend
```

### Core Principle

```text
COMMANDS change the system.
KAFKA distributes events.
AI + OPTIMIZATION makes planning decisions.
OPERATIONAL DB stores the truth.
READ STORE serves read-heavy workloads.
REDIS accelerates frequent reads.
QUERY SERVICE serves reads.
COMMAND SERVICE handles writes.
FRONTEND interacts only through APIs.
```

## 26. Important Architectural Decision

The Query Service must be directly connected to both Redis and the Read Store.

It must NOT be connected to Kafka for normal read requests.

Correct:

```text
Query Service
     |
     +----> Redis
     |
     +----> Read Store
```

Incorrect:

```text
Query Service
     |
     v
Kafka
     |
     v
Read Store
```

Kafka belongs to the event-driven write and real-time processing side.

The architecture should remain understandable to developers and operators without requiring Kafka to answer ordinary dashboard queries.

---

## 27. Problem Statement — Deep Dive

501. Indian Railways (and similar rail networks) must periodically shut down a track,
     signal, or overhead electric (OHE) traction line to allow maintenance, inspection,
     or construction work. This is commonly called a **Traffic Block** (track unavailable
     for train movement) or a **Power Block** (OHE de-energized for electrical safety).
502. Blocks are requested by multiple departments: Engineering (track/bridge work),
     Electrical/OHE (power infrastructure), Signal & Telecommunication (S&T), and
     Operating/Safety (inspections, trials).
503. Every block reduces line capacity and can delay passenger and freight trains,
     so blocks are traditionally negotiated manually between departments and the
     section/division Control Office — a slow, spreadsheet- and phone-call-driven process.
504. Manual planning struggles to see all overlapping requests across departments at once,
     so genuinely combinable work (e.g., Engineering + S&T on the same stretch) is often
     scheduled separately, wasting total block-hours and causing repeated disruption.
505. The manual process also struggles to react quickly when real-world conditions change
     (train delays, weather, asset failures), so approved blocks are not re-evaluated
     once granted, even if circumstances make them sub-optimal or unsafe.
506. There is no centralized system of record correlating: the original request, the
     approved plan, the actual execution outcome, and the resulting traffic impact —
     making it hard to learn from history or defend planning decisions after the fact.
507. The goal of this system is to digitize the full lifecycle of a block — request,
     validation, conflict/dependency detection, AI-assisted optimization, approval,
     execution, and post-block reporting — while preserving human authority over
     safety-critical approval decisions.
508. The system is explicitly a **decision-support and workflow platform**, not a fully
     autonomous system: the optimizer proposes plans; accountable humans (Section
     Controllers / Control Office) approve, reject, or adjust them.

---

## 28. Stakeholders & Personas

509. **Requesting Engineer / Department User** — submits technical or operational block
     requests from a depot, section office, or the mobile app; tracks request status.
510. **Section Controller / Control Office (Operating Dept.)** — reviews AI-proposed plans,
     resolves conflicts with train schedules, approves/rejects/modifies blocks, and can
     issue emergency blocks.
511. **Divisional/Zonal Planning Officer** — reviews aggregated block calendars across
     multiple sections, balances competing department priorities, and monitors KPIs.
512. **Safety Officer** — reviews high-risk block categories, enforces hard safety
     constraints, and audits historical execution reports.
513. **Field Supervisor (on-site)** — confirms block start/end via mobile app, reports
     actual work progress, and raises real-time exceptions (e.g., overrun requests).
514. **System Administrator** — manages users, roles, departments, master data (tracks,
     stations, assets), and constraint/optimizer configuration.
515. **AI/Optimization Operator (internal)** — the optimization service itself, acting as
     an automated participant that proposes plans but never has final approval authority.
516. Roles map to Role-Based Access Control (RBAC): every API call is authorized against
     the caller's role and department scope, not just authentication identity.

---

## 29. Expanded Feature Set

These features extend the core read/write architecture (Sections 1–26) to make the
platform a complete, competition-grade solution.

### 29.1 Corridor Block Bundling

517. The system should let the optimizer propose a **Corridor Block**: a single combined
     block window covering multiple compatible requests/assets on the same section.
518. Corridor blocks should be visually distinct from single-request blocks in the UI and
     should list every contributing request for traceability.

### 29.2 Emergency / Fast-Track Block Requests

519. The system should support an **emergency block** request type for safety-critical
     situations (e.g., a damaged rail or failed signal).
520. Emergency requests should bypass the normal optimization queue and go directly to
     the Control Office for expedited approval, while still being logged and reconciled
     with the plan afterward.

### 29.3 Approval Workflow & Escalation

521. Every block request should move through an explicit workflow: `draft → submitted →
under_review → approved/rejected → scheduled → in_progress → completed/aborted`.
522. Approvals can require one or more sign-offs depending on request type/risk level
     (e.g., Safety Officer sign-off for high-risk operational reasons).
523. If a request is not actioned within its SLA window, the system should automatically
     escalate it to the next role in the approval chain and notify stakeholders.

### 29.4 What-If Simulation

524. Planners should be able to run a **what-if simulation**: propose a hypothetical
     request or change and see the optimizer's projected plan/impact without committing it.
525. Simulation results should be discardable or promotable to a real request/plan.

### 29.5 Notifications & Alerts

526. The system should notify relevant users (email/SMS/push/in-app) on key events:
     new request submitted, approval needed, plan changed, block starting soon, overrun
     detected, or emergency block raised.
527. Notification preferences should be configurable per user/role.

### 29.6 GIS / Network Map Visualization

528. The frontend should offer a geographic or schematic track-network map view showing
     active/upcoming blocks, affected tracks, and train positions where available.
529. This supports faster human understanding of Track Dependency Analysis results
     (Section 19).

### 29.7 Weather & Environmental Risk Awareness

530. Outdoor works (tree cutting, bridge work, cable work) can be affected by weather.
531. The system should optionally ingest weather forecasts/alerts and flag risk to
     planned blocks, feeding this as a soft constraint/input to the optimizer.

### 29.8 Post-Block Execution Reporting & Feedback Loop

532. After a block completes, the field supervisor or system should record actual
     start/end time, actual work completed, and any deviation from the plan.
533. These execution reports feed back into historical data used to improve future
     duration estimates and ML predictions (Section 16), closing the learning loop.

### 29.9 Analytics & Reporting Dashboards

534. The system should provide dashboards for block utilization %, on-time approval
     rate, punctuality impact, department-wise block-hours, and corridor-bundling savings.
535. Reports should be exportable and filterable by zone/division/section/date range.

### 29.10 Multi-Zone / Division / Section Hierarchy

536. Real railway networks are organized as Zone → Division → Section → Station/Track.
537. The domain model should represent this hierarchy so requests, plans, and dashboards
     can be scoped and rolled up correctly across organizational levels.

### 29.11 Audit Trail & Compliance

538. Every state-changing action (create/update/approve/reject/cancel) should be recorded
     in an immutable audit log with actor, timestamp, and before/after state.
539. Audit logs support safety investigations and regulatory compliance reviews.

### 29.12 Role-Based Access Control (RBAC)

540. Users authenticate via the API Gateway; authorization is enforced per role and
     department/section scope at the Command Service and Query Service layers.
541. Sensitive actions (approve, reject, emergency override) require elevated roles.

---

## 30. Extended Component Additions

These are additional logical components layered onto the core architecture
(Sections 2–24); they do not change the fundamental read/write separation.

- **Notification Service** — consumes Kafka events (e.g., `plan.approved`,
  `block.starting_soon`, `escalation.triggered`) and dispatches email/SMS/push/in-app
  notifications. It is a Kafka consumer, symmetrical to the AI Optimization Service.
- **Simulation Engine** — a stateless mode of the AI + Optimization Service that runs
  against a hypothetical input snapshot and returns results without persisting a Plan,
  unless explicitly promoted.
- **Reporting/Analytics Module** — scheduled or on-demand aggregation jobs that populate
  the Read Store's reporting projections (utilization, punctuality, savings metrics).
- **GIS/Map Layer** — a frontend module (and optional lightweight backend endpoint) that
  renders track topology and active blocks; consumes the same Query Service read APIs.
- **Audit Logger** — a cross-cutting concern implemented at the Command Service: every
  command handler writes an audit record in the same transaction as the state change.

---

## 31. Extended Flows

### 31.1 Approval Workflow Flow

```text
Requester submits request
  -> Command Service validates + creates request (status: submitted)
  -> Kafka: block_request.submitted
  -> Notification Service notifies approver(s)
  -> Approver reviews (Query Service shows AI-proposed plan context)
  -> Approver approves/rejects via Command Service
  -> Kafka: block_request.approved | block_request.rejected
  -> If SLA exceeded before action -> Escalation Service triggers next approver
```

### 31.2 Emergency Block Flow

```text
Field user raises emergency request (priority: emergency)
  -> Command Service fast-tracks validation (reduced checks, safety-critical flag)
  -> Kafka: block_request.emergency_raised (high-priority topic/partition)
  -> Control Office approves immediately (manual, often out-of-band e.g. phone + system entry)
  -> Command Service records approval
  -> AI + Optimization reconciles the emergency block into the active plan asynchronously
  -> Operational DB updated -> Read Store/Redis refreshed as usual
```

### 31.3 What-If Simulation Flow

```text
Planner submits simulation input via Command Service (or a dedicated Simulation endpoint)
  -> AI + Optimization runs optimizer against snapshot (no Operational DB write for Plan)
  -> Simulation result stored (simulation_runs/simulation_results) for reference
  -> Planner reviews result in frontend
  -> Planner may "promote" simulation to a real block request/plan (creates real Plan)
```

---

## 32. Revised Database Entity List

542. The entities in Section 10 remain valid and are extended by:
543. Organizational hierarchy: Zone, Division, Section, Station.
544. Identity/authorization: User, Role, User Role Assignment.
545. Workflow: Approval, Approval Step, Escalation.
546. Corridor bundling: Corridor Group (linking multiple Block Requests/Blocks).
547. Simulation: Simulation Run, Simulation Result.
548. Notifications: Notification, Notification Recipient.
549. Weather: Weather Observation, Weather Risk Assessment.
550. Execution feedback: Block Execution Report.
551. Compliance: Audit Log.
552. See [database_schema.md](./database_schema.md) for the full PostgreSQL implementation
     of these entities.
