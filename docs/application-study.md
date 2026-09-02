# RIVM INFRA — Exhaustive Application Study

> **Scope of this document**
> This is a read-only, evidence-based technical study of the repository located at
> `c:\Users\z0059stn\Projects\work\infra` (Gradle root project name: **`rivm-infra`**).
> Every statement below is traced to a concrete file, class, method, property or schema in that
> repository. Where something could **not** be determined from the codebase it is explicitly
> marked **`NOT FOUND / NOT DETERMINED`**.
>
> **No application file was modified, created, deleted, renamed or executed** while producing this
> document. The only file written is this one.
>
> **Secrets policy:** wherever a credential-shaped value exists it is reported as
> `[SECRET / CREDENTIAL PRESENT — VALUE OMITTED]`.
>
> **Accuracy note:** the repository contains several pre-existing Markdown documents
> (`components/infra-webapp/doc/architecture.md`, `components/infra-trainoperation-etl/docs/*`,
> `components/infra-webapp/AGENTS.md`). Those documents are **partially stale** — they reference
> classes that do not exist in the current source tree (e.g. `MovementToInfraMapper`,
> `MovementUtil`, `TileCalculator`, `MapConfigController`, `SessionMgmtService`,
> `InfraTrainOperationEventHandler`) and quote older framework versions. **This study documents the
> code as it actually exists**, and flags the divergences in
> [§23.N Known unknowns / stale documentation](#23n--known-unknowns--information-not-found).

---

## Table of Contents

1. [Application Overview](#1--application-overview)
2. [Complete Application Flow](#2--complete-application-flow)
3. [Frontend — Angular / MFEs](#3--frontend--angular--mfes)
4. [Map / Main Content Implementation](#4--map--main-content-implementation)
5. [Backend Architecture — Java](#5--backend-architecture--java)
6. [All APIs / Endpoints](#6--all-apis--endpoints)
7. [Database — Complete Data Model](#7--database--complete-data-model)
8. [Database → Backend Contracts](#8--database--backend-contracts)
9. [Backend → Frontend Contracts](#9--backend--frontend-contracts)
10. [RabbitMQ — Complete Analysis](#10--rabbitmq--complete-analysis)
11. [Events and Message Contracts](#11--events-and-message-contracts)
12. [Train Management](#12--train-management)
13. [Track / Network Management](#13--track--network-management)
14. [Restrictions](#14--restrictions)
15. [Authentication & Authorization](#15--authentication--authorization)
16. [Error Handling](#16--error-handling)
17. [Configuration](#17--configuration)
18. [Complete Feature Inventory](#18--complete-feature-inventory)
19. [Complete Service Inventory](#19--complete-service-inventory)
20. [Complete Data-Flow Map](#20--complete-data-flow-map)
21. [File / Class / Function Reference](#21--file--class--function-reference)
22. [Architecture Diagrams](#22--architecture-diagrams)
23. [Final System Summary](#23--final-system-summary)

---

# 1 — APPLICATION OVERVIEW

## 1.1 In simple terms

RIVM INFRA is a **railway control-room screen**. It draws a map of a rail network — every track,
every junction, every station platform — and then draws little train icons moving over that map.

A dispatcher looking at the screen can:

- See where every train **is right now**.
- Scrub a small time slider backwards (‑10 minutes) or forwards (+50 minutes) to see where trains
  **were** or where they are **predicted to be**.
- See coloured overlays on stretches of track where a **restriction** is in force (a blockage, a
  speed reduction, or reduced wheel-rail adhesion), with an icon and a hover popover explaining it.
- Open a **train list** panel, pick a train, look at its detail panel, and make small edits
  (change its arrival time, its departure time, or which platform track it uses).
- Open a **restriction list** panel and Activate / Deactivate a restriction.
- Open an **AEM (alert/event) message panel**.
- Toggle which map layers are visible (trains, restrictions, station names, platform names).

Nothing in the map is computed by the browser from raw timetables. Instead a set of small
background **ETL programs** listen to a company-wide message bus (RabbitMQ), translate whatever
arrives into a simple "this train is at X,Y between time A and time B" record, and store it in
MongoDB. One read-only REST service then serves those records to the browser.

## 1.2 Primary purpose

Real-time and simulated **visualisation of train positions on a microscopic rail-infrastructure
graph**, with time-travel (past / present / forecast) and a 3-dimensional (X, Y, Time) data-tiling
strategy so that only the data actually visible in the viewport and time window is transferred.

Evidence:

- [components/doc/features/infra-data-tile-concept.md](../infra/components/doc/features/infra-data-tile-concept.md) — the tiling concept document.
- [components/infra-webapp/doc/architecture.md](../infra/components/infra-webapp/doc/architecture.md) — "RIVM INFRA (Railway Infrastructure Visualization Module)".
- `InfraContentComponent` (the map view) in [components/infra-webapp/src/app/master-layout/infra-content/infra-content.component.ts](../infra/components/infra-webapp/src/app/master-layout/infra-content/infra-content.component.ts).

## 1.3 Who uses it — roles / personas

| Persona                             | Evidence                                                                                                                                                                             | Notes                                                                                                                 |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------- |
| **Dispatcher / operator** (primary) | `doc/architecture.md` — "enables dispatchers and operators to monitor train traffic"; `doc/features/infra-data-tile-concept.md` — "help dispatchers monitor rail traffic"            | The whole UI is a single-workstation control screen (`workStationLabel: 'Workstation 1'` in `MasterLayoutComponent`). |
| **`TECHNICAL_USER`**                | `RIVMUserRole` examples in [components/schemas/basic/RIVMTypes.yaml](../infra/components/schemas/basic/RIVMTypes.yaml); sample events carry `userData.userRoles: ["TECHNICAL_USER"]` | Role of the upstream bridge service that publishes events.                                                            |
| **`ADMINISTRATOR`**                 | `RIVMUserRole` examples in `RIVMTypes.yaml`                                                                                                                                          | Declared in the shared type only; **no administrator screen exists in this repository**.                              |
| **`TPS_USER`**                      | Sample event `TrainOperationEvent.json` → `changeDetails[].changeCommand.userData.userRoles`                                                                                         | Role stamped on upstream change commands.                                                                             |

> **NOT FOUND / NOT DETERMINED:** there is **no role-based UI gating, no permission check and no
> role-aware routing anywhere in `infra-webapp` or `infra-query-svc`**. `ConfigService.loadConfig()`
> ([components/infra-webapp/src/app/services/config-service/config.service.ts](../infra/components/infra-webapp/src/app/services/config-service/config.service.ts))
> returns a hard-coded empty `UserInfo { firstName: '', lastName: '', roles: '' }`. Roles are a
> _data_ concept carried in upstream events, not an _authorisation_ concept in this repository.

## 1.4 Main business workflows

| #   | Workflow                                      | Trigger                                                  | Terminal effect                                                                            |
| --- | --------------------------------------------- | -------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| W1  | **Infrastructure ingest (base graph)**        | `InfraMicroscopicRegionEvent` on RabbitMQ                | `infra-rivm.basegraph` document per region                                                 |
| W2  | **Infrastructure ingest (track coordinates)** | `InfraMicroscopicRegionEvent` on RabbitMQ                | `infra-rivm.track-coordinates` documents, one per `location_track`                         |
| W3  | **Business clock ingest**                     | `BusinessClockEvent` on RabbitMQ                         | Single-row `infra-rivm.business-clock` collection                                          |
| W4  | **Train position ingest (ACTUAL/planned)**    | `TrainOperationEvent` on RabbitMQ                        | `infra-rivm.train-position` + `infra-rivm.data-tile`                                       |
| W5  | **Train position ingest (FORECAST)**          | `TrainOperationForecastEvent` on RabbitMQ                | `infra-rivm.train-position` (forecast rows replaced) + `infra-rivm.data-tile` version bump |
| W6  | **Restriction ingest**                        | `RestrictionEvent` on RabbitMQ                           | `infra-rivm.restriction` upsert/delete                                                     |
| W7  | **Map bootstrap**                             | User opens `/ui/infra`                                   | Map rendered from `/basegraph`, `/configs`, `/location-track-coordinates`                  |
| W8  | **Live train polling**                        | Map zoom ≥ trains-layer `minZoom`                        | Repeated `POST /trainpositions` on visible tiles                                           |
| W9  | **Restriction polling**                       | Map zoom > restrictions-layer `minZoom`                  | Repeated `GET /restrictions?effectiveAt=…`                                                 |
| W10 | **Time travel**                               | Time-offset slider / header date+time pickers            | New rounded tile timestamp → new tile IDs → new train set                                  |
| W11 | **Train inspection**                          | Double-click a train / train-list row                    | Right-slot `tps-mfe-train-info-panel` opens                                                |
| W12 | **Train edit**                                | Ribbon _Edit_ section or map right-click context menu    | `tps-mfe-train-edit-panel` PUT (executed **inside the MFE**)                               |
| W13 | **Restriction activate/deactivate**           | Ribbon _Actions_ section with a restriction row selected | PATCH executed **inside `@tps/rimfe-restriction`**                                         |
| W14 | **Layer show/hide**                           | Ribbon _Show/Hide_ → filter panels                       | OpenLayers layer `setVisible()`; state persisted to `localStorage`                         |
| W15 | **AEM message panel**                         | Sidebar `messages` item                                  | `tps-aem-events-panel` from `@tps/rimfe-aem`                                               |
| W16 | **Sign out**                                  | Header user menu                                         | `POST {baseAuthUrl}/logout`                                                                |

## 1.5 Main features

- Microscopic node/edge rail-network rendering (OpenLayers vector layer).
- Station (location) name labels and platform (track) name labels as separate zoom-gated layers.
- Train position rendering with **dynamic clustering** (donut cluster icon + count) and a
  **collision-avoiding label placement engine**.
- Train colouring by **train type derived from the first digit of `trainServiceId`**.
- Restriction rendering as coloured poly-lines with a composited SVG marker at the line midpoint,
  plus a white-halo hover highlight.
- Hover popovers for trains and restrictions.
- Right-click context menu on a selected train (Arrival Time / Departure Time / Change Track).
- Frozen **overview map** (mini-map) control.
- 3D data tiling (X, Y, Time) with **tile-version-based delta transfer**.
- Business clock with **REALTIME / CONTROLLED** modes plus a client-side **custom clock**.
- IndexedDB (Dexie) caching of base graph, map config and location-track coordinates.
- Angular **i18n** (`en-US` source locale + `fr`).
- **Demo mode** — all HTTP intercepted and served from in-repo fixtures.

## 1.6 Major modules (Gradle subprojects)

Declared in [settings.gradle.kts](../infra/settings.gradle.kts):

```kotlin
rootProject.name = "rivm-infra"

include(":components:platform")
include(":components:infra-common-lib")
include(":components:infra-query-svc")
include(":components:infra-business-clock-etl")
include(":components:infra-micro-etl")
include(":components:infra-trainoperation-etl")
include(":components:infra-basegraph-etl")
include(":components:infra-restriction-etl")
include(":components:infra-webapp")
```

Additionally, **not** a Gradle subproject but part of the repository:

- `components/schemas/` — the OpenAPI 3.1 schema library (`.yaml`) that generates the domain model.
- `components/doc/` — concept documents.
- `module-tests/` — Playwright + Cucumber (playwright-bdd) end-to-end test harness.
- `deployment/helm/` — Helm chart `rivm-infra`.

## 1.7 Major backend applications/services

| Service                    | Main class                                                                     | Type                                            | Port                  |
| -------------------------- | ------------------------------------------------------------------------------ | ----------------------------------------------- | --------------------- |
| `infra-query-svc`          | `de.hacon.tps.rise.infra.query.QueryServiceApplication`                        | Spring Boot Web (REST)                          | `${SERVER_PORT:9101}` |
| `infra-business-clock-etl` | `de.hacon.tps.rise.infra.businessclock.etl.InfraBusinessClockEtlApplication`   | Spring Boot AMQP consumer                       | none                  |
| `infra-micro-etl`          | `de.hacon.tps.rise.infra.micro.etl.InfraMicroEtlApplication`                   | Spring Boot AMQP consumer                       | none                  |
| `infra-basegraph-etl`      | `de.hacon.tps.rise.infra.basegraph.etl.InfraBaseGraphEtlApplication`           | Spring Boot AMQP consumer                       | none                  |
| `infra-trainoperation-etl` | `de.hacon.tps.rise.infra.trainoperation.etl.InfraTrainOperationEtlApplication` | Spring Boot AMQP consumer + `@EnableScheduling` | none                  |
| `infra-restriction-etl`    | `de.hacon.tps.rise.infra.restriction.RestrictionEtlApplication`                | Spring Boot AMQP consumer                       | none                  |
| `infra-common-lib`         | _(library — has an `application()` block but is consumed as `java-library`)_   | Shared library                                  | n/a                   |
| `platform`                 | _(Gradle `java-platform` / BOM)_                                               | Dependency constraints                          | n/a                   |

## 1.8 Major frontend applications / MFEs

There is **one** Angular application, `infra-webapp`. It is **not** a Module-Federation host —
the "MFEs" are **npm-packaged Angular libraries** consumed as ordinary standalone components.

| Package                       | Version | Components used                                                                                                                                                                                                                                                                                        | Where                                               |
| ----------------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------- |
| `@tps/rivm-common-components` | `2.9.1` | `RivmFrameComponent`, `RivmRibbonSectionComponent`, `FrameLeftOverlayPanelDirective`, `RivmContextMenuComponent`, `RivmTrainInformationPopoverComponent`, `RivmRestrictionPopoverComponent`, `RivmFilterPanelComponent`, `checkboxState`, `TabInstanceData`, `SidebarMenuItem`, `MenuItem`, `UserData` | Frame/shell, ribbon, popovers, filter panels        |
| `@tps/mfe-train-operation`    | `2.7.3` | `TrainListComponent` (`tps-mfe-train-list`), `TrainInfoPanelComponent` (`tps-mfe-train-info-panel`), `TrainEditPanelComponent` (`tps-mfe-train-edit-panel`), `provideTrainOperationIcons`, `TrainRun`, `TrainEditPanelData`                                                                            | Left docked train list, right slot TIP + edit panel |
| `@tps/rimfe-restriction`      | `0.7.0` | `RestrictionListComponent` (`tps-mfe-restriction-list`), `provideRestrictionIcons`, `Restriction`                                                                                                                                                                                                      | Left docked restriction list                        |
| `@tps/rimfe-aem`              | `1.1.1` | `AemEventsPanelComponent` (`tps-aem-events-panel`), `provideAemIcons`, `DetectionEvent`                                                                                                                                                                                                                | Left docked AEM events panel                        |

Local wrapper components in this repository:

- `MfeViewRestrictionListComponent` — [master-layout/mfe-view-restriction-list/mfe-view-restriction-list.component.ts](../infra/components/infra-webapp/src/app/master-layout/mfe-view-restriction-list/mfe-view-restriction-list.component.ts)
- `MfeViewTrainListComponent` — [master-layout/mfe-view-train-list/mfe-view-train-list.component.ts](../infra/components/infra-webapp/src/app/master-layout/mfe-view-train-list/mfe-view-train-list.component.ts)
  _(declared and tested but **not referenced** by `master-layout.component.html`, which embeds
  `tps-mfe-train-list` directly — see §3.4)_

## 1.9 External systems

| External system                                                                                                                                                                               | Interface                                                                                                                                                                            | Evidence                                                                                 |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------- |
| **RISE event bus** (upstream RIDS services: `de.hacon.tps.rids.business_clock`, `de.hacon.tps.rids.train_operation`, `de.hacon.tps.rids.restriction`, `bridge.infra`, `rise.bridge.tps_live`) | RabbitMQ topic exchange `rise.events`                                                                                                                                                | `sourceService` in every sample event JSON; `module-tests/config/rabbitmq.config.js`     |
| **`de.hacon.tps.rise:rise-api-utils` v13.1.0**                                                                                                                                                | Java library — supplies the AMQP listener infrastructure, DTOs (`TrainOperationEvent`, `RestrictionEvent`, …), `RISEApplicationContext`, signature validation                        | `gradle/libs.versions.toml`, all `build.gradle.kts`                                      |
| **`de.hacon.tps.rise:rise-infra-utils` v13.1.0**                                                                                                                                              | Java library — `MicroscopicInfra`, `Types.EdgeWithOffset`, `Types.EdgePath`; geometric resolution of km-addresses and segments to edges/coordinates                                  | `MicroscopicInfraService` in both `infra-trainoperation-etl` and `infra-restriction-etl` |
| **`rise-common` Helm library chart** (`oci://tps-helm.repo.imscloud.de`, `^2.x`)                                                                                                              | Provides `rise.common.deployment`, `rise.common.java-container`, `rise.common.connection.mongodb`, `rise.common.connection.rabbitmq`, `rise.common.endpoints`, `rise.common.service` | `deployment/helm/Chart.yaml`, all templates                                              |
| **API gateway / endpoint registry**                                                                                                                                                           | `deployment/helm/templates/endpoints.yaml` registers each path with `permissions: null`                                                                                              | See §15                                                                                  |
| **Keycloak SSO**                                                                                                                                                                              | Only referenced from the **E2E test harness** and a comment in `app.config.ts`                                                                                                       | `module-tests/playwright/e2e/common/pages/locators/LoginLocators.js`                     |
| **Artifactory (`repo.imscloud.de` / `tps-gradle-plugins`, `tps-helm.repo.imscloud.de`)**                                                                                                      | Build-time dependency source                                                                                                                                                         | `settings.gradle.kts`, `Chart.yaml`                                                      |
| **GitLab** (`gitlab.local.hacon.de/tps/live/nextgen/rivm/rivm-infra`)                                                                                                                         | Source hosting / CI                                                                                                                                                                  | `README.md`                                                                              |

## 1.10 Messaging system

**RabbitMQ**, consumed only (this repository contains **no producer**).

- Exchange: **`rise.events`**, type **topic**, `durable: true`
  (`module-tests/playwright/plugins/rabbitmq.js` asserts it; `infra-business-clock-etl/README.md`
  shows `--exchange rise.events --routing_key event.business_clock`).
- Queue names are **configured per ETL** via `rise.api.utils.event*handling.*.queue*name`
  properties (see §10.2).
- The actual `@RabbitListener`/binding machinery lives inside `rise-api-utils` and is **not present
  in this repository** — handlers are contributed via `META-INF/spring.factories`.

## 1.11 Databases

**MongoDB only.** Database name defaults to `risedb`
(`spring.mongodb.database=${MONGO_DATABASE:risedb}` in every service). Collections are all prefixed
`infra-rivm.` — see §7.

There is **no relational database, no SQL, no JPA, no Flyway/Liquibase migration** anywhere in the
repository.

Additional client-side storage:

- **IndexedDB** via Dexie — database `RIVM-INFRA`, object store `cache` (key `&key`).
- **localStorage** — key `infra-filter-state` (layer visibility + checkbox states).

## 1.12 Authentication / authorization

See §15 for the full trace. Summary: **none is implemented inside this repository.** The frontend
calls `POST {baseAuthUrl}/logout` and nothing else; the backend has no Spring Security dependency,
no filter, no `@PreAuthorize`; the Helm endpoint registry declares `permissions: null` for every
route.

## 1.13 Configuration management

- Backend: Spring Boot `application.properties` per service, every value overridable by an
  environment variable with an inline default (`${MONGO_HOST:localhost}` style).
- Frontend: compile-time `src/environments/environment*.ts` selected by Angular CLI
  `fileReplacements`.
- Runtime map behaviour (layers, zoom thresholds, tile sizes, polling frequency) is **data-driven
  from MongoDB** via `GET /configs` → `MapConfig`.
- Deployment: Helm `values.yaml` + `rise-common` library chart.

## 1.14 Deployment-related components

`deployment/helm/`:

- `Chart.yaml` — chart `rivm-infra`, version `0.0.0-dev`, appVersion `dev`, dependencies
  `rise-common ^2.x`, `mfe-train-operation 2.7.3`, `rimfe-restriction 0.7.0`.
- `values.yaml` — image repository `rise/rivm-infra`, `pullPolicy: IfNotPresent`, replica counts
  (all `1`), `querySvc.service.port: 9101`, `webapp.service.port: 80`, sub-chart values
  `deploymentType: "infra-rivm"` and `endpoints.apiPrefix: "infra"`.
- `templates/endpoints.yaml` — declarative gateway route registry (§6.9).
- `templates/*.yaml` — one Deployment per component; Java services use
  `rise.common.java-container`, the webapp uses `rise.common.container` with image suffix
  `frontend`.

Container entrypoint commands (from the templates):
`infra-basegraph-etl`, `infra-business-clock-etl`, `infra-micro-etl`, `infra-query-svc`,
`infra-restriction-etl`, `infra-trainoperation-etl`.

> **Observation:** `infra-query-svc`'s container only receives `rise.common.connection.mongodb`
> (no RabbitMQ) — consistent with it being a pure read service.
> `infra-trainoperation-etl` and `infra-restriction-etl` use `rise.common.container` (generic)
> whereas the other three ETLs use `rise.common.java-container`.

## 1.15 Technical explanation (one paragraph)

`rivm-infra` is a **CQRS-shaped, event-driven micro-service set**. Five Spring Boot AMQP consumers
subscribe to the RISE `rise.events` topic exchange through the vendor library `rise-api-utils`,
transform vendor DTOs into a locally-generated OpenAPI domain model
(`de.hacon.tps.rise.infra.common.generated.rivm.*`, produced at build time by
`org.openapi.generator` from `components/infra-common-lib/infra-model.yaml` which `$ref`s the
`components/schemas/**` YAML library), and write them into MongoDB collections through a
hand-rolled _pure repository interface + Mongo adapter_ pattern in `infra-common-lib`. A single
stateless read service, `infra-query-svc` (Spring Boot Web + springdoc), exposes seven REST
endpoints under context path `/api/infra/query`, wrapping results in `APIResponse<T>` or
`APIPaginatedResponse<T>`. The Angular 21 single-page app `infra-webapp` renders the network on an
**OpenLayers 10** canvas, uses **NgRx classic store** for the business clock / base graph / polling
slices and **NgRx Signal Stores** for everything newer (train positions, restrictions, map config,
locations, panel state, ribbon state, filter state, AEM panel), caches immutable payloads in
IndexedDB through Dexie, and drives incremental data loading with a 3-dimensional tile identifier
`"{x}_{y}_{yyyy-MM-dd'T'HH:mm}"` plus per-tile UUID versions that let the server return an empty
page when nothing changed.

---

# 2 — COMPLETE APPLICATION FLOW

The generic shape is:

```
USER → ANGULAR COMPONENT → ANGULAR SERVICE / SIGNAL STORE → HttpClient
     → (gateway) → Spring @RestController → @Service → Repository interface
     → Mongo adapter → MongoDB
     → domain POJO → APIPaginatedResponse/APIResponse → JSON
     → TypeScript interface → store → OpenLayers feature → pixels
```

The **write** side never involves the user of this app — it is driven exclusively by RabbitMQ.

---

## 2.1 Workflow W7 — Application bootstrap & map render

### 1. Trigger

User navigates to `/ui/infra` (gateway rewrite → `/`). Angular bootstraps.

### 2. Frontend component that starts it

- `main.ts` → `bootstrapApplication(AppComponent, appConfig)`.
- `appConfig` ([app.config.ts](../infra/components/infra-webapp/src/app/app.config.ts)) registers:
  - `provideHttpClient(withInterceptors(environment.interceptors))`
  - `provideRouter(routes, withHashLocation())` — **hash routing**
  - `provideStore({ businessClock, polling, customClock, edgeData })`
  - `provideEffects(BusinessClockEffects, EdgeDataEffects)`
  - `provideStoreDevtools({ maxAge: 25, logOnly: !isDevMode(), autoPause: true, trace: false })`
  - `APP_INITIALIZER` → `initializeApp(ConfigService)` → `ConfigService.loadConfig()`
  - `provideTrainOperationIcons('icons/')`, `provideRestrictionIcons('icons/')`, `provideAemIcons('icons/')`
- `AppComponent.ngOnInit()` → `IconService.register(ICONS)` (registers ~90 SVGs into
  `MatIconRegistry` from `icons/{name}.svg`).
- Router: `''` → `home` → `MasterLayoutComponent` with child `''` → `InfraContentComponent`.

### 3–6. APIs called during bootstrap

| Order | Caller                                                                                                                            | Method | Path                                                             | Request                       |
| ----- | --------------------------------------------------------------------------------------------------------------------------------- | ------ | ---------------------------------------------------------------- | ----------------------------- |
| a     | `MasterLayoutComponent.ngOnInit()` → `store.dispatch(loadBusinessClockData())` → `BusinessClockEffects`                           | `GET`  | `{baseUrl}/business-clock`                                       | none                          |
| b     | `InfraContentComponent.loadConfigurations()` → `MapConfigStore.loadMapConfig()` → `MapConfigService`                              | `GET`  | `{baseUrl}/configs`                                              | none                          |
| c     | `InfraContentComponent.loadConfigurations()` → `LocationsStore.loadLocations()` → `LocationTrackCoordinatesApiService`            | `GET`  | `{baseUrl}/location-track-coordinates?pageNumber=n&pageSize=100` | none (repeated for all pages) |
| d     | `InfraContentComponent.loadEdgeDataAndSubscribe()` → `store.dispatch(loadEdgeData())` → `EdgeDataEffects` → `BaseGraphApiService` | `GET`  | `{baseUrl}/basegraph`                                            | none                          |

`{baseUrl}` = `environment.baseUrl` (`../../api/infra/query` in production).

### 7. Backend controllers

- `BusinessClockController.getBusinessClock()`
- `ConfigController.getAllMapConfigs()`
- `LocationTrackCoordinatesController.getLocationTrackCoordinates(pageNumber, pageSize)`
- `BaseGraphController.getAllBaseGraphDetails(pageNumber, pageSize)`

### 8–11. Service → repository → database

| Controller                           | Service                                                         | Repository interface                                           | Mongo adapter                                                                                                        | Collection / operation                                  |
| ------------------------------------ | --------------------------------------------------------------- | -------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| `BusinessClockController`            | `BusinessClockService.getBusinessClock()`                       | `BusinessClockRepository.findAll()`                            | `MongoBusinessClockRepositoryCustomImpl` → `MongoBusinessClockRepository.findAll()`                                  | `infra-rivm.business-clock`, full scan, `clocks.get(0)` |
| `ConfigController`                   | `ConfigService.getAllMapConfigs()`                              | `MapConfigRepository.findAll()`                                | `MongoMapConfigRepositoryCustomImpl`                                                                                 | `infra-rivm.map-config`, full scan                      |
| `LocationTrackCoordinatesController` | `LocationTrackCoordinatesService.getLocationTrackCoordinates()` | `TrackCoordinatesRepository.findLocationsWithTracks(pageable)` | `MongoTrackCoordinatesRepositoryCustomImpl` — **two aggregation pipelines + one `findByLocationSubEntityData_IdIn`** | `infra-rivm.track-coordinates`                          |
| `BaseGraphController`                | `BaseGraphService.getAllBaseGraphs()`                           | `BaseGraphRepository.findAll(pageable)`                        | `MongoBaseGraphRepositoryCustomImpl`                                                                                 | `infra-rivm.basegraph`                                  |

The `findLocationsWithTracks` implementation is worth spelling out
([MongoTrackCoordinatesRepositoryCustomImpl.java](../infra/components/infra-common-lib/src/main/java/de/hacon/tps/rise/infra/common/repository/mongodb/MongoTrackCoordinatesRepositoryCustomImpl.java)):

1. `Criteria`: `locationSubEntityData != null AND locationSubEntityData.id != null`.
2. **Count aggregation** — `match` → `group("locationSubEntityData.id")` → `count().as("total")`.
3. If `0` → empty `PageImpl`.
4. **Page aggregation** — `match` → `group("locationSubEntityData.id")` → `sort(asc(_id))` →
   `skip(pageable.getOffset())` → `limit(pageable.getPageSize())` → list of location IDs.
5. `mongoRepository.findByLocationSubEntityData_IdIn(pageLocationIds)`.
6. Group in Java by `locationSubEntityData.id`, sort tracks by `trackSubEntityData.id`,
   build `LocationWithTracks { id, name, shortName, tracks[] }` where each
   `LocationWithTracksTracksInner { id, name, shortName, description, businessRefs, nodeCoordinates }`.

### 12. RabbitMQ interaction

**None** on this path — `infra-query-svc` has no AMQP dependency in its `build.gradle.kts`
(only `spring-boot-starter-amqp-test` for tests).

### 13. Other services involved

None. `infra-query-svc` calls no other service.

### 14. Response formats

`GET /business-clock`:

```json
{
  "data": {
    "businessTime": "2026-08-31T09:15:00Z",
    "businessTimeZone": "Europe/London",
    "serverTime": "2026-08-31T09:15:00.123Z",
    "mode": "REALTIME"
  }
}
```

`GET /configs`:

```json
{ "data": [ { "id": "INFRA_MAP_01", "mapType": "OCTOLINEAR", "mapName": "…",
              "coordinateSystem": "CARTESIAN", "minZoomLevel": 0, "maxZoomLevel": 100,
              "defaultZoom": 20, "layers": [ … ] } ] }
```

`GET /basegraph` and `GET /location-track-coordinates`:

```json
{ "data": [ … ],
  "meta": { "page": { "pageNumber": 0, "size": 1000, "totalElements": 3, "totalPages": 1 },
            "dataTileVersions": [] } }
```

### 15. How the frontend consumes it

- **Business clock** → `BusinessClockApiService.getBusinessClockApiData()` maps
  `response.body?.data` → `loadBusinessClockDataSuccess({ businessClock })` →
  `businessClockReducer` also computes a `timeWindow` via `calculateTimeWindow()`
  (`-INFRA_VIEW.pastTimeIntervalMin = -10 min` … `+INFRA_VIEW.futureTimeIntervalMin = +50 min`,
  plus `slots[]` = one `yyyy-MM-ddTHH` string per hour in between).
- **Map config** → `MapConfigStore.mapConfig` signal. `InfraContentComponent` extracts layers by
  id: `baseGraph`, `trains`, `restrictions`, `locations`, `platforms`.
- **Locations** → `LocationsStore.locations` signal → `MapService.loadLocationLabels(...)`.
- **Base graph** → NgRx `edgeData` slice → `OpenLayerInfraUtility.extractNodes/extractEdges` →
  `MapService.loadGraphData(nodes, edges)` → `fitViewToData()` → `loadOverviewMapData()`.

### 16. UI changes

Map canvas paints the network; `View.fit(extent, {padding:[50,50,50,50], maxZoom:10})` is applied
and the resulting zoom becomes the **minimum zoom** (`view.setMinZoom(currentZoom)`), so the user
cannot zoom out beyond the full network. The frozen overview mini-map appears. A loading spinner
overlay (`loading$ | async`) is shown while `edgeData.loading` is true.

### 17. Error handling

- `EdgeDataEffects` → `catchError` → `loadEdgeDataFailure({ error })` → `edgeDataReducer` sets
  `error` and `loaded:false`; `InfraContentComponent.error$` is bound but the template does **not**
  render it (only `loading$` is used). → **latent gap**.
- `MapConfigStore.loadMapConfig` / `LocationsStore.loadLocations` `catchError` → `patchState({error})`,
  return `of([])`.
- `LocationTrackCoordinatesApiService.fetchPage` → `retry({ count: 3, delay: 1000 })`.
- `BusinessClockApiService` → `catchError` → `throwError(new Error('Error fetching data: …'))`.

### 18. Validation

Client-side: none on these GETs. Server-side: `@Min/@Max` bean validation on `pageNumber`/`pageSize`
(see §6).

### 19. Permissions/authorization

None (`permissions: null` in `endpoints.yaml`).

---

## 2.2 Workflow W8 — Live train position polling (the core loop)

### 1. Trigger

`InfraContentComponent.handleResolutionChange()` (OpenLayers `change:resolution`) or
`handleMoveEnd()` (`moveend`), or a business-clock tick, or the time slider.

### 2. Component

`InfraContentComponent` → `TrainPollingCoordinatorService`.

### 3. Tile computation (before any HTTP)

`TileManagementService.calculateTileBoundaries(nodes, trainsLayer)`
([tile-management.service.ts](../infra/components/infra-webapp/src/app/services/tile-management/tile-management.service.ts)):

```
minX/minY/maxX/maxY   = bounding box over ALL InfraNode.x / .y
xSize                 = trainsLayer.tileSize.width
ySize                 = trainsLayer.tileSize.height
tileMinX = floor(minX / xSize) * xSize
tileMinY = floor(minY / ySize) * ySize
tileMaxX = ceil (maxX / xSize) * xSize
tileMaxY = ceil (maxY / ySize) * ySize
tilesX   = ceil((tileMaxX - tileMinX) / xSize)
tilesY   = ceil((tileMaxY - tileMinY) / ySize)
```

Returns `null` when `nodes.length === 0`, `trainsLayer` is falsy, or `xSize`/`ySize` is 0/undefined.

`TileManagementService.getVisibleTiles(extent, tileResult, timestamp)`:

```
startTileX = floor((extentMinX - tileMinX) / xSize)
endTileX   = ceil ((extentMaxX - tileMinX) / xSize)
startTileY = floor((extentMinY - tileMinY) / ySize)
endTileY   = ceil ((extentMaxY - tileMinY) / ySize)
for i in [max(0,startTileX) , min(tilesX,endTileX))
  for j in [max(0,startTileY) , min(tilesY,endTileY))
     tileId = `${tileMinX + i*xSize}_${tileMinY + j*ySize}_${timestamp}`
```

`timestamp` comes from `TimeCalculationService.calculateAdjustedTime(baseBusinessTime, offsetMin, timeSpanSecs)`:

- `applyTimeOffsetInUtc()` — `new Date(base).getTime() + offsetMinutes*60000` → `toISOString()`.
- `roundToInterval(ts, intervalMinutes = timeSpanSecs/60)` — splits on `T` and `:`, floors minutes
  to the interval, returns `"yyyy-MM-ddTHH:mm"` (**no seconds, no `Z`**).
- `timeSpanSecs` = `trainsLayer.tileSize.timeSpanSecs`, fallback `900` (15 min).

### 4–6. HTTP request

`TrainPositionService.getTrainPositions(tiles, pageNumber = 0, pageSize = 1000)`:

- **Method:** `POST`
- **Path:** `{baseUrl}/trainpositions`
- **Query:** `pageNumber`, `pageSize`
- **Body:** `TileVersion[]` mapped to `{id}` or `{id, version}` — the `version` key is omitted
  entirely when `undefined` (first request for a tile).

```jsonc
// first poll
[ { "id": "125000_-10000_2026-08-31T09:15" }, { "id": "130000_-10000_2026-08-31T09:15" } ]
// later polls
[ { "id": "125000_-10000_2026-08-31T09:15", "version": "8f1c…-uuid" } ]
```

### 7. Backend controller

`TrainPositionController.getPositions(@RequestBody @Valid @NotEmpty List<@Valid DataTile> tiles,
Integer pageNumber, Integer pageSize)` — `@PostMapping` on `@RequestMapping("/trainpositions")`.

### 8–9. Service + business logic

`TrainPositionService.getModifiedTrainPositionsByTiles(tiles, pageNumber, pageSize)`
([TrainPositionService.java](../infra/components/infra-query-svc/src/main/java/de/hacon/tps/rise/infra/query/service/TrainPositionService.java)):

1. `validateDataTiles(tiles)` — throws `BadRequestException("Tile ID must not be null or empty",
ErrorCodes.INVALID_DATA_TILE_ID /* "20001" */)` if any `id` is null/empty.
2. `tileMap = tiles.stream().collect(toMap(DataTile::getId, identity()))`
   — **note:** duplicate tile IDs in the request would throw `IllegalStateException` from
   `Collectors.toMap`, which the `GlobalExceptionHandler` maps to `500`.
3. `dataTileRepository.findAllById(tileMap.keySet())` → filter
   `hasTileVersionChanged(dt, tileMap)` = `!StringUtils.equals(requestVersion, storedVersion)` →
   `updatedTileVersions : Map<tileId, storedVersion>`.
4. If `updatedTileVersions` is empty → `result = Page.empty()` (short-circuit; **no train-position
   query at all**).
5. Else `trainPositionRepository.findByDataTileIdsIn(updatedTileVersions.keySet(),
PageRequest.of(pageNumber, pageSize, Sort.by(ASC, "id", "trainServiceId")))`.
6. `meta = apiMapper.mapPageToMetaPage(result, updatedTileVersions)` — `meta.dataTileVersions` is a
   **list containing exactly one map**.
7. Return `new APIPaginatedResponse<>(result.getContent(), meta)`.

### 10–11. Repository / database

`MongoTrainPositionRepositoryCustomImpl.findByDataTileIdsIn` → Spring Data derived query
`findByDataTileIdsIn(Collection<String>, Pageable)` on collection `infra-rivm.train-position`,
i.e. `{ dataTileIds: { $in: [...] } }`.

Indexes created at ETL start-up by `IndexConfig` (see §7.9).

### 12. RabbitMQ

None on the read path.

### 14. Response format

```jsonc
{
  "data": [
    {
      "id": "TrainOperation-9N70-KNGX-DONC-sub-entity-ID-8",
      "trainServiceId": "TrainOperation-9N70-KNGX-DONC",
      "dataTileIds": ["125000_-10000_2026-08-31T09:15"],
      "fromTime": "2026-08-31T09:14:10Z",
      "toTime": "2026-08-31T09:16:00Z",
      "runningType": "FORECAST",
      "activityId": "sub-entity-ID-8",
      "activityType": "ARRIVAL",
      "origin": "entity-id-2",
      "destination": "entity-id-5",
      "coordinates": { "x": 125190, "y": -6035 },
    },
  ],
  "meta": {
    "page": {
      "pageNumber": 0,
      "size": 1000,
      "totalElements": 1,
      "totalPages": 1,
    },
    "dataTileVersions": [{ "125000_-10000_2026-08-31T09:15": "8f1c…-uuid" }],
  },
}
```

### 15. Frontend consumption

`TrainPositionStore.startPolling` (`rxMethod<void>`,
[train-position.store.ts](../infra/components/infra-webapp/src/app/signal-store/train-position.store.ts)):

```
merge( interval(pollingIntervalMs).pipe(startWith(0)), fetchNow$ )
  .pipe(takeUntil(stopPolling$),
        switchMap(() => tiles.length === 0 ? EMPTY
                        : trainPositionService.getTrainPositions(tiles)))
```

On each response:

- `versionsMap = response.meta?.dataTileVersions?.[0] || {}`
- every tracked tile's `version` is replaced when present in `versionsMap`
- positions merged by `id`: existing rows replaced, unseen rows appended
  (**positions are never removed by the store** — filtering happens at render time)
- `patchState({ positions, tiles, loading:false, error:null })`

`catchError` → `patchState({ error: error.message || 'Failed to fetch train positions', loading:false })`, `return EMPTY` (the polling loop survives).

### 16. UI changes

`InfraContentComponent.updateTrainDisplay()`:

1. `TimeCalculationService.filterPositionsByTime(allPositions, adjustedTimestamp)` — keeps rows where
   `fromTime <= target <= toTime`, then **per `trainServiceId` keeps the row with the earliest
   `toTime`** (so at a shared boundary the _ending_ position wins).
2. `MapService.updateTrainPositions(filtered)` → clears `trainPositionsVectorSource`,
   `OpenLayerClusterUtility.createTrainPositionFeatures(...)`, `clusterSource.refresh()`.
3. `updateTrainVisibility()` → `setTrainLayerVisible(currentMapZoom >= selectedZoomLevel && filterStateStore.showTrains())`.

### 17. Error handling

Store-level `catchError` only (no toast, no retry backoff). The polling `interval` continues.

### 18. Validation

Server: `@NotEmpty` on the body list; `@Min(1) @Max(1000)` on `pageSize`;
`validateDataTiles()` on tile IDs.
Client: `TrainPositionStore` refuses to call when `tiles.length === 0` (returns `EMPTY`).

### 19. Authorization

`permissions: null`.

---

## 2.3 Workflow W9 — Restriction polling

- **Trigger:** `InfraContentComponent.handleRestrictionsZoomChange(zoom)` — polls when
  `zoom > restrictionsLayer.minZoom && mapStateStore.isGraphLoaded() && !!baseBusinessTime`.
- **Store:** `RestrictionsStore.startPolling(initialBusinessTime)` — `interval(pollingIntervalMs)`
  with `startWith(0)`, `takeUntil(stopPolling$)`; each tick calls
  `restrictionApiService.getRestrictionData(store.currentBusinessTime())`.
- **`currentBusinessTime`** is kept in sync with the **slider-adjusted** time by
  `InfraContentComponent.updateTimestamps()` → `restrictionsStore.setCurrentBusinessTime(result.adjustedUtcTime)`.
- **API:** `GET {baseUrl}/restrictions?effectiveAt=<ISO>&pageNumber=0&pageSize=100`.
- **Controller:** `RestrictionController.getRestrictionsByTime(Instant effectiveAt, Integer pageNumber, Integer pageSize)`.
- **Service:** `RestrictionService.getRestrictionsByEffectiveTime(...)` →
  `PageRequest.of(pageNumber, pageSize, Sort.by(DESC, "lastModified"))` →
  `restrictionRepository.findByEffectiveTime(effectiveAt, pageable)`.
- **Mongo query** (`MongoRestrictionRepository`, SpEL-templated):
  ```json
  {
    "restrictionData.effectiveTimePeriod.startTime": {
      "$lte": "<effectiveAt.toString()>"
    },
    "restrictionData.effectiveTimePeriod.endTime": {
      "$gte": "<effectiveAt.toString()>"
    }
  }
  ```
  i.e. a **lexical string comparison** against ISO-8601 strings (both stored fields are `String`).
- **Response normalisation:** `RestrictionApiService.normalizeApiResponse()` accepts either a bare
  array or `{data, meta}`; per restriction it sets `id = restriction.id ?? restriction._id` and
  defaults `impacts` / `edgePaths` / `pathEdges` / `pathCoordinates` to `[]`.
- **Render:** `RestrictionsStore.visibleRestrictionInfos` (computed) →
  `InfraContentComponent.updateRestrictionsDisplay(infos)` → `MapService.updateRestrictions(infos)`
  → `OpenLayerRestrictionUtility.updateRestrictionFeatures(...)`.

---

## 2.4 Workflow W10 — Time travel

Two independent mechanisms:

**(a) Map time-offset slider** (`infra-content.component.html`, `input[type=range]`,
`min = INFRA_VIEW.minTimeOffsetSeconds = -600`, `max = 3000`, `step = 5`):

```
onTimeOffsetChange() / incrementTime() / decrementTime() / resetToNow()
  → updateTimestamps()
      adjustedTimestamp   = applyTimeOffsetInUtc(baseBusinessTime, offsetSeconds/60)
      restrictionsStore.setCurrentBusinessTime(adjustedTimestamp)
      roundedTimestamp    = roundToInterval(adjusted, timeSpanSecs/60)
      if (roundedTimestamp changed) → recalculateTiles()  → new tile IDs → new POST
      updateTrainDisplay()                                 → re-filter existing positions
```

This **never touches the NgRx clock** — it is a purely local view offset.

**(b) Header date/time pickers** (`MasterLayoutComponent.onClockChange`):

```
FrameClockChange
  mode === CLOCK_CHANGE_MODE.live         → handleResetDateTime → dispatch(resetCustomClock())
  value.includes(':')                     → handleTimeChange    → dispatch(setCustomClockDateTime({date, time:`${date}T${time}`, businessTimeZone}))
  otherwise                               → handleDateChange    → dispatch(setCustomClockDateTime({date, time: businessTime, businessTimeZone}))
```

`customClockReducer` (`business-clock.reducer.ts`) parses with `moment(date, 'DD.MM.YYYY')`,
composes `YYYY-MM-DDTHH:mm:ss`, converts to UTC with `moment.tz(...).utc()`, recomputes
`timeWindow`, and sets `customClockEnabled: true`.

`selectEffectiveClock` then returns the **custom** clock when `customClockEnabled`, otherwise the
polled business clock. `InfraContentComponent.subscribeToBusinessClock()` listens to
`selectEffectiveClock`, so a header change immediately re-drives `updateTimestamps()`.

---

## 2.5 Workflow W11 — Open Train Information Panel (TIP)

| Step        | Detail                                                                                                                                                                                                                                                                                         |
| ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Trigger     | Double-click on a single train feature on the map, **or** `(openTrainInfo)` from `tps-mfe-train-list`                                                                                                                                                                                          |
| Component   | `InfraContentComponent.handleTrainDoubleClick(evt)` / `MasterLayoutComponent.onOpenTrainInfo(event)`                                                                                                                                                                                           |
| Guard       | Returns immediately if `panelStateStore.overlayPanel()` is already `tip` or `edit-panel`                                                                                                                                                                                                       |
| Resolution  | `MapService.resolveTrainServiceIdAtPixel(evt)` → `getClusterFeatureAtPixel(pixel)`; returns `null` for multi-train clusters                                                                                                                                                                    |
| State       | `MapService.setSelectedTrain(id)`; `PanelStateStore.openTIP({ trainServiceId, trainNumber })`                                                                                                                                                                                                  |
| Side effect | `InfraContentComponent` `effect()` → `handlePanelStateChange()` captures `mapCenterBeforeTip`, pushes `{panTo: selectedTrainCoordinate}` into `mapResizeSubject` (debounced `MAP_VIEW_CONFIG.panelResizeDebounceMs = 350 ms`) → `map.updateSize()` + `MapService.panToKeepVisible(coord, 0.5)` |
| UI          | `master-layout.component.html` renders `<tps-mfe-train-info-panel [baseUrl]="mfeBaseUrl" [trainServiceId]="…" [businessClockTimezone]="…" [containerManaged]="true" …>` in `frameRightSlot`                                                                                                    |
| API         | **Executed inside `@tps/mfe-train-operation`** against `mfeBaseUrl` — the host does not issue it. Demo-mode interception shows the shape: `/train-operation/query/train-operations/{trainServiceId}` and `/compositions`                                                                       |
| Close       | `(closePanel)` → `PanelStateStore.closeOverlay()` → `handlePanelStateChange` restores `mapCenterBeforeTip` via `MapService.restoreViewCenter()`                                                                                                                                                |

---

## 2.6 Workflow W12 — Edit a train

```
Ribbon "Edit" item click ─┐
map right-click → context menu ─┴→ PanelStateStore.openEditPanel({trainServiceId, trainNumber, operatingDay, editType})
                                    ├ overlayPanel = 'edit-panel'
                                    ├ restrictionListState = 'none'
                                    ├ ribbonAction = editType
                                    └ isEditPanelDirty = false
```

1. `MasterLayoutComponent` `effect(_editPanelCloseEffect)` → `syncApplyEditsSection(ctx)` →
   `isApplyEditsSection.set(true)` and `ribbonStateStore.setRibbonExpanded(true)` → the ribbon
   switches to the single **Apply Edits** section (`applyEditsRibbon()`).
2. `tps-mfe-train-edit-panel` emits `(editedTrainData)` → `handleEditPanelDataChanged` →
   `lastEditedField.set(editedField)`, `panelState.setEditPanelDirty(true)`.
   `buildApplyEditsItems(isEditPanelDirty)` enables the **Apply** button only when dirty.
3. User clicks **Apply** → `handleApplyEditAction` → `panelState.requestApply()` →
   `applyRequested = true`.
4. `effect(_applyRequestedEffect)` → `submitPendingEdit(ctx)`:
   - `panelState.clearApplyRequest()`
   - `payload = buildEditPayload(lastEditedField(), panelState.ribbonAction())`
   - `editTrainApiPayload.set(payload)` — the payload is an **input** to the MFE, which performs
     the HTTP call.
5. `buildEditPayload` (train-edit.handlers.ts):

| `ribbonAction`   | Produced `EditableTrainDetails`                                                                                                                                                                  |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `change_track`   | `{ trainServiceId, locationId, editRunningLocationTrack: { currentLocationTrack: previousValue, requestedLocationTrack: typeof currentValue === 'string' ? currentValue : currentValue.name } }` |
| `arrival_time`   | `{ trainServiceId, locationId, editRunningArrivalTime: { currentSetTime: previousValue, requestedTime: currentValue } }`                                                                         |
| `departure_time` | `{ trainServiceId, locationId, editRunningDepartureTime: { currentSetTime: previousValue, requestedTime: currentValue } }`                                                                       |
| anything else    | `null`                                                                                                                                                                                           |

6. MFE emits `(editedTrainApiResponse)` → `handleEditPanelSaved(ctx, result)`:
   - `'success'` → `panelState.bumpTrainDataVersion()` + `panelState.closeOverlay()`
   - `'error'` → `snackbarAlertService.showError(COMMON_ERROR_MESSAGES)`
   - both → `editTrainApiPayload.set(null)`, `lastEditedField.set(null)`

> **The concrete HTTP verb/path of the train edit is inside `@tps/mfe-train-operation` and is
> `NOT FOUND / NOT DETERMINED` from this repository.**

---

## 2.7 Workflow W13 — Activate / Deactivate a restriction

```
Sidebar "restrictions" → PanelStateStore.openRestrictionListCollapsed()
                       → ribbonStateStore.setRibbonExpanded(true)
Restriction list expand → handleExpandRestrictionList → openRestrictionListExpanded()
                       → ribbonStateStore.setSelectedRestriction(null)
Grid row select        → MfeViewRestrictionListComponent.onRestrictionSelected(r)
                       → ribbonStateStore.setSelectedRestriction({ id, state })
MFE emits actionable   → onSelectionActionable(bool) → setRestrictionActionable(bool)
```

Ribbon enablement — `buildRestrictionActionItems(selected, isActionable)`
([master-layout.ribbon-sections.ts](../infra/components/infra-webapp/src/app/master-layout/master-layout.ribbon-sections.ts)):

```
isActive = !!selected && ACTIVE_RESTRICTION_STATES.has(selected.state.trim().toLowerCase())
           // ACTIVE_RESTRICTION_STATES = { 'effective', 'active' }
Activate   → disabled = !selected || isActive  || !isActionable
Deactivate → disabled = !selected || !isActive || !isActionable
Cancel     → always disabled (out of scope)
```

Action — `handleRestrictionAction(ctx, item)`:

```
newState = item.action === 'activate_restriction' ? 'ACTIVE' : 'INACTIVE'
request$ = ctx.getRestrictionListView()?.requestRestrictionStateChange(selected.id, newState)
if (!request$)  → snackbarAlertService.showError(COMMON_ERROR_MESSAGES)
else request$.subscribe(ok => { if (!ok) showError(COMMON_ERROR_MESSAGES) })
```

`MfeViewRestrictionListComponent.requestRestrictionStateChange` performs a **duck-typed** lookup of
`requestRestrictionStateChange` on the `RestrictionListComponent` instance and returns `of(false)`
when the method is absent — the actual PATCH is issued **inside `@tps/rimfe-restriction`**.

> The host `AGENTS.md` of `rivm-ui-components` documents the shape as
> `PATCH {baseUrl}/api/restriction/cmd/restrictions/{id}` with body `{ id, state: 'EFFECTIVE' | 'CANCELLED' }`.
> **That is library documentation, not code in this repository — treat as unverified here.**

---

## 2.8 Workflow W14 — Show/hide layers

```
Ribbon "Show/Hide" item → handleShowHideAction → openLeftOverlayPanel(ctx, 'infraElements'|'trainOperations')
     panelState.closeMinimizedLists(); aemPanelStore.close(); leftPanelStore.open(panel)
Filter panel checkbox   → InfraElementsPanelComponent / TrainOperationsPanelComponent
     .onPanelSelectionChanged(RivmFilterPanelToggleEvent)
        - "All" item propagates CHECKED/UNCHECKED to every enabled sibling
        - otherwise syncAllCheckbox() recomputes "All"
        - persistCheckboxState() → FilterStateStore.set{InfraElements|TrainOperations}CheckboxState
        - emits InfraPanelSelectionEvent
Host                    → handleInfraElementsSelectionChanged / handleTrainOperationsSelectionChanged
     → FilterStateStore.setShowLocationTracks / setShowPlatforms / setShowTrains / setShowRestrictions
InfraContentComponent   → effect() → MapService.setLocationLayerVisible / setPlatformLayerVisible
                                    / updateTrainVisibility() / updateRestrictionsVisibility()
FilterStateStore hook   → effect() → localStorage.setItem('infra-filter-state', JSON.stringify(state))
```

Mapping table (`filter-panel.handlers.ts`):

| Panel                   | item id                | Store setter            | Map layer                          |
| ----------------------- | ---------------------- | ----------------------- | ---------------------------------- |
| Infrastructure Elements | `infra-all`            | all of the below        | both label layers                  |
| Infrastructure Elements | `station-information`  | `setShowLocationTracks` | `locationLabelLayer`               |
| Infrastructure Elements | `platforms`            | `setShowPlatforms`      | `trackLabelLayer`                  |
| Train Operations        | `train-operations-all` | all of the below        | trains + restrictions              |
| Train Operations        | `trains`               | `setShowTrains`         | cluster / non-cluster train layers |
| Train Operations        | `restrictions`         | `setShowRestrictions`   | `restrictionsVectorLayer`          |

---

## 2.9 Workflow W16 — Sign out

`MasterLayoutComponent.signOut()` → `handleSignOut(ctx)` → `LogoutApiService.logout()`:

- `POST {environment.baseAuthUrl}/logout`, body `{}`, `observe:'response'`, `responseType:'text'`
- `catchError` → `throwError(new Error('Error fetching data: …'))`
- `.subscribe()` with **no next/error callback** → an error would surface as an unhandled RxJS error.
- **No navigation, no token clearing, no state reset is performed by this application.**

---

# 3 — FRONTEND — ANGULAR / MFEs

## 3.1 The single Angular application

| Property            | Value                                                                                                                                                  | Evidence                                 |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------- |
| **Name**            | `infra-webapp`                                                                                                                                         | `angular.json` → `projects.infra-webapp` |
| **Location**        | `components/infra-webapp/`                                                                                                                             | —                                        |
| **Purpose**         | RIVM INFRA live visualisation SPA                                                                                                                      | `README.md`, `AGENTS.md`                 |
| **Entry point**     | `src/main.ts` → `bootstrapApplication(AppComponent, appConfig)`                                                                                        | `main.ts`                                |
| **Root component**  | `AppComponent` (`app-root`), template = `<router-outlet />` only                                                                                       | `app.component.ts/.html`                 |
| **Prefix**          | `app`                                                                                                                                                  | `angular.json`                           |
| **Source root**     | `src`                                                                                                                                                  | `angular.json`                           |
| **Output**          | `dist`                                                                                                                                                 | `angular.json`                           |
| **Builder**         | `@angular/build:application`                                                                                                                           | `angular.json`                           |
| **Package manager** | `yarn@4.5.0`                                                                                                                                           | `package.json`                           |
| **Framework**       | Angular `^21.2.0`                                                                                                                                      | `package.json`                           |
| **TypeScript**      | `~5.9.0`                                                                                                                                               | `package.json`                           |
| **Map engine**      | `ol` (OpenLayers) `^10.10.0`                                                                                                                           | `package.json`                           |
| **State**           | `@ngrx/store`, `@ngrx/effects`, `@ngrx/signals`, `@ngrx/store-devtools` — all `^21.0.0`; `@angular-architects/ngrx-toolkit ^21.0.0` for `withDevtools` | `package.json`                           |
| **Grid**            | `ag-grid-angular` / `ag-grid-community` `^32.3.3`                                                                                                      | `package.json`                           |
| **IndexedDB**       | `dexie ^4.4.2`                                                                                                                                         | `package.json`                           |
| **Time**            | `moment-timezone ^0.5.46`                                                                                                                              | `package.json`                           |
| **i18n**            | `@angular/localize`; source locale `en-US` (`baseHref /tps/ui/infra/`), locale `fr` (`src/locale/messages.fr.xlf`)                                     | `angular.json`                           |
| **Global styles**   | `src/styles.scss`, `ol/ol.css`, `ag-grid.css`, `ag-theme-alpine.css`                                                                                   | `angular.json`                           |
| **Assets**          | `public/**`, plus `@tps/rivm-common-components` `icons/`, `fonts/`, `scss/` (→ `common-scss/`)                                                         | `angular.json`                           |
| **Build budgets**   | initial warn 500 kB / error **6 MB**; component style warn 600 kB / error 900 kB                                                                       | `angular.json`                           |

### npm scripts

```
ng, start, start:demo, start:demo-fr, build (ng build --localize),
watch, test:local, test (ChromiumHeadless, --no-watch --code-coverage),
lint (ng lint --max-warnings 0), extract-i18n
```

Gradle integration: `components/infra-webapp/build.gradle.kts` applies only
`de.hacon.tps.convention.node.angular`.

## 3.2 Routing

[src/app/app.routes.ts](../infra/components/infra-webapp/src/app/app.routes.ts):

```typescript
export const routes: Routes = [
  { path: "", pathMatch: "full", redirectTo: "home" },
  {
    path: "home",
    component: MasterLayoutComponent,
    children: [
      { path: "train-list", redirectTo: "", pathMatch: "full" },
      { path: "restriction-list", redirectTo: "", pathMatch: "full" },
      { path: "", component: InfraContentComponent },
    ],
  },
  { path: "**", redirectTo: "home" },
];
```

- `withHashLocation()` is used, so URLs are `…/ui/infra/#/home`.
- **There is exactly one visual screen.** `train-list` and `restriction-list` are legacy route
  aliases that redirect back to the map; panel visibility is driven by `PanelStateStore` signals,
  not the router.
- **No route guards exist** (`ng g guard` was never used; no `CanActivate` anywhere).

## 3.3 Guards, interceptors, state, shared libs

| Concern                               | Status                                                                                                                                                                                                                                          |
| ------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Guards**                            | **NONE.** `NOT FOUND` — no file matches `*.guard.ts`.                                                                                                                                                                                           |
| **HTTP interceptors**                 | Exactly one: `httpMockInterceptor` (`src/app/mocks/http-mock.interceptor.ts`), registered **only** via `environment.demo.ts` → `interceptors: [httpMockInterceptor]`. In `environment.ts` and `environment.development.ts`, `interceptors: []`. |
| **Error interceptor**                 | **NONE.**                                                                                                                                                                                                                                       |
| **Auth interceptor**                  | **NONE** — no `Authorization` header is ever attached.                                                                                                                                                                                          |
| **Classic NgRx slices**               | `businessClock`, `polling`, `customClock`, `edgeData` (registered in `app.config.ts`)                                                                                                                                                           |
| **Registered-but-unregistered slice** | `tabs` — `tabs.action.ts`, `tabs.reducer.ts`, `tabs.selector.ts`, `tabs.state.ts` all exist and are unit-tested, but `tabsReducer` is **not** passed to `provideStore(...)`. Dead code.                                                         |
| **Signal stores**                     | 9 (see §3.5)                                                                                                                                                                                                                                    |
| **Shared library**                    | `@tps/rivm-common-components` (frame, ribbon, popovers, filter panel, context menu, checkbox, `TabInstanceData`)                                                                                                                                |
| **Shared component in-repo**          | `SnackbarContentComponent` (`src/app/shared/components/snackbar-content/`)                                                                                                                                                                      |
| **Pipes / directives (own)**          | **NONE** in-repo; `FrameLeftOverlayPanelDirective` comes from the library                                                                                                                                                                       |
| **WebSocket / SSE**                   | **NONE.** All liveness is HTTP polling.                                                                                                                                                                                                         |
| **Direct RabbitMQ from the browser**  | **NONE** and architecturally impossible here.                                                                                                                                                                                                   |

## 3.4 Component inventory

| Selector                        | Class                             | File                                                     | Change detection | Purpose                                                                             |
| ------------------------------- | --------------------------------- | -------------------------------------------------------- | ---------------- | ----------------------------------------------------------------------------------- |
| `app-root`                      | `AppComponent`                    | `app.component.ts`                                       | default          | Bootstrap shell, icon registration                                                  |
| `app-master-layout`             | `MasterLayoutComponent`           | `master-layout/master-layout.component.ts`               | default          | Application shell: frame, header, sidebar, ribbon, left/right slots                 |
| `app-infra-content`             | `InfraContentComponent`           | `master-layout/infra-content/infra-content.component.ts` | **OnPush**       | The OpenLayers map view + time slider + clustering toggle + popovers + context menu |
| `app-mfe-view-restriction-list` | `MfeViewRestrictionListComponent` | `master-layout/mfe-view-restriction-list/…`              | default          | Wrapper around `tps-mfe-restriction-list`                                           |
| `app-mfe-view-train-list`       | `MfeViewTrainListComponent`       | `master-layout/mfe-view-train-list/…`                    | default          | Wrapper around `tps-mfe-train-list` — **not used by any template**                  |
| `app-infra-elements-panel`      | `InfraElementsPanelComponent`     | `master-layout/panels/infra-elements-panel/…`            | **OnPush**       | Left overlay filter panel (station info / platforms)                                |
| `app-train-operations-panel`    | `TrainOperationsPanelComponent`   | `master-layout/panels/train-operations-panel/…`          | **OnPush**       | Left overlay filter panel (trains / restrictions)                                   |
| _(library)_                     | `SnackbarContentComponent`        | `shared/components/snackbar-content/…`                   | default          | MatSnackBar content                                                                 |

### `MasterLayoutComponent` — frame configuration

Rendered as `<tps-rivm-frame [headerConfig] [sidebarConfig] [ribbonConfig] [leftSlotConfig] [rightSlotConfig]>`
with these computed configs:

```typescript
headerConfig = {
  title,
  currentDateTime,
  dateTimeControlsEnabled,
  appAndMenuOptions,
  onClockChange,
  onSignOut,
};
sidebarConfig = {
  applicationIcon: "haf_station_departures",
  applicationTitle,
  selectedMenuKey,
  onMenuSelected,
};
ribbonConfig = { expanded: isRibbonExpanded(), onExpandedChange };
leftSlotConfig = {
  pushing: {
    open: isTrainListVisible || isRestrictionListVisible || aemOpen,
    expanded:
      isTrainListExpanded ||
      isRestrictionListExpanded ||
      (aemOpen && aemExpanded),
  },
  overlay: { contentKey: openLeftPanel() },
};
rightSlotConfig = {
  open: isTIPOpen || isEditPanelOpen,
  expanded: isTIPOpen && rightSlotExpanded(),
  onRequestClose,
  onWidthChange,
};
```

`selectedSidebarMenuKey()` precedence: `messages` → `train` → `restrictions` → `home`.

### Ribbon modes (`ribbonSections()` computed)

| Condition                                                       | Sections rendered                                                                                                                                                     |
| --------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `isApplyEditsSection()`                                         | `applyEditsSection` (rows 1)                                                                                                                                          |
| `isRestrictionListExpanded() && selectedRestriction() !== null` | `restrictionActionsSection` (1) + `exportSection` (2)                                                                                                                 |
| otherwise (default)                                             | `locationsSection`(2), `basicSection`(2), `panesSection`(2), `showHideSection`(2), `restrictionsSection`(2), `editSection`(2), `replaySection`(1), `exportSection`(2) |

### Ribbon section contents (from `config/infra.config.ts`)

| Section key                 | Title        | Items (`action` — enabled?)                                                                                                      |
| --------------------------- | ------------ | -------------------------------------------------------------------------------------------------------------------------------- |
| `locationsSection`          | Views        | `addView` (disabled), `savedViews` (disabled)                                                                                    |
| `basicSection`              | Basic        | `find` (disabled), `filter` (disabled)                                                                                           |
| `panesSection`              | Panes        | `geographicalView`, `schemanticView`, `octolinearView`, `geographicalAndSchemanticView` — **all disabled**                       |
| `showHideSection`           | Show/Hide    | `infraElements` **enabled**, `trainOperations` **enabled**, `operationalInformation` (disabled)                                  |
| `restrictionsSection`       | Restrictions | `edit`, `copyRestriction`, `newRestriction`, `deleteRestriction` — all disabled                                                  |
| `editSection`               | Edit         | 21 items; only `arrival_time`, `departure_time`, `change_track` become enabled (via `EDITABLE_ACTIONS`) when a train is selected |
| `replaySection`             | Replay       | `replay` (disabled)                                                                                                              |
| `applyEditsSection`         | Apply Edits  | `apply` (enabled only when the edit panel is dirty), `cancel`                                                                    |
| `exportSection`             | Export       | `pdf`, `csv`, `xlsx` — all disabled                                                                                              |
| `restrictionActionsSection` | Actions      | `activate_restriction`, `deactivate_restriction`, `cancel_restriction` (always disabled)                                         |

Header apps menu (`HEADER_APPS_AND_MENU_LIST`):
`ITOP → /ui/itop/home` (enabled), `GTT → /ui/gtt/home` (enabled),
`Octolinear View → /ui/infra/home` (**disabled** — it is the current app).

## 3.5 Services (own)

| Service                              | File                                                        | `providedIn` | Responsibility                                                                                                                          | HTTP                                       |
| ------------------------------------ | ----------------------------------------------------------- | ------------ | --------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| `BaseGraphApiService`                | `services/base-graph-api/basegraph-api.service.ts`          | root         | Base graph, IndexedDB-cached                                                                                                            | `GET {baseUrl}/basegraph`                  |
| `BusinessClockApiService`            | `services/business-clock-api/business-clock-api.service.ts` | root         | Business clock                                                                                                                          | `GET {baseUrl}/business-clock`             |
| `BusinessClockService`               | `services/business-clock/business-clock.service.ts`         | root         | UTC→local conversion (`moment.tz`), dispatches `loadBusinessClockData()` from its constructor, legacy `hourFromTime$` `BehaviorSubject` | —                                          |
| `InfraCacheDbService`                | `services/cache/infra-cache-db.service.ts`                  | root         | Dexie wrapper, DB `RIVM-INFRA`, table `cache` schema `&key`, TTL `CACHE_TTL_MS = 3 600 000 ms`                                          | —                                          |
| `ConfigService`                      | `services/config-service/config.service.ts`                 | root         | **Stub.** `loadConfig()` resolves a hard-coded empty `UserInfo`; `getConfig()` returns `{ apiUrl: 'Empty API URL', data }`              | —                                          |
| `IconService`                        | `services/icon/icon.service.ts`                             | root         | `MatIconRegistry.addSvgIcon(name, bypassSecurityTrustResourceUrl('icons/{name}.svg'))` and `addSvgIconLiteral`                          | —                                          |
| `LocationTrackCoordinatesApiService` | `services/location-track-coordinates-api/…`                 | root         | Fetches **all** pages sequentially (`concatMap` + `reduce`), page size 100, `retry({count:3, delay:1000})` per page, caches result      | `GET {baseUrl}/location-track-coordinates` |
| `LogoutApiService`                   | `services/logout-api/logout-api.service.ts`                 | root         | `POST {baseAuthUrl}/logout`                                                                                                             | yes                                        |
| `MapConfigService`                   | `services/map-config/map-config-api.service.ts`             | root         | Map config; **removes the cache key in its constructor** so config is always re-fetched after a page refresh                            | `GET {baseUrl}/configs`                    |
| `MapService`                         | `services/map/map.service.ts`                               | root         | **All** OpenLayers ownership — 746 lines, see §4                                                                                        | —                                          |
| `RestrictionApiService`              | `services/restrictions-api/restriction-api.service.ts`      | root         | Restrictions + response normalisation                                                                                                   | `GET {baseUrl}/restrictions`               |
| `RibbonStateService`                 | `services/ribbon-state/ribbon-state.service.ts`             | root         | Legacy `BehaviorSubject` ribbon state — **superseded by `RibbonStateStore`; not injected anywhere in `src/app` outside its own spec**   | —                                          |
| `SnackbarAlertService`               | `services/snackbar-alert/snackbar-alert.service.ts`         | root         | `MatSnackBar` + `SnackbarContentComponent`                                                                                              | —                                          |
| `TileManagementService`              | `services/tile-management/tile-management.service.ts`       | root         | Tile grid maths (§2.2)                                                                                                                  | —                                          |
| `TimeCalculationService`             | `services/time-calculation/time-calculation.service.ts`     | root         | Offset, rounding, `filterPositionsByTime`                                                                                               | —                                          |
| `TooltipPositionService`             | `services/tooltip-position/tooltip-position.service.ts`     | root         | Hover popover content + viewport-clamped positioning; registers restriction SVG icons on demand                                         | —                                          |
| `TrainPollingCoordinatorService`     | `services/train-polling-coordinator/…`                      | root         | Zoom/viewport → start/stop/refresh polling, 100 ms re-entrancy guard                                                                    | —                                          |
| `TrainPositionService`               | `services/train-position/train-position-api.service.ts`     | root         | `POST {baseUrl}/trainpositions`                                                                                                         | yes                                        |

### Signal stores (`@ngrx/signals`)

| Store                | File                                   | Scope                                 | State                                                                                                                                | Notable                                                                                                                                                                                         |
| -------------------- | -------------------------------------- | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `TrainPositionStore` | `signal-store/train-position.store.ts` | root, `withDevtools('trainPosition')` | `positions, allTileIds, activeTileIds, tiles, loading, error, pollingIntervalMs (2000 default), isPollingActive`                     | `startPolling` = `rxMethod<void>`; `merge(interval, fetchNow$)`; computed `positionCount, tileCount, allTileCount, activeTileCount, hasPositions, tileIds, pollingActive, getPositionsByTileId` |
| `RestrictionsStore`  | `signal-store/restrictions.store.ts`   | root, `withDevtools('restrictions')`  | `restrictions, loading, error, pollingIntervalMs (2000), isPollingActive, currentBusinessTime`                                       | computed `visibleRestrictions, activeRestrictions, visibleRestrictionInfos`                                                                                                                     |
| `MapConfigStore`     | `signal-store/configs.store.ts`        | root, `withDevtools('mapConfig')`     | `mapConfig[], loading, error`                                                                                                        | computed `mapConfigCount, hasConfig, getMapConfigById`                                                                                                                                          |
| `LocationsStore`     | `signal-store/locations.store.ts`      | root, `withDevtools('locations')`     | `locations[], loading, error`                                                                                                        | computed `locationCount, hasLocations, getLocationById`                                                                                                                                         |
| `MapStateStore`      | `signal-store/map-state.store.ts`      | root                                  | `loadedNodes: InfraNode[]`                                                                                                           | computed `isGraphLoaded` — gives O(1) node access instead of scanning OL features                                                                                                               |
| `PanelStateStore`    | `signal-store/panel-state.store.ts`    | root                                  | `trainListState, restrictionListState, overlayPanel, panelContext, trainDataVersion, ribbonAction, isEditPanelDirty, applyRequested` | 11 computed + 16 methods; the single source of truth for panel geometry                                                                                                                         |
| `RibbonStateStore`   | `signal-store/ribbon-state.store.ts`   | root                                  | `isRibbonExpanded, ribbonIconAction, ribbonIconEnabled, selectedRestriction, isSelectedRestrictionActionable`                        |                                                                                                                                                                                                 |
| `FilterStateStore`   | `signal-store/filter-state.store.ts`   | root                                  | `showTrains, showLocationTracks, showPlatforms, showRestrictions, infraElementsCheckboxState, trainOperationsCheckboxState`          | Hydrated from `localStorage['infra-filter-state']`; `withHooks.onInit` persists on every change                                                                                                 |
| `AemPanelStore`      | `signal-store/aem-panel.store.ts`      | root                                  | `isOpen, isExpanded, selectedRow: DetectionEvent \| null`                                                                            |                                                                                                                                                                                                 |
| `LeftPanelStore`     | `signal-store/left-panel.store.ts`     | root                                  | plain `@Injectable` with `signal<LeftPanelId>` (`'infraElements' \| 'trainOperations' \| null`)                                      | `toggle/open/close`                                                                                                                                                                             |

### Classic NgRx store

| Slice                     | Actions                                                                                                                                                                                      | Reducer                                                   | Effects                                                                                 | Selectors                                                                                                                                |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- | --------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `businessClock`           | `loadBusinessClockData`, `loadBusinessClockDataSuccess`, `loadBusinessClockDataFailure`, `toggleFullTimeMode`, `setFullTimeMode`, `setTimeWindow`, `setTimeWindowForTab`, `activeTabChanged` | `businessClockReducer` (computes `timeWindow` on success) | `BusinessClockEffects.loadBusinessClockData$`                                           | `selectBusinessClockState`, `selectBusinessClockData`, `selectTimeWindow`, `selectEffectiveClock`                                        |
| `customClock`             | `setCustomClockDateTime`, `resetCustomClock`                                                                                                                                                 | `customClockReducer`                                      | —                                                                                       | `selectCustomClockState` (via `selectEffectiveClock`)                                                                                    |
| `polling`                 | `setPollingActive`                                                                                                                                                                           | `pollingReducer` (initial `isPollingActive: true`)        | —                                                                                       | `selectPollingState`                                                                                                                     |
| `edgeData`                | `loadEdgeData`, `loadEdgeDataSuccess`, `loadEdgeDataFailure`, `clearEdgeData`                                                                                                                | `edgeDataReducer`                                         | `EdgeDataEffects.loadEdgeData$` (short-circuits with `filter(([, loaded]) => !loaded)`) | `selectAllEdgeData`, `selectEdgeDataLoading`, `selectEdgeDataLoaded`, `selectEdgeDataError`, `selectEdgeDataById`, `selectEdgeDataCount` |
| `tabs` _(not registered)_ | `addTab`, `selectTab`, `deleteTab`, `clearTabs`                                                                                                                                              | `tabsReducer`                                             | —                                                                                       | `selectAllTabs`, `selectActiveTab`, `selectTabById`                                                                                      |

`BusinessClockEffects.loadBusinessClockData$` detail:

```typescript
ofType(loadBusinessClockData)
 → switchMap(() => store.select(selectPollingState).pipe(
     switchMap(pollingState =>
       interval(BUSINESS_CLOCK_API_POLLING_TIMER /* 10 000 ms */).pipe(
         startWith(0),
         takeWhile(() => !!pollingState && pollingState.isPollingActive),
         mergeMap(() => pollingState.isPollingActive
            ? businessClockApiService.getBusinessClockApiData().pipe(
                map(businessClock => loadBusinessClockDataSuccess({ businessClock })),
                catchError(error => of(loadBusinessClockDataFailure({ error: error.message }))))
            : of())))))
```

## 3.6 Models / interfaces

| File                                          | Key exports                                                                                                                                                                                                                                                                                          |
| --------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `models/business-clock-api-results.model.ts`  | `BusinessClockApiResults { businessTime, businessTimeZone, serverTime, mode?, timeWindow? }`                                                                                                                                                                                                         |
| `models/configs.model.ts`                     | `TileSize`, `MapLayer`, `MapConfig`, `MapConfigApiEnvelope`                                                                                                                                                                                                                                          |
| `models/infra-region.model.ts`                | `InfraNodeAddress`, `SignalInfo`, `RawNode`, `InfraNode`, `RawEdgeRef`, `RawEdge`, `EdgeRecord`, `EdgeDataApiEnvelope`                                                                                                                                                                               |
| `models/location.model.ts`                    | `LocationTrackWithCoordinates`, `LocationWithTracks`, `LocationsApiEnvelope`                                                                                                                                                                                                                         |
| `models/master-layout-event-context.model.ts` | `MasterLayoutEventContext` (the DI bundle passed to every handler)                                                                                                                                                                                                                                   |
| `models/master-layout.model.ts`               | `TrainPanelRequest`, `TrainEditRequest`, `RibbonSectionView`, enums `EditAction`, `ApplyEditAction`, `RestrictionAction`, `RestrictionTargetState`, `ActiveRestrictionState`, `EditPanelSaveResult`; consts `EDITABLE_ACTIONS`, `ACTIVE_RESTRICTION_STATES`, `SIDEBAR_MENU_KEY`, `LEFT_PANEL_ACTION` |
| `models/response-transform.model.ts`          | `DataTileVersionEntry`, `ApiResponseMeta`, `ApiResponse<T>`                                                                                                                                                                                                                                          |
| `models/restriction-list.model.ts`            | `Restriction` (flat grid shape — used only by demo mocks)                                                                                                                                                                                                                                            |
| `models/restriction.model.ts`                 | `ApiResponse`, `RestrictionApiRawResponse`, `Restriction`, `getRestrictionId()`, `RestrictionData`, `TimePeriod`, `RestrictionImpact*`, `EdgePath`, `PathEdge`, `PathEdgeRef`, `PathCoordinate`, `RestrictionMeta`, `UI`, `Payload`, `Meta`, `Page`, `PaginatedResponse<T>`                          |
| `models/session-mgmt-model.ts`                | `SerializableTransform`, `SerializableTimelineZoomEvent`, `SerializableLocationZoomEvent`, `LocationTab`, `Button`, `TabPreferences` — **not referenced by any runtime code**                                                                                                                        |
| `models/time-window.model.ts`                 | `TimeWindow`, `TimeWindowResult { utc, local, slots }`                                                                                                                                                                                                                                               |
| `models/train-edit.model.ts`                  | `EditedField<T>`, `EditRunningLocationTrack`, `EditRunningTime`, `EditableTrainDetails`, `Track`                                                                                                                                                                                                     |
| `models/train-position.model.ts`              | `RunningType` enum, `TileVersion`, `InfraGraphicalCoordinates`, `TrainPosition`, `PaginatedResponse<T>`, `TrainPositionsResponse`                                                                                                                                                                    |

> Note: `TrainPosition` (frontend) declares optional `direction`, `length`, `weight`, `maxSpeed`,
> `hasDangerousGoods` that the **backend schema does not define** — they are always `undefined`
> in production and render as `'-'` in the popover.

## 3.7 Configuration constants

| File                             | Contents                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| -------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `app-constant.ts`                | `DATE_FORMAT='DD.MM.YYYY'`, `TIME_FORMAT='HH:mm'`, `BUSINESS_CLOCK_API_POLLING_TIMER=10000`, `TILE_API_POLLING_TIMER=2000` _(declared, unused — the real interval comes from `MapLayer.updateFrequencySecs`)_, `PAGE_SIZE=10000` _(declared, unused)_                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `config/cache.config.ts`         | `CACHE_TTL_MS = 3 600 000`; keys `infra_mapconfig_cache`, `infra_location_track_coordinates_cache`, `infra_basegraph_cache`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| `config/filter-panels.config.ts` | i18n strings for both filter panels                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `config/infra-view.config.ts`    | `INFRA_VIEW` (`pastTimeIntervalMin 10`, `futureTimeIntervalMin 50`, `minTimeOffsetSeconds -600`, `maxTimeOffsetSeconds 3000`, `timeSliderStepSeconds 5`), `INFRA_ZOOM_CONFIG` (`labelZoomThreshold 18`, `initialZoomLevel 1`, `defaultTrainVisibilityZoom 12`, `minZoom 2.5`, `maxZoom 20`, `maxZoomOnViewportFit 10`, `defaultMaxZoomFallback 18`, `defaultLocationLabelZIndex 30`, `defaultTrackLabelZIndex 40`), `MAP_VIEW_CONFIG` (`viewFitPadding [50,50,50,50]`, `zoomAnimationDuration 500`, `panAnimationDuration 300`, `panelResizeDebounceMs 350`, `tooltipOffset [0,-10]`), `INFRA_COLOR_CONFIG` (`edgeColor '#898995'`, `edgeWidth 1`), `ISO_DATE_PATTERN`, `OPERATING_DAY_FORMAT 'YYYY-MM-DD'`, `DEFAULT_TIMEZONE 'UTC'`, `INFRA_URLS.mfeBaseUrl`, `RESTRICTION_MINIMIZED_COLUMNS 'name,state'`, `TRAIN_LIST_CONTEXT_MENU` |
| `config/infra.config.ts`         | `HEADER_APPS_AND_MENU_LIST`, `ICONS_PATH 'icons/'`, `ICONS[]` (~90), all ribbon section arrays, `RIBBON_SECTIONS_COLLECTIONS`, `SESSION_MGMT_DB_NAME 'RIVM-INFRA'`, `MAXIMUM_ALLOWED_COUNT_FOR_ADD_INFRA 100`, `COMMON_ERROR_MESSAGES`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `config/open-layer.config.ts`    | `CLUSTER_CONFIG` (40+ constants), `RESTRICTION_STYLE_CONFIG`, `MAP_LAYER_ZINDEX`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `config/tooltip.config.ts`       | `TOOLTIP_CONFIG { cursorOffsetX 12, cursorOffsetY 12, panelWidth 450, fallbackHeight 180 }`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |

## 3.8 The single screen — full breakdown

### Route `#/home` (and `#/home/…`)

| Aspect                    | Detail                                                                                                                                           |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| **URL**                   | `/ui/infra/#/home`                                                                                                                               |
| **Parent component**      | `MasterLayoutComponent`                                                                                                                          |
| **Child (router-outlet)** | `InfraContentComponent`                                                                                                                          |
| **Library shell**         | `tps-rivm-frame` with named slots `frameRibbon`, `frameLeftPushingSlot`, `tpsFrameLeftOverlayPanel` templates, default content, `frameRightSlot` |

#### Regions and their child components

| Region                | Rendered when                                                   | Content                                                                                                                                              |
| --------------------- | --------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| Header                | always                                                          | Frame header — title `TPS.live`, live clock label, date/time pickers, Apps&Menu (`ITOP`, `GTT`, `Octolinear View`), user (`Workstation 1`), sign-out |
| Sidebar               | always                                                          | Frame sidebar — icon `haf_station_departures`; keys `home`, `train`, `restrictions`, `messages`                                                      |
| Ribbon                | `isRibbonExpanded()`                                            | `@for (section of ribbonSections())` → `tps-rivm-ribbon-section`                                                                                     |
| Left **pushing** slot | `isTrainListVisible \|\| isRestrictionListVisible \|\| aemOpen` | `tps-mfe-train-list` / `app-mfe-view-restriction-list` / `tps-aem-events-panel`                                                                      |
| Left **overlay** slot | `openLeftPanel() !== null`                                      | `app-infra-elements-panel` or `app-train-operations-panel` (keyed `ng-template`s)                                                                    |
| Main                  | always                                                          | `.map-content > .map-canvas > router-outlet` → `InfraContentComponent`                                                                               |
| Right slot            | `isTIPOpen \|\| isEditPanelOpen`                                | `tps-mfe-train-info-panel` or `tps-mfe-train-edit-panel`                                                                                             |

#### `InfraContentComponent` template elements

- `div.ol-map-container > div#mapElement.ol-map` — the OpenLayers target
- `.clustering-toggle` — button toggling `clusteringEnabled` (`icons/toggle_on.svg` / `toggle_off.svg`, 36×24)
- `.time-slider-container` — `−` button, `input[type=range][min=-600][max=3000][step=5]` bound with
  `[(ngModel)]="timeOffsetSeconds"`, `+` button, `−10m` / `+50m` labels
- `.time-value` — `{{adjustedTimeDisplay}}`, `({{timeOffsetDisplay}})`,
  `Time: {{currentTimestampDisplay}}`, `Reset to Now` button
- `.loading-overlay > .spinner` — while `loading$ | async`
- `div#tooltip.ol-tooltip` — hosts either `rivm-train-information-popover` or
  `tps-rivm-restriction-popover` (mutually exclusive via `trainPopoverData` / `restrictionPopoverData`)
- `tps-rivm-context-menu` — `[menu]="contextMenuItems"`, `[x]`, `[y]`, `[visible]`,
  `(selectContextMenu)="onContextMenuSelect($event)"`

#### User actions → flow

| Action            | Handler                                                                                   | Result                                                                                                                                                                          |
| ----------------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Pan / zoom map    | OL `moveend` / `change:resolution` → `handleMoveEnd` / `handleResolutionChange`           | `refreshSemanticZoom()`, `updateTrainVisibility()`, `updateRestrictionsDisplay()`, `handleRestrictionsZoomChange()`, `pollingCoordinator.handleZoomChange/handleViewportChange` |
| Hover             | `onPointerMove` → `MapService.handlePointerMove` + `TooltipPositionService.handleTooltip` | Cursor `pointer` over a train; train or restriction popover shown; hovered restriction gets a white halo                                                                        |
| Single click      | `handleTrainSingleClick` + `MapService.handleClusterClick`                                | Select/deselect train (`setSelectedTrain`), `updatePanelContext`; clicking a multi-train cluster fits the view to its extent                                                    |
| Double click      | `handleTrainDoubleClick`                                                                  | `PanelStateStore.openTIP(...)`                                                                                                                                                  |
| Right click       | `handleTrainContextMenu`                                                                  | Only when the feature under the cursor **is the already-selected train**: `preventDefault()`, show `tps-rivm-context-menu` at `clientX/clientY`                                 |
| Context-menu item | `onContextMenuSelect(action)`                                                             | `PanelStateStore.openEditPanel({ trainNumber, operatingDay:'', trainServiceId, editType: action })`                                                                             |
| Document click    | `@HostListener('document:click') onDocumentClick()`                                       | Hides the context menu                                                                                                                                                          |
| Clustering toggle | `toggleClustering()`                                                                      | `MapService.setClusteringEnabled(...)` — swaps cluster ↔ non-cluster layer                                                                                                      |
| Time slider       | `onTimeOffsetChange/incrementTime/decrementTime/resetToNow`                               | `updateTimestamps()`                                                                                                                                                            |

#### Navigation flow

There is effectively **no navigation**. The only `router.navigate` in the app is
`navigateHome(ctx)` in `sidebar.handlers.ts`:
`ctx.router.navigate([''], { relativeTo: ctx.activatedRoute })`, and it is skipped entirely when
`panelState.isEditPanelDirty()`.

## 3.9 Event-handler layer

`master-layout/event-handlers/` — pure functions taking `MasterLayoutEventContext`:

| File                       | Exports                                                                                                                                                                         |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `filter-panel.handlers.ts` | `handleInfraElementsSelectionChanged`, `handleTrainOperationsSelectionChanged`                                                                                                  |
| `header.handlers.ts`       | `handleDateChange`, `handleTimeChange`, `handleResetDateTime`, `handleChevronButtonClicked`, `handleSignOut`                                                                    |
| `panel.handlers.ts`        | `handleRightSlotExpandedChange`, `handleCollapseTrainList`, `handleExpandTrainList`, `handleCollapseRestrictionList`, `handleExpandRestrictionList`                             |
| `ribbon.handlers.ts`       | `handleEditActionClick`, `handleApplyEditAction`, `syncApplyEditsSection`, `handleShowHideAction`, `handleRestrictionAction`                                                    |
| `sidebar.handlers.ts`      | `handleMenuSelected` (+ private `toggleAemPanel`, `toggleDockedList`, `navigateHome`, `closeDockedLists`, `clearPanelContextWhenNoOverlay`)                                     |
| `train-edit.handlers.ts`   | `handleTrainSelected`, `handleEditTrain`, `handleOpenTrainInfo`, `handleEditPanelDataChanged`, `submitPendingEdit`, `handleEditPanelSaved`, `isEditedField`, `buildEditPayload` |
| `index.ts`                 | barrel                                                                                                                                                                          |

## 3.10 Demo mode

`environment.demo.ts` → `demo: true`, `interceptors: [httpMockInterceptor]`.

`httpMockInterceptor` ([mocks/http-mock.interceptor.ts](../infra/components/infra-webapp/src/app/mocks/http-mock.interceptor.ts)) short-circuits by URL suffix / substring:

| Matched path fragment                                                        | Fixture                                                                                                  |
| ---------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `/train-operation-overviews-presets`                                         | `train-list-presets.mock.ts`                                                                             |
| `/me`                                                                        | `me.mock.ts`                                                                                             |
| `/business-clock`                                                            | `business-clock.mock.ts` (with a 10 s `TICK_INCREMENT` drift)                                            |
| `/basegraph`                                                                 | Lazily loads and merges `public/mocks/infra-rivm.basegraph.mock.part1..5.json`                           |
| `/location-track-coordinates`                                                | `infra-location-tracks.mock.ts`                                                                          |
| `/configs`                                                                   | `map-config.mock.ts`                                                                                     |
| `/trainpositions`                                                            | `train-positions.mock.ts` (`TRAIN_POSITIONS_MOCK`, `TRAIN_POSITIONS_BY_TIME`)                            |
| `/compositions`                                                              | `composition.mock.ts`                                                                                    |
| `/aem/query/detection-describers` \| `/detection-events` \| `/unread-counts` | `aem-mock-handler.ts` + `aem-events.mock.ts`, `category-descriptors.mock.ts`, `detection-events.mock.ts` |
| GET with `effectiveAt` param                                                 | `restrictions.mock.ts` — filtered by `effectiveTimePeriod`                                               |
| trains list GET                                                              | `trains-list.mock.ts`, page size 100                                                                     |
| `/train-operation/query/train-operations/{id}` or `/trainoperations/{id}`    | `train-operation.mock.ts`                                                                                |

---

# 4 — MAP / MAIN CONTENT IMPLEMENTATION

This is the heart of the application.

## 4.1 Library / framework

**OpenLayers `ol` `^10.10.0`** — plain vector rendering on a `<canvas>`.
No basemap, no tile server, no projection: the map works directly in the **infrastructure's own
Cartesian coordinate space** (`MapConfig.coordinateSystem = "CARTESIAN"`), with node coordinates
taken verbatim from `InfraGraphicalCoordinates.x/.y` (`Signed32BitInteger`).

Imports actually used (`map.service.ts`):
`ol` → `Feature, Map, MapBrowserEvent, Overlay, View`;
`ol/control` → `defaults as defaultControls, OverviewMap`;
`ol/geom` → `Point, LineString, Polygon`;
`ol/layer` → `Vector as VectorLayer`;
`ol/source` → `Cluster as ClusterSource, Vector as VectorSource`;
`ol/style` → `Circle as CircleStyle, Fill, Icon, Stroke, Style, Text`;
`ol/extent` → `createEmpty, extend`;
`ol/Observable` → `unByKey`.

## 4.2 Main map component & service

- **Component:** `InfraContentComponent`
  ([master-layout/infra-content/infra-content.component.ts](../infra/components/infra-webapp/src/app/master-layout/infra-content/infra-content.component.ts), 690 lines, `ChangeDetectionStrategy.OnPush`).
- **Service (owns the `Map` instance):** `MapService`
  ([services/map/map.service.ts](../infra/components/infra-webapp/src/app/services/map/map.service.ts), 746 lines, `providedIn: 'root'`).

Because `MapService` is root-scoped and `initializeMap()` **re-attaches** an existing map
(`this.map.setTarget(mapElement)`) instead of rebuilding it, the map, its layers and all loaded
features **survive route re-navigation**.

## 4.3 Initialisation sequence

`InfraContentComponent.ngOnInit()`:

```
ribbonStateStore.setRibbonExpanded(true)
loadTrainIconTemplate()          // fetch('icons/train_directional.svg') → cache text
initializeMap()
loadConfigurations()
subscribeToBusinessClock()
```

`initializeMap()`:

```
tooltipPositionService.init(tooltipElement.nativeElement)
mapService.initializeMap(mapElement.nativeElement, document.createElement('div'), {
   onResolutionChange, onMoveEnd, onPointerMove, onClick, onDoubleClick, onContextMenu })
currentMapZoom = Math.round(mapService.getCurrentZoom() ?? currentMapZoom)
```

> Note the second argument: the **OL `Overlay` element is a throw-away detached `div`** — the real
> tooltip DOM node (`#tooltip`) is positioned manually in CSS pixels by `TooltipPositionService`,
> **not** by the OL overlay. The `Overlay` is created but never given a position.

`MapService.initializeMap()` first-time path:

```
createVectorLayers()            → vectorLayer (infrastructure)
createClusteredTrainLayers()    → trainPositionsClusterSource, trainPositionsVectorLayer,
                                  trainPositionsNonClusteredLayer  (both setVisible(false))
createRestrictionsLayer()       → restrictionsVectorLayer          (setVisible(false))
createOverviewMapControl()      → OverviewMap
createTooltipOverlay(el)        → Overlay { positioning:'bottom-center', stopEvent:false,
                                            offset: MAP_VIEW_CONFIG.tooltipOffset }
createMapInstance(el)           → new Map({...})
registerEventCallbacks(cbs)
```

`createMapInstance`:

```typescript
new Map({
  target: mapElement,
  layers: [
    vectorLayer,
    trainPositionsVectorLayer,
    trainPositionsNonClusteredLayer,
    restrictionsVectorLayer,
  ],
  view: new View({
    center: [0, 0],
    zoom: INFRA_ZOOM_CONFIG.initialZoomLevel /* 1 */,
    minZoom: INFRA_ZOOM_CONFIG.minZoom /* 2.5 */,
    maxZoom: INFRA_ZOOM_CONFIG.maxZoom /* 20 */,
  }),
  controls: defaultControls({ zoom: false, rotate: false }).extend([
    overviewMapControl,
  ]),
  overlays: [tooltipOverlay],
});
map.getView().on("change:resolution", () => this.updateClusteringDistance());
```

Label layers (`locationLabelLayer`, `trackLabelLayer`) are created **lazily** inside
`loadLocationLabels()` and then `map.addLayer(...)`.

## 4.4 Map configuration (data-driven)

`MapConfig` is fetched from `GET /configs` and drives almost every visual threshold.

Schema — [components/schemas/infra/MapConfig.yaml](../infra/components/schemas/infra/MapConfig.yaml):

```
MapConfig { id, mapType(OCTOLINEAR|GEOGRAPHIC|SCHEMATIC), mapName,
            coordinateSystem(CARTESIAN|GEOGRAPHIC), minZoomLevel, maxZoomLevel,
            defaultZoom, layers[] }
MapLayer  { id, layerType(EDGE_OBJECT|TIMED_SINGLE_POINT_OBJECT), layerDataType, layerName,
            zindex, minZoom, maxZoom, defaultVisibility(SHOW|HIDE), updateFrequencySecs,
            tileSize? { width, height, timeSpanSecs } }
```

Reference document (`infra-trainoperation-etl/src/test/resources/MapConfig.json`):

| Layer `id`     | `layerDataType` | `layerType`   | `zindex` | `minZoom` | `maxZoom` | `updateFrequencySecs` | `tileSize`                                        |
| -------------- | --------------- | ------------- | -------- | --------- | --------- | --------------------- | ------------------------------------------------- |
| `baseGraph`    | `baseGraph`     | `EDGE_OBJECT` | 0        | 0         | 100       | 3600                  | `{0,0,3600}`                                      |
| `locations`    | `location`      | `EDGE_OBJECT` | 20       | 14        | 100       | 3600                  | —                                                 |
| `platforms`    | `platform`      | `EDGE_OBJECT` | 30       | 17        | 100       | 3600                  | —                                                 |
| `restrictions` | `restriction`   | `EDGE_OBJECT` | 40       | 5         | 100       | 3600                  | —                                                 |
| `trains`       | _(see fixture)_ | —             | —        | —         | —         | —                     | _(has `tileSize`, required by `DataTileService`)_ |

How the frontend consumes it (`InfraContentComponent.loadConfigurations()`):

```typescript
const baseGraphLayer = configs[0]?.layers?.find((l) => l.id === "baseGraph");
mapService.setInfraLayerZIndex(
  baseGraphLayer?.zindex ?? MAP_LAYER_ZINDEX.infrastructure /*10*/,
);

this.trainsLayer = configs[0]?.layers?.find((l) => l.id === "trains") || null;
this.restrictionsLayer =
  configs[0]?.layers?.find((l) => l.id === "restrictions") || null;

if (this.trainsLayer) {
  this.selectedZoomLevel = this.trainsLayer.minZoom;
  this.loadEdgeDataAndSubscribe();
}
if (this.restrictionsLayer) {
  this.restrictionsMinZoom = this.restrictionsLayer.minZoom;
  if (this.restrictionsLayer.updateFrequencySecs > 0)
    this.restrictionsStore.setPollingInterval(
      this.restrictionsLayer.updateFrequencySecs,
    );
}
```

and, once locations are also available:

```typescript
mapService.loadLocationLabels(
  locations,
  locationsLayer?.minZoom ?? 0,
  locationsLayer?.maxZoom ?? INFRA_ZOOM_CONFIG.defaultMaxZoomFallback /*18*/,
  tracksLayer?.minZoom ?? 10,
  tracksLayer?.maxZoom ?? INFRA_ZOOM_CONFIG.defaultMaxZoomFallback,
  locationsLayer?.zindex ?? INFRA_ZOOM_CONFIG.defaultLocationLabelZIndex /*30*/,
  tracksLayer?.zindex ?? INFRA_ZOOM_CONFIG.defaultTrackLabelZIndex /*40*/,
);
```

> **Critical dependency:** `DataTileService` (backend) refuses to compute tile IDs unless a layer
> with `layerDataType === 'train'` **and** a non-null `tileSize` exists. `RiseToInfraMapper` /
> `RiseToInfraForecastMapper` short-circuit with `"MapConfig not available - skipping … event
processing"` if it is missing. **No `MapConfig` in Mongo ⇒ no train positions are ever ingested.**

## 4.5 Layer stack

Canonical ordering (`config/open-layer.config.ts`):

```typescript
export const MAP_LAYER_ZINDEX = {
  infrastructure: 10,
  restrictions: 20,
  locationLabels: 30,
  trackLabels: 40,
  trainSingle: CLUSTER_CONFIG.zIndexSingleTrain, // 100
  trainClusters: CLUSTER_CONFIG.zIndexClusters, // 1000
} as const;
```

Actual runtime layers:

| #   | Field in `MapService`             | OL type                      | Source                        | z-index applied                                                                                           | Visibility rule                                                                                   |
| --- | --------------------------------- | ---------------------------- | ----------------------------- | --------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| 1   | `vectorLayer`                     | `VectorLayer<VectorSource>`  | `vectorSource`                | `MAP_LAYER_ZINDEX.infrastructure` at creation, overridden by `setInfraLayerZIndex(baseGraphLayer.zindex)` | always visible                                                                                    |
| 2   | `restrictionsVectorLayer`         | `VectorLayer<VectorSource>`  | `restrictionsVectorSource`    | `RESTRICTION_STYLE_CONFIG.zIndex = 50`                                                                    | `showRestrictions && zoom > restrictionsMinZoom && infos.length > 0`                              |
| 3   | `locationLabelLayer`              | `VectorLayer<VectorSource>`  | `locationLabelSource`         | from config (`30`)                                                                                        | `filterStateStore.showLocationTracks()`; also `minZoom`/`maxZoom` on the layer; `declutter: true` |
| 4   | `trackLabelLayer`                 | `VectorLayer<VectorSource>`  | `trackLabelSource`            | from config (`40`)                                                                                        | `filterStateStore.showPlatforms()`; `minZoom`/`maxZoom`                                           |
| 5   | `trainPositionsVectorLayer`       | `VectorLayer<ClusterSource>` | `trainPositionsClusterSource` | `CLUSTER_CONFIG.zIndexClusters = 1000`                                                                    | clustering ON and zoom ≥ `selectedZoomLevel` and `showTrains`                                     |
| 6   | `trainPositionsNonClusteredLayer` | `VectorLayer<VectorSource>`  | `trainPositionsVectorSource`  | `1000`                                                                                                    | clustering OFF and same gates                                                                     |
| 7   | `overviewVectorLayer`             | inside `OverviewMap` control | `overviewVectorSource`        | n/a                                                                                                       | always (mini-map)                                                                                 |

> **Observation:** the restriction layer's actual z-index is `50` (from `RESTRICTION_STYLE_CONFIG`),
> not `20` as the `MAP_LAYER_ZINDEX` doc-comment implies — so restrictions render **above**
> location/track labels in practice.

## 4.6 Track (infrastructure) rendering

`OpenLayerInfraUtility` — [utility/open-layer-utility/open-layer-infra.utility.ts](../infra/components/infra-webapp/src/app/utility/open-layer-utility/open-layer-infra.utility.ts)

**Extraction from the API payload:**

```typescript
static extractNodes(edgeData: EdgeDataPayload[]): InfraNode[]
  // per region, per raw node:
  //   id = raw.baseSubEntityData.id
  //   x  = raw.nodeData.coordinates.graphical.x
  //   y  = raw.nodeData.coordinates.graphical.y
  //   guard: typeof id === 'string' && typeof x === 'number' && typeof y === 'number'
  //   → { id, x, y, kmValue: raw.nodeData.infraNodeAddress?.kmValueMillimeters,
  //       signalInfo, isBoundaryNode, address, raw, region: region.id }

static extractEdges(edgeData: EdgeDataPayload[]): EdgeRecord[]
  //   id   = raw.baseSubEntityData.id
  //   refs = raw.edgeData.infraNodeRefs   (needs length >= 2)
  //   a    = refs[0].infraMicroscopicNodeRef.subEntityID
  //   b    = refs[1].infraMicroscopicNodeRef.subEntityID
  //   → { id, a, b, raw, length: raw.edgeData.edgeLengthMillimeters }
```

> **Field-name mismatch worth recording:** the frontend reads
> `nodeData.infraNodeAddress.kmValueMillimeters`, but the backend schema
> (`BaseGraph.yaml` → `InfraMicroscopicNodeAddress`) defines the property as **`kmValue`**
> (int64). Therefore `InfraNode.kmValue` is **always `undefined`** in production.
> It is not used for rendering, so there is no visible effect.

**Feature creation:**

```typescript
createNodeFeatures(nodes, vectorSource)
  → new Feature({ geometry: new Point([node.x, node.y]), type: 'node', nodeData: node })

createEdgeFeatures(edges, nodes, vectorSource)
  → lookup: { [nodeId]: InfraNode }
  → skip edges whose a/b node is missing
  → new Feature({ geometry: new LineString([[a.x,a.y],[b.x,b.y]]),
                  type: 'edge', edgeData: edge })
```

**Styling:**

```typescript
getFeatureStyle(feature, zoom)
  'edge' → new Style({ stroke: new Stroke({ color:'#898995', width:1,
                                            lineCap:'round', lineJoin:'round' }) })
  'node' → new Style({ text: (zoom >= 18 && node) ? new Text({ text: node.id,
                                                     fill: new Fill({color:'#000000'}) })
                                                  : undefined })
```

> Nodes therefore have **no visible geometry symbol** — they only contribute a black text label of
> the node id at zoom ≥ `INFRA_ZOOM_CONFIG.labelZoomThreshold` (18). The visible network is made of
> the edge line-strings alone.
>
> **Note:** `createMainVectorLayer` passes `getFeatureStyle(feature)` **without a zoom argument**,
> so `showLabel` is always `false` on the main layer. `MapService.refreshSemanticZoom()` calls
> `vectorLayer.getSource()?.changed()` on every resolution change, but because zoom is not
> forwarded the node labels never actually appear. Recorded as an observation, not a fix.

**View fitting:**

```typescript
MapService.fitViewToData(onComplete?)
  extent = vectorSource.getExtent()
  OpenLayerInfraUtility.fitViewToExtent(extent, ext => {
     map.getView().fit(ext, { padding: [50,50,50,50], maxZoom: 10 });
     requestAnimationFrame(() => {
        const z = map.getView().getZoom();
        if (z !== undefined && !initialZoom) { initialZoom = z; map.getView().setMinZoom(z); }
        onComplete?.();
     });
  });
```

`fitViewToExtent` guards with `extent.every(c => isFinite(c))`.

**Overview (mini) map** — `createOverviewMapControl` + `setupFrozenOverview`:

```
new OverviewMap({ layers:[overviewVectorLayer], collapsed:false,
                  className:'ol-overviewmap ol-custom-overviewmap' })
setupFrozenOverview:
  om.updateSize(); omView.fit(fullExtent, { size: om.getSize(), padding:[20,20,20,20] });
  om.render(); mainMap.getView().changed(); mainMap.render();
  frozenZoom/frozenCenter captured →
  omView.setMinZoom(frozenZoom); omView.setMaxZoom(frozenZoom);
  omView.on('change:center', revert); omView.on('change:resolution', revert);
  om.getInteractions().forEach(i => i.setActive(false));
```

`loadOverviewMapData()` wraps this in a bare `setTimeout(...)` so the main map paints first.

## 4.7 Station (location) and platform (track) label rendering

`OpenLayerLocationLabelUtility` — [utility/open-layer-utility/open-layer-location-label.utility.ts](../infra/components/infra-webapp/src/app/utility/open-layer-utility/open-layer-location-label.utility.ts)

- **Location label** — placed at the **centre of the bounding box of every coordinate of every
  track of that location**, shifted `+3` on Y:
  `new Point([center.x, center.y + 3])`, `type:'locationLabel'`, `labelText: location.name`,
  `locationId`.
- A second, invisible `Polygon` feature (`type:'locationBBox'`) is emitted per location for
  debugging (its style is an empty `Style` with the stroke commented out).
- **Track label** — placed at the bounding-box centre of that track's `nodeCoordinates`;
  `labelText = track.shortName || track.name || track.id`.
- Styles:
  - location: `font: '800 10px "Public Sans", sans-serif'`, fill `#FFFFFF`, stroke `#111118` w1,
    `padding [2,4,2,4]`, `overflow: true`, `textAlign:'center'`
  - track: `font: '400 10px "Public Sans", sans-serif'`, same fill/stroke
- Location layer is created with `declutter: true`; the track layer is not.
- Both layers get `minZoom`/`maxZoom` from `MapConfig`.

## 4.8 Train rendering

`OpenLayerClusterUtility` — [utility/open-layer-cluster-utility/open-layer-cluster.utility.ts](../infra/components/infra-webapp/src/app/utility/open-layer-cluster-utility/open-layer-cluster.utility.ts)

### Feature creation

```typescript
static createTrainPositionFeatures(positions: TrainPosition[], vectorSource: VectorSource): void {
  const features = positions.map(position => {
    const direction = 90;                       // ← HARD-CODED placeholder
    return new Feature({
      geometry: new Point([position.coordinates.x, position.coordinates.y]),
      id: position.id,
      trainServiceId: position.trainServiceId,
      activityId: position.activityId,
      runningType: position.runningType,
      fromTime: position.fromTime,
      toTime: position.toTime,
      origin: position.origin,
      destination: position.destination,
      direction,
      weight: position.weight,          // always undefined from the API
      length: position.length,          // always undefined
      maxSpeed: position.maxSpeed,      // always undefined
      hasDangerousGoods: position.hasDangerousGoods, // always undefined
    });
  });
  vectorSource.addFeatures(features);
}
```

The source comment states: _"not adding const variable as this would be replaced by api entity
value once composition is present"_. **Train heading is therefore constant (90°) today.**

### Cluster source

```typescript
new ClusterSource({
  distance,
  source: vectorSource,
  geometryFunction: (f) =>
    f.getGeometry() instanceof Point ? f.getGeometry() : null,
});
```

### Dynamic cluster distance (`getClusteringDistanceForZoom`)

| Zoom        | Distance (px) | Constant                   |
| ----------- | ------------- | -------------------------- |
| undefined/0 | 20            | `defaultDistance`          |
| ≤ 5         | 80            | `maxDistance`              |
| ≤ 8         | 60            | `highClusteringDistance`   |
| ≤ 10        | 50            | `mediumClusteringDistance` |
| ≤ 12        | 20            | `defaultDistance`          |
| ≤ 14        | 30            | `lowClusteringDistance`    |
| > 14        | 20            | `minDistance`              |

`MapService.updateClusteringDistance()` recreates the cluster source only when
`Math.abs(newDistance - currentClusterDistance) > CLUSTER_CONFIG.distanceChangeThreshold (5)`.

### Single-train style

```typescript
getTrainIconStyle(trainServiceId, direction, isSelected);
cacheKey = `${extractTrainColor(trainServiceId)}|${quantizeDirection(direction)}|${isSelected}`;
// quantize = round(direction / 22.5) * 22.5
scale = isSelected ? 0.75 * 1.75 : 0.75;
strokeColor = isSelected ? "white" : "none";
new Style({
  image: new Icon({
    src: buildTrainIconDataUri(color, strokeColor),
    scale,
    anchor: [0.5, 0.5],
    rotateWithView: true,
  }),
  zIndex: 100,
});
```

`buildTrainIconDataUri` (train-type.utility.ts) substitutes `{{FILL_COLOR}}` and
`{{STROKE_COLOR}}` in the cached text of `public/icons/train_directional.svg` and returns
`data:image/svg+xml;charset=utf-8,` + `encodeURIComponent(svg)`.
`loadTrainIconTemplate()` must have completed first — `InfraContentComponent.ngOnInit()` calls it
(without awaiting).

### Train colour by type

`extractTrainColor(trainServiceId, isCancelled=false)` reads **`trainServiceId.charAt(0)`**:

| Digit     | Type name                                | Colour                          |
| --------- | ---------------------------------------- | ------------------------------- |
| 1         | Express passenger                        | `#FD4958` (passenger red)       |
| 2         | Ordinary passenger                       | `#FD4958`                       |
| 3         | Parcels, postal, or empty coaching stock | `#56AFF6` (freight blue)        |
| 4         | Freight (max 75 mph)                     | `#56AFF6`                       |
| 5         | Empty coaching stock                     | `#56AFF6`                       |
| 6         | Freight (60 mph max)                     | `#56AFF6`                       |
| 7         | Freight (45 mph max)                     | `#56AFF6`                       |
| 8         | Freight (35 mph max)                     | `#56AFF6`                       |
| 9         | International or special use             | `#FF00FF` (locomotives magenta) |
| cancelled | —                                        | `#D5D5D8`                       |
| fallback  | —                                        | passenger `#FD4958`             |

`getTrainTypeCategory(char)` → `passenger` (1–2), `freight` (3–8), `international-special` (9).
`extractTrainDisplayName('1P_IC_123_A')` → `'1P IC 123'` (drops the last `_`-segment).

### Cluster style (size > 1)

Four stacked `Style` objects:

```
radius = min(21 + ln(size) * 3, 30)

1. hit-detection CircleStyle(radius, fill rgba(0,0,0,0))   zIndex 49 + size
2. custom canvas renderer "donut"                          zIndex 50 + size
     outer arc r=radius (cw) + inner arc r=radius*0.6 (ccw) → fill #51E4A4
     stroke outer edge #25252D width 3
     fill inner circle #25252D
3. Icon 'icons/cluster_train.svg' scale 1, displacement [0,6], opacity 1   zIndex 52 + size
4. Text = size, font 'bold 12px Public Sans, sans-serif', fill #FFFFFF,
   offsetY 9                                                              zIndex 52 + size
```

### Train label + connector line (zoom > 18)

`resolveTrainStyles(...)` adds two more styles when
`zoom > INFRA_ZOOM_CONFIG.labelZoomThreshold (18)` and a `trainServiceId` exists:

1. **Connector line** — a custom `renderer` that strokes from
   `(x + dx*labelLineGap, y + dy*labelLineGap)` to `(x + offsetX, y + offsetY)` in the train's
   colour, `lineWidth = CLUSTER_CONFIG.labelLineWidth (1.5)`, `zIndex 99`.
2. **Label text** — `Text` with `offsetX/offsetY` pushed a further
   `CLUSTER_CONFIG.labelPadding (6)` along the same unit vector,
   `font 'bold 11px Public Sans, sans-serif'`, fill = train colour,
   stroke `#25252D` width 3, `textBaseline:'middle'`, `zIndex 101`.

Placement is computed by the **`LabelPlacementEngine`**
([utility/label-placement.engine.ts](../infra/components/infra-webapp/src/app/utility/label-placement.engine.ts)):

- `LABEL_GAP = 18` px, `PADDING = 4` px, `RINGS = [1, 1.8]`.
- 8 candidate directions, priority order: right (0°), up-right (−30°), down-right (30°),
  left (180°), up-left (−150°), down-left (150°), above (−90°), below (90°) —
  with `textAlign` `left|left|left|right|right|right|center|center`.
- Occupied rectangles stored in a growable `Float64Array` (`[l,t,r,b]` quads).
- `placeLabel` tries 2 rings × 8 candidates = **16 slots**, returns the first non-overlapping one;
  otherwise the **least-overlapping** by computed intersection area.
- `registerIcon(cx, cy, radius=CLUSTER_CONFIG.iconRegistrationRadius /*10*/)` reserves the icon
  footprint before labels are placed.
- `resetIfViewChanged(zoom, centerX, centerY, featureCount)` keys on
  `` `${zoom.toFixed(4)}|${round(cx)}|${round(cy)}|${featureCount}` `` and is called from the
  layer's `prerender` event; the per-feature cache key is
  `` `${trainServiceId}|${round(px)}|${round(py)}` ``.
- `estimateLabelWidth(text, 11) = text.length * 11 * 0.62 + 6`;
  `estimateLabelHeight(11) = 15`.

### Selection highlight

`MapService.setSelectedTrain(id)` stores `selectedTrainServiceId` and calls `.changed()` on **both**
train layers to force style re-evaluation. Selected trains get `scale × 1.75` and a white stroke.

`MapService.focusSelectedTrain(targetZoom = 19)`:

```
coordinate = getSelectedTrainCoordinate()   // scans trainPositionsVectorSource for the id
if (!coordinate) { pendingFocusSelectedTrain = selectedTrainServiceId !== null; return false; }
view.cancelAnimations();
view.animate({ center: coordinate, zoom: max(currentZoom, targetZoom), duration: 500 });
```

`updateTrainPositions()` retries the focus if `pendingFocusSelectedTrain` is set.

## 4.9 Restriction rendering

`OpenLayerRestrictionUtility` — [utility/open-layer-utility/open-layer-restriction.utility.ts](../infra/components/infra-webapp/src/app/utility/open-layer-utility/open-layer-restriction.utility.ts)

**Feature creation** — one `LineString` **per `edgePath`** (i.e. per coordinate set with ≥ 2 points):

```typescript
new Feature({
  geometry: new LineString(coordinates),
  type: "restriction",
  restriction,
  restrictionName,
  restrictionId,
  edgeLocation,
  isActive,
  color,
});
```

`edgeLocation` = `pathLocations[index] ?? 'Path {index+1}'`, where `pathLocations[i]` is
`"x0, y0 → xN, yN"` from `RestrictionDisplayUtility.formatPathLocation`.

**Style function** (returns an array):

```
zoom      = map.getView().getZoom() ?? 2.5
isHovered = feature.restrictionId === hoveredRestrictionId
radius    = radiusForZoom(zoom) + (isHovered ? 2 : 0)
            radiusForZoom: t = clamp((zoom-2.5)/(20-2.5), 0, 1)
                           round(4 + t*(18-4))
baseWidth = isActive ? 4 : 2
lineDash  = isActive ? [] : []          // inactiveDash is intentionally empty

[0] (only when hovered) white stroke, width = baseWidth + 8 + 4
[1] colour stroke,        width = baseWidth
[2] colour + '66' stroke, width = baseWidth + 8      // ~40 % opacity overlay
[3] Icon at geom.getCoordinateAt(0.5) (line midpoint),
    src = composite marker data-URI, width=height=markerSize,
    displacement = isHovered ? [0,6] : [0,0]
```

**Composite marker construction** — `RestrictionDisplayUtility.buildRestrictionMarkerDataUri(meta, bgColor, radius)`:

1. Requires `meta.ui.icon.type === 'image/svg+xml'` and a base64 `payload`.
2. `atob(payload)` → raw SVG text.
3. `prepareRestrictionMarkerSvg` strips existing `width`/`height` attributes and injects
   `width="{size}" height="{size}"` (plus optional `x`/`y`).
4. `paintRestrictionMarkerSvg`:
   - finds the **first `<circle>`** and, if its `fill` is a paintable colour, replaces it with a
     sentinel token `__restriction_marker_background__`;
   - then rewrites every `fill`/`stroke`: the sentinel → `bgColor`, every other paintable colour → `white`;
   - if there was no circle, the **first paintable `fill`** becomes `bgColor` and the rest become `white`.
   - "paintable" excludes `''`, `none`, `transparent`, `currentcolor`.
5. Returns `data:image/svg+xml;charset=utf-8,` + `encodeURIComponent(svg)`.

`buildRestrictionHoverMarkerDataUri` wraps the same output in an outer SVG with a
2 px white background circle.

Both are memoised in `markerCache` / `hoverMarkerCache`, keyed
`` `${restrictionId}|${state}|${color}|${radius}|${iconPayload}` ``.

**Colour resolution** — `RestrictionDisplayUtility.getVisibleRestrictionInfo`:

```
isActive = restrictionData.state === 'EFFECTIVE'
color    = isActive ? getRestrictionColor(meta) : '#999'
getRestrictionColor: getRestrictionIconColor(meta)   // first usable <circle fill>, else first usable fill
                     ?? first /color:\s*([^;"'}\s]+)/i match in atob(meta.ui.style.payload)
                     ?? null
```

> **Enum divergence:** the backend schema `RestrictionTypes.yaml` defines
> `RestrictionState = ACTIVE | INACTIVE | CANCELLED`, and the restriction ETL maps
> `RestrictionData.StateEnum.valueOf(state.name())` straight through. But the frontend's
> `isRestrictionActive()` tests for the string **`'EFFECTIVE'`**, which the schema does not
> contain. With the current backend, `isActive` is therefore always `false`, restrictions render in
> the inactive grey `#999` at width 2. The `ACTIVE_RESTRICTION_STATES` set used for ribbon
> enablement accepts both `'effective'` and `'active'`. Recorded as an observed inconsistency.

**Hover** — `MapService.setHoveredRestriction(id)` → `OpenLayerRestrictionUtility.setHoveredRestriction(id, source)` → `vectorSource.changed()`.

## 4.10 Tooltips / popovers

`TooltipPositionService` — [services/tooltip-position/tooltip-position.service.ts](../infra/components/infra-webapp/src/app/services/tooltip-position/tooltip-position.service.ts)

```
handleTooltip(evt):
  if (evt.dragging) → hideTooltip()
  pixel   = map.getEventPixel(evt.originalEvent)
  feature = mapService.getClusterFeatureAtPixel(pixel)      // active train layer only
  clusterFeatures = feature?.get('features')
  singleFeature = clusterFeatures?.length === 1 ? clusterFeatures[0]
                : !clusterFeatures                ? feature
                : null                            // multi-train cluster → no train tooltip
  if (singleFeature) → renderTooltipContent(singleFeature); updateTooltipPosition(evt.originalEvent)
  else               → tryRenderRestrictionTooltip(pixel, evt.originalEvent)
```

`updateTooltipPosition(event)` — pure DOM positioning with viewport clamping:

```
x = clientX + 12 ; y = clientY + 12
if (x + 450 > innerWidth)          x = clientX - 450 - 12
if (x < 0)                          x = 12
if (y + (el.offsetHeight || 180) > innerHeight)  y = clientY - popoverHeight - 12
if (y < 0)                          y = 12
el.style.left/top = …px ; el.style.display = ''
```

**Train popover mapping** — `mapFeatureToPopoverData(feature, timeZone)`
([utility/train-popover.mapper.ts](../infra/components/infra-webapp/src/app/utility/train-popover.mapper.ts)):

| Popover field           | Source                                                                                      |
| ----------------------- | ------------------------------------------------------------------------------------------- |
| `header.title`          | `Train {extractTrainDisplayName(trainServiceId)}`                                           |
| `header.subtitle`       | `` `${origin} → ${destination}` `` or a single value or `'-'`                               |
| `body[0]` Train Weight  | `feature.get('weight') ? '{w}t' : '-'`                                                      |
| `body[1]` Train Length  | `feature.get('length') ? '{l}m' : '-'`                                                      |
| `body[2]` Max Speed     | `feature.get('maxSpeed') ? '{s} km/h' : '-'`                                                |
| `trainDepartureInfoRow` | icon `departure_time_infra_popover`, value = `moment.utc(toTime).tz(tz).format('HH:mm:ss')` |
| `footer`                | `{ title: 'Dangerous Goods' }` only when `hasDangerousGoods` truthy                         |

**Restriction popover mapping** — `mapRestrictionFeatureToPopoverData(feature, iconName, timeZone)`
([utility/restriction-popover.mapper.ts](../infra/components/infra-webapp/src/app/utility/restriction-popover.mapper.ts)):

```
header  = { icon: iconName || 'restriction', iconBackgroundColor: color,
            text: name || shortName || 'Restriction' }
bodyRows[0] = [ ID, Name of Restriction, State, Affected Trains ('N/A') ]
bodyRows[1] = [ From (DD/MM/YYYY\nHH:mm), To (same), Impact Type ]
notes       = { title:'Notes', content:'N/A' }
impactTypes = unique keys of every impact object, camelCase → Title Case, joined ', '
              e.g. "Train Filter, Blocking, Speed Reduction"
```

Restriction icons are registered on the fly:
`resolveRestrictionIconName(feature)` → `restriction-icon-{id}` via
`IconService.registerSvgLiteral(name, atob(payload))`, memoised in a `Set`; falls back to the
static `'restriction'` icon.

## 4.11 Zooming, panning, selection, editing, drag/drop

| Capability                      | Present?                                                 | Implementation                                                                                        |
| ------------------------------- | -------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Zoom                            | Yes (mouse wheel / pinch — OL default interactions)      | `View` `minZoom 2.5` / `maxZoom 20`; effective min raised to the fitted zoom after `fitViewToData`    |
| Zoom buttons                    | **No** — `defaultControls({ zoom:false, rotate:false })` | —                                                                                                     |
| Pan                             | Yes (OL default)                                         | `moveend` → tile refresh                                                                              |
| Programmatic pan                | Yes                                                      | `panToKeepVisible(coord, overlayFraction = 0.5)`, `restoreViewCenter(center)`, `focusSelectedTrain()` |
| Selection                       | Yes                                                      | Single click; `selectedTrainServiceId` in `MapService`                                                |
| Hover                           | Yes                                                      | Cursor change + popover + restriction halo                                                            |
| Context menu                    | Yes                                                      | Native `contextmenu` listener on `map.getViewport()`; only fires for the already-selected train       |
| Double-click zoom               | **Disabled**                                             | The `dblclick` handler calls `preventDefault()`, `stopPropagation()` and returns `false`              |
| Cluster click-to-fit            | Yes                                                      | `handleClusterClick` → `view.fit(clusterExtent, { duration: 500, padding:[50,50,50,50] })`            |
| **Editing geometry on the map** | **NO**                                                   | `NOT FOUND` — no `ol/interaction/Draw`, `Modify`, `Translate`, `Snap`, `Select` anywhere              |
| **Drag & drop**                 | **NO**                                                   | `NOT FOUND` — no HTML5 DnD, no CDK DragDrop                                                           |
| Real-time updates               | Yes — **polling only**                                   | `TrainPositionStore` + `RestrictionsStore` + `BusinessClockEffects`                                   |

## 4.12 Map state maintenance

| State                          | Owner                                                                                                                | Notes                                                                                         |
| ------------------------------ | -------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| `Map`, all layers, all sources | `MapService` (root singleton)                                                                                        | Survives navigation; `cleanup()` only detaches (`setTarget(undefined)`) and removes listeners |
| Loaded nodes                   | `MapStateStore.loadedNodes`                                                                                          | O(1) access, avoids scanning OL features                                                      |
| Selected train                 | `MapService.selectedTrainServiceId` (private)                                                                        | + `pendingFocusSelectedTrain` retry flag                                                      |
| Hovered restriction            | `OpenLayerRestrictionUtility.hoveredRestrictionId` (static) and `TooltipPositionService.currentHoveredRestrictionId` |                                                                                               |
| Cluster distance / enabled     | `MapService.currentClusterDistance`, `clusteringEnabled`                                                             |                                                                                               |
| OL listener keys               | `MapService.boundHandlerKeys: EventsKey[]` + `contextMenuHandler`                                                    | `unByKey()` in `clearBoundHandlers()`                                                         |
| Tile grid                      | `TrainPollingCoordinatorService.tileCalculationResult`                                                               | Plus `viewportTileUpdateInProgress` re-entrancy guard (released after `setTimeout(…, 100)`)   |
| Layer visibility               | `FilterStateStore` (+ `localStorage`)                                                                                |                                                                                               |
| Timestamps                     | `InfraContentComponent.baseBusinessTime / adjustedTimestamp / currentTimestamp`                                      |                                                                                               |

## 4.13 Map data end-to-end trace

### (A) Infrastructure geometry

```
RabbitMQ  rise.events / event.infra.microscopic_region
   → queue de.hacon.tps.rise.client.infrabasegraph.event.consumer
   → InfraBaseGraphEventHandler.handleValidatedMessage(InfraMicroscopicRegionEvent)
   → RISEApplicationContext.getComponent(InfraBaseGraphService)
   → InfraBaseGraphService.processBaseGraphEvent(event)
   → BaseGraphMapper.map(event)
        id            = event.baseEntityEvent.entityID
        baseGraph     = { nodes: mapNodes(...), edges: mapEdges(...) }
        node          = { baseSubEntityData{id,name,shortName,description},
                          nodeData{ coordinates.graphical{x,y},
                                    infraNodeAddress{kmRegion, kmValue ← source.infraAddress.kmValueMillimeters} } }
        edge          = { baseSubEntityData{...},
                          edgeData{ infraNodeRefs: LinkedHashSet<InfraMicroscopicNodeRef>,
                                    edgeLengthMillimeters (Long→int), direction } }
   → BaseGraphRepository.save(baseGraph)
   → MongoBaseGraphRepositoryCustomImpl.save → MongoBaseGraphEntity
   → MongoDB  infra-rivm.basegraph   (_id = region entityID)

HTTP  GET /api/infra/query/basegraph?pageNumber=0&pageSize=1000
   → BaseGraphController.getAllBaseGraphDetails
   → BaseGraphService.getAllBaseGraphs → BaseGraphRepository.findAll(PageRequest)
   → APIPaginatedResponse<BaseGraph>{ data, meta.page }
   → JSON

Angular
   → BaseGraphApiService.getEdgeData()                (IndexedDB cache 'infra_basegraph_cache', TTL 1 h)
   → EdgeDataEffects.loadEdgeData$ → loadEdgeDataSuccess({edgeData})
   → edgeDataReducer → selectAllEdgeData
   → InfraContentComponent.loadGraphData(edgeData)
        nodes = OpenLayerInfraUtility.extractNodes(edgeData)
        edges = OpenLayerInfraUtility.extractEdges(edgeData)
   → TrainPollingCoordinatorService.initializeTiles(nodes, trainsLayer, currentTimestamp)
   → MapService.loadGraphData(nodes, edges)
        vectorSource.clear()
        mapStateStore.setLoadedNodes(nodes)
        createNodeFeatures(nodes, vectorSource)   → Point features
        createEdgeFeatures(edges, nodes, vectorSource) → LineString features
   → fitViewToData() → loadOverviewMapData()
   → CANVAS: grey (#898995) 1-px polylines
```

### (B) Train positions

```
RabbitMQ  rise.events / event.train_operation.train_operation  (or …forecast)
   → queue de.hacon.tps.rise.client.trainoperation.event.consumer
   → InfraTrainOperationMovementEventHandler.handleValidatedMessage(TrainOperationEvent)
   → InfraTrainOperationService.processTrainOperationMovementEvent(event)
   → RiseToInfraMapper.map(trainOperationData, trainServiceId, baseEntityData, existingPositions)
        → ActivityContext[]  (extract + filter)
        → TrainOperationUtil.createTrainPosition(TrainPositionParams)
             coordinates ← TrackCoordinatesService cache  (location activities)
                         ← MicroscopicInfraService.findEdges(infraAddress) (km activities)
             dataTileIds ← DataTileService.createTileIds(trainPosition)
   → InfraTrainOperationService.filterMovementPositions(...) → savePositionsAndTiles(...)
   → DataTileService.createDataTiles(ids) → DataTileRepository.saveAll  (new random UUID version)
   → TrainPositionRepository.saveAll
   → MongoDB  infra-rivm.train-position  +  infra-rivm.data-tile

HTTP  POST /api/infra/query/trainpositions  body [{id,version?}…]
   → TrainPositionController.getPositions
   → TrainPositionService.getModifiedTrainPositionsByTiles
       (version diffing; empty page if nothing changed)
   → APIPaginatedResponse<TrainPosition>{ data, meta.page, meta.dataTileVersions[0] }

Angular
   → TrainPositionService.getTrainPositions(tiles)
   → TrainPositionStore (merge by id, update tile versions)
   → InfraContentComponent.updateTrainDisplay()
        TimeCalculationService.filterPositionsByTime(positions, adjustedTimestamp)
   → MapService.updateTrainPositions(filtered)
   → OpenLayerClusterUtility.createTrainPositionFeatures → Point features
   → ClusterSource.refresh()
   → layer style fn → getClusterStyle / resolveTrainStyles
   → CANVAS: coloured train icon (+ label + connector at zoom > 18) or green donut cluster
```

### (C) Restrictions

```
RabbitMQ  rise.events / <restriction routing key: NOT DETERMINED>
   → queue de.hacon.tps.rise.client.restriction.event.consumer
   → RestrictionEventHandler.handleValidatedMessage(RestrictionEvent)
   → RestrictionService.processRestrictionEvent(event)   [restriction-etl]
        ENTITY_CREATED / ENTITY_UPDATED → RestrictionMapper.mapEventToRestriction → repo.save
        ENTITY_DELETED                  → repo.deleteById(entityID)
   → RestrictionMapper.mapEdgePaths(dtoData.segments)
        → MicroscopicInfraService.findEdgePaths(segments)   [rise-infra-utils]
        → EdgePath { pathEdges: EdgeWithOffsets[], pathCoordinates: InfraGraphicalCoordinates[] }
   → MongoDB  infra-rivm.restriction

HTTP  GET /api/infra/query/restrictions?effectiveAt=…&pageNumber=0&pageSize=100
   → RestrictionController.getRestrictionsByTime
   → RestrictionService.getRestrictionsByEffectiveTime  (Sort DESC lastModified)
   → MongoRestrictionRepository.findByEffectiveTime  (startTime <= t <= endTime, string compare)
   → APIPaginatedResponse<Restriction>

Angular
   → RestrictionApiService.getRestrictionData(effectiveAt) → normalizeApiResponse
   → RestrictionsStore (polling) → visibleRestrictionInfos (computed)
   → InfraContentComponent.updateRestrictionsDisplay(infos)
   → MapService.updateRestrictions(infos)
   → OpenLayerRestrictionUtility.updateRestrictionFeatures → LineString features per edgePath
   → style fn → 2–4 strokes + composite marker Icon at line midpoint
   → CANVAS: coloured track overlay + circular icon
```

### (D) Location / platform labels

```
RabbitMQ event.infra.microscopic_region
   → queue de.hacon.tps.rise.client.inframicro.event.consumer
   → InfraMicroEventHandler → InfraMicroService.setInfraMicro(event)
   → RiseToInfraMapper.map(InfraMicroscopicRegionData)          [micro-etl]
        indexBaseGraphNodes(baseGraph) : Map<nodeId, InfraMicroscopicNode>
        for each location.locationData.tracks[]:
            TrackCoordinates.id = `${location.baseSubEntityData.id}_${track.baseSubEntityData.id}`
            nodeCoordinates = trackData.subGraph.nodeRefs → baseGraphNodesById → {x,y}
            trackSubEntityData / locationSubEntityData = mapped BaseSubEntityData
   → TrackCoordinatesRepository.saveAll
   → MongoDB infra-rivm.track-coordinates

HTTP GET /api/infra/query/location-track-coordinates?pageNumber&pageSize
   → LocationTrackCoordinatesController → LocationTrackCoordinatesService
   → TrackCoordinatesRepository.findLocationsWithTracks(pageable)   (aggregation, §2.1)
   → APIPaginatedResponse<LocationWithTracks>

Angular
   → LocationTrackCoordinatesApiService (all pages, retry 3, cached in IndexedDB)
   → LocationsStore.locations
   → MapService.loadLocationLabels(...)
   → OpenLayerLocationLabelUtility.createLocationLabelFeatures / createTrackLabelFeatures
   → CANVAS: white text with dark halo, zoom-gated per MapConfig
```

## 4.14 Exact files/classes/functions involved in the map

| File                                                                      | Class / function                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `master-layout/infra-content/infra-content.component.ts`                  | `InfraContentComponent` — `ngOnInit`, `initializeMap`, `loadConfigurations`, `loadEdgeDataAndSubscribe`, `subscribeToBusinessClock`, `loadGraphData`, `handleRestrictionsZoomChange`, `fitMapAndLoadOverview`, `updateTimestamps`, `recalculateTiles`, `updateTrainDisplay`, `updateTrainVisibility`, `updateRestrictionsVisibility`, `updateRestrictionsDisplay`, `handleResolutionChange`, `handleMoveEnd`, `handleTrainSingleClick`, `handleTrainDoubleClick`, `handleTrainContextMenu`, `onContextMenuSelect`, `onDocumentClick`, `onZoomLevelChange`, `toggleClustering`, `incrementTime`, `decrementTime`, `resetToNow`, `onTimeOffsetChange`, `handlePanelStateChange`                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `services/map/map.service.ts`                                             | `MapService` — `initializeMap`, `createVectorLayers`, `createLocationLabelLayers`, `createClusteredTrainLayers`, `createRestrictionsLayer`, `createOverviewMapControl`, `createTooltipOverlay`, `createMapInstance`, `registerEventCallbacks`, `addHandler`, `clearBoundHandlers`, `resolveTrainServiceIdAtPixel`, `resolveTrainServiceIdAtPixelCoords`, `setInfraLayerZIndex`, `loadGraphData`, `loadLocationLabels`, `loadOverviewMapData`, `fitViewToData`, `updateTrainPositions`, `setTrainLayerVisible`, `setLocationLayerVisible`, `setPlatformLayerVisible`, `setClusteringEnabled`, `updateClusteringDistance`, `handlePointerMove`, `handleClusterClick`, `getClusterFeatureAtPixel`, `refreshSemanticZoom`, `getCurrentZoom`, `getVisibleExtent`, `getLoadedNodes`, `getTooltipOverlay`, `getMap`, `getViewCenter`, `restoreViewCenter`, `setSelectedTrain`, `getSelectedTrainServiceId`, `getSelectedTrainCoordinate`, `focusSelectedTrain`, `panToKeepVisible`, `getTrainPositionsLayer`, `updateRestrictions`, `setRestrictionsLayerVisible`, `setHoveredRestriction`, `getRestrictionFeatureAtPixel`, `getRestrictionsLayer`, `cleanup` |
| `utility/open-layer-utility/open-layer-infra.utility.ts`                  | `OpenLayerInfraUtility` — `extractNodes`, `extractEdges`, `createNodeFeatures`, `createEdgeFeatures`, `getFeatureStyle`, `getNodeStyle`, `getEdgeStyle`, `fitViewToExtent`, `createOverviewMapControl`, `setupFrozenOverview`, `fitMapViewWithMinZoom`, `createMainVectorLayer`, `loadGraphData`, `createTileGrid`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `utility/open-layer-cluster-utility/open-layer-cluster.utility.ts`        | `OpenLayerClusterUtility` — `quantizeDirection`, `getTrainIconStyle`, `getTrainLabelStyles`, `resolveTrainStyles`, `createTrainPositionFeatures`, `createTrainClusterSource`, `createClusteredTrainPositionsVectorLayer`, `createNonClusteredTrainLayer`, `getClusterStyle`, `getClusteringDistanceForZoom`, `getTrainsFromCluster`, `getClusterExtent`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `utility/open-layer-utility/open-layer-location-label.utility.ts`         | `OpenLayerLocationLabelUtility` — `createLocationLabelLayer`, `createTrackLabelLayer`, `buildLayer`, `createLocationLabelFeatures`, `createTrackLabelFeatures`, `calculateBoundingBox`, `calculateBoundingBoxCenter`, `getLabelStyle`, `getLocationLabelStyle`, `getTrackLabelStyle`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `utility/open-layer-utility/open-layer-restriction.utility.ts`            | `OpenLayerRestrictionUtility` — `radiusForZoom`, `getMarkerCacheKey`, `getMarker`, `getHoverMarker`, `setHoveredRestriction`, `createRestrictionFeatures`, `createRestrictionVectorLayer`, `updateRestrictionFeatures`, `getRestrictionFromFeature`, `filterRestrictionsByStatus`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `utility/label-placement.engine.ts`                                       | `LabelPlacementEngine` — `resetIfViewChanged`, `getCached`, `setCached`, `reset`, `registerIcon`, `placeLabel`, `rectLeft`, `hasOverlap`, `overlapArea`, `pushRect`, `estimateLabelWidth`, `estimateLabelHeight`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `utility/restriction-display.utility.ts`                                  | `RestrictionDisplayUtility` (20 static methods)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `utility/train-type.utility.ts`                                           | `extractTrainColor`, `extractTrainHighlightColor`, `getTrainTypeName`, `getTrainTypeCategory`, `extractTrainDisplayName`, `loadTrainIconTemplate`, `_resetTrainIconCache`, `buildTrainIconDataUri`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `utility/train-popover.mapper.ts`                                         | `mapFeatureToPopoverData`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| `utility/restriction-popover.mapper.ts`                                   | `mapRestrictionFeatureToPopoverData`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `services/tooltip-position/tooltip-position.service.ts`                   | `TooltipPositionService`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `services/tile-management/tile-management.service.ts`                     | `TileManagementService`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `services/train-polling-coordinator/train-polling-coordinator.service.ts` | `TrainPollingCoordinatorService`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `services/time-calculation/time-calculation.service.ts`                   | `TimeCalculationService`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `config/open-layer.config.ts`                                             | `CLUSTER_CONFIG`, `RESTRICTION_STYLE_CONFIG`, `MAP_LAYER_ZINDEX`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `config/infra-view.config.ts`                                             | `INFRA_VIEW`, `INFRA_ZOOM_CONFIG`, `MAP_VIEW_CONFIG`, `INFRA_COLOR_CONFIG`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |

---

# 5 — BACKEND ARCHITECTURE — JAVA

## 5.0 Build platform

`components/platform/build.gradle.kts` is a Gradle **`java-platform`** (BOM) with
`allowDependencies()`:

| Imported BOM / constraint                               | Version   |
| ------------------------------------------------------- | --------- |
| `org.springframework.boot:spring-boot-dependencies`     | **4.1.0** |
| `com.fasterxml.jackson:jackson-bom`                     | 2.19.2    |
| `org.testcontainers:testcontainers-bom`                 | 1.21.4    |
| `org.openapitools:openapi-generator` / `-gradle-plugin` | 7.20.0    |
| `io.swagger.core.v3:swagger-annotations(-jakarta)`      | 2.2.28    |
| `org.openapitools:jackson-databind-nullable`            | 0.2.6     |
| `org.springdoc:springdoc-openapi-starter-webmvc-ui`     | 3.0.3     |
| `org.awaitility:awaitility`                             | 4.2.0     |

Root [build.gradle.kts](../infra/build.gradle.kts) applies `de.hacon.tps.convention.root.product`
(`3.+`) and declares `org.openapi.generator` (`7.20.0`) with `apply false`.
`gradle/libs.versions.toml` pins `rise-utils = "13.1.0"` for both
`de.hacon.tps.rise:rise-api-utils` and `de.hacon.tps.rise:rise-infra-utils`.

Common convention plugins: `de.hacon.tps.convention.java.application`,
`…java.library`, `…node.angular`.

---

## 5.1 `infra-common-lib`

**Location:** `components/infra-common-lib/`
**Purpose:** OpenAPI-generated domain model + persistence abstraction + shared API envelopes +
global exception handling.

### Build & code generation

`build.gradle.kts`:

```kotlin
plugins { alias(libs.plugins.tps.convention.java.application)
          alias(libs.plugins.org.openapi.generator)
          `java-library` }

openApiGenerate {
  generatorName = "spring"
  inputSpec     = "$rootDir/components/infra-common-lib/infra-model.yaml"
  outputDir     = "$buildDir/generated"
  modelPackage  = "de.hacon.tps.rise.infra.common.generated.rivm"
  globalProperties = mapOf("apis" to "false", "models" to "", "supportingFiles" to "false")
  configOptions    = mapOf(
      "dateLibrary" to "java21",
      "useSpringController" to "false",
      "useBeanValidation" to "true",
      "openApiNullable" to "true",
      "useSpringBoot4" to "true",
      "additionalModelTypeAnnotations" to
        "@lombok.Generated;@lombok.Data;@lombok.NoArgsConstructor;@lombok.AllArgsConstructor;" +
        "@com.fasterxml.jackson.annotation.JsonInclude(…Include.NON_NULL)",
      "additionalEnumTypeAnnotations" to "@lombok.Generated")
}
sourceSets.main { java { srcDirs("$buildDir/generated/src/main/java") } }
rise { coverage { excludePatterns = listOf("**.generated.**") } }
tasks.withType<JavaCompile> { dependsOn(tasks.openApiGenerate) }
```

> Key consequence: **all domain POJOs are `@lombok.Data` + `@JsonInclude(NON_NULL)`**, so null
> fields never appear in JSON responses.

`infra-model.yaml` (OpenAPI 3.1) declares the generated set:

| Generated model      | `$ref` source                                               |
| -------------------- | ----------------------------------------------------------- |
| `ApiErrorResponse`   | `schemas/basic/ErrorResponse.yaml#/ApiErrorResponse`        |
| `Meta`               | `schemas/basic/Meta.yaml#/Meta`                             |
| `BusinessClock`      | `schemas/clock/BusinessClock.yaml#/BusinessClock`           |
| `BaseGraph`          | `schemas/infra/BaseGraph.yaml#/BaseGraph`                   |
| `LocationDataTile`   | `schemas/infra/LocationDataTile.yaml#/LocationDataTile`     |
| `TrainPosition`      | `schemas/infra/TrainPosition.yaml#/TrainPosition`           |
| `DataTile`           | `schemas/infra/DataTile.yaml#/DataTile`                     |
| `Region`             | `schemas/infra/Region.yaml#/Region`                         |
| `TrackCoordinates`   | `schemas/infra/TrackCoordinates.yaml#/TrackCoordinates`     |
| `LocationWithTracks` | `schemas/infra/LocationWithTracks.yaml#/LocationWithTracks` |
| `MapConfig`          | `schemas/infra/MapConfig.yaml#/MapConfig`                   |
| `Activity`           | `schemas/infra/Activity.yaml#/Activity`                     |
| `Restriction`        | `schemas/infra/Restriction.yaml#/Restriction`               |

Transitively generated (inline/`$ref`ed sub-objects observed in imports):
`ErrorResponse`, `MetaPage`, `InfraMicroscopicBaseGraph`, `InfraMicroscopicNode`,
`InfraMicroscopicNodeData`, `InfraMicroscopicNodeAddress`, `InfraMicroscopicNodeCoordinates`,
`InfraMicroscopicNodeBaseSubEntityData`, `InfraGraphicalCoordinates`, `InfraMicroscopicEdge`,
`InfraMicroscopicEdgeData` (+ `DirectionEnum`), `InfraMicroscopicNodeRef`,
`InfraMicroscopicNodeRefInfraMicroscopicNodeRef`, `InfraMicroscopicNodeRefRegionRef`,
`InfraMicroscopicEdgeRef`, `NodeCoordinates`, `LocationWithTracksTracksInner`, `MapLayer`,
`TileSize`, `RestrictionData` (+ `StateEnum`), `RestrictionDataEffectiveTimePeriod`,
`RestrictionDataGroup`, `RestrictionDataMeta`, `RestrictionDataMetaUi`, `RestrictionDataMetaUiIcon`,
`RestrictionImpact`, `RestrictionImpactBlocking`, `RestrictionImpactSpeedReduction`,
`RestrictionImpactAdhesion` (+ `AdhesionLevelEnum`), `RestrictionImpactTrainFilter`,
`RestrictionImpactTrainOperationFilter` (+ `OperatorEnum`),
`RestrictionImpactTrainCompositionFilter` (+ `OperatorEnum`),
`PropertyFilterCondition` (+ `OperatorEnum`), `EdgePath`, `EdgeWithOffsets`,
`TrainPosition.RunningTypeEnum`, `TrainPosition.ActivityTypeEnum`, `BusinessClock.ModeEnum`,
`MapConfig.MapTypeEnum`.

### Packages

```
de.hacon.tps.rise.infra.common
├── api.response
│   ├── APIResponse<T>            { T data }
│   └── APIPaginatedResponse<T>   { List<T> data = new ArrayList<>(); Meta meta;
│                                   MIN_PAGE_SIZE = 1;
│                                   MAX_PAGE_SIZE = 1000;
│                                   COORDINATES_MAX_PAGE_SIZE = 10000 }
├── exception
│   ├── ErrorCodes                { DATA_NOT_FOUND "404", INTERNAL_SERVER_ERROR "500",
│   │                               BAD_REQUEST "400", INVALID_DATA_TILE_ID "20001" }
│   ├── BadRequestException       extends RuntimeException, carries String code
│   ├── ResourceNotFoundException extends RuntimeException
│   └── GlobalExceptionHandler    @ControllerAdvice extends ResponseEntityExceptionHandler
├── repository                    (pure interfaces — no Spring Data inheritance)
│   ├── BaseGraphRepository, BusinessClockRepository, DataTileRepository,
│   ├── MapConfigRepository, RestrictionRepository, TrackCoordinatesRepository,
│   └── TrainPositionRepository
├── repository.mongodb            (entities + Spring Data repos + adapters)
└── generated.rivm                (build-time OpenAPI models)
```

### Repository interfaces (the "pure" contract)

| Interface                    | Methods                                                                                                                                                                                                                                                                                  |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `BaseGraphRepository`        | `Page<BaseGraph> findAll(Pageable)`, `void deleteAll()`, `List<BaseGraph> saveAll(List<BaseGraph>)`, `BaseGraph save(BaseGraph)`                                                                                                                                                         |
| `BusinessClockRepository`    | `BusinessClock save(BusinessClock)`, `List<BusinessClock> findAll()`, `void deleteAll()`                                                                                                                                                                                                 |
| `DataTileRepository`         | `List<DataTile> saveAll(List<DataTile>)`, `List<DataTile> findAllById(List<String>)`, `void deleteAll()`                                                                                                                                                                                 |
| `MapConfigRepository`        | `List<MapConfig> findAll()`                                                                                                                                                                                                                                                              |
| `RestrictionRepository`      | `Page<Restriction> findByEffectiveTime(Instant, Pageable)`, `List<Restriction> saveAll(List<Restriction>)`, `void deleteAll()`, `void deleteById(String)`, `Restriction save(Restriction)`, `Optional<Restriction> findById(String)`                                                     |
| `TrackCoordinatesRepository` | `List<TrackCoordinates> saveAll(List<TrackCoordinates>)`, `Page<TrackCoordinates> findAll(Pageable)`, `List<TrackCoordinates> findAll()`, `Page<LocationWithTracks> findLocationsWithTracks(Pageable)`, `void deleteAll()`                                                               |
| `TrainPositionRepository`    | `List<TrainPosition> findByTrainServiceId(String)`, `List<TrainPosition> saveAll(List<TrainPosition>)`, `List<TrainPosition> findAllById(List<String>)`, `Page<TrainPosition> findByDataTileIdsIn(Collection<String>, Pageable)`, `void deleteAll()`, `void deleteAllById(List<String>)` |

### Mongo entities

Each entity **extends the generated model** and adds `@Document(collection = "${property}")`:

| Entity                        | Extends            | Collection property                      | Extra annotations                          |
| ----------------------------- | ------------------ | ---------------------------------------- | ------------------------------------------ |
| `MongoBaseGraphEntity`        | `BaseGraph`        | `${app.db.collection.basegraph}`         | `@NoArgsConstructor`                       |
| `MongoBusinessClockEntity`    | `BusinessClock`    | `${app.db.collection.business-clock}`    | `@NoArgsConstructor` + 4-arg ctor          |
| `MongoDataTileEntity`         | `DataTile`         | `${app.db.collection.data-tile}`         | `@Data @EqualsAndHashCode(callSuper=true)` |
| `MongoMapConfigEntity`        | `MapConfig`        | `${app.db.collection.map-config}`        | _(none)_                                   |
| `MongoRestrictionEntity`      | `Restriction`      | `${app.db.collection.restriction}`       | `@Data @EqualsAndHashCode(callSuper=true)` |
| `MongoTrackCoordinatesEntity` | `TrackCoordinates` | `${app.db.collection.track-coordinates}` | `@NoArgsConstructor`                       |
| `MongoTrainPositionEntity`    | `TrainPosition`    | `${app.db.collection.train-position}`    | `@Data @EqualsAndHashCode(callSuper=true)` |

> **`app.db.collection.map-config` is NOT declared in `infra-common-lib/src/main/resources/application.properties`.**
> It is declared only in `infra-query-svc` and `infra-trainoperation-etl`. Any application that
> component-scans `…common.repository.mongodb` without defining that property would fail to resolve
> the `@Document` placeholder for `MongoMapConfigEntity`.

### Spring Data repositories

| Repository                        | Derived / `@Query` methods                                                                                                                                                                                                                     |
| --------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `MongoBaseGraphRepository`        | _(none)_                                                                                                                                                                                                                                       |
| `MongoBusinessClockRepository`    | _(none)_                                                                                                                                                                                                                                       |
| `MongoDataTileRepository`         | _(none)_                                                                                                                                                                                                                                       |
| `MongoMapConfigRepository`        | _(none)_                                                                                                                                                                                                                                       |
| `MongoRestrictionRepository`      | `@Query("{ 'restrictionData.effectiveTimePeriod.startTime': { $lte: ?#{[0].toString()} }, 'restrictionData.effectiveTimePeriod.endTime': { $gte: ?#{[0].toString()} } }") Page<MongoRestrictionEntity> findByEffectiveTime(Instant, Pageable)` |
| `MongoTrackCoordinatesRepository` | `List<MongoTrackCoordinatesEntity> findByLocationSubEntityData_IdIn(List<String>)`                                                                                                                                                             |
| `MongoTrainPositionRepository`    | `Page<TrainPosition> findByDataTileIdsIn(Collection<String>, Pageable)`, `List<MongoTrainPositionEntity> findByTrainServiceId(String)`                                                                                                         |

`MongoRepositoryConfiguration` — `@Configuration @EnableMongoRepositories(basePackages = "de.hacon.tps.rise.infra.common.repository.mongodb")`.

### Adapters (`*CustomImpl`)

All are `@Component public final class … implements <PureInterface>` with `@Autowired` field
injection. They perform an `instanceof` check and, when the incoming object is a plain generated
model, **copy field-by-field** into the Mongo entity:

- `MongoBaseGraphRepositoryCustomImpl` — copies `id` and rebuilds `InfraMicroscopicBaseGraph{nodes, edges}`.
- `MongoBusinessClockRepositoryCustomImpl` — uses the 4-arg entity constructor.
- `MongoDataTileRepositoryCustomImpl` — copies `id`, `version`.
- `MongoMapConfigRepositoryCustomImpl` — read-only `findAll()`.
- `MongoRestrictionRepositoryCustomImpl` — `copyProperties`: `id, name, shortName, description, restrictionData, lastModified`.
- `MongoTrackCoordinatesRepositoryCustomImpl` — copies `id, nodeCoordinates, locationSubEntityData, trackSubEntityData`; implements the two-stage aggregation described in §2.1.
- `MongoTrainPositionRepositoryCustomImpl` — copies `id, trainServiceId, activityId, activityType, dataTileIds, fromTime, toTime, runningType, origin, destination, coordinates`.

### Configuration

`infra-common-lib/src/main/resources/application.properties`:

```properties
spring.application.name=infra-common-lib
app.db.collection.business-clock=infra-rivm.business-clock
app.db.collection.location=infra-rivm.location
app.db.collection.basegraph=infra-rivm.basegraph
app.db.collection.train-position=infra-rivm.train-position
app.db.collection.data-tile=infra-rivm.data-tile
app.db.collection.track-coordinates=infra-rivm.track-coordinates
app.db.collection.restriction=infra-rivm.restriction
```

(`app.db.collection.location` is declared but **no entity references it** — dead property.)

### Dependencies

`spring-boot-starter-webmvc`, `spring-boot-starter-data-mongodb`, `spring-boot-starter-validation`,
`rise-api-utils`, `swagger-annotations` (api), `swagger-annotations-jakarta` (api),
`jackson-annotations` (api), `jackson-databind-nullable`, Lombok.

---

## 5.2 `infra-query-svc`

**Entry point:** `de.hacon.tps.rise.infra.query.QueryServiceApplication`

```java
@SpringBootApplication
@EnableSpringDataWebSupport(pageSerializationMode = PageSerializationMode.VIA_DTO)
@ComponentScan(basePackages = {
    "de.hacon.tps.rise.infra.query",
    "de.hacon.tps.rise.infra.common.exception",
    "de.hacon.tps.rise.infra.common.repository",
    "de.hacon.tps.rise.api.utils.config" })
@ConfigurationPropertiesScan("de.hacon.tps.rise.api.utils")
public class QueryServiceApplication {
  public static void main(String[] args) { SpringApplication.run(...); }

  @Bean public WebMvcConfigurer corsConfigurer() {
    return new WebMvcConfigurer() {
      @Override public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/**").allowedOrigins("http://localhost:4200");
      }};
  }
}
```

> **CORS is hard-coded to `http://localhost:4200`.** There is no property to change it.
> In production the SPA is served same-origin behind the gateway, so CORS is not exercised.

### Packages / classes

| Package                 | Classes                                                                                                                                                                                      |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `…query`                | `QueryServiceApplication`                                                                                                                                                                    |
| `…query.controller.api` | `BaseGraphController`, `BusinessClockController`, `ConfigController`, `LocationTrackCoordinatesController`, `RestrictionController`, `TrackCoordinatesController`, `TrainPositionController` |
| `…query.service`        | `BaseGraphService`, `BusinessClockService`, `ConfigService`, `LocationTrackCoordinatesService`, `RestrictionService`, `TrackCoordinatesService`, `TrainPositionService`                      |
| `…query.util`           | `APIMapper<T>`                                                                                                                                                                               |

### `APIMapper<T>` (`@Component public final class`)

```java
public Meta mapPageToMetaPage(Page<T> page) {
  Meta meta = new Meta();
  meta.setPage(new MetaPage(page.getNumber(), page.getSize(),
                            (int) page.getTotalElements(), page.getTotalPages()));
  return meta;
}
public Meta mapPageToMetaPage(Page<T> page, Map<String,String> dataTileVersions) {
  var meta = mapPageToMetaPage(page);
  meta.getDataTileVersions().add(dataTileVersions);   // list with exactly one map
  return meta;
}
```

### Injection styles (inconsistent by design age)

- Field `@Autowired`: `BaseGraphController`, `BusinessClockController`, `ConfigController`,
  `BaseGraphService`, `BusinessClockService`, `ConfigService`.
- Lombok `@AllArgsConstructor` constructor injection: `LocationTrackCoordinatesController/Service`,
  `RestrictionController/Service`, `TrackCoordinatesController/Service`,
  `TrainPositionController/Service`.

### Business logic summary

| Service                           | Logic                                                                                                                                                                  |
| --------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `BaseGraphService`                | `PageRequest.of(pageNumber, pageSize)` — **no sort**                                                                                                                   |
| `BusinessClockService`            | `findAll()`; `throw ResourceNotFoundException("No clock data found")` if empty; else `clocks.get(0)`                                                                   |
| `ConfigService`                   | `findAll()`; `throw ResourceNotFoundException("No map configuration data found")` if empty                                                                             |
| `LocationTrackCoordinatesService` | `PageRequest.of(p, s, Sort.by(Order.asc("id").nullsLast()))`; builds `Meta` **manually** (does not use `APIMapper`), so `meta.dataTileVersions` is left at its default |
| `RestrictionService`              | `PageRequest.of(p, s, Sort.by(DESC, "lastModified"))`; `log.info` before and after                                                                                     |
| `TrackCoordinatesService`         | `PageRequest.of(p, s, Sort.by(Order.asc("id").nullsLast()))`                                                                                                           |
| `TrainPositionService`            | tile-version diffing (§2.2)                                                                                                                                            |

### Configuration (`application.properties`)

```properties
spring.application.name=infra-query-svc
server.port=${SERVER_PORT:9101}
spring.mongodb.host=${MONGO_HOST:localhost}
spring.mongodb.port=${MONGO_PORT:27017}
spring.mongodb.database=${MONGO_DATABASE:risedb}
spring.mongodb.username=${MONGO_USERNAME:guest}     # [SECRET / CREDENTIAL PRESENT — VALUE OMITTED]
spring.mongodb.password=${MONGO_PASSWORD:guest}     # [SECRET / CREDENTIAL PRESENT — VALUE OMITTED]
server.servlet.context-path=/api/infra/query
testcontainers.reuse.enable=true
app.feature.dataTileVersion.isActive=false
app.db.collection.business-clock=infra-rivm.business-clock
app.db.collection.location=infra-rivm.location
app.db.collection.basegraph=infra-rivm.basegraph
app.db.collection.train-position=infra-rivm.train-position
app.db.collection.data-tile=infra-rivm.data-tile
app.db.collection.map-config=infra-rivm.map-config
app.db.collection.track-coordinates=infra-rivm.track-coordinates
app.db.collection.restriction=infra-rivm.restriction
```

> `app.feature.dataTileVersion.isActive` is **not read by any Java code** (grep found only the
> property files) — a dead feature flag.
> `spring.mongodb.*` (rather than `spring.data.mongodb.*`) implies the connection is assembled by
> `rise-api-utils`/`rise-common` conventions rather than Spring Boot's own auto-configuration keys.

### Dependencies

`spring-boot-starter-webmvc`, `-json`, `-data-mongodb`, `-validation`,
`jackson-databind`, `jackson-datatype-jsr310`, `springdoc-openapi-starter-webmvc-ui`,
`project(":components:infra-common-lib")`, Lombok. Tests add Testcontainers (mongodb),
`spring-boot-starter-amqp-test`.

### Scheduled jobs / background workers

**None.**

---

## 5.3 `infra-business-clock-etl`

| Aspect       | Detail                                                                                                                                                                                                                                                              |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Entry point  | `InfraBusinessClockEtlApplication` — `@SpringBootApplication @ComponentScan({"de.hacon.tps.rise.infra.businessclock.etl", "de.hacon.tps.rise.api.utils", "de.hacon.tps.rise.infra.common.repository"}) @ConfigurationPropertiesScan("de.hacon.tps.rise.api.utils")` |
| Handler      | `BusinessClockEventHandler implements de.hacon.tps.rise.api.utils.eventhandling.businessclock.BusinessClockEventHandler`                                                                                                                                            |
| Registration | `META-INF/spring.factories` → `…eventhandling.businessclock.BusinessClockEventHandler=de.hacon.tps.rise.infra.businessclock.etl.eventhandling.BusinessClockEventHandler`                                                                                            |
| Queue        | `rise.api.utils.event_handling.business_clock.queue_name=de.hacon.tps.rise.client.businessclock.event.consumer`                                                                                                                                                     |
| Service name | `rise.api.utils.service.name=de.hacon.tps.rise.infra.businessclock`                                                                                                                                                                                                 |
| Service      | `BusinessClockService.setBusinessClock(BusinessClockEvent)`                                                                                                                                                                                                         |
| Mapper       | `RiseToInfraMapper.map(BusinessClockData)`                                                                                                                                                                                                                          |
| Repository   | `BusinessClockRepository`                                                                                                                                                                                                                                           |
| Collection   | `infra-rivm.business-clock`                                                                                                                                                                                                                                         |

Handler body:

```java
@Override public boolean handleValidatedMessage(BusinessClockEvent message) {
  log.info("Handling validated business clock event");
  try {
    Optional<BusinessClockService> svc = RISEApplicationContext.getComponent(BusinessClockService.class);
    svc.get().setBusinessClock(message);
    return true;
  } catch (RuntimeException e) {
    log.error("Failed to process validated business clock event " + e);
    return false;
  }
}
```

> The `RISEApplicationContext.getComponent(...)` pattern (instead of `@Autowired`) is used in
> **every** handler; `infra-business-clock-etl/README.md` explains it as a workaround for autowiring
> problems inside the `rise-api-utils` listener context, and advises removing DevTools
> (`spring.devtools.restart.enabled=false` is set in every ETL).

Service:

```java
public void setBusinessClock(BusinessClockEvent e) {
  try {
    BusinessClockData d = e.getBusinessClockData();
    BusinessClock bc = riseToInfraMapper.map(d);
    businessClockRepository.deleteAll();   // ← collection is truncated first
    businessClockRepository.save(bc);
  } catch (Exception ex) { log.error("Failed to convert and save message " + ex); }
}
```

**The `business-clock` collection therefore holds at most one document.**
The `deleteAll()`+`save()` pair is **not transactional** — a crash between them leaves the
collection empty and `GET /business-clock` returns HTTP 404.

Mapper (`RiseToInfraMapper`):

| Target             | Source                                            | Transformation                                               |
| ------------------ | ------------------------------------------------- | ------------------------------------------------------------ |
| `businessTime`     | `businessClockRISE.getBusinessTime()` (`Instant`) | `SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'")`, TZ = UTC     |
| `serverTime`       | `businessClockRISE.getSystemTime()` (`Instant`)   | `SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")`, TZ = UTC |
| `businessTimeZone` | `businessClockRISE.getBusinessTimeZone()`         | verbatim                                                     |
| `mode`             | `businessClockRISE.getMode().getValue()`          | `BusinessClock.ModeEnum.fromValue(...)`                      |

> Note the field-name change: RISE `systemTime` → RIVM **`serverTime`**.
> `SimpleDateFormat` instances are `static` and **not thread-safe** — a latent concurrency hazard
> if the listener container ever uses more than one consumer thread.

---

## 5.4 `infra-micro-etl`

| Aspect       | Detail                                                                                                                 |
| ------------ | ---------------------------------------------------------------------------------------------------------------------- |
| Entry point  | `InfraMicroEtlApplication`                                                                                             |
| Handler      | `InfraMicroEventHandler implements …eventhandling.infra.microscopicregion.InfraMicroscopicRegionEventHandler`          |
| Queue        | `rise.api.utils.event-handling.infra.microscopic-region.queue-name=de.hacon.tps.rise.client.inframicro.event.consumer` |
| Service name | `de.hacon.tps.rise.infra.micro`                                                                                        |
| Service      | `InfraMicroService.setInfraMicro(InfraMicroscopicRegionEvent)`                                                         |
| Mapper       | `RiseToInfraMapper.map(InfraMicroscopicRegionData) : List<TrackCoordinates>`                                           |
| Repository   | `TrackCoordinatesRepository.saveAll(...)`                                                                              |
| Collection   | `infra-rivm.track-coordinates`                                                                                         |

Mapper algorithm:

```java
locationLayer      = region.getLocationLayer();
baseGraph          = region.getBaseGraph();
baseGraphNodesById = indexBaseGraphNodes(baseGraph);   // Map<node.baseSubEntityData.id, node>

for (location : locationLayer.getLocations())
  tracks = location.getLocationData().getTracks(); if (null||empty) continue;
  for (track : tracks)
    tc.id                  = location.baseSubEntityData.id + "_" + track.baseSubEntityData.id
    tc.nodeCoordinates     = toNodes(track.trackData.subGraph, baseGraphNodesById)
    tc.trackSubEntityData  = mapBaseSubEntityData(track.baseSubEntityData)
    tc.locationSubEntityData = mapBaseSubEntityData(location.baseSubEntityData)
```

`toNodes` iterates `subGraph.getNodeRefs()` (a `Set`!) and for each ref resolves
`nodeRef.getInfraMicroscopicNodeRef().getSubEntityID()` in the index; the node's
`nodeData.coordinates.graphical` `{x,y}` becomes a `NodeCoordinates`. Refs that cannot be resolved
(or nodes without coordinates) are silently dropped.

> **Ordering caveat:** because `nodeRefs` is a `Set`, the resulting `nodeCoordinates` array has **no
> guaranteed order**. Downstream, `TrainOperationUtil.resolveLocationCoordinates()` uses
> `nodeCoordinates.getFirst()`, and `OpenLayerLocationLabelUtility` uses only the bounding box, so
> the impact is limited to which node is treated as "the" platform anchor point.

`mapBaseSubEntityData` maps `id`, `name`, `description`, `shortName` (drops `businessRefs`).

`saveAll` is an **upsert by `_id`** — regions may be re-published freely; stale tracks are **never
deleted**.

---

## 5.5 `infra-basegraph-etl`

| Aspect       | Detail                                                                                        |
| ------------ | --------------------------------------------------------------------------------------------- |
| Entry point  | `InfraBaseGraphEtlApplication`                                                                |
| Handler      | `InfraBaseGraphEventHandler` — same interface as micro-etl, **different queue**               |
| Queue        | `…infra.microscopic-region.queue-name=de.hacon.tps.rise.client.infrabasegraph.event.consumer` |
| Service name | `de.hacon.tps.rise.infra.basegraph`                                                           |
| Service      | `InfraBaseGraphService.processBaseGraphEvent(event)`                                          |
| Mapper       | `BaseGraphMapper.map(InfraMicroscopicRegionEvent) : BaseGraph`                                |
| Repository   | `BaseGraphRepository.save(...)` (single save, not `saveAll`)                                  |
| Collection   | `infra-rivm.basegraph`                                                                        |

`BaseGraphMapper` validation chain:

```
isValidEvent(event)  = event != null
                    && event.getBaseEntityEvent() != null
                    && event.getInfraMicroscopicRegionData() != null
                    && event.getInfraMicroscopicRegionData().getBaseGraph() != null
isValidEntityId(id)  = id != null && !id.isEmpty()
```

Returns `null` (→ "skipping save") at any failure; every exception is caught and logged.

Mapping detail:

| Target                                               | Source                                            | Transformation                                                                     |
| ---------------------------------------------------- | ------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `BaseGraph.id`                                       | `event.baseEntityEvent.entityID`                  | verbatim                                                                           |
| `node.baseSubEntityData`                             | `source.baseSubEntityData`                        | `mapBaseSubEntityData`                                                             |
| `node.nodeData.coordinates.graphical.{x,y}`          | `source.nodeData.coordinates.graphical.{x,y}`     | verbatim                                                                           |
| `node.nodeData.infraNodeAddress.kmRegion`            | `source.nodeData.infraAddress.kmRegion`           | **field renamed `infraAddress` → `infraNodeAddress`**                              |
| `node.nodeData.infraNodeAddress.kmValue`             | `source.nodeData.infraAddress.kmValueMillimeters` | **field renamed**, `Long` → target type                                            |
| `edge.edgeData.infraNodeRefs`                        | `source.edgeData.infraNodeRefs` (List)            | → `LinkedHashSet<InfraMicroscopicNodeRef>` (**List → Set**)                        |
| `edge.edgeData.edgeLengthMillimeters`                | same                                              | `Long.intValue()` — **narrowing**                                                  |
| `edge.edgeData.direction`                            | `source.edgeData.direction`                       | `DirectionEnum.fromValue(source.getValue())`                                       |
| `nodeRef.infraMicroscopicNodeRef.{type,subEntityID}` | same                                              | `infraMicroscopicRegionRef` is **explicitly dropped** ("not in the target schema") |

Nodes/edges with a missing `baseSubEntityData` or data object are skipped (`log.debug`).

> **Both `infra-micro-etl` and `infra-basegraph-etl` consume the _same_ event type from _different_
> queues.** The broker therefore needs two bindings of `event.infra.microscopic_region` — one per
> queue — so each service gets its own copy.

---

## 5.6 `infra-trainoperation-etl`

The largest ETL. **Entry point:**

```java
@SpringBootApplication
@EnableScheduling
@ComponentScan({ "de.hacon.tps.rise.infra.trainoperation.etl",
                 "de.hacon.tps.rise.api.utils",
                 "de.hacon.tps.rise.infra.utils",
                 "de.hacon.tps.rise.infra.common.repository" })
@ConfigurationPropertiesScan({ "de.hacon.tps.rise.api.utils", "de.hacon.tps.rise.infra.utils" })
public class InfraTrainOperationEtlApplication
```

### Registered handlers (`META-INF/spring.factories`)

```
…eventhandling.trainoperation.trainoperation.TrainOperationEventHandler
      = …etl.eventhandling.InfraTrainOperationMovementEventHandler
…eventhandling.trainoperation.forecast.TrainOperationForecastEventHandler
      = …etl.eventhandling.InfraTrainOperationMovementForecastEventHandler
…eventhandling.infra.microscopicregion.InfraMicroscopicRegionEventHandler
      = …etl.eventhandling.InfraMicroscopicRegionEventHandler
…eventhandling.infra.operationalperiod.InfraOperationalPeriodEventHandler
      = …etl.eventhandling.InfraOperationalPeriodEventHandler
```

### Queues

```properties
rise.api.utils.event-handling.train-operation.queue-name           = de.hacon.tps.rise.client.trainoperation.event.consumer
rise.api.utils.event-handling.train-operation.forecast.queue-name  = de.hacon.tps.rise.client.trainoperation.forecast.event.consumer
rise.api.utils.event-handling.infra.operational-period.queue-name  = de.hacon.tps.rise.client.infra.operational-period.event.consumer
rise.api.utils.event-handling.infra.microscopic-region.queue-name  = de.hacon.tps.rise.client.infra.microscopic-region.event.consumer
rise.api.utils.service.name                                        = de.hacon.tps.rise.infra.trainoperation
```

### Configuration & scheduling

```properties
app.db.collection.map-config        = infra-rivm.map-config
app.db.collection.train-position    = infra-rivm.train-position
app.db.collection.track-coordinates = infra-rivm.track-coordinates
app.db.collection.data-tile         = infra-rivm.data-tile
scheduler.trackcoordinates.load.interval = ${TRACKCOORDINATES_LOAD_INTERVAL:3600000}  # 1 h
scheduler.mapconfig.load.interval        = ${MAPCONFIG_LOAD_INTERVAL:60000}           # 1 min
```

### Classes

| Package              | Class                                             | Role                                                                                                                                                                                                                                           |
| -------------------- | ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `…etl`               | `InfraTrainOperationEtlApplication`               | boot                                                                                                                                                                                                                                           |
| `…etl.config`        | `IndexConfig`                                     | `@PostConstruct initIndexes()` — creates three indexes on the train-position collection                                                                                                                                                        |
| `…etl.dto`           | `ActivitiesDTO`                                   | `{ List<TrainOperationActivity> baselineActivities; currentActivities; }` — **not referenced by main code**                                                                                                                                    |
| `…etl.dto`           | `ActivityContext`                                 | `{ activityId, activityType, timeValue: Instant, positionReference, trackId, hasActualTime, infraAddress }` with nested `PositionReference` marker + `LocationReference{locationId}` + `KmReference{kmRegion, kmValueMillimeters, complement}` |
| `…etl.eventhandling` | `InfraTrainOperationMovementEventHandler`         | `TrainOperationEvent` → `processTrainOperationMovementEvent`                                                                                                                                                                                   |
| `…etl.eventhandling` | `InfraTrainOperationMovementForecastEventHandler` | `TrainOperationForecastEvent` → `processTrainOperationMovementForecastEvent`                                                                                                                                                                   |
| `…etl.eventhandling` | `InfraMicroscopicRegionEventHandler`              | → `MicroscopicInfraService.addMicroscopicRegion(event)`                                                                                                                                                                                        |
| `…etl.eventhandling` | `InfraOperationalPeriodEventHandler`              | → `MicroscopicInfraService.init(event)`                                                                                                                                                                                                        |
| `…etl.service`       | `InfraTrainOperationService`                      | 583 lines — orchestration                                                                                                                                                                                                                      |
| `…etl.service`       | `DataTileService`                                 | tile ID computation + versioning                                                                                                                                                                                                               |
| `…etl.service`       | `MapConfigService`                                | cached OCTOLINEAR map config                                                                                                                                                                                                                   |
| `…etl.service`       | `MicroscopicInfraService`                         | wraps `de.hacon.tps.rise.infra.utils.MicroscopicInfra`                                                                                                                                                                                         |
| `…etl.service`       | `TrackCoordinatesService`                         | cached `List<TrackCoordinates>`                                                                                                                                                                                                                |
| `…etl.util`          | `RiseToInfraMapper`                               | `TrainOperationData` → `List<TrainPosition>`                                                                                                                                                                                                   |
| `…etl.util`          | `RiseToInfraForecastMapper`                       | `TrainOperationForecastData` → `List<TrainPosition>`                                                                                                                                                                                           |
| `…etl.util`          | `TrainOperationUtil`                              | builds a single `TrainPosition` (coords, times, tiles)                                                                                                                                                                                         |
| `…etl.util`          | `LocationAttributes`                              | `{type, previous, next, origin, destination}` — **not referenced by main code**                                                                                                                                                                |

### `IndexConfig`

```java
@PostConstruct public void initIndexes() {
  mongoTemplate.indexOps(trainPositionCollection).createIndex(new Index().on("trainServiceId", ASC));
  mongoTemplate.indexOps(trainPositionCollection).createIndex(new Index().on("dataTileIds",   ASC));
  mongoTemplate.indexOps(trainPositionCollection).createIndex(
      new Index().on("dataTileIds", ASC).on("_id", ASC).on("trainServiceId", ASC));
}
```

> Note the third index exactly matches the query executed by `infra-query-svc`
> (`{dataTileIds: {$in: […]}}` sorted by `id, trainServiceId`) — but the index is created by the
> **ETL**, not by the query service. If only the query service runs, the index is absent.

### `MapConfigService`

```java
private final AtomicReference<MapConfig> cachedConfig = new AtomicReference<>();
public MapConfig getMapConfig() { return cachedConfig.get(); }
public void refresh() {
  cachedConfig.set(mapConfigRepository.findAll().stream()
      .filter(c -> MapConfig.MapTypeEnum.OCTOLINEAR.equals(c.getMapType()))
      .findFirst().orElse(null));
  log.info("ConfigMap present: {}", config != null);
}
@PostConstruct @Scheduled(fixedRateString = "${scheduler.mapconfig.load.interval}")
private void init() { refresh(); }
```

Only **`OCTOLINEAR`** map configurations are considered.

### `TrackCoordinatesService`

```java
private final AtomicReference<List<TrackCoordinates>> cachedCoordinates = new AtomicReference<>();
@PostConstruct @Scheduled(fixedRateString = "${scheduler.trackcoordinates.load.interval}")
public void init() { cachedCoordinates.set(coordinatesRepository.findAll());
                     log.info("TrackCoordinates loaded: {}", coordinates.size()); }
public List<TrackCoordinates> getCachedCoordinates() { return cachedCoordinates.get(); }
```

**The full track-coordinates collection is held in memory** and refreshed hourly.

### `MicroscopicInfraService`

```java
private MicroscopicInfra microscopicInfra = new MicroscopicInfra();   // from rise-infra-utils
public synchronized void init(InfraOperationalPeriodEvent e)          { microscopicInfra.initialize(e); }
public synchronized void addMicroscopicRegion(InfraMicroscopicRegionEvent e)
                                                                      { microscopicInfra.addMicroscopicRegionData(e); }
public Set<Types.EdgeWithOffset> findEdges(InfraAddress a) {
  if (a == null || a.getKmValueMillimeters() == null) return Set.of();
  var r = microscopicInfra.findEdges(a); return r != null ? r : Set.of();
}
```

**In-memory, non-persistent.** Restarting the ETL loses the graph until the operational-period and
region events are re-delivered.

### `DataTileService`

```java
private static final DateTimeFormatter TILE_TIME_FORMATTER =
    DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm").withZone(ZoneOffset.UTC);

isMapConfigAvailable() = mapConfig != null && layers non-empty
                      && exists layer with layerDataType "train"
                      && that layer.tileSize != null

createDataTiles(List<String> ids) → ids.map(id -> new DataTile(id, UUID.randomUUID().toString()))

createTileIds(TrainPosition tp):
  tileSize = train layer tileSize          (else empty list + warn)
  xSize, ySize, timeSpanSecs
  minX = tp.coordinates.x ; minY = tp.coordinates.y     (null → warn + empty)
  fromTime/toTime parsed with ISO_OFFSET_DATE_TIME      (parse failure → warn + empty)

  tileMinX = floor(minX / xSize) * xSize        tileMaxX = ceil(minX / xSize) * xSize
  tileMinY = floor(minY / ySize) * ySize        tileMaxY = ceil(minY / ySize) * ySize
  tilesX   = ceil((tileMaxX - tileMinX)/xSize)  tilesY   = ceil((tileMaxY - tileMinY)/ySize)

  tileMinTime = floor(fromEpochSec / timeSpanSecs) * timeSpanSecs
  tileMaxTime = ceil (toEpochSec   / timeSpanSecs) * timeSpanSecs
  timeSlots   = ceil((tileMaxTime - tileMinTime)/timeSpanSecs)

  totalTiles = tilesX * tilesY * timeSlots
  for i in [0, totalTiles):
     tt = i / (tilesX*tilesY); rem = i % (tilesX*tilesY); ty = rem / tilesX; tx = rem % tilesX
     tileId = `${tileMinX + tx*xSize}_${tileMinY + ty*ySize}_${TILE_TIME_FORMATTER(tileMinTime + tt*timeSpanSecs)}`
```

> **Important behavioural note:** the spatial extent is computed from a **single point**
> (`minX == maxX`). When the coordinate lands exactly on a grid boundary,
> `floor == ceil` ⇒ `tilesX == 0` ⇒ `totalTiles == 0` ⇒ **no tile IDs and therefore no visibility**
> for that position. Off-boundary coordinates give `tilesX == tilesY == 1`. Recorded as observed
> behaviour only.

### `InfraTrainOperationService` — full control flow

Public API:

| Method                                                                    | Trigger                                                                                                                                                         |
| ------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `processTrainOperationEvent(TrainOperationEvent)`                         | switch on `triggerType`: `ENTITY_CREATED`/`ENTITY_UPDATED` → `processTrainOperationMovementEvent`; else warn. **Not invoked by any handler** (dead entry point) |
| `processTrainOperationMovementEvent(TrainOperationEvent)`                 | from `InfraTrainOperationMovementEventHandler`                                                                                                                  |
| `processTrainOperationMovementForecastEvent(TrainOperationForecastEvent)` | from `InfraTrainOperationMovementForecastEventHandler`                                                                                                          |
| `hasEntityChangedForEvent(updated, existing)`                             | public helper (compares `fromTime`, `toTime`, `runningType`, `coordinates.x/y`); **not called from the main flow**                                              |

`processEventWithErrorHandling(trainServiceId, triggerType, name, Runnable)` wraps both public
processors: logs, switches on `ENTITY_CREATED`/`ENTITY_UPDATED`, catches every `Exception`.

**ACTUAL/planned path — `processMovementEventForCreateOrUpdate(TrainOperationEvent)`:**

```
trainServiceId    = event.baseEntityEvent.entityID
existingPositions = trainPositionRepository.findByTrainServiceId(trainServiceId)
newPositions      = riseToInfraMapper.map(event.trainOperationData, trainServiceId,
                                          event.baseEntityData, existingPositions)
if (newPositions.isEmpty()) → warn + return
positionsToSave   = filterMovementPositions(newPositions, existingPositions, trainServiceId)
if (empty) → info + return
savePositionsAndTiles(positionsToSave)
```

`filterMovementPositions` rules:

| Position kind                                          | Rule                                                                                                                                    |
| ------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------- |
| `activityType == MOVEMENT`                             | save **only if `runningType == ACTUAL`** (`shouldSaveMovementActivity`), else count as `skippedForecastMovements`                       |
| location activity (`DEPARTURE`/`ARRIVAL`/`RUNTHROUGH`) | save if **no existing row with the same `id`** OR the new row is `ACTUAL` (`shouldSaveLocationActivity`), else `skippedForecastUpdates` |

**FORECAST path — `processMovementForecastEventForCreateOrUpdate(TrainOperationForecastEvent)`:**

```
trainServiceId = event.trainOperationForecastData.trainOperationRef   // ← NOT the forecast entity ID
existingPositions = repo.findByTrainServiceId(trainServiceId)
newPositions      = riseToInfraForecastMapper.map(forecastData, trainServiceId, baseEntityData, existingPositions)
if (empty) → warn + return

// 1. delete every existing FORECAST row for this train
existingForecasts = existingPositions.filter(runningType == FORECAST)
if (!empty) {
   repo.deleteAllById(ids)
   dataTileService.saveAll(dataTileService.createDataTiles(distinct dataTileIds))  // version bump
}

// 2. never let a forecast overwrite the actual frontier
existingActuals = existingPositions.filter(runningType == ACTUAL)
actualFrontier  = max(existingActuals.fromTime)          // lexicographic on the ISO string
positionsToSave = actualFrontier == null ? newPositions
                  : newPositions.filter(p -> p.fromTime.compareTo(actualFrontier) >= 0)
if (empty) → warn + return
savePositionsAndTiles(positionsToSave)

// 3. close the gap between the last ACTUAL and the first FORECAST
extendLastActualToForecast(trainServiceId, positionsToSave)
```

`extendLastActualToForecast`:

```
allPositions   = repo.findByTrainServiceId(trainServiceId)
lastActual     = max by fromTime among ACTUAL rows           (none → return)
firstForecast  = min fromTime among FORECAST rows with fromTime >= lastActual.fromTime
if (firstForecast < lastActual.toTime) { lastActual.toTime = firstForecast;
                                         savePositionsAndTiles([lastActual]); }
```

`savePositionsAndTiles(positions)`:

```
dataTileIds = flatten(positions.dataTileIds)               // duplicates retained
dataTiles   = dataTileService.createDataTiles(dataTileIds) // new random UUID per entry
dataTileService.saveAll(dataTiles)                         // upsert by _id
trainPositionRepository.saveAll(positions)
```

> **Ordering note:** data tiles are versioned **before** the positions are written. A client polling
> in that window can observe a new tile version whose position data has not landed yet; the next
> poll (2 s later by default) corrects it.

Private helpers that exist but are **never called** in the current flow:
`shouldSaveForecastMovement`, `shouldSaveForecastLocation`, `countExistingLocationActivities`,
`logSkippedMovement`, `logMissingLocation`, and the private static class `FilteredPositions`.

### `RiseToInfraMapper` (ACTUAL / planned)

```
map(trainOperationData, trainServiceId, baseEntityData, existingPositions):
  if (!trainOperationUtil.isMapConfigAvailable())              → warn + []
  if (!isValidTrainOperationData(...))                          → warn + []
        (data != null && currentPlan != null && currentPlan.planData != null)
  activities = trainOperationData.currentPlan.planData.activities
  if (null || empty)                                            → warn + []
  activitySequence = extractAndFilterActivitySequence(activities)
  if (empty)                                                    → warn + []
  return createTrainPositions(activitySequence, trainServiceId, existingPositions)
```

`extractActivityContext(activity, isFirstLocationActivity)` — the rule engine:

| Step | Rule                                                                                                                                                                                                                      |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1    | `isValidActivity` = `activity != null && activityData != null && baseActivityData != null`                                                                                                                                |
| 2    | `isCancelledActivity` — skip when `baseOperationElementData.status.value == "CANCELLED"` (logs a **warn**)                                                                                                                |
| 3    | `determineActivityType` — `activityData.departure != null → "DEPARTURE"`; `arrival → "ARRIVAL"`; `movement → "MOVEMENT"`; `runThrough → "RUNTHROUGH"`; else `null` → skip                                                 |
| 4    | `shouldSkipIntermediateDeparture` — skip `"DEPARTURE"` unless it is the first location activity                                                                                                                           |
| 5    | `hasActualTime` = `baseActivityData.actualEndTime != null && actualPlaces != null && !actualPlaces.isEmpty()`                                                                                                             |
| 6    | `shouldSkipMovementWithoutActual` — skip `"MOVEMENT"` when `!hasActualTime`                                                                                                                                               |
| 7    | `extractTimeAndPlaces` — prefer `{actualEndTime, actualPlaces}`, else `{plannedTime.planned, plannedPlaces}`, else `null`                                                                                                 |
| 8    | `extractPositionReference(places)` — first place with `infraEntityRef.entityID` → `LocationReference`; else first place with `infraAddress` → `KmReference{kmRegion, kmValueMillimeters, complement}`; else `null` → skip |
| 9    | `determineOutputActivityType` — `MOVEMENT`→`MOVEMENT`; `RUNTHROUGH`→`RUNTHROUGH`; otherwise first-location→`DEPARTURE`, all later→`ARRIVAL`                                                                               |
| 10   | `extractTrackId(places)` — first place whose `infraSubEntityRef.type == "tracks"` → its `subEntityID`                                                                                                                     |
| 11   | `activityId = activity.baseSubEntityData.id` (null → skip)                                                                                                                                                                |
| 12   | `infraAddress = extractInfraAddressFromActualPlaces(activity)` — first `actualPlaces[*].infraAddress`, else first `plannedPlaces[*].infraAddress`, else `null`                                                            |

`filterMovementsBetweenStations(all)` is now a **pass-through** (`log.warn("Processing activities - total: {}")` then `return allActivities`) — the historical station-pair filtering described in
`docs/TrainOperationMovementFlow.md` has been removed because the activity type is now derived from
the position-reference kind.

`createTrainPositions`:

```
originId      = first activity where type ∈ {ARRIVAL, DEPARTURE} → LocationReference.locationId
destinationId = last  activity where type ∈ {ARRIVAL, DEPARTURE} → LocationReference.locationId
for i in [0, n):
   current = seq[i]; next = i < n-1 ? seq[i+1] : null
   tp = trainOperationUtil.createTrainPosition(new TrainPositionParams(current, next,
                                                trainServiceId, originId, destinationId))
   if (tp != null) add
```

Dead private helpers in this class: `isDeparture`, `isArrival`.

### `RiseToInfraForecastMapper` (FORECAST)

Same structure with these differences:

| Aspect                               | Forecast mapper                                                                                                                                         |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Source list                          | `trainOperationForecastData.getForecastedActivities()`                                                                                                  |
| Validity                             | `data != null && forecastedActivities != null && !isEmpty()`                                                                                            |
| Time/places                          | `extractForecastedTimeAndPlaces` → `{ baseActivityData.forecastedEndTime, baseActivityData.forecastedPlaces }`; `null` when `forecastedEndTime == null` |
| `hasActualTime`                      | hard-coded **`false`**                                                                                                                                  |
| `infraAddress`                       | `extractInfraAddressFromForecastedPlaces(baseActivityData)` — first `forecastedPlaces[*].infraAddress`                                                  |
| No `shouldSkipMovementWithoutActual` | movements are always kept                                                                                                                               |
| Creation call                        | `trainOperationUtil.createTrainPositionForForecast(params)`                                                                                             |
| `extractDestinationId`               | `stream().filter(isArrivalOrDeparture).reduce((a,b)=>b)` (functional last-element)                                                                      |
| `isCancelledActivity`                | same CANCELLED skip                                                                                                                                     |
| `shouldSkipIntermediateDeparture`    | logs at **warn** instead of debug                                                                                                                       |

### `TrainOperationUtil`

```java
private static final SimpleDateFormat ISO_FORMATTER_WITHOUT_MILLISECONDS =
        createFormatter("yyyy-MM-dd'T'HH:mm:ss'Z'");   // TimeZone UTC, static → not thread-safe

public boolean isMapConfigAvailable() { return dataTileService.isMapConfigAvailable(); }

public TrainPosition createTrainPosition(TrainPositionParams p) {
   runningType = p.current.isHasActualTime() ? ACTUAL : FORECAST;
   return createTrainPositionWithRunningType(p, runningType);
}
public TrainPosition createTrainPositionForForecast(TrainPositionParams p) {
   return createTrainPositionWithRunningType(p, FORECAST);
}

private TrainPosition createTrainPositionWithRunningType(p, runningType) {
   tp = createBaseTrainPosition(p);   if (tp == null) return null;
   tp.setRunningType(runningType);
   setTimeWindows(tp, p.current, p.next);
   tp.setDataTileIds(dataTileService.createTileIds(tp));
   return tp;
}

private TrainPosition createBaseTrainPosition(p) {
   activityId = p.current.activityId
   tp.id             = p.trainServiceId + "-" + activityId
   tp.trainServiceId = p.trainServiceId
   tp.activityId     = activityId
   tp.activityType   = TrainPosition.ActivityTypeEnum.fromValue(p.current.activityType)
   coordinates       = resolveCoordinates(p.current, activityId)
   if (coordinates == null) { warn; return null; }          // ← position is DROPPED
   tp.coordinates    = new rivm.InfraGraphicalCoordinates(x, y)
   tp.origin         = p.originId
   tp.destination    = p.destinationId
}

private void setTimeWindows(tp, current, next) {
   tp.fromTime = format(current.timeValue)
   tp.toTime   = next != null ? format(next.timeValue)
                              : format(current.timeValue.plus(Duration.ofMinutes(10)))
}
```

`resolveCoordinates(context, activityId)`:

```
if (positionRef instanceof LocationReference) {
    if (context.infraAddress != null) {
       c = resolveKmCoordinates(context, activityId);         // TRY km-based FIRST
       if (c != null) return c;
       warn("InfraAddress-based resolution failed …, falling back to track coordinates");
    }
    return resolveLocationCoordinates(locationId, context.trackId, activityId);
}
if (positionRef instanceof KmReference) return resolveKmCoordinates(context, activityId);
warn("Unknown position reference type"); return null;
```

`resolveLocationCoordinates(locationId, trackId, activityId)`:

```
trackCoordinateId = locationId + "_" + trackId
list  = trackCoordinatesService.getCachedCoordinates()
match = list.stream().filter(tc -> tc.getId().equals(trackCoordinateId)).findFirst().orElse(null)
if (match == null)                        → warn "Track coordinates not found for key" ; null
if (match.nodeCoordinates empty/null)     → warn "No nodes found for track" ; null
return { x: nodeCoordinates.getFirst().getX(), y: …getY() }
```

`resolveKmCoordinates(context, activityId)`:

```
infraAddress = context.infraAddress ; if (null) → warn ; null
edges = microscopicInfraService.findEdges(infraAddress)
if (!edges.isEmpty()) {
   if (edges.size() > 1) warn("Multiple edges found … Using first edge.")
   e = edges.iterator().next()
   if (e.coordinates() != null) { log.info("Found coordinates …"); return e.coordinates(); }
}
warn("No edges found for infraAddress {kmRegion, km, complement} … cannot resolve coordinates")
return null
```

> Because `findEdges` returns a `Set`, "first edge" is **non-deterministic** when several edges
> match. The code logs a warning when that happens.

---

## 5.7 `infra-restriction-etl`

**Entry point:**

```java
@SpringBootApplication
@ComponentScan({ "de.hacon.tps.rise.infra.restriction", "de.hacon.tps.rise.api.utils",
                 "de.hacon.tps.rise.infra.utils", "de.hacon.tps.rise.infra.common.repository" })
@ConfigurationPropertiesScan({ "de.hacon.tps.rise.api.utils", "de.hacon.tps.rise.infra.utils" })
public class RestrictionEtlApplication
```

**Handlers (`spring.factories`):**

```
…eventhandling.restriction.restriction.RestrictionEventHandler
      = de.hacon.tps.rise.infra.restriction.eventhandling.RestrictionEventHandler
…eventhandling.infra.microscopicregion.InfraMicroscopicRegionEventHandler
      = …restriction.eventhandling.InfraMicroscopicRegionEventHandler
…eventhandling.infra.operationalperiod.InfraOperationalPeriodEventHandler
      = …restriction.eventhandling.InfraOperationalPeriodEventHandler
```

**Queues:**

```properties
rise.api.utils.event-handling.restriction.queue-name              = de.hacon.tps.rise.client.restriction.event.consumer
rise.api.utils.event-handling.infra.operational-period.queue-name = de.hacon.tps.rise.client.infra.operational-period.event.consumer
rise.api.utils.event-handling.infra.microscopic-region.queue-name = de.hacon.tps.rise.client.infra.microscopic-region.event.consumer
rise.api.utils.service.name                                       = de.hacon.tps.rise.infra.restriction
```

> ⚠️ **The `infra.operational-period` and `infra.microscopic-region` queue names are IDENTICAL to
> those configured in `infra-trainoperation-etl`.** With AMQP semantics both services become
> **competing consumers on the same queues**, so each infra event is delivered to only **one** of
> the two services. Since each maintains its own in-memory `MicroscopicInfra`, this means one of
> them will hold an incomplete graph. Recorded strictly as an observation.

**`RestrictionEventHandler`:**

```java
if (message.getBaseEntityEvent() == null || entityID == null || entityID.isBlank()) {
    log.warn("Skipping restriction event - entityId is null or blank");
    return true;                       // ACK without reprocessing
}
Optional<RestrictionService> svc = RISEApplicationContext.getComponent(RestrictionService.class);
if (svc.isEmpty()) { log.error("RestrictionService not found in application context"); return false; }
svc.get().processRestrictionEvent(message);
log.info("Successfully processed restriction event for Restriction ID: {}", entityId);
return true;
// catch (Exception e) → log.error(…) ; return false
```

**`RestrictionService`:**

```java
switch (event.baseEntityEvent.triggerType.value) {
  case "ENTITY_CREATED": case "ENTITY_UPDATED": processEntityForCreateOrUpdate(event); break;
  case "ENTITY_DELETED":                        processEntityForDelete(event);        break;
  default: log.warn("Unhandled trigger type: {}", triggerType);
}
// catch → log.error + RETHROW (this service rethrows; the handler converts it to `false`)
```

- create/update → `restrictionMapper.mapEventToRestriction(event)` → `restrictionRepository.save(...)`
  (full replace of `restrictionData`).
- delete → `restrictionRepository.deleteById(entityId)`.

**`RestrictionMapper`** (448 lines, field-by-field, null-safe at every level):

| Domain target                                           | DTO source                              | Transformation                                                |
| ------------------------------------------------------- | --------------------------------------- | ------------------------------------------------------------- |
| `Restriction.id`                                        | `baseEntityEvent.entityID`              | verbatim                                                      |
| `.name` / `.shortName` / `.description`                 | `baseEntityData.*`                      | verbatim                                                      |
| `.lastModified`                                         | `baseEntityData.lastModified`           | **`String.valueOf(...)`** (Instant → String)                  |
| `restrictionData.state`                                 | `dto.state`                             | `RestrictionData.StateEnum.valueOf(state.name())`             |
| `restrictionData.effectiveTimePeriod.startTime/endTime` | `dto.effectiveTimePeriod.*` (`Instant`) | `.toString()`                                                 |
| `restrictionData.group.id`                              | `dto.group.id`                          | verbatim                                                      |
| `restrictionData.impacts[]`                             | `dto.impacts[]`                         | per-impact mapping (below)                                    |
| `restrictionData.edgePaths[]`                           | **`dto.segments[]`**                    | `microscopicInfraService.findEdgePaths(segments)` then mapped |
| `restrictionData.meta.ui.icon/style`                    | `dto.meta.ui.icon/style`                | `{type, payload}` copy (both mapped by `mapUiIcon`)           |

Impact mapping:

```
impact.trainFilter.trainOperationFilter   ← PropertyFilter { operator (enum valueOf), conditions[] }
impact.trainFilter.trainCompositionFilter ← PropertyFilter { operator (enum valueOf), conditions[] }
condition = { path, operator (PropertyFilterMatchOperator.valueOf),
              valueString, valueInteger, valueBoolean,
              valueDate     : dto.valueDate?.toString(),
              valueDateTime : dto.valueDateTime?.toString() }
impact.blocking.dummyToNotHaveEmptyObject ← verbatim
impact.speedReduction.{absoluteMaxSpeedMillimetersPerHour,
                       relativeSpeedReductionMillimetersPerHour} ← verbatim
impact.adhesion.adhesionLevel ← RestrictionImpactAdhesion.AdhesionLevelEnum.valueOf(dto.name())
```

Edge-path mapping:

```
mapEdgePaths(segments):
   if (null || empty) → []
   infraEdgePaths = microscopicInfraService.findEdgePaths(segments)   // rise-infra-utils
   if (null || empty) → []
   → EdgePath { pathEdges: EdgeWithOffsets[], pathCoordinates: InfraGraphicalCoordinates[] }

mapInfraEdgeWithOffsets(infra):
   edgeRef         = { infraMicroscopicRegionRef {type, entityID},
                       infraMicroscopicEdgeRef   {type, subEntityID} }
   startPercentage = BigDecimal.valueOf(infra.startPercentage()).setScale(2, HALF_UP)
   startPercentage = new BigDecimal(startPercentage.toString())     // ← redundant re-assignment
   endPercentage   = BigDecimal.valueOf(infra.endPercentage()).setScale(2, HALF_UP)
```

> `RestrictionMapper` translates **`segments` → `edgePaths`**: the event carries km-based
> infrastructure segments, and the geometric expansion into concrete edges + graphical coordinates
> is done at ingest time so the frontend only has to draw poly-lines.

---

## 5.8 Backend flow patterns

### Read path (synchronous)

```
HTTP Request
  → @RestController (bean-validated params)
      → @Service (pagination + sort + domain rules)
          → pure Repository interface   (de.hacon.tps.rise.infra.common.repository)
              → Mongo*RepositoryCustomImpl   (@Component adapter)
                  → Mongo*Repository (Spring Data)  /  MongoTemplate aggregation
                      → MongoDB collection
          ← Page<DomainModel> / List<DomainModel>
      ← APIPaginatedResponse<T>{data, meta} | APIResponse<T>{data}
  ← ResponseEntity → Jackson → JSON (NON_NULL)
```

### Write path (asynchronous, no HTTP)

```
RabbitMQ  rise.events  (topic)
  → routing key → queue (configured per ETL)
      → rise-api-utils listener + signature validation
          → <X>EventHandler.handleValidatedMessage(<X>Event)   [spring.factories]
              → RISEApplicationContext.getComponent(<X>Service)
                  → <X>Service.processX(event)
                      → <X>Mapper.map(dto)  [+ MicroscopicInfraService / TrackCoordinatesService
                                              / DataTileService for coordinates & tiles]
                      → Repository.save / saveAll / deleteById / deleteAllById
                          → MongoDB
              ← boolean (true = ACK, false = NACK — retry policy owned by rise-api-utils)
```

### "Controller → Service → RabbitMQ → Consumer → Another Service"

**This pattern does not exist in this repository.** No component publishes to RabbitMQ. The only
inter-service coupling is **through MongoDB collections** (`infra-trainoperation-etl` reads
`track-coordinates` written by `infra-micro-etl`, and `map-config` written by an unknown external
process).

> **`infra-rivm.map-config` has no writer in this repository.** `MapConfigRepository` exposes only
> `findAll()`. The collection must be seeded externally (the E2E harness does exactly that —
> `module-tests/playwright/data/eventBasedTesting/dbCollections/infra-rivm.map-config.json` +
> `config/db.config.js` → `collections.mapConfig`). Marked **NOT FOUND / NOT DETERMINED** for
> production provisioning.

---

# 6 — ALL APIs / ENDPOINTS

**Base:** `server.servlet.context-path = /api/infra/query`; port `${SERVER_PORT:9101}`.
All controllers are `@Validated`. No `@RequestMapping` prefix beyond the context path, except where
noted. No endpoint declares any header requirement, authentication or authorization.

Global response envelope types:

```java
class APIResponse<T>          { T data; }
class APIPaginatedResponse<T> { List<T> data; Meta meta; }
class Meta                    { MetaPage page; List<Map<String,String>> dataTileVersions; }
class MetaPage                { Integer pageNumber; Integer size;
                                Integer totalElements; Integer totalPages; }
```

---

## 6.1 `GET /api/infra/query/basegraph`

| Item                             | Value                                                                                                                                                                                   |
| -------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Controller**                   | `de.hacon.tps.rise.infra.query.controller.api.BaseGraphController`                                                                                                                      |
| **Method**                       | `getAllBaseGraphDetails(Integer pageNumber, Integer pageSize)`                                                                                                                          |
| **Mapping**                      | `@RequestMapping(method = GET, value = "/basegraph", produces = "application/json")`                                                                                                    |
| **Swagger**                      | `@Tag(name="basegraphs")`, `operationId = getAllBaseGraphDetails`                                                                                                                       |
| **Query params**                 | `pageNumber` (optional, default `0`) — `@Valid`; `pageSize` (optional, default `1000`) — `@Min(APIPaginatedResponse.MIN_PAGE_SIZE = 1) @Max(APIPaginatedResponse.MAX_PAGE_SIZE = 1000)` |
| **Path params / headers / body** | none                                                                                                                                                                                    |
| **Auth**                         | none                                                                                                                                                                                    |
| **Service**                      | `BaseGraphService.getAllBaseGraphs(pageNumber, pageSize)`                                                                                                                               |
| **Business logic**               | `PageRequest.of(pageNumber, pageSize)`; **no sort**                                                                                                                                     |
| **Repository / DB**              | `BaseGraphRepository.findAll(Pageable)` → `MongoBaseGraphRepositoryCustomImpl` → `MongoBaseGraphRepository.findAll` → `infra-rivm.basegraph`                                            |
| **RabbitMQ**                     | none                                                                                                                                                                                    |
| **Response DTO**                 | `APIPaginatedResponse<BaseGraph>`                                                                                                                                                       |
| **HTTP status**                  | `200`                                                                                                                                                                                   |
| **Errors**                       | `400` (constraint violation on `pageSize`), `500`                                                                                                                                       |
| **Frontend consumer**            | `BaseGraphApiService.getEdgeData()` → `EdgeDataEffects` → `edgeData` slice → `OpenLayerInfraUtility.extractNodes/extractEdges`                                                          |

Response shape:

```jsonc
{
  "data": [
    {
      "id": "REGION-A_0_0",
      "baseGraph": {
        "nodes": [
          {
            "baseSubEntityData": {
              "id": "n1",
              "name": "...",
              "shortName": "...",
              "description": "...",
            },
            "nodeData": {
              "infraNodeAddress": { "kmRegion": "A", "kmValue": 12345 },
              "coordinates": { "graphical": { "x": 125190, "y": -6035 } },
            },
          },
        ],
        "edges": [
          {
            "baseSubEntityData": { "id": "e1" },
            "edgeData": {
              "edgeLengthMillimeters": 1200,
              "direction": "FORWARD",
              "infraNodeRefs": [
                {
                  "infraMicroscopicNodeRef": {
                    "type": "baseGraph.nodes",
                    "subEntityID": "n1",
                  },
                },
                {
                  "infraMicroscopicNodeRef": {
                    "type": "baseGraph.nodes",
                    "subEntityID": "n2",
                  },
                },
              ],
            },
          },
        ],
      },
    },
  ],
  "meta": {
    "page": {
      "pageNumber": 0,
      "size": 1000,
      "totalElements": 1,
      "totalPages": 1,
    },
    "dataTileVersions": [],
  },
}
```

---

## 6.2 `GET /api/infra/query/business-clock`

| Item                   | Value                                                                                                        |
| ---------------------- | ------------------------------------------------------------------------------------------------------------ |
| **Controller**         | `BusinessClockController`                                                                                    |
| **Method**             | `getBusinessClock()`                                                                                         |
| **Mapping**            | `@RequestMapping(method = GET, value = "/business-clock", produces = "application/json")`                    |
| **Swagger**            | `@Tag(name="business-clock")`, `operationId = getBusinessClock`, documents `200` and `404`                   |
| **Params**             | none                                                                                                         |
| **Service**            | `BusinessClockService.getBusinessClock()`                                                                    |
| **Business logic**     | `findAll()`; empty → `throw new ResourceNotFoundException("No clock data found")`; otherwise `clocks.get(0)` |
| **Repository / DB**    | `BusinessClockRepository.findAll()` → `infra-rivm.business-clock`                                            |
| **Response DTO**       | `APIResponse<BusinessClock>`                                                                                 |
| **Status**             | `200`; `404` when the collection is empty                                                                    |
| **Error body (`404`)** | `{"errors":[{"code":"404","message":"No clock data found"}]}`                                                |
| **Frontend consumer**  | `BusinessClockApiService.getBusinessClockApiData()` (polled every 10 s by `BusinessClockEffects`)            |

```json
{
  "data": {
    "businessTime": "2026-08-31T09:15:00Z",
    "businessTimeZone": "Europe/London",
    "serverTime": "2026-08-31T09:15:00.123Z",
    "mode": "REALTIME"
  }
}
```

---

## 6.3 `GET /api/infra/query/configs`

| Item                  | Value                                                                                                             |
| --------------------- | ----------------------------------------------------------------------------------------------------------------- |
| **Controller**        | `ConfigController` — class-level `@RequestMapping("/configs")`                                                    |
| **Method**            | `getAllMapConfigs()` — `@GetMapping(produces = "application/json")`                                               |
| **Swagger**           | `@Tag(name="configs")`, `operationId = getAllMapConfigs`, documents `200`, `404`                                  |
| **Params**            | none                                                                                                              |
| **Service**           | `ConfigService.getAllMapConfigs()`                                                                                |
| **Business logic**    | `findAll()`; empty → `ResourceNotFoundException("No map configuration data found")`                               |
| **Repository / DB**   | `MapConfigRepository.findAll()` → `infra-rivm.map-config`                                                         |
| **Response DTO**      | `APIResponse<List<MapConfig>>`                                                                                    |
| **Status**            | `200`, `404`                                                                                                      |
| **Frontend consumer** | `MapConfigService.getMapConfig()` → `MapConfigStore` → `InfraContentComponent`, `MfeViewRestrictionListComponent` |

---

## 6.4 `GET /api/infra/query/location-track-coordinates`

| Item                  | Value                                                                                                                                   |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| **Controller**        | `LocationTrackCoordinatesController` — `@RequestMapping("/location-track-coordinates")`, `@AllArgsConstructor`                          |
| **Method**            | `getLocationTrackCoordinates(Integer pageNumber, Integer pageSize)` — `@GetMapping(produces="application/json")`                        |
| **Swagger**           | `@Tag(name="LocationTrackCoordinates")`, documents `200`, `400`                                                                         |
| **Query params**      | `pageNumber` default `0`, `@Min(0)`; `pageSize` default `100`, `@Min(1) @Max(1000)`                                                     |
| **Service**           | `LocationTrackCoordinatesService.getLocationTrackCoordinates(...)`                                                                      |
| **Business logic**    | `PageRequest.of(p, s, Sort.by(Order.asc("id").nullsLast()))`; builds `Meta` manually                                                    |
| **Repository / DB**   | `TrackCoordinatesRepository.findLocationsWithTracks(Pageable)` — 2 aggregations + 1 `$in` find on `infra-rivm.track-coordinates`        |
| **Response DTO**      | `APIPaginatedResponse<LocationWithTracks>`                                                                                              |
| **Status**            | `200`, `400`                                                                                                                            |
| **Frontend consumer** | `LocationTrackCoordinatesApiService` (all pages, `retry 3 × 1 s`, IndexedDB cache) → `LocationsStore` → `MapService.loadLocationLabels` |

```jsonc
{
  "data": [
    { "id": "70_KNGX", "name": "London King's Cross", "shortName": "KNGX",
      "tracks": [
        { "id": "T-1", "name": "Platform 1", "shortName": "P1", "description": "…",
          "businessRefs": [ … ],
          "nodeCoordinates": [ { "x": 125190, "y": -6035 }, { "x": 125240, "y": -6030 } ] }
      ] }
  ],
  "meta": { "page": { "pageNumber": 0, "size": 100, "totalElements": 14, "totalPages": 1 } }
}
```

> `LocationTrackCoordinatesService` constructs `Meta` directly, so `dataTileVersions` is whatever the
> generated `Meta` defaults to (an empty list) — it is not populated here.

---

## 6.5 `GET /api/infra/query/restrictions`

| Item                  | Value                                                                                                                                                                                               |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Controller**        | `RestrictionController` — `@RequestMapping("/restrictions")`, `@AllArgsConstructor`                                                                                                                 |
| **Method**            | `getRestrictionsByTime(Instant effectiveAt, Integer pageNumber, Integer pageSize)` — `@GetMapping`                                                                                                  |
| **Swagger**           | `@Tag(name="Restriction")`, documents `200`, `400`                                                                                                                                                  |
| **Query params**      | `effectiveAt` — **required**, `@DateTimeFormat(iso = DATE_TIME)`, example `2026-05-31T12:00:00Z`; `pageNumber` default `0`, `@Valid @Min(0)`; `pageSize` default `100`, `@Valid @Min(1) @Max(1000)` |
| **Service**           | `RestrictionService.getRestrictionsByEffectiveTime(...)`                                                                                                                                            |
| **Business logic**    | `PageRequest.of(p, s, Sort.by(DESC, "lastModified"))`; INFO logs before/after                                                                                                                       |
| **Repository / DB**   | `RestrictionRepository.findByEffectiveTime(Instant, Pageable)` → `MongoRestrictionRepository` `@Query` (string `$lte`/`$gte`) on `infra-rivm.restriction`                                           |
| **Response DTO**      | `APIPaginatedResponse<Restriction>`                                                                                                                                                                 |
| **Status**            | `200`, `400` (missing/unparseable `effectiveAt` → `400` via the `IllegalArgumentException` / `ConstraintViolationException` handlers)                                                               |
| **Frontend consumer** | `RestrictionApiService.getRestrictionData(effectiveAt, pageNumber=0, pageSize=100)` → `RestrictionsStore`                                                                                           |

```jsonc
{
  "data": [
    {
      "id": "R01",
      "name": "Restriction 1",
      "shortName": "R1",
      "description": "Description of Restriction 1",
      "lastModified": "2023-12-12T07:59:56.123Z",
      "restrictionData": {
        "state": "ACTIVE",
        "effectiveTimePeriod": {
          "startTime": "2023-12-24T10:00:00Z",
          "endTime": "2023-12-31T08:00:00Z",
        },
        "group": { "id": "G1" },
        "impacts": [
          {
            "trainFilter": {
              "trainOperationFilter": {
                "operator": "AND",
                "conditions": [
                  { "path": "$.path.to.prop", "valueString": "Match4711" },
                ],
              },
            },
            "blocking": {},
          },
        ],
        "edgePaths": [
          {
            "pathEdges": [
              {
                "edgeRef": {
                  "infraMicroscopicRegionRef": {
                    "type": "InfraMicroscopicRegion",
                    "entityID": "REGION-A",
                  },
                  "infraMicroscopicEdgeRef": {
                    "type": "baseGraph.edges",
                    "subEntityID": "e1",
                  },
                },
                "startPercentage": 0.0,
                "endPercentage": 1.0,
              },
            ],
            "pathCoordinates": [
              { "x": 125190, "y": -6035 },
              { "x": 125240, "y": -6030 },
            ],
          },
        ],
        "meta": {
          "ui": {
            "icon": { "type": "image/svg+xml", "payload": "PHN2Zy…" },
            "style": { "type": "text/css", "payload": "Y29sb3I6…" },
          },
        },
      },
    },
  ],
  "meta": {
    "page": {
      "pageNumber": 0,
      "size": 100,
      "totalElements": 1,
      "totalPages": 1,
    },
    "dataTileVersions": [],
  },
}
```

---

## 6.6 `GET /api/infra/query/track-coordinates`

| Item                  | Value                                                                                                                                                                                                              |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Controller**        | `TrackCoordinatesController` — `@RequestMapping("/track-coordinates")`, `@AllArgsConstructor`                                                                                                                      |
| **Method**            | `getTrackCoordinates(Integer pageNumber, Integer pageSize)` — `@GetMapping`                                                                                                                                        |
| **Swagger**           | `@Tag(name="TrackCoordinates")`, documents `200`, `400`                                                                                                                                                            |
| **Query params**      | `pageNumber` default `0`, `@Min(0)`; `pageSize` default `1000`, `@Min(1) @Max(APIPaginatedResponse.COORDINATES_MAX_PAGE_SIZE = 10000)`                                                                             |
| **Service**           | `TrackCoordinatesService.getTrackCoordinates(...)`                                                                                                                                                                 |
| **Business logic**    | `PageRequest.of(p, s, Sort.by(Order.asc("id").nullsLast()))`; `APIMapper.mapPageToMetaPage(page)`                                                                                                                  |
| **Repository / DB**   | `TrackCoordinatesRepository.findAll(Pageable)` → `infra-rivm.track-coordinates`                                                                                                                                    |
| **Response DTO**      | `APIPaginatedResponse<TrackCoordinates>`                                                                                                                                                                           |
| **Status**            | `200`, `400`                                                                                                                                                                                                       |
| **Frontend consumer** | **NONE.** `NOT FOUND` — no Angular service calls `/track-coordinates`. It is registered in `endpoints.yaml` and covered by `TrackCoordinatesEndToEndTest`, but the SPA uses `/location-track-coordinates` instead. |

---

## 6.7 `POST /api/infra/query/trainpositions`

| Item                  | Value                                                                                                                                    |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| **Controller**        | `TrainPositionController` — `@RequestMapping("/trainpositions")`, `@AllArgsConstructor`                                                  |
| **Method**            | `getPositions(List<DataTile> tiles, Integer pageNumber, Integer pageSize)` — `@PostMapping`                                              |
| **Swagger**           | `@Tag(name="TrainPosition")`, documents `200`, `400` (twice: invalid paging, invalid tiles)                                              |
| **Body**              | `@Valid @NotEmpty @RequestBody List<@Valid DataTile>` — content type `application/json`                                                  |
| **Request DTO**       | `DataTile { String id (required); String version (optional) }`                                                                           |
| **Query params**      | `pageNumber` default `0`, `@Valid`; `pageSize` default `1000`, `@Min(1) @Max(1000)`                                                      |
| **Service**           | `TrainPositionService.getModifiedTrainPositionsByTiles(tiles, pageNumber, pageSize)`                                                     |
| **Validation**        | `validateDataTiles(tiles)` → `BadRequestException("Tile ID must not be null or empty", "20001")`                                         |
| **Business logic**    | version diffing → optional short-circuit → paged `$in` query (see §2.2)                                                                  |
| **Repository / DB**   | `DataTileRepository.findAllById` on `infra-rivm.data-tile`; `TrainPositionRepository.findByDataTileIdsIn` on `infra-rivm.train-position` |
| **Response DTO**      | `APIPaginatedResponse<TrainPosition>` with `meta.dataTileVersions = [ { tileId: version } ]`                                             |
| **Status**            | `200`; `400` for empty body / invalid tile id / bad paging; `500` for duplicate tile ids in the body                                     |
| **Frontend consumer** | `TrainPositionService.getTrainPositions(...)` inside `TrainPositionStore.startPolling`                                                   |

Request:

```json
[
  { "id": "125000_-10000_2026-08-31T09:15" },
  { "id": "125000_-5000_2026-08-31T09:15", "version": "0f0b1f4e-…" }
]
```

Empty-delta response (all versions matched):

```json
{
  "data": [],
  "meta": {
    "page": { "pageNumber": 0, "size": 0, "totalElements": 0, "totalPages": 0 },
    "dataTileVersions": [{}]
  }
}
```

(`Page.empty()` → `getSize()` is `0`.)

---

## 6.8 Springdoc / OpenAPI UI

`org.springdoc:springdoc-openapi-starter-webmvc-ui` is on the `infra-query-svc` classpath, so the
default endpoints exist:

- `/api/infra/query/swagger-ui/index.html`
- `/api/infra/query/v3/api-docs`

`infra-query-svc/README.md` quotes an older path
(`http://localhost:8080/api/v1/infra-query/swagger-ui/index.html#/`) which **no longer matches** the
configured context path — treat the README as stale.

**No `springdoc.*` properties are configured**, so all defaults apply.

## 6.9 Gateway endpoint registry (`deployment/helm/templates/endpoints.yaml`)

| Host           | Path                                          | Methods | Allowed params                          | Allowed headers                  | Permissions |
| -------------- | --------------------------------------------- | ------- | --------------------------------------- | -------------------------------- | ----------- |
| query-svc:9101 | `/api/infra/query/business-clock`             | GET     | —                                       | —                                | `null`      |
| query-svc:9101 | `/api/infra/query/basegraph`                  | GET     | `pageNumber`, `pageSize`                | —                                | `null`      |
| query-svc:9101 | `/api/infra/query/track-coordinates`          | GET     | `pageNumber`, `pageSize`                | —                                | `null`      |
| query-svc:9101 | `/api/infra/query/restrictions`               | GET     | `pageNumber`, `pageSize`, `effectiveAt` | —                                | `null`      |
| query-svc:9101 | `/api/infra/query/location-track-coordinates` | GET     | `pageNumber`, `pageSize`                | —                                | `null`      |
| query-svc:9101 | `/api/infra/query/trainpositions`             | POST    | `pageNumber`, `pageSize`                | `Content-Type`, `Content-Length` | `null`      |
| query-svc:9101 | `/api/infra/query/configs`                    | GET     | —                                       | —                                | `null`      |
| webapp:80      | `/ui/infra` → rewrite `/`                     | GET     | —                                       | `Accept`, `Accept-Language`      | `null`      |
| webapp:80      | `/ui/infra/{*path}` → rewrite `{path}`        | GET     | —                                       | `Accept`, `Accept-Language`      | `null`      |

The MFE sub-charts (`mfe-train-operation`, `rimfe-restriction`) register their **own** endpoints
under `endpoints.apiPrefix: "infra"` — those routes are **NOT FOUND / NOT DETERMINED** from this
repository.

## 6.10 Internal service-to-service APIs

**NONE.** No service in this repository calls another service over HTTP. The only cross-service
contract is the shared MongoDB database plus the shared RabbitMQ exchange.

## 6.11 APIs consumed by the frontend but implemented elsewhere

Observed only through `environment.mfeBaseUrl` bindings and demo-mode interception:

| Path fragment                                              | Consumer                         | Source                                       |
| ---------------------------------------------------------- | -------------------------------- | -------------------------------------------- |
| `/train-operation/query/train-operations/{trainServiceId}` | `@tps/mfe-train-operation` (TIP) | mock interceptor                             |
| `/train-operation/query/trainoperations/{trainServiceId}`  | same (alternate spelling)        | mock interceptor                             |
| `/train-operation-overviews-presets`                       | train list presets               | mock interceptor                             |
| `/compositions`                                            | train composition                | mock interceptor                             |
| `/me`                                                      | user info                        | mock interceptor                             |
| `/aem/query/detection-describers`                          | `@tps/rimfe-aem`                 | `aem-mock-handler.ts`                        |
| `/aem/query/detection-events`                              | `@tps/rimfe-aem`                 | `aem-mock-handler.ts`                        |
| `/aem/query/unread-counts`                                 | `@tps/rimfe-aem`                 | `aem-mock-handler.ts`                        |
| restriction list + PATCH                                   | `@tps/rimfe-restriction`         | `restrictionBaseUrl = INFRA_URLS.mfeBaseUrl` |
| `{baseAuthUrl}/logout`                                     | `LogoutApiService`               | in-repo                                      |

---

# 7 — DATABASE — COMPLETE DATA MODEL

## 7.1 Technology

| Item                                                         | Value                                                                                                                                      |
| ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Engine                                                       | **MongoDB** (document store)                                                                                                               |
| Driver / mapping                                             | Spring Data MongoDB (`spring-boot-starter-data-mongodb`)                                                                                   |
| Database                                                     | `${MONGO_DATABASE:risedb}`                                                                                                                 |
| Host / port                                                  | `${MONGO_HOST:localhost}` / `${MONGO_PORT:27017}`                                                                                          |
| Credentials                                                  | `${MONGO_USERNAME:guest}` / `${MONGO_PASSWORD:guest}` — `[SECRET / CREDENTIAL PRESENT — VALUE OMITTED]`                                    |
| E2E URI                                                      | `mongodb://guest:guest@localhost:27017/risedb` (`module-tests/config/db.config.js`) — `[SECRET / CREDENTIAL PRESENT — VALUE OMITTED]`      |
| Repositories enabled                                         | `@EnableMongoRepositories(basePackages = "de.hacon.tps.rise.infra.common.repository.mongodb")`                                             |
| Migrations                                                   | **NONE** — `NOT FOUND` (no Mongock, no Flyway, no Liquibase, no `db/migration`)                                                            |
| Views / stored procedures / functions / triggers / sequences | **NONE** — not applicable to MongoDB and none emulated                                                                                     |
| Seed data                                                    | **NONE in production code.** E2E fixtures exist: `module-tests/playwright/data/eventBasedTesting/dbCollections/infra-rivm.map-config.json` |
| Query files                                                  | **NONE** — queries are Java annotations / derived method names / `Aggregation` builders                                                    |

## 7.2 Collection inventory

| Collection                     | Entity                        | Written by                 | Read by                                       | `_id`                                                     |
| ------------------------------ | ----------------------------- | -------------------------- | --------------------------------------------- | --------------------------------------------------------- |
| `infra-rivm.business-clock`    | `MongoBusinessClockEntity`    | `infra-business-clock-etl` | `infra-query-svc`                             | auto (`ObjectId`) — the model has no `id` field           |
| `infra-rivm.basegraph`         | `MongoBaseGraphEntity`        | `infra-basegraph-etl`      | `infra-query-svc`                             | `BaseGraph.id` = region `entityID`                        |
| `infra-rivm.track-coordinates` | `MongoTrackCoordinatesEntity` | `infra-micro-etl`          | `infra-query-svc`, `infra-trainoperation-etl` | `TrackCoordinates.id` = `{locationId}_{trackId}`          |
| `infra-rivm.train-position`    | `MongoTrainPositionEntity`    | `infra-trainoperation-etl` | `infra-query-svc`                             | `TrainPosition.id` = `{trainServiceId}-{activityId}`      |
| `infra-rivm.data-tile`         | `MongoDataTileEntity`         | `infra-trainoperation-etl` | `infra-query-svc`                             | `DataTile.id` = `{x}_{y}_{yyyy-MM-ddTHH:mm}`              |
| `infra-rivm.restriction`       | `MongoRestrictionEntity`      | `infra-restriction-etl`    | `infra-query-svc`                             | `Restriction.id` = restriction `entityID`                 |
| `infra-rivm.map-config`        | `MongoMapConfigEntity`        | **NO WRITER in this repo** | `infra-query-svc`, `infra-trainoperation-etl` | `MapConfig.id` (e.g. `INFRA_MAP_01`)                      |
| `infra-rivm.location`          | _(no entity)_                 | —                          | —                                             | property `app.db.collection.location` declared but unused |

> MongoDB is schemaless; the "columns" below are the **Java/OpenAPI-declared fields**, which are what
> Spring Data will read and write. Actual documents may contain a Spring-added `_class` discriminator
> (the frontend `Restriction` model even declares an optional `_class?: string`).

## 7.3 `infra-rivm.business-clock` — `BusinessClock`

Schema: [components/schemas/clock/BusinessClock.yaml](../infra/components/schemas/clock/BusinessClock.yaml)

| Field              | Type                                                   | Required | Default | Meaning                                                       |
| ------------------ | ------------------------------------------------------ | -------- | ------- | ------------------------------------------------------------- |
| `businessTime`     | `string` (`UTCTime`, `yyyy-MM-ddTHH:mm:ssZ`)           | ✔        | —       | The simulated "now" of the whole platform                     |
| `businessTimeZone` | `string` (`TimeZoneStr`, e.g. `Europe/London`)         | ✔        | —       | Display time zone                                             |
| `serverTime`       | `string` (`UTCTimeMillis`, `yyyy-MM-ddTHH:mm:ss.SSSZ`) | ✔        | —       | Real system clock (RISE `systemTime`)                         |
| `mode`             | enum `REALTIME` \| `CONTROLLED`                        | ✔        | —       | Whether the clock advances in real time or is driven manually |

- **PK:** implicit `_id`.
- **Cardinality:** at most one document (`deleteAll()` before every `save`).
- **No FK, no index, no unique constraint.**
- **Audit fields:** none (`serverTime` is data, not audit).

## 7.4 `infra-rivm.basegraph` — `BaseGraph`

Schema: [components/schemas/infra/BaseGraph.yaml](../infra/components/schemas/infra/BaseGraph.yaml)

```
BaseGraph
├── id            : string  (required)  "<region>_<x>_<y>"  ← PK, from event entityID
└── baseGraph     : InfraMicroscopicBaseGraph (required)
    ├── nodes[]   : InfraMicroscopicNode      (minItems 2, maxItems 1 048 575)
    │   ├── baseSubEntityData : BaseSubEntityData (required)
    │   │   ├── id           : RIVMEntityID (required, 1..255)
    │   │   ├── name         : RIVMEntityName (1..2000)
    │   │   ├── shortName    : RIVMEntityShortName (1..20)
    │   │   ├── description  : RIVMEntityDescription (1..65535)
    │   │   └── businessRefs : RIVMBusinessRef[] (1..255)
    │   └── nodeData         : InfraMicroscopicNodeData (required)
    │       ├── infraNodeAddress : InfraMicroscopicNodeAddress
    │       │   ├── kmRegion : NonEmptyShortString (required)
    │       │   └── kmValue  : integer int64       (required)
    │       └── coordinates  : InfraMicroscopicNodeCoordinates (required)
    │           └── graphical : InfraGraphicalCoordinates { x: int32 (req), y: int32 (req) }
    └── edges[]   : InfraMicroscopicEdge      (minItems 1, maxItems 524 287)
        ├── baseSubEntityData : BaseSubEntityData (required)
        └── edgeData          : InfraMicroscopicEdgeData (required)
            ├── edgeLengthMillimeters : LengthMillimeters (integer, min 0)
            ├── infraNodeRefs[]       : InfraMicroscopicNodeRef (required, exactly 2, uniqueItems)
            │   ├── regionRef               : RIVMEntityRef   { type, entityID }
            │   └── infraMicroscopicNodeRef : RIVMSubEntityRef{ type, subEntityID } (required)
            └── direction            : InfraEdgeDirection  FORWARD | REVERSE | BOTH (default FORWARD)
```

- **PK:** `id`.
- **"Foreign keys" (logical, not enforced):** `edgeData.infraNodeRefs[*].infraMicroscopicNodeRef.subEntityID`
  → `baseGraph.nodes[*].baseSubEntityData.id` **within the same document**.
- **Indexes:** only the implicit `_id`.
- **Business meaning:** the complete microscopic topology of one region — the drawable network.

## 7.5 `infra-rivm.track-coordinates` — `TrackCoordinates`

Schema: [components/schemas/infra/TrackCoordinates.yaml](../infra/components/schemas/infra/TrackCoordinates.yaml)

| Field                   | Type                                                                 | Required (schema) | Meaning                                                               |
| ----------------------- | -------------------------------------------------------------------- | ----------------- | --------------------------------------------------------------------- |
| `id`                    | `string`                                                             | ✔                 | `{locationId}_{trackId}` — PK                                         |
| `nodeCoordinates[]`     | `NodeCoordinates` (`= InfraGraphicalCoordinates {x:int32, y:int32}`) | —                 | Every node of the track, in `Set` iteration order                     |
| `locationSubEntityData` | `BaseSubEntityData`                                                  | —                 | `{id, name, shortName, description}` (populated by `infra-micro-etl`) |
| `trackSubEntityData`    | `BaseSubEntityData`                                                  | —                 | `{id, name, shortName, description}`                                  |

> The YAML `required` list is `[id, nodes, locationBaseSubEntityData, trackBaseSubEntityData]`,
> but the declared **properties** are `id, nodeCoordinates, locationSubEntityData,
trackSubEntityData`. Three of the four required names do not exist as properties — an
> **inconsistency in the schema** that has no runtime effect because the generator emits the
> properties and MongoDB does not validate.

- **Index used by queries:** `locationSubEntityData.id` (via `findByLocationSubEntityData_IdIn` and
  the two aggregations). **No explicit index is created for it anywhere** — the aggregation and the
  `$in` will be collection scans.
- **Logical FK:** `id` prefix ↔ `LocationWithTracks.id`; also referenced by
  `TrainOperationUtil.resolveLocationCoordinates` as `locationId + "_" + trackId`.

## 7.6 `infra-rivm.train-position` — `TrainPosition`

Schema: [components/schemas/infra/TrainPosition.yaml](../infra/components/schemas/infra/TrainPosition.yaml)

| Field            | Type                                                        | Required | Nullable in practice                                     | Meaning                                                          |
| ---------------- | ----------------------------------------------------------- | -------- | -------------------------------------------------------- | ---------------------------------------------------------------- |
| `id`             | `string`                                                    | ✔        | no                                                       | `{trainServiceId}-{activityId}` — PK                             |
| `trainServiceId` | `IdAlpha` (1..80)                                           | ✔        | no                                                       | Train operation identifier, e.g. `TrainOperation-9N70-KNGX-DONC` |
| `dataTileIds[]`  | `TileId[]` (`{x}_{y}_{timeslot}`)                           | ✔        | can be `[]` when `MapConfig` is missing / boundary case  | Spatial-temporal tiles this position belongs to                  |
| `fromTime`       | `UTCTime`                                                   | ✔        | no                                                       | Inclusive start of the position's validity                       |
| `toTime`         | `UTCTime`                                                   | ✔        | no                                                       | End of validity (next activity time, or `+10 min` for the last)  |
| `runningType`    | enum `ACTUAL` \| `FORECAST`                                 | ✔        | no                                                       | Confirmed vs predicted                                           |
| `activityId`     | `IdAlpha`                                                   | ✔        | no                                                       | Source `TrainOperationActivity.baseSubEntityData.id`             |
| `activityType`   | enum `ARRIVAL` \| `DEPARTURE` \| `MOVEMENT` \| `RUNTHROUGH` | ✔        | no                                                       | Kind of activity                                                 |
| `origin`         | `IdAlpha`                                                   | ✔        | **can be `null`** (no location activity in the sequence) | First arrival/departure location id                              |
| `destination`    | `IdAlpha`                                                   | ✔        | **can be `null`**                                        | Last arrival/departure location id                               |
| `coordinates`    | `InfraGraphicalCoordinates {x:int32, y:int32}`              | ✔        | no (positions without coordinates are dropped)           | Where to draw the train                                          |

- **Indexes** (created by `infra-trainoperation-etl` `IndexConfig`):
  1. `{ trainServiceId: 1 }`
  2. `{ dataTileIds: 1 }` (multikey)
  3. `{ dataTileIds: 1, _id: 1, trainServiceId: 1 }` (compound, matches the query + sort)
     **None are `unique`.**
- **Logical FKs:** `dataTileIds[*]` → `infra-rivm.data-tile._id`;
  `origin` / `destination` → location entity IDs (also the prefix of `track-coordinates._id`).
- **Audit/status fields:** none. `runningType` is the closest thing to a status field.

## 7.7 `infra-rivm.data-tile` — `DataTile`

Schema: [components/schemas/infra/DataTile.yaml](../infra/components/schemas/infra/DataTile.yaml)

| Field     | Type                              | Required | Meaning                                                            |
| --------- | --------------------------------- | -------- | ------------------------------------------------------------------ |
| `id`      | `TileId` = `"{x}_{y}_{timeslot}"` | ✔        | PK                                                                 |
| `version` | `string`                          | —        | A **new random UUID** every time the tile's content is (re)written |

- Written by `DataTileService.createDataTiles(ids)` → `new DataTile(id, UUID.randomUUID().toString())`
  → `dataTileRepository.saveAll(...)` (upsert).
- Read by `TrainPositionService` for delta detection.
- **No index** beyond `_id`.
- Nothing ever deletes stale tiles — the collection grows monotonically with time slots.

## 7.8 `infra-rivm.restriction` — `Restriction`

Schemas: [Restriction.yaml](../infra/components/schemas/infra/Restriction.yaml),
[RestrictionData.yaml](../infra/components/schemas/infra/RestrictionData.yaml),
[RestrictionTypes.yaml](../infra/components/schemas/infra/RestrictionTypes.yaml)

```
Restriction
├── id            : IdAlpha  (required)  ← PK, event entityID
├── name          : RIVMEntityName
├── shortName     : RIVMEntityShortName
├── description   : RIVMEntityDescription
├── lastModified  : UTCTimeMillis        ← used as the SORT KEY (DESC) by the query service
└── restrictionData : RestrictionData    (required)
    ├── state               : ACTIVE | INACTIVE | CANCELLED          (required)
    ├── effectiveTimePeriod : TimeRange { startTime?, endTime? }      (required)
    │      convention: startTime inclusive, endTime exclusive, both optional = unbounded
    ├── group               : { id: NonEmptyShortString }
    ├── impacts[]           : RestrictionImpact (0..255)              (required)
    │   ├── trainFilter (required)
    │   │   ├── trainOperationFilter   : PropertyFilter { operator AND|OR (default AND),
    │   │   │                                             conditions[1..255] }
    │   │   └── trainCompositionFilter : PropertyFilter
    │   │        condition = { path (RIVMPropertyJsonPath, required),
    │   │                      operator EQUAL|NOT_EQUAL|GREATER|GREATER_OR_EQUAL|LESS|LESS_OR_EQUAL
    │   │                                (default EQUAL),
    │   │                      valueString|valueInteger|valueBoolean|valueDate|valueDateTime
    │   │                      — exactly one must be set }
    │   ├── blocking       : { dummyToNotHaveEmptyObject? }
    │   ├── speedReduction : { absoluteMaxSpeedMillimetersPerHour?,
    │   │                      relativeSpeedReductionMillimetersPerHour? }
    │   └── adhesion       : { adhesionLevel: DRY_MEDIUM|DRY_LOW|LOW|VERY_LOW|EXTREMELY_LOW }
    ├── edgePaths[]        : EdgePath (1..524 287)                    (required)
    │   ├── pathEdges[]       : EdgeWithOffsets (1..524 287, required)
    │   │   ├── edgeRef         : InfraMicroscopicEdgeRef (required)
    │   │   ├── startPercentage : number 0.0..1.0 (required)
    │   │   └── endPercentage   : number 0.0..1.0 (required)
    │   └── pathCoordinates[] : InfraGraphicalCoordinates (1..524 287, required)
    └── meta               : MetaData { ui: { icon: EncodedPayloadData,
                                              style: EncodedPayloadData } }
                             EncodedPayloadData = { type (required, e.g. "image/svg+xml"),
                                                    payload (required, Base64, 1..1 000 000) }
```

- **PK:** `id`.
- **Query index requirement:** `restrictionData.effectiveTimePeriod.startTime` /
  `.endTime` and the `lastModified` sort key — **no index is created for any of them anywhere in
  this repository.**
- **Status field:** `restrictionData.state`.
- **Enumerations:** `RestrictionState`, `RestrictionImpactAdhesionLevel`,
  `PropertyFilterConditionOperator`, `PropertyFilterMatchOperator`.

## 7.9 `infra-rivm.map-config` — `MapConfig`

See §4.4 for the schema and the reference document. Key points:

- `_id` = `MapConfig.id`, e.g. `INFRA_MAP_01`.
- `mapType` must be `OCTOLINEAR` for `infra-trainoperation-etl` to use it.
- Exactly one layer must have `layerDataType == "train"` **with** a `tileSize`
  (`{width, height, timeSpanSecs}`) or **no train position will ever be ingested**.
- Layer ids consumed by the frontend: `baseGraph`, `locations`, `platforms`, `restrictions`, `trains`.
- **No writer exists in this repository** — see §5.8.

## 7.10 Relationship map

```
infra-rivm.map-config  (MapConfig)
    │  layers[layerDataType="train"].tileSize  ──► drives tile id generation
    ▼
infra-rivm.data-tile   (DataTile)
    ▲   _id = "{x}_{y}_{yyyy-MM-ddTHH:mm}"
    │   (logical FK, multikey)
infra-rivm.train-position (TrainPosition.dataTileIds[])
    │   trainServiceId  ──►  (external TrainOperation entity — not stored here)
    │   activityId      ──►  (external TrainOperationActivity sub-entity)
    │   origin / destination ─┐
    │                          ▼
infra-rivm.track-coordinates (TrackCoordinates)
    │   _id = "{locationSubEntityData.id}_{trackSubEntityData.id}"
    │   nodeCoordinates[] ◄── resolved from
    ▼
infra-rivm.basegraph (BaseGraph)
    │   baseGraph.nodes[].baseSubEntityData.id
    │        ▲
    │        │ (intra-document FK)
    │   baseGraph.edges[].edgeData.infraNodeRefs[].infraMicroscopicNodeRef.subEntityID
    ▲
    │  (logical, via rise-infra-utils MicroscopicInfra)
infra-rivm.restriction (Restriction)
        restrictionData.edgePaths[].pathEdges[].edgeRef.infraMicroscopicEdgeRef.subEntityID
        restrictionData.edgePaths[].pathEdges[].edgeRef.infraMicroscopicRegionRef.entityID → basegraph._id

infra-rivm.business-clock (BusinessClock)   — standalone singleton, no references
```

Cardinalities:

| Relationship                                                      | Cardinality                                          | Enforced?   |
| ----------------------------------------------------------------- | ---------------------------------------------------- | ----------- |
| `BaseGraph` 1 ── n `InfraMicroscopicNode`                         | 2 … 1 048 575 (embedded)                             | schema only |
| `BaseGraph` 1 ── n `InfraMicroscopicEdge`                         | 1 … 524 287 (embedded)                               | schema only |
| `InfraMicroscopicEdge` n ── 2 `InfraMicroscopicNode`              | exactly 2, unique                                    | schema only |
| `LocationWithTracks` 1 ── n `TrackCoordinates`                    | derived by aggregation on `locationSubEntityData.id` | no          |
| `TrackCoordinates` 1 ── n `NodeCoordinates`                       | embedded array                                       | no          |
| `TrainPosition` n ── n `DataTile`                                 | via `dataTileIds[]`                                  | **no**      |
| `TrainPosition` n ── 1 train service                              | via `trainServiceId`                                 | no          |
| `Restriction` 1 ── n `EdgePath`                                   | 1 … 524 287 (embedded)                               | schema only |
| `EdgePath` 1 ── n `EdgeWithOffsets` / `InfraGraphicalCoordinates` | 1 … 524 287 each                                     | schema only |
| `Restriction` 1 ── n `RestrictionImpact`                          | 0 … 255 (embedded)                                   | schema only |

**There is no referential-integrity enforcement of any kind** — MongoDB has no FK constraints and
the application performs no cross-collection validation.

## 7.11 Enumerations (complete list)

| Enum                              | Values                                                                                                        | Where                                                |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------- |
| `BusinessClock.mode`              | `REALTIME`, `CONTROLLED`                                                                                      | `clock/BusinessClock.yaml`                           |
| `InfraEdgeDirection`              | `FORWARD` (default), `REVERSE`, `BOTH`                                                                        | `infra/InfraTypes.yaml`                              |
| `TrainPosition.runningType`       | `ACTUAL`, `FORECAST`                                                                                          | `infra/TrainPosition.yaml`                           |
| `TrainPosition.activityType`      | `ARRIVAL`, `DEPARTURE`, `MOVEMENT`, `RUNTHROUGH`                                                              | `infra/TrainPosition.yaml`                           |
| `Activity.type`                   | `ORIGIN`, `DESTINATION`, `STOP`, `RUN_THROUGH`                                                                | `infra/Activity.yaml` — **generated but never used** |
| `RestrictionState`                | `ACTIVE`, `INACTIVE`, `CANCELLED`                                                                             | `infra/RestrictionTypes.yaml`                        |
| `RestrictionImpactAdhesionLevel`  | `DRY_MEDIUM`, `DRY_LOW`, `LOW`, `VERY_LOW`, `EXTREMELY_LOW`                                                   | `infra/RestrictionTypes.yaml`                        |
| `PropertyFilterConditionOperator` | `AND` (default), `OR`                                                                                         | `basic/PropertyFilter.yaml`                          |
| `PropertyFilterMatchOperator`     | `EQUAL` (default), `NOT_EQUAL`, `GREATER`, `GREATER_OR_EQUAL`, `LESS`, `LESS_OR_EQUAL`                        | `basic/PropertyFilter.yaml`                          |
| `MapType`                         | `OCTOLINEAR`, `GEOGRAPHIC`, `SCHEMATIC`                                                                       | `infra/MapConfig.yaml`                               |
| `CoordinateSystem`                | `CARTESIAN` (default), `GEOGRAPHIC`                                                                           | `infra/MapConfig.yaml`                               |
| `LayerType`                       | `EDGE_OBJECT`, `TIMED_SINGLE_POINT_OBJECT`                                                                    | `infra/MapConfig.yaml`                               |
| `LayerVisibility`                 | `SHOW` (default), `HIDE`                                                                                      | `infra/MapConfig.yaml`                               |
| `RIVMCommandResultType`           | `SUCCESS`, `ERROR_NOT_AUTHORIZED`, `ERROR_NOT_ALLOWED`, `ERROR_NOT_FOUND`, `ERROR_BAD_ARGS`, `ERROR_INTERNAL` | `basic/RIVMTypes.yaml`                               |
| `RIVMEventTriggerType`            | `ENTITY_CREATED`, `ENTITY_UPDATED`, `ENTITY_DELETED`, `COMMAND_FAILED`                                        | `basic/RIVMTypes.yaml`                               |
| `RIVMErrorType`                   | `UNKNOWN_ERROR`, `INVALID_SIGNATURE`, `MALFORMED_MESSAGE`, `BUSINESS_CLOCK_NOT_SET`                           | `basic/RIVMTypes.yaml`                               |
| `RIVMSetModeType`                 | `FULL_REPLACE`, `PROPERTY_REPSERT`                                                                            | `basic/RIVMTypes.yaml`                               |

## 7.12 Schema library (complete file list)

| Folder        | File                      | Defines                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| ------------- | ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `base-entity` | `BaseEntityData.yaml`     | `BaseEntityData { name*, shortName*, description, lastModified, businessRefs[] }`                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `base-entity` | `BaseSubEntityData.yaml`  | `BaseSubEntityData { id*, name, shortName, description, businessRefs[1..255] }`, `CreateBaseSubEntityData`                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `basic`       | `datetime.yaml`           | `Date`, `DateHour`, `TimeSeconds`, `TimeZoneStr`, `UTCTime`, `UTCTimeMillis`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `basic`       | `EncodedPayloadData.yaml` | `EncodedPayloadData { type*, payload* }`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `basic`       | `ErrorResponse.yaml`      | `ErrorResponse { code, message }`, `ApiErrorResponse { errors[] }`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| `basic`       | `Integer.yaml`            | `Signed32BitInteger`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `basic`       | `Meta.yaml`               | `Meta { page, dataTileVersions[] }`, `KeyValue`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `basic`       | `PageResult.yaml`         | `PageResult { pageNumber*, size*, totalElements*, totalPages* }`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `basic`       | `PropertyFilter.yaml`     | `PropertyFilter`, `PropertyFilterConditionOperator`, `PropertyFilterCondition`, `PropertyFilterMatchOperator`                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `basic`       | `rest.yaml`               | An **alternative** `PageResult` (Spring `Page` shape: `number`, `numberOfElements`, `first`, `last`, `unsorted`, `totalPages`, `totalElements`, `size`) — **not referenced by `infra-model.yaml`**                                                                                                                                                                                                                                                                                                                                                              |
| `basic`       | `RIVMTypes.yaml`          | `RIVMUserData`, `RIVMUserID`, `RIVMUserRole`, `RIVMEntityID`, `RIVMServiceID`, `RIVMUUID`, `RIVMEventID`, `RIVMCommandID`, `RIVMEntityName`, `RIVMEntityShortName`, `RIVMEntityDescription`, `RIVMCommandResult`, `RIVMCommandResultType`, `RIVMMessageSignature`, `RIVMEventTriggerType`, `RIVMErrorType`, `RIVMTriggeringCommand`, `RIVMSetModeType`, `RIVMDataVersion`, `RIVMMasterDataType`, `RIVMBusinessRef`, `RIVMEntityRef`, `RIVMSubEntityRef`, `RIVMEntityType`, `RIVMSubEntityType`, `RIVMPropertyJsonPath`, `RIVMUicCountryCode`, `RISEBusinessRef` |
| `basic`       | `String.yaml`             | `NonEmptyShortString` (≤255), `NonEmptyMediumString` (≤2000), `NonEmptyLongString` (≤65535), `Base64String` (≤1 000 000)                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `basic`       | `TimeRange.yaml`          | `TimeRange { startTime, endTime }` (half-open)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `basic`       | `types.yaml`              | `IdAlpha` (1..80), `DescriptionString` (1..255), `SequenceNumber`, `LengthInMeters`, `RIVMEntityShortName`                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `basic`       | `UnitTypes.yaml`          | `LengthMillimeters`, `WeightKilograms`, `SpeedMillimetersPerHour`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `clock`       | `BusinessClock.yaml`      | `BusinessClock`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `infra`       | `Activity.yaml`           | `Activity { id*, type*, description* }`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `infra`       | `BaseGraph.yaml`          | `BaseGraph`, `InfraMicroscopicBaseGraph`, `InfraMicroscopicNode(+Data,+Address,+Coordinates)`, `InfraMicroscopicEdge(+Data)`                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `infra`       | `DataTile.yaml`           | `DataTile`, `TileId`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `infra`       | `InfraTypes.yaml`         | `InfraPlace`, `InfraGraphicalCoordinates`, `InfraMicroscopicSubGraph`, `InfraEdgeDirection`, `InfraMicroscopicNodeRef`, `InfraMicroscopicEdgeRef`, `InfraMicroscopicLocationRef`                                                                                                                                                                                                                                                                                                                                                                                |
| `infra`       | `LocationDataTile.yaml`   | `LocationDataTile`, `LocationData` (`locationId*, name*, tracks*, shortName*, uicCountryCode*, isAuxiliary, level, nodes[]`)                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `infra`       | `LocationTrack.yaml`      | `LocationTrack { id*, name*, description*, shortName*, sequence, effectiveLengthMeters, isElectrified, hasPassengerPlatform, nodes[] }`                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `infra`       | `LocationWithTracks.yaml` | `LocationWithTracks`, `TrackWithCoordinates`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `infra`       | `MapConfig.yaml`          | `MapConfig`, `MapType`, `CoordinateSystem`, `MapLayer`, `LayerType`, `LayerVisibility`, `TileSize`                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| `infra`       | `Region.yaml`             | `Region { id*, region* }` — generated, **never used**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| `infra`       | `Restriction.yaml`        | `Restriction`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `infra`       | `RestrictionData.yaml`    | `RestrictionData`, `RestrictionGroup`, `RestrictionImpact*`, `EdgePath`, `EdgeWithOffsets`, plus a **duplicate** `InfraMicroscopicEdgeData` definition                                                                                                                                                                                                                                                                                                                                                                                                          |
| `infra`       | `RestrictionTypes.yaml`   | `RestrictionState`, `RestrictionImpactAdhesionLevel`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `infra`       | `TrackCoordinates.yaml`   | `TrackCoordinates`, `NodeCoordinates`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| `infra`       | `TrainPosition.yaml`      | `TrainPosition`, `RunningType`, `ActivityType`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `meta`        | `MetaData.yaml`           | `MetaData { ui }`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `meta`        | `MetaUIData.yaml`         | `MetaUIData { icon, style }`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |

Generated-but-unused models: `Activity`, `Region`, `LocationDataTile` (no controller, service or
repository references them).

---

# 8 — DATABASE → BACKEND CONTRACTS

The persistence model in this system is **unusually flat**: the Mongo entity classes literally
_extend_ the generated API model, so **DB field name ≡ entity field name ≡ DTO field name ≡ JSON
field name** for every collection. There is no `@Field` remapping and no separate DTO layer.

```
MongoDB document
   → Mongo<X>Entity          (extends <X>, adds @Document(collection="${…}"))
   → Mongo<X>Repository      (Spring Data)
   → Mongo<X>RepositoryCustomImpl  (adapter → pure interface type <X>)
   → <X>Repository           (pure interface, returns <X> / Page<X>)
   → <X>Service              (pagination, sort, domain rules)
   → APIPaginatedResponse<X> | APIResponse<X>
   → <X>Controller           (ResponseEntity)
   → Jackson (@JsonInclude NON_NULL)
   → JSON
```

The only place a _real_ transformation happens is:

1. **Wrapping** — `Page<T>` → `Meta` (`APIMapper.mapPageToMetaPage`).
2. **Aggregation projection** — `TrackCoordinates` documents → `LocationWithTracks` view objects.
3. **Ingest-time mapping** — RISE DTO → RIVM model (that is §11, not §8).

## 8.1 `BusinessClock`

| DB field           | Type in Mongo | Entity field                 | DTO field | JSON field         | Transformation                          | Default | Nullable        |
| ------------------ | ------------- | ---------------------------- | --------- | ------------------ | --------------------------------------- | ------- | --------------- |
| `businessTime`     | String        | `BusinessClock.businessTime` | same      | `businessTime`     | none                                    | —       | schema-required |
| `businessTimeZone` | String        | `businessTimeZone`           | same      | `businessTimeZone` | none                                    | —       | required        |
| `serverTime`       | String        | `serverTime`                 | same      | `serverTime`       | none                                    | —       | required        |
| `mode`             | String        | `ModeEnum`                   | same      | `mode`             | Jackson enum ↔ string                   | —       | required        |
| `_id`              | ObjectId      | _(not modelled)_             | —         | **not emitted**    | dropped (no `id` property on the model) | auto    | —               |

Flow: `infra-rivm.business-clock` → `MongoBusinessClockEntity` → `MongoBusinessClockRepository.findAll()`
→ `MongoBusinessClockRepositoryCustomImpl.findAll()` (`new ArrayList<>(entities)`)
→ `BusinessClockService.getBusinessClock()` (`get(0)` or throw)
→ `new APIResponse<>(businessClock)` → `{"data":{…}}`.

## 8.2 `BaseGraph`

| DB path                                                        | Entity/DTO/JSON path | Transformation                                                                                                                                         |
| -------------------------------------------------------------- | -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `_id`                                                          | `id`                 | Spring Data maps `_id` ↔ the `@Id`-less `id` property by convention (the generated model's `id` is treated as the identifier because it is named `id`) |
| `baseGraph.nodes[]`                                            | `baseGraph.nodes[]`  | identical                                                                                                                                              |
| `baseGraph.nodes[].nodeData.coordinates.graphical.x/y`         | same                 | identical (`int32`)                                                                                                                                    |
| `baseGraph.nodes[].nodeData.infraNodeAddress.kmRegion/kmValue` | same                 | identical                                                                                                                                              |
| `baseGraph.edges[].edgeData.infraNodeRefs[]`                   | same                 | stored as an array; typed as `Set` in Java                                                                                                             |
| `baseGraph.edges[].edgeData.edgeLengthMillimeters`             | same                 | `int32`                                                                                                                                                |
| `baseGraph.edges[].edgeData.direction`                         | same                 | enum ↔ string                                                                                                                                          |

`MongoBaseGraphRepositoryCustomImpl.findAll(Pageable)` returns `new PageImpl<>(content, pageable,
entityPage.getTotalElements())`. `BaseGraphService` then wraps it.

**Frontend field names are identical**, but the SPA renames locally:

```
API  baseGraph.nodes[].baseSubEntityData.id           → InfraNode.id
API  baseGraph.nodes[].nodeData.coordinates.graphical.x → InfraNode.x
API  baseGraph.nodes[].nodeData.coordinates.graphical.y → InfraNode.y
API  baseGraph.nodes[].nodeData.infraNodeAddress.kmValueMillimeters → InfraNode.kmValue   ⚠ always undefined
API  <region>.id                                       → InfraNode.region
API  baseGraph.edges[].edgeData.infraNodeRefs[0]…subEntityID → EdgeRecord.a
API  baseGraph.edges[].edgeData.infraNodeRefs[1]…subEntityID → EdgeRecord.b
API  baseGraph.edges[].edgeData.edgeLengthMillimeters   → EdgeRecord.length
```

## 8.3 `TrackCoordinates` → `LocationWithTracks` (the one real projection)

| Source (`infra-rivm.track-coordinates`) | Target (`LocationWithTracks`)  | Transformation                                         |
| --------------------------------------- | ------------------------------ | ------------------------------------------------------ |
| `locationSubEntityData.id`              | `LocationWithTracks.id`        | aggregation `$group` key                               |
| `locationSubEntityData.name`            | `LocationWithTracks.name`      | taken from `trackCoordinates.get(0)`                   |
| `locationSubEntityData.shortName`       | `LocationWithTracks.shortName` | taken from `trackCoordinates.get(0)`                   |
| _(document set)_                        | `LocationWithTracks.tracks[]`  | grouped in Java, **sorted by `trackSubEntityData.id`** |
| `trackSubEntityData.id`                 | `tracks[].id`                  | verbatim                                               |
| `trackSubEntityData.name`               | `tracks[].name`                | verbatim                                               |
| `trackSubEntityData.shortName`          | `tracks[].shortName`           | verbatim                                               |
| `trackSubEntityData.description`        | `tracks[].description`         | verbatim                                               |
| `trackSubEntityData.businessRefs`       | `tracks[].businessRefs`        | verbatim                                               |
| `nodeCoordinates[]`                     | `tracks[].nodeCoordinates[]`   | verbatim                                               |
| `_id` (`{locationId}_{trackId}`)        | **dropped**                    | not projected                                          |

Guards: documents where `locationSubEntityData == null` are filtered out before grouping; a group
that resolves to an empty track list yields `null` and is removed by `.filter(l -> l != null)`.

Frontend rename: none — `LocationWithTracks` / `LocationTrackWithCoordinates` mirror the API.

## 8.4 `TrainPosition`

| DB field               | Type     | Entity/DTO/JSON             | Transformation                           | Nullable        |
| ---------------------- | -------- | --------------------------- | ---------------------------------------- | --------------- |
| `_id`                  | String   | `id`                        | identity `{trainServiceId}-{activityId}` | never null      |
| `trainServiceId`       | String   | `trainServiceId`            | none                                     | never null      |
| `activityId`           | String   | `activityId`                | none                                     | never null      |
| `activityType`         | String   | `ActivityTypeEnum`          | enum ↔ string                            | never null      |
| `dataTileIds`          | String[] | `List<String>`              | none                                     | may be empty    |
| `fromTime`             | String   | `fromTime`                  | none                                     | never null      |
| `toTime`               | String   | `toTime`                    | none                                     | never null      |
| `runningType`          | String   | `RunningTypeEnum`           | enum ↔ string                            | never null      |
| `origin`               | String   | `origin`                    | none                                     | **may be null** |
| `destination`          | String   | `destination`               | none                                     | **may be null** |
| `coordinates.x` / `.y` | int      | `InfraGraphicalCoordinates` | none                                     | never null      |

Because of `@JsonInclude(NON_NULL)`, a `null` `origin`/`destination` **disappears from the JSON**,
and the TypeScript model declares them optional (`origin?`, `destination?`) accordingly.

Frontend rename: none. Fields present in the TS model but absent from the API
(`direction`, `length`, `weight`, `maxSpeed`, `hasDangerousGoods`) are always `undefined`.

## 8.5 `DataTile`

| DB        | Entity/DTO/JSON | Transformation                         |
| --------- | --------------- | -------------------------------------- |
| `_id`     | `id`            | identity, `{x}_{y}_{yyyy-MM-ddTHH:mm}` |
| `version` | `version`       | random UUID v4 string per write        |

In the response, `DataTile` never appears as an object — it is **flattened into
`meta.dataTileVersions[0]` as a `{ tileId: version }` map** by
`APIMapper.mapPageToMetaPage(page, dataTileVersions)`.

Frontend: `TileVersion { id, version? }` — reconstructed from that map inside
`TrainPositionStore.startPolling`.

## 8.6 `Restriction`

| DB path                                                                 | JSON path | Transformation               | Notes                                                       |
| ----------------------------------------------------------------------- | --------- | ---------------------------- | ----------------------------------------------------------- |
| `_id`                                                                   | `id`      | identity                     | Frontend accepts `id ?? _id`                                |
| `name`, `shortName`, `description`                                      | same      | none                         |                                                             |
| `lastModified`                                                          | same      | none                         | **String**, produced at ingest by `String.valueOf(Instant)` |
| `restrictionData.state`                                                 | same      | enum ↔ string                |                                                             |
| `restrictionData.effectiveTimePeriod.startTime/endTime`                 | same      | none                         | **String** ISO-8601, produced by `Instant.toString()`       |
| `restrictionData.group.id`                                              | same      | none                         |                                                             |
| `restrictionData.impacts[]`                                             | same      | none                         |                                                             |
| `restrictionData.edgePaths[].pathEdges[].startPercentage/endPercentage` | same      | `BigDecimal` scale 2 HALF_UP | serialised as a JSON number, e.g. `0.25`                    |
| `restrictionData.edgePaths[].pathCoordinates[]`                         | same      | none                         |                                                             |
| `restrictionData.meta.ui.icon.{type,payload}`                           | same      | none                         | Base64 SVG                                                  |
| `restrictionData.meta.ui.style.{type,payload}`                          | same      | none                         | Base64 CSS                                                  |
| `_class`                                                                | `_class`  | Spring Data type hint        | Frontend model tolerates it (`_class?: string`)             |

Frontend renames: `PathEdgeRef`, `PathCoordinate`, `Payload`, `UI` are TypeScript-local names for
the same JSON shapes.

## 8.7 `MapConfig`

Straight-through: `_id` → `id`; every other field name is identical from Mongo to JSON to the
TypeScript `MapConfig` / `MapLayer` / `TileSize` interfaces.

## 8.8 Field-name transformations across the whole system

The interesting renames all happen at **ingest** (RISE DTO → RIVM model), not at read time:

| RISE DTO field                                                                            | RIVM model field                                          | Where                                                         |
| ----------------------------------------------------------------------------------------- | --------------------------------------------------------- | ------------------------------------------------------------- |
| `businessClockData.systemTime`                                                            | `BusinessClock.serverTime`                                | `businessclock…RiseToInfraMapper.map`                         |
| `nodeData.infraAddress`                                                                   | `nodeData.infraNodeAddress`                               | `basegraph…BaseGraphMapper.mapNodeData`                       |
| `infraAddress.kmValueMillimeters`                                                         | `infraNodeAddress.kmValue`                                | `basegraph…BaseGraphMapper.mapNodeAddress`                    |
| `edgeData.infraNodeRefs` (`List`)                                                         | `edgeData.infraNodeRefs` (`LinkedHashSet`)                | `basegraph…BaseGraphMapper.mapEdgeData`                       |
| `edgeData.edgeLengthMillimeters` (`Long`)                                                 | same (`int`)                                              | `basegraph…BaseGraphMapper.mapEdgeData` (`intValue()`)        |
| `nodeRef.infraMicroscopicRegionRef`                                                       | **dropped**                                               | `basegraph…BaseGraphMapper.mapNodeRef`                        |
| `location.baseSubEntityData` + `track.baseSubEntityData`                                  | `TrackCoordinates.id = "{loc}_{track}"`                   | `micro…RiseToInfraMapper.toTrackCoordinates`                  |
| `track.trackData.subGraph.nodeRefs`                                                       | `TrackCoordinates.nodeCoordinates[]`                      | `micro…RiseToInfraMapper.toNodes`                             |
| `restrictionData.segments`                                                                | `restrictionData.edgePaths`                               | `RestrictionMapper.mapEdgePaths` (**via `rise-infra-utils`**) |
| `baseEntityData.lastModified` (`Instant`)                                                 | `Restriction.lastModified` (`String`)                     | `RestrictionMapper.mapEventToRestriction`                     |
| `effectiveTimePeriod.startTime/endTime` (`Instant`)                                       | same (`String`)                                           | `RestrictionMapper.mapEffectiveTimePeriod`                    |
| `activity.baseSubEntityData.id`                                                           | `TrainPosition.activityId` and part of `TrainPosition.id` | `TrainOperationUtil.createBaseTrainPosition`                  |
| `activity.baseActivityData.actualEndTime` \| `plannedTime.planned` \| `forecastedEndTime` | `TrainPosition.fromTime`                                  | `TrainOperationUtil.setTimeWindows`                           |
| _next_ activity's time (or `+10 min`)                                                     | `TrainPosition.toTime`                                    | `TrainOperationUtil.setTimeWindows`                           |
| `place.infraEntityRef.entityID`                                                           | `TrainPosition.origin` / `.destination`                   | `RiseToInfraMapper.extractOriginId/extractDestinationId`      |
| derived from `ActivityContext.activityType`                                               | `TrainPosition.activityType`                              | `TrainPosition.ActivityTypeEnum.fromValue`                    |
| derived from `hasActualTime`                                                              | `TrainPosition.runningType`                               | `TrainOperationUtil.createTrainPosition`                      |

Frontend-side renames:

```
API  meta.page.pageNumber/size/totalElements/totalPages → Page / ApiResponseMeta (same names)
API  meta.dataTileVersions[0]                            → TileVersion[] (id/version pairs)
API  baseGraph.nodes[]                                   → InfraNode[]  (id, x, y, region, raw)
API  baseGraph.edges[]                                   → EdgeRecord[] (id, a, b, raw, length)
API  restriction.restrictionData.edgePaths[].pathCoordinates[] → [number, number][]  (tuple form)
```

---

# 9 — BACKEND → FRONTEND CONTRACTS

Each contract below is given as `REQUEST → BACKEND → RESPONSE → FRONTEND` with a per-field table.

---

## 9.1 Business clock

```
REQUEST
GET /api/infra/query/business-clock
(no params, no body, no headers)

BACKEND
BusinessClockController.getBusinessClock()
  → BusinessClockService.getBusinessClock()
    → BusinessClockRepository.findAll()
      → MongoBusinessClockRepositoryCustomImpl → MongoBusinessClockRepository
        → infra-rivm.business-clock
  → new APIResponse<>(businessClock)

RESPONSE  200
{ "data": { "businessTime": "2026-08-31T09:15:00Z",
            "businessTimeZone": "Europe/London",
            "serverTime": "2026-08-31T09:15:00.123Z",
            "mode": "REALTIME" } }

RESPONSE  404
{ "errors": [ { "code": "404", "message": "No clock data found" } ] }

FRONTEND
BusinessClockApiService.getBusinessClockApiData()
  → map(r => r.body?.data as BusinessClockApiResults)
  → BusinessClockEffects → loadBusinessClockDataSuccess({businessClock})
  → businessClockReducer (+ computed timeWindow)
  → selectEffectiveClock
  → MasterLayoutComponent.currentDateTime (header), InfraContentComponent.baseBusinessTime,
    MfeViewRestrictionListComponent.businessClockTime/Timezone, MfeViewTrainListComponent.operatingDay
```

| Field                   | Type                     | Req. | Meaning        | Source                                | Transformation                                | Consumer                                                                |
| ----------------------- | ------------------------ | ---- | -------------- | ------------------------------------- | --------------------------------------------- | ----------------------------------------------------------------------- |
| `data.businessTime`     | string ISO-8601 Z        | ✔    | Platform "now" | RISE `businessClockData.businessTime` | `SimpleDateFormat("…'T'HH:mm:ss'Z'")` UTC     | Header clock, tile timestamps, restriction `effectiveAt`, operating day |
| `data.businessTimeZone` | IANA TZ id               | ✔    | Display zone   | RISE `businessTimeZone`               | verbatim                                      | `moment.tz(...)` everywhere                                             |
| `data.serverTime`       | string ISO-8601 millis Z | ✔    | Real clock     | RISE `systemTime`                     | `SimpleDateFormat("…'T'HH:mm:ss.SSS'Z'")` UTC | Stored in state, **not rendered**                                       |
| `data.mode`             | `REALTIME`\|`CONTROLLED` | ✔    | Clock mode     | RISE `mode.value`                     | `ModeEnum.fromValue`                          | Stored in state, **not rendered**                                       |

---

## 9.2 Map configuration

```
REQUEST   GET /api/infra/query/configs
BACKEND   ConfigController → ConfigService → MapConfigRepository.findAll() → infra-rivm.map-config
RESPONSE  200 { "data": [ MapConfig, … ] }   |   404 { "errors":[{ "code":"404",
                                                    "message":"No map configuration data found"}]}
FRONTEND  MapConfigService (IndexedDB, key cleared on construction) → MapConfigStore.mapConfig
```

| Field                                         | Type                                       | Req.                           | Meaning                          | Consumer                                                                                                                   |
| --------------------------------------------- | ------------------------------------------ | ------------------------------ | -------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `id`                                          | string                                     | ✔                              | Config identity (`INFRA_MAP_01`) | `MapConfigStore.getMapConfigById`                                                                                          |
| `mapType`                                     | `OCTOLINEAR`\|`GEOGRAPHIC`\|`SCHEMATIC`    | ✔                              | Rendering flavour                | **Backend** `MapConfigService` filters for `OCTOLINEAR`; frontend ignores it                                               |
| `mapName`                                     | string                                     | ✔                              | Human label                      | not rendered                                                                                                               |
| `coordinateSystem`                            | `CARTESIAN`\|`GEOGRAPHIC`                  | ✔                              | Coordinate space                 | not read by code                                                                                                           |
| `minZoomLevel`/`maxZoomLevel`/`defaultZoom`   | int                                        | ✔                              | Map-level zoom bounds            | **not read** — the SPA uses `INFRA_ZOOM_CONFIG` instead                                                                    |
| `layers[].id`                                 | string                                     | ✔                              | Layer key                        | `find(l => l.id === 'baseGraph'\|'trains'\|'restrictions'\|'locations'\|'platforms')`                                      |
| `layers[].layerDataType`                      | string                                     | ✔                              | Data kind                        | Backend train-layer lookup; `MfeViewRestrictionListComponent` fallback match `'restriction'`                               |
| `layers[].layerType`                          | `EDGE_OBJECT`\|`TIMED_SINGLE_POINT_OBJECT` | ✔                              | Geometry kind                    | not read                                                                                                                   |
| `layers[].layerName`                          | string                                     | ✔                              | Label                            | not read                                                                                                                   |
| `layers[].zindex`                             | int                                        | ✔                              | Stacking                         | `setInfraLayerZIndex`, label layer z-indices                                                                               |
| `layers[].minZoom`                            | int                                        | ✔                              | Visibility floor                 | `selectedZoomLevel` (trains), `restrictionsMinZoom`, label layer `minZoom`                                                 |
| `layers[].maxZoom`                            | int                                        | ✔                              | Visibility ceiling               | label layer `maxZoom`                                                                                                      |
| `layers[].defaultVisibility`                  | `SHOW`\|`HIDE`                             | ✔                              | Initial visibility               | **not read** — `FilterStateStore` defaults to all-visible                                                                  |
| `layers[].updateFrequencySecs`                | int                                        | ✔                              | Poll period                      | `trainPositionStore.setPollingInterval()`, `restrictionsStore.setPollingInterval()`, restriction MFE `pollingIntervalSecs` |
| `layers[].tileSize.width/height/timeSpanSecs` | int                                        | — (required inside `TileSize`) | Tile grid                        | `TileManagementService`, `TimeCalculationService`, backend `DataTileService`                                               |

---

## 9.3 Base graph

```
REQUEST   GET /api/infra/query/basegraph?pageNumber=0&pageSize=1000
BACKEND   BaseGraphController → BaseGraphService → BaseGraphRepository.findAll(PageRequest)
RESPONSE  200 { data: BaseGraph[], meta: { page, dataTileVersions: [] } }
FRONTEND  BaseGraphApiService.getEdgeData()  (IndexedDB 'infra_basegraph_cache', TTL 1 h)
          → map(r => Array.isArray(r.data) ? r.data : [])
          → EdgeDataEffects → edgeData slice → InfraContentComponent.loadGraphData
```

| Field                                                            | Type           | Req. | Meaning             | Consumer                                                                                                     |
| ---------------------------------------------------------------- | -------------- | ---- | ------------------- | ------------------------------------------------------------------------------------------------------------ |
| `data[].id`                                                      | string         | ✔    | Region id           | `InfraNode.region`                                                                                           |
| `data[].baseGraph.nodes[].baseSubEntityData.id`                  | string         | ✔    | Node id             | `InfraNode.id`, edge endpoint lookup, node text label                                                        |
| `…nodeData.coordinates.graphical.x` / `.y`                       | int32          | ✔    | Drawing position    | `Point([x, y])`                                                                                              |
| `…nodeData.infraNodeAddress.kmRegion` / `kmValue`                | string / int64 | —    | Km address          | carried in `InfraNode.address` / `.raw`; **`kmValue` is not read** (frontend looks for `kmValueMillimeters`) |
| `data[].baseGraph.edges[].baseSubEntityData.id`                  | string         | ✔    | Edge id             | `EdgeRecord.id`                                                                                              |
| `…edgeData.infraNodeRefs[0].infraMicroscopicNodeRef.subEntityID` | string         | ✔    | Start node          | `EdgeRecord.a`                                                                                               |
| `…edgeData.infraNodeRefs[1].infraMicroscopicNodeRef.subEntityID` | string         | ✔    | End node            | `EdgeRecord.b`                                                                                               |
| `…edgeData.edgeLengthMillimeters`                                | int            | —    | Length              | `EdgeRecord.length` (stored, not rendered)                                                                   |
| `…edgeData.direction`                                            | enum           | —    | Traversal direction | in `.raw` only, **not rendered**                                                                             |
| `meta.page.*`                                                    | int            | ✔    | Pagination          | **not read by the SPA** (it requests one big page)                                                           |

---

## 9.4 Location track coordinates

```
REQUEST   GET /api/infra/query/location-track-coordinates?pageNumber=n&pageSize=100
BACKEND   LocationTrackCoordinatesController → LocationTrackCoordinatesService
          → TrackCoordinatesRepository.findLocationsWithTracks(PageRequest.of(n,100,asc id nullsLast))
RESPONSE  200 { data: LocationWithTracks[], meta: { page } }
FRONTEND  LocationTrackCoordinatesApiService.getLocationTrackCoordinates()
          → fetchPage(0) → read meta.page.totalPages → concatMap over 1..totalPages-1
          → reduce into one array → cache in IndexedDB → LocationsStore.locations
          → MapService.loadLocationLabels(...)
```

| Field                                    | Type     | Req. | Meaning          | Consumer                                   |
| ---------------------------------------- | -------- | ---- | ---------------- | ------------------------------------------ |
| `data[].id`                              | string   | ✔    | Location id      | feature property `locationId`              |
| `data[].name`                            | string   | ✔    | Station name     | **location label text**                    |
| `data[].shortName`                       | string   | ✔    | Station code     | not rendered on the map                    |
| `data[].tracks[].id`                     | string   | ✔    | Track id         | feature property `trackId`; label fallback |
| `data[].tracks[].name`                   | string   | —    | Track name       | label fallback #2                          |
| `data[].tracks[].shortName`              | string   | —    | Track short name | **track label text (first choice)**        |
| `data[].tracks[].description`            | string   | —    | Description      | not rendered                               |
| `data[].tracks[].businessRefs[]`         | object[] | —    | External refs    | not rendered                               |
| `data[].tracks[].nodeCoordinates[].x/.y` | int      | ✔    | Geometry         | bounding-box centre for both labels        |
| `meta.page.totalPages`                   | int      | ✔    | Page count       | **drives the sequential fetch loop**       |

---

## 9.5 Train positions

```
REQUEST
POST /api/infra/query/trainpositions?pageNumber=0&pageSize=1000
Content-Type: application/json
[ { "id": "125000_-10000_2026-08-31T09:15" },
  { "id": "125000_-5000_2026-08-31T09:15", "version": "0f0b1f4e-…" } ]

BACKEND
TrainPositionController.getPositions
  → TrainPositionService.getModifiedTrainPositionsByTiles
      validateDataTiles
      DataTileRepository.findAllById            (infra-rivm.data-tile)
      filter hasTileVersionChanged
      [if any changed] TrainPositionRepository.findByDataTileIdsIn
                       (infra-rivm.train-position, sort id,trainServiceId ASC)
      APIMapper.mapPageToMetaPage(page, updatedTileVersions)

RESPONSE 200
{ "data": [ TrainPosition… ],
  "meta": { "page": {...}, "dataTileVersions": [ { "<tileId>": "<uuid>" } ] } }

FRONTEND
TrainPositionService.getTrainPositions(tiles)
  → TrainPositionStore (merge positions by id; update tile versions from meta)
  → InfraContentComponent.updateTrainDisplay()
      TimeCalculationService.filterPositionsByTime(positions, adjustedTimestamp)
  → MapService.updateTrainPositions(filtered)
  → OpenLayerClusterUtility.createTrainPositionFeatures
```

Request fields:

| Field         | Type   | Required                                         | Meaning                              |
| ------------- | ------ | ------------------------------------------------ | ------------------------------------ |
| `[].id`       | string | ✔ (`@NotEmpty` list + `validateDataTiles`)       | Tile id `{x}_{y}_{yyyy-MM-ddTHH:mm}` |
| `[].version`  | string | optional — **omitted entirely on first request** | Last known tile version              |
| `?pageNumber` | int    | optional, default 0                              |                                      |
| `?pageSize`   | int    | optional, default 1000, max 1000                 |                                      |

Response fields:

| Field                      | Type                  | Req.                       | Meaning                               | Source                                           | Consumer                                                                  |
| -------------------------- | --------------------- | -------------------------- | ------------------------------------- | ------------------------------------------------ | ------------------------------------------------------------------------- |
| `data[].id`                | string                | ✔                          | `{trainServiceId}-{activityId}`       | `TrainOperationUtil`                             | store merge key; feature `id`                                             |
| `data[].trainServiceId`    | string                | ✔                          | Train identity                        | `baseEntityEvent.entityID` / `trainOperationRef` | colour, label, selection, popover title, `filterPositionsByTime` grouping |
| `data[].activityId`        | string                | ✔                          | Source activity                       | `activity.baseSubEntityData.id`                  | feature property only                                                     |
| `data[].activityType`      | enum                  | ✔                          | ARRIVAL/DEPARTURE/MOVEMENT/RUNTHROUGH | derived                                          | **not rendered**                                                          |
| `data[].dataTileIds[]`     | string[]              | ✔                          | Owning tiles                          | `DataTileService.createTileIds`                  | `getPositionsByTileId` computed (unused in templates)                     |
| `data[].fromTime`          | ISO Z                 | ✔                          | Valid from                            | activity time                                    | `filterPositionsByTime`                                                   |
| `data[].toTime`            | ISO Z                 | ✔                          | Valid until                           | next activity time or `+10 min`                  | `filterPositionsByTime`; popover "Departure time"                         |
| `data[].runningType`       | `ACTUAL`\|`FORECAST`  | ✔                          | Confirmed vs predicted                | `hasActualTime`                                  | feature property; **no visual difference today**                          |
| `data[].origin`            | string                | ✔ in schema, may be absent | Origin location id                    | first ARR/DEP `LocationReference`                | popover subtitle                                                          |
| `data[].destination`       | string                | ✔ in schema, may be absent | Destination location id               | last ARR/DEP `LocationReference`                 | popover subtitle                                                          |
| `data[].coordinates.x/.y`  | int                   | ✔                          | Position                              | track cache or `MicroscopicInfra.findEdges`      | `Point([x,y])`                                                            |
| `meta.page.*`              | int                   | ✔                          | Pagination                            | Spring `Page`                                    | not read                                                                  |
| `meta.dataTileVersions[0]` | `{[tileId]: version}` | ✔                          | New versions                          | `updatedTileVersions`                            | tile version bookkeeping                                                  |

---

## 9.6 Restrictions

```
REQUEST   GET /api/infra/query/restrictions?effectiveAt=2026-08-31T09:15:00Z&pageNumber=0&pageSize=100
BACKEND   RestrictionController → RestrictionService (Sort DESC lastModified)
          → MongoRestrictionRepository.findByEffectiveTime  (string $lte/$gte)
RESPONSE  200 { data: Restriction[], meta: { page, dataTileVersions } }
FRONTEND  RestrictionApiService.getRestrictionData → normalizeApiResponse
          → RestrictionsStore.restrictions
          → visibleRestrictionInfos (computed) → MapService.updateRestrictions
```

| Field                                                                | Type                              | Req. | Meaning             | Consumer                                                                                                           |
| -------------------------------------------------------------------- | --------------------------------- | ---- | ------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `data[].id` (or `_id`)                                               | string                            | ✔    | Identity            | `getRestrictionId()`; feature `restrictionId`; hover key; popover `ID`; icon registry name                         |
| `data[].name`                                                        | string                            | —    | Display name        | feature `restrictionName`; popover header/`Name of Restriction`                                                    |
| `data[].shortName`                                                   | string                            | —    | Short name          | popover fallback                                                                                                   |
| `data[].description`                                                 | string                            | —    | Description         | `getRestrictionDisplayInfo` only                                                                                   |
| `data[].lastModified`                                                | ISO string                        | —    | Last change         | **backend sort key**; not rendered                                                                                 |
| `…restrictionData.state`                                             | `ACTIVE`\|`INACTIVE`\|`CANCELLED` | ✔    | State               | `isRestrictionActive()` compares against `'EFFECTIVE'` (⚠ §4.9); ribbon enablement via `ACTIVE_RESTRICTION_STATES` |
| `…effectiveTimePeriod.startTime`/`endTime`                           | ISO string                        | ✔    | Validity            | popover `From`/`To`; **backend filter**                                                                            |
| `…group.id`                                                          | string                            | —    | Grouping            | not rendered                                                                                                       |
| `…impacts[]`                                                         | object[]                          | ✔    | Impact set          | popover `Impact Type` = unique camelCase keys, Title-Cased                                                         |
| `…impacts[].blocking`                                                | object                            | —    | Full block          | key presence only                                                                                                  |
| `…impacts[].speedReduction.absoluteMaxSpeedMillimetersPerHour`       | int                               | —    | Speed cap           | key presence only                                                                                                  |
| `…impacts[].speedReduction.relativeSpeedReductionMillimetersPerHour` | int                               | —    | Speed cut           | key presence only                                                                                                  |
| `…impacts[].adhesion.adhesionLevel`                                  | enum                              | —    | Adhesion            | key presence only                                                                                                  |
| `…impacts[].trainFilter.*`                                           | PropertyFilter                    | —    | Affected trains     | **not evaluated by the SPA**                                                                                       |
| `…edgePaths[].pathCoordinates[].x/.y`                                | int                               | ✔    | Geometry            | `LineString` per path (needs ≥ 2 points)                                                                           |
| `…edgePaths[].pathEdges[]`                                           | object[]                          | ✔    | Edge refs + offsets | normalised to `[]`; **not rendered**                                                                               |
| `…meta.ui.icon.{type,payload}`                                       | string                            | —    | Base64 SVG          | composite marker; `MatIconRegistry` literal for the popover                                                        |
| `…meta.ui.style.{type,payload}`                                      | string                            | —    | Base64 CSS          | colour extraction fallback (`/color:\s*([^;"'}\s]+)/i`)                                                            |

---

## 9.7 Error contract (all endpoints)

```
{ "errors": [ { "code": "<string>", "message": "<exception message>" } ] }
```

| HTTP | `code`    | Raised by                                                             |
| ---- | --------- | --------------------------------------------------------------------- |
| 400  | `"400"`   | `ConstraintViolationException`, `IllegalArgumentException`            |
| 400  | `"20001"` | `BadRequestException` from `TrainPositionService.validateDataTiles`   |
| 404  | `"404"`   | `ResourceNotFoundException` (`BusinessClockService`, `ConfigService`) |
| 500  | `"500"`   | any other `Exception`                                                 |

**The frontend never parses this envelope.** Every consumer either uses `error.message` from the
`HttpErrorResponse` or silently swallows the failure.

---

# 10 — RABBITMQ — COMPLETE ANALYSIS

> **Scope caveat, stated up front:** this repository contains **no `@RabbitListener`, no
> `RabbitTemplate`, no `Queue`/`Exchange`/`Binding` `@Bean`, no `spring.rabbitmq.listener.*`
> property and no publisher.** All broker interaction is performed by the external library
> **`de.hacon.tps.rise:rise-api-utils:13.1.0`**, which the ETLs pull in and configure purely through
> `application.properties` + `META-INF/spring.factories`.
> Facts below are therefore drawn from: (a) the properties, (b) the `spring.factories` files,
> (c) the `infra-business-clock-etl/README.md` instructions, (d) the E2E harness
> (`module-tests/config/rabbitmq.config.js`, `module-tests/playwright/plugins/rabbitmq.js`).
> Anything that lives inside `rise-api-utils` is marked **NOT DETERMINED**.

## 10.1 Exchanges

| Exchange          | Type      | Durable  | Evidence                                                                                                                                                                                                                                                                              |
| ----------------- | --------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`rise.events`** | **topic** | **true** | `module-tests/config/rabbitmq.config.js` → `exchanges: { riseEvents: 'rise.events', events: 'rise.events' }`; `module-tests/playwright/plugins/rabbitmq.js` → `assertExchange(exchange, 'topic', { durable: true })`; `infra-business-clock-etl/README.md` → `--exchange rise.events` |

No other exchange is referenced anywhere. Dead-letter or retry exchanges: **NOT FOUND**.

## 10.2 Queues (all configured in this repository)

| Queue name                                                         | Property                                                            | Service                                                    |
| ------------------------------------------------------------------ | ------------------------------------------------------------------- | ---------------------------------------------------------- |
| `de.hacon.tps.rise.client.businessclock.event.consumer`            | `rise.api.utils.event_handling.business_clock.queue_name`           | `infra-business-clock-etl`                                 |
| `de.hacon.tps.rise.client.inframicro.event.consumer`               | `rise.api.utils.event-handling.infra.microscopic-region.queue-name` | `infra-micro-etl`                                          |
| `de.hacon.tps.rise.client.infrabasegraph.event.consumer`           | `rise.api.utils.event-handling.infra.microscopic-region.queue-name` | `infra-basegraph-etl`                                      |
| `de.hacon.tps.rise.client.trainoperation.event.consumer`           | `rise.api.utils.event-handling.train-operation.queue-name`          | `infra-trainoperation-etl`                                 |
| `de.hacon.tps.rise.client.trainoperation.forecast.event.consumer`  | `rise.api.utils.event-handling.train-operation.forecast.queue-name` | `infra-trainoperation-etl`                                 |
| `de.hacon.tps.rise.client.infra.operational-period.event.consumer` | `rise.api.utils.event-handling.infra.operational-period.queue-name` | `infra-trainoperation-etl` **and** `infra-restriction-etl` |
| `de.hacon.tps.rise.client.infra.microscopic-region.event.consumer` | `rise.api.utils.event-handling.infra.microscopic-region.queue-name` | `infra-trainoperation-etl` **and** `infra-restriction-etl` |
| `de.hacon.tps.rise.client.restriction.event.consumer`              | `rise.api.utils.event-handling.restriction.queue-name`              | `infra-restriction-etl`                                    |

> **Two queue names are shared by two different services.** Because AMQP delivers each message on a
> queue to exactly one consumer, `infra-trainoperation-etl` and `infra-restriction-etl` **compete**
> for `…infra.operational-period.event.consumer` and `…infra.microscopic-region.event.consumer`.
> Each keeps its own private in-memory `MicroscopicInfra`, so in a deployment where both run, each
> receives roughly half of the infra events. Reported as an observation only.

**Queue declaration** (durability, exclusivity, arguments, `x-dead-letter-exchange`,
`x-message-ttl`, `x-max-length`, quorum vs classic): **NOT DETERMINED** — performed inside
`rise-api-utils`.

## 10.3 Routing keys

Known from the E2E harness (`module-tests/config/rabbitmq.config.js`):

| Logical event            | Routing key                             |
| ------------------------ | --------------------------------------- |
| Business clock           | `event.business_clock`                  |
| Infra location           | `event.infra.location`                  |
| Infra microscopic region | `event.infra.microscopic_region`        |
| Train operation          | `event.train_operation.train_operation` |
| Train operation forecast | `event.train_operation.forecast`        |
| Detection (AEM)          | `event.detection`                       |

**Not present in the harness and therefore NOT DETERMINED:**

- the routing key for **`RestrictionEvent`** (queue `…restriction.event.consumer` exists, key unknown);
- the routing key for **`InfraOperationalPeriodEvent`** (queue exists, key unknown).

`event.infra.location` and `event.detection` are published by the harness but **no ETL in this
repository consumes an `InfraLocationEvent`**; `event.detection` belongs to the AEM MFE backend.

## 10.4 Bindings

Bindings are **not declared in this repository**. From the queue/routing-key pairing, the required
topology is:

```
rise.events (topic)
 ├─ event.business_clock            → de.hacon.tps.rise.client.businessclock.event.consumer
 ├─ event.infra.microscopic_region  → de.hacon.tps.rise.client.inframicro.event.consumer
 ├─ event.infra.microscopic_region  → de.hacon.tps.rise.client.infrabasegraph.event.consumer
 ├─ event.infra.microscopic_region  → de.hacon.tps.rise.client.infra.microscopic-region.event.consumer
 ├─ <NOT DETERMINED>                → de.hacon.tps.rise.client.infra.operational-period.event.consumer
 ├─ event.train_operation.train_operation → de.hacon.tps.rise.client.trainoperation.event.consumer
 ├─ event.train_operation.forecast  → de.hacon.tps.rise.client.trainoperation.forecast.event.consumer
 └─ <NOT DETERMINED>                → de.hacon.tps.rise.client.restriction.event.consumer
```

Whether `rise-api-utils` declares these bindings itself, or whether they are provisioned by the
`rise-common` platform, is **NOT DETERMINED**.

## 10.5 Producers

**NONE in this repository.**
The only producer-shaped code is test tooling:

- `module-tests/playwright/plugins/rabbitmq.js` — `publishJson({url, exchange, routingKey, message, exchangeType='topic'})`
- `infra-business-clock-etl/README.md` — `python ./rise_send_signed_message.py --exchange rise.events --routing_key event.business_clock --message business-clock.json` (the script itself is **not in this repository**)

## 10.6 Consumers (message listeners)

| #   | Handler class                                                                                      | Implements (`rise-api-utils` interface)                                     | Event DTO                     | Delegates to                                                            |
| --- | -------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- | ----------------------------- | ----------------------------------------------------------------------- |
| 1   | `de.hacon.tps.rise.infra.businessclock.etl.eventhandling.BusinessClockEventHandler`                | `…eventhandling.businessclock.BusinessClockEventHandler`                    | `BusinessClockEvent`          | `BusinessClockService.setBusinessClock`                                 |
| 2   | `de.hacon.tps.rise.infra.micro.etl.eventhandling.InfraMicroEventHandler`                           | `…eventhandling.infra.microscopicregion.InfraMicroscopicRegionEventHandler` | `InfraMicroscopicRegionEvent` | `InfraMicroService.setInfraMicro`                                       |
| 3   | `de.hacon.tps.rise.infra.basegraph.etl.eventhandling.InfraBaseGraphEventHandler`                   | same interface                                                              | `InfraMicroscopicRegionEvent` | `InfraBaseGraphService.processBaseGraphEvent`                           |
| 4   | `de.hacon.tps.rise.infra.trainoperation.etl.eventhandling.InfraTrainOperationMovementEventHandler` | `…eventhandling.trainoperation.trainoperation.TrainOperationEventHandler`   | `TrainOperationEvent`         | `InfraTrainOperationService.processTrainOperationMovementEvent`         |
| 5   | `…trainoperation.etl.eventhandling.InfraTrainOperationMovementForecastEventHandler`                | `…eventhandling.trainoperation.forecast.TrainOperationForecastEventHandler` | `TrainOperationForecastEvent` | `InfraTrainOperationService.processTrainOperationMovementForecastEvent` |
| 6   | `…trainoperation.etl.eventhandling.InfraMicroscopicRegionEventHandler`                             | `…infra.microscopicregion.…`                                                | `InfraMicroscopicRegionEvent` | `MicroscopicInfraService.addMicroscopicRegion`                          |
| 7   | `…trainoperation.etl.eventhandling.InfraOperationalPeriodEventHandler`                             | `…infra.operationalperiod.InfraOperationalPeriodEventHandler`               | `InfraOperationalPeriodEvent` | `MicroscopicInfraService.init`                                          |
| 8   | `de.hacon.tps.rise.infra.restriction.eventhandling.RestrictionEventHandler`                        | `…eventhandling.restriction.restriction.RestrictionEventHandler`            | `RestrictionEvent`            | `RestrictionService.processRestrictionEvent`                            |
| 9   | `…restriction.eventhandling.InfraMicroscopicRegionEventHandler`                                    | `…infra.microscopicregion.…`                                                | `InfraMicroscopicRegionEvent` | `MicroscopicInfraService.addMicroscopicRegion`                          |
| 10  | `…restriction.eventhandling.InfraOperationalPeriodEventHandler`                                    | `…infra.operationalperiod.…`                                                | `InfraOperationalPeriodEvent` | `MicroscopicInfraService.init`                                          |

Every handler implements a **single method**:

```java
boolean handleValidatedMessage(<X>Event message)
```

The `Validated` in the name indicates that `rise-api-utils` has **already validated the message
signature and schema** before invoking the handler.

## 10.7 Handler registration

`META-INF/spring.factories` per module (Spring's classic factories mechanism, keyed by the
interface FQN):

```properties
# infra-business-clock-etl
de.hacon.tps.rise.api.utils.eventhandling.businessclock.BusinessClockEventHandler=\
  de.hacon.tps.rise.infra.businessclock.etl.eventhandling.BusinessClockEventHandler

# infra-micro-etl
de.hacon.tps.rise.api.utils.eventhandling.infra.microscopicregion.InfraMicroscopicRegionEventHandler=\
  de.hacon.tps.rise.infra.micro.etl.eventhandling.InfraMicroEventHandler

# infra-basegraph-etl
de.hacon.tps.rise.api.utils.eventhandling.infra.microscopicregion.InfraMicroscopicRegionEventHandler=\
  de.hacon.tps.rise.infra.basegraph.etl.eventhandling.InfraBaseGraphEventHandler

# infra-trainoperation-etl  (4 entries)
de.hacon.tps.rise.api.utils.eventhandling.trainoperation.trainoperation.TrainOperationEventHandler=…InfraTrainOperationMovementEventHandler
de.hacon.tps.rise.api.utils.eventhandling.trainoperation.forecast.TrainOperationForecastEventHandler=…InfraTrainOperationMovementForecastEventHandler
de.hacon.tps.rise.api.utils.eventhandling.infra.microscopicregion.InfraMicroscopicRegionEventHandler=…InfraMicroscopicRegionEventHandler
de.hacon.tps.rise.api.utils.eventhandling.infra.operationalperiod.InfraOperationalPeriodEventHandler=…InfraOperationalPeriodEventHandler

# infra-restriction-etl  (3 entries)
de.hacon.tps.rise.api.utils.eventhandling.restriction.restriction.RestrictionEventHandler=…RestrictionEventHandler
de.hacon.tps.rise.api.utils.eventhandling.infra.microscopicregion.InfraMicroscopicRegionEventHandler=…InfraMicroscopicRegionEventHandler
de.hacon.tps.rise.api.utils.eventhandling.infra.operationalperiod.InfraOperationalPeriodEventHandler=…InfraOperationalPeriodEventHandler
```

## 10.8 Serialization format

| Aspect                 | Value                                                                       | Evidence                                                                                                    |
| ---------------------- | --------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Body format            | **JSON**, UTF-8                                                             | `Buffer.from(JSON.stringify(message), 'utf-8')` in the harness; all fixtures are `.json`                    |
| `contentType` property | `application/json`                                                          | harness `publishJson`                                                                                       |
| Delivery mode          | `persistent: true`                                                          | harness                                                                                                     |
| `userId` property      | `guest`                                                                     | harness — `[SECRET / CREDENTIAL PRESENT — VALUE OMITTED]` (the value is a well-known default, not a secret) |
| Deserialization        | Jackson (Spring Boot `spring-boot-starter-json`) into `rise-api-utils` DTOs | `build.gradle.kts`                                                                                          |

## 10.9 Message headers

| Header      | Value                                              | Purpose                                                                                                | Evidence                                                                                                                                                                                                                                                   |
| ----------- | -------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `signature` | `sha256(JSON.stringify(message))` as lowercase hex | Integrity / authenticity check performed by `rise-api-utils` before `handleValidatedMessage` is called | `module-tests/playwright/plugins/rabbitmq.js` → `generateSignature()`; `RIVMMessageSignature` in `basic/RIVMTypes.yaml` describes exactly this ("A SHA256 hash of the message payload as hexadecimal string (will be extended to something secure later)") |

`RIVMErrorType.INVALID_SIGNATURE` and `MALFORMED_MESSAGE` (in `RIVMTypes.yaml`) confirm that
signature and schema validation failures are modelled error cases upstream.

Any other header (`x-death`, `x-retry-count`, correlation id, reply-to): **NOT DETERMINED**.

## 10.10 Acknowledgement, retry, DLQ, ordering

| Aspect                              | Finding                                                                                                                                                                                                                                                                                                                                                                                                                     |
| ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **ACK contract**                    | Every handler returns `boolean`. `true` on success, `false` on failure. The actual `basicAck` / `basicNack` / `basicReject` mapping lives in `rise-api-utils` — **NOT DETERMINED**.                                                                                                                                                                                                                                         |
| **Explicit ACK-without-processing** | `RestrictionEventHandler` returns **`true`** when `entityID` is null/blank, with the comment _"Return true to acknowledge the message without reprocessing"_ — a deliberate poison-message drop.                                                                                                                                                                                                                            |
| **Swallowed failures**              | `BusinessClockService.setBusinessClock`, `InfraMicroService.setInfraMicro`, `InfraBaseGraphService.processBaseGraphEvent` and `InfraTrainOperationService.processEventWithErrorHandling` **catch `Exception` internally and return normally**. Their handlers therefore return `true` even though nothing was persisted → **the message is ACKed and lost**.                                                                |
| **Propagated failures**             | `RestrictionService.processRestrictionEvent` **rethrows**, so `RestrictionEventHandler` catches it and returns `false`. Restriction is the only flow that can NACK.                                                                                                                                                                                                                                                         |
| **Retry policy**                    | **NOT DETERMINED** (no `spring.rabbitmq.listener.simple.retry.*` properties anywhere).                                                                                                                                                                                                                                                                                                                                      |
| **Dead-letter queue**               | **NOT FOUND** in this repository.                                                                                                                                                                                                                                                                                                                                                                                           |
| **Prefetch / concurrency**          | **NOT DETERMINED**.                                                                                                                                                                                                                                                                                                                                                                                                         |
| **Ordering assumptions**            | Two are visible in the code: (1) `InfraTrainOperationService` assumes ACTUAL data for a train may arrive _before or after_ the forecast and compensates with `actualFrontier` filtering + `extendLastActualToForecast`; (2) `MicroscopicInfraService.init(operationalPeriod)` is expected **before** `addMicroscopicRegion(region)` — nothing enforces it. `synchronized` on both methods serialises concurrent deliveries. |
| **Idempotency**                     | All writes are upserts keyed by a deterministic `_id`, so redelivery is safe — **except** `BusinessClockService` which does `deleteAll()` then `save()` non-transactionally.                                                                                                                                                                                                                                                |

## 10.11 Per-event documentation

### EVENT 1 — Business Clock

```
EVENT NAME:      BusinessClockEvent
Producer:        RISE business clock service (sourceService "business-clock" /
                 "de.hacon.tps.rids.business_clock")            [external]
Exchange:        rise.events (topic)
Routing key:     event.business_clock
Queue:           de.hacon.tps.rise.client.businessclock.event.consumer
Consumer:        infra-business-clock-etl → BusinessClockEventHandler
Message format:  JSON, header signature = sha256(body)
Trigger:         Clock tick or manual clock change upstream
Processing:      BusinessClockService.setBusinessClock
                   → RiseToInfraMapper.map(businessClockData)
                   → businessClockRepository.deleteAll()
                   → businessClockRepository.save(businessClock)
Database impact: infra-rivm.business-clock replaced (single document)
Other services:  none directly; every consumer of GET /business-clock is affected
Frontend impact: Header clock label, effective clock, restriction effectiveAt, tile timestamps,
                 operating day for the train-list MFE
Error/retry:     All exceptions caught inside the service and logged
                 ("Failed to convert and save message") → handler still returns true → ACK.
                 A crash between deleteAll() and save() leaves the collection empty → 404.
```

Sample payload (`infra-business-clock-etl/src/test/resources/BusinessClockEvent.json`):

```json
{
  "baseEvent": {
    "eventID": "2c3821b8-1cdb-4b77-bcd8-a1da701e46aa",
    "sourceService": "business-clock",
    "businessClockTime": "2023-12-12T07:59:56Z",
    "systemClockTime": "2023-12-12T07:59:56.123Z"
  },
  "baseEntityEvent": { "triggerType": "ENTITY_UPDATED" },
  "baseEntityData": {
    "lastModified": "2015-10-21T07:28:42.123Z",
    "shortName": "clock",
    "name": "clock"
  },
  "businessClockData": {
    "businessTime": "2024-10-10T10:00:00Z",
    "businessTimeZone": "Europe/Berlin",
    "systemTime": "2024-12-12T07:59:56.123Z",
    "mode": "CONTROLLED"
  },
  "entityType": "BusinessClock"
}
```

(An invalid counterpart exists: `BusinessClockInvalidEvent.json`.)

---

### EVENT 2 — Infra Microscopic Region → base graph

```
EVENT NAME:      InfraMicroscopicRegionEvent  (base-graph consumer)
Producer:        RISE infra service (sourceService "bridge.infra")          [external]
Exchange:        rise.events
Routing key:     event.infra.microscopic_region
Queue:           de.hacon.tps.rise.client.infrabasegraph.event.consumer
Consumer:        infra-basegraph-etl → InfraBaseGraphEventHandler
Message format:  JSON { baseEvent, baseEntityEvent{entityID, triggerType, triggeringCommand},
                        baseEntityData, infraMicroscopicRegionData{ baseGraph{nodes,edges},
                        locationLayer{locations[]}, … } }
Trigger:         Infrastructure master data published/republished
Processing:      InfraBaseGraphService.processBaseGraphEvent
                   → BaseGraphMapper.map(event)  (validate, rename infraAddress→infraNodeAddress,
                     kmValueMillimeters→kmValue, List→LinkedHashSet, Long→int, drop regionRef)
                   → baseGraphRepository.save(baseGraph)
Database impact: infra-rivm.basegraph upsert, _id = entityID
Other services:  none
Frontend impact: The entire drawn network (GET /basegraph)
Error/retry:     Mapper returns null on any validation failure (logged warn) — nothing saved,
                 handler returns true. Service catches Exception → log.error → true.
```

Fixtures: `InfraMicroscopicRegionEvent.json`, `InfraMicroscopicRegionInvalidEvent.json`.

---

### EVENT 3 — Infra Microscopic Region → track coordinates

```
EVENT NAME:      InfraMicroscopicRegionEvent  (micro consumer)
Exchange/Key:    rise.events / event.infra.microscopic_region
Queue:           de.hacon.tps.rise.client.inframicro.event.consumer
Consumer:        infra-micro-etl → InfraMicroEventHandler
Processing:      InfraMicroService.setInfraMicro
                   → RiseToInfraMapper.map(infraMicroscopicRegionData)
                       index base-graph nodes by baseSubEntityData.id
                       for each location → each track:
                         id = "{locationId}_{trackId}"
                         nodeCoordinates = resolve trackData.subGraph.nodeRefs → graphical {x,y}
                         trackSubEntityData / locationSubEntityData = {id,name,shortName,description}
                   → trackCoordinatesRepository.saveAll(list)
Database impact: infra-rivm.track-coordinates upserts (never deletes)
Other services:  infra-trainoperation-etl reads this collection (hourly cache refresh)
Frontend impact: Station + platform labels (GET /location-track-coordinates)
Error/retry:     Whole method wrapped in try/catch → log.error → ACK.
Notes:           A code comment records that RISE API utils 5.1.0 had no dedicated "inframicro"
                 event type, so InfraMicroscopicRegionEvent is reused.
```

---

### EVENT 4 — Train Operation (ACTUAL / planned)

```
EVENT NAME:      TrainOperationEvent
Producer:        de.hacon.tps.rids.train_operation                          [external]
Exchange:        rise.events
Routing key:     event.train_operation.train_operation
Queue:           de.hacon.tps.rise.client.trainoperation.event.consumer
Consumer:        infra-trainoperation-etl → InfraTrainOperationMovementEventHandler
Trigger:         triggerType ENTITY_CREATED | ENTITY_UPDATED (others logged and ignored)
Processing:      InfraTrainOperationService.processTrainOperationMovementEvent
                   → processMovementEventForCreateOrUpdate
                       existing = repo.findByTrainServiceId(entityID)
                       new      = RiseToInfraMapper.map(trainOperationData, …)
                       save     = filterMovementPositions(new, existing)
                       savePositionsAndTiles(save)
Database impact: infra-rivm.train-position upserts; infra-rivm.data-tile new UUID versions
Other services:  none (MongoDB is the only coupling)
Frontend impact: Train icons appear/move; tile version change forces the next poll to return data
Error/retry:     processEventWithErrorHandling catches Exception → log.error → ACK
```

Sample payload skeleton (`TrainOperationEvent.json`):

```jsonc
{
  "baseEvent": { "eventID": "fe0aa11b-…", "sourceService": "de.hacon.tps.rids.train_operation",
                 "businessClockTime": "2015-10-21T07:28:42Z",
                 "systemClockTime": "2015-10-21T07:28:42.123Z" },
  "baseEntityEvent": { "entityID": "TrainOperation-9N70-KNGX-DONC",
                       "triggerType": "ENTITY_CREATED",
                       "triggeringCommand": { "userData": { "userID": "tps_live.bridge",
                                                            "userRoles": ["TECHNICAL_USER"] },
                                              "commandID": "9e0a811b-…",
                                              "sourceService": "bridge.infra",
                                              "result": { "result": "SUCCESS" } } },
  "baseEntityData": { "name": "9N70-KNGX-DONC", "shortName": "9N70",
                      "description": "Train Operation from KNGX to DONC",
                      "lastModified": "2015-10-21T07:28:42.123Z",
                      "businessRefs": [ { "idType": "HeadCode", "value": "9N70",
                                          "validityFrom": "2015-10-20T07:28:42Z",
                                          "validityUntil": "2015-10-20T23:59:59Z" } ] },
  "trainOperationData": {
    "effectiveDate": "2015-10-21",
    "currentPlan": {
      "baseSubEntityData": { "id": "sub-entity-ID-1", "name": "P 9N70 KNGX-PBRO",
                             "shortName": "P-9N70" },
      "planData": { "lastModified": "…", "planStatus": "ACTIVE", "operationalStatus": "RUNNING",
                    "changeDetails": [ { "changeCommand": { … }, "changeReason": { … } } ],
                    "activities": [ /* TrainOperationActivity[] */ ] } } }
}
```

`TrainOperationActivity` fields consumed by the mapper:

```
baseSubEntityData.id                                   → activityId
baseOperationElementData.status.value                  → "CANCELLED" ⇒ skip
activityData.departure | .arrival | .movement | .runThrough  → source activity type
baseActivityData.actualEndTime + .actualPlaces[]       → ACTUAL time & places
baseActivityData.plannedTime.planned + .plannedPlaces[]→ planned fallback
place.infraEntityRef.entityID                          → LocationReference
place.infraAddress { kmRegion, kmValueMillimeters, complement } → KmReference
place.infraSubEntityRef where type == "tracks" → subEntityID → trackId
```

Related fixtures: `TrainOperationUpdateEvent.json`, `TrainOperationMovementEvent.json`,
`TrainOperationMovementUpdateEvent.json`, `TrainOperationInvalidDate.json`.

---

### EVENT 5 — Train Operation Forecast

```
EVENT NAME:      TrainOperationForecastEvent
Producer:        de.hacon.tps.rids.train_operation (forecast stream)        [external]
Exchange:        rise.events
Routing key:     event.train_operation.forecast
Queue:           de.hacon.tps.rise.client.trainoperation.forecast.event.consumer
Consumer:        infra-trainoperation-etl → InfraTrainOperationMovementForecastEventHandler
Trigger:         triggerType ENTITY_CREATED | ENTITY_UPDATED
Processing:      processMovementForecastEventForCreateOrUpdate
                   trainServiceId = trainOperationForecastData.trainOperationRef   ← NOT entityID
                   new = RiseToInfraForecastMapper.map(forecastData, …)  (always FORECAST)
                   delete ALL existing FORECAST rows for the train
                     + bump the version of every dataTile they referenced
                   actualFrontier = max(fromTime of existing ACTUAL rows)
                   keep only new rows with fromTime >= actualFrontier
                   savePositionsAndTiles(kept)
                   extendLastActualToForecast(...)
Database impact: infra-rivm.train-position (delete + insert), infra-rivm.data-tile (versions)
Frontend impact: Predicted positions replaced wholesale; tiles invalidated so the client refetches
Error/retry:     processEventWithErrorHandling catches Exception → log.error → ACK
```

Fixture: `TrainOperationMovementForecastEvent.json`.

---

### EVENT 6 — Infra Operational Period

```
EVENT NAME:      InfraOperationalPeriodEvent
Exchange:        rise.events        Routing key: NOT DETERMINED
Queue:           de.hacon.tps.rise.client.infra.operational-period.event.consumer
Consumers:       infra-trainoperation-etl → InfraOperationalPeriodEventHandler
                 infra-restriction-etl    → InfraOperationalPeriodEventHandler
                 (SAME queue → competing consumers)
Processing:      MicroscopicInfraService.init(event) → MicroscopicInfra.initialize(event)
Database impact: NONE — purely in-memory
Frontend impact: Indirect: without it, km-based coordinate resolution and restriction edge-path
                 resolution return empty, so train movements and restriction geometry are dropped
Error/retry:     RuntimeException caught → log.error → returns false (NACK)
```

Fixture: `InfraOperationalPeriodInfraEvent.json` (in both ETLs' test resources).

---

### EVENT 7 — Infra Microscopic Region (in-memory graph)

```
EVENT NAME:      InfraMicroscopicRegionEvent  (graph consumers)
Exchange:        rise.events        Routing key: event.infra.microscopic_region
Queue:           de.hacon.tps.rise.client.infra.microscopic-region.event.consumer
Consumers:       infra-trainoperation-etl and infra-restriction-etl (competing)
Processing:      MicroscopicInfraService.addMicroscopicRegion(event)
                   → MicroscopicInfra.addMicroscopicRegionData(event)
Database impact: NONE — in-memory only
Frontend impact: Indirect (see EVENT 6)
Error/retry:     RuntimeException caught → log.error → returns false
```

Fixture: `InfraMicroscopicRegionData-region-A.json` (in both ETLs).

---

### EVENT 8 — Restriction

```
EVENT NAME:      RestrictionEvent
Producer:        de.hacon.tps.rids.restriction                              [external]
Exchange:        rise.events        Routing key: NOT DETERMINED
Queue:           de.hacon.tps.rise.client.restriction.event.consumer
Consumer:        infra-restriction-etl → RestrictionEventHandler
Trigger:         ENTITY_CREATED | ENTITY_UPDATED | ENTITY_DELETED
Processing:      create/update → RestrictionMapper.mapEventToRestriction → repo.save
                 delete        → repo.deleteById(entityID)
                 segments → edgePaths via MicroscopicInfraService.findEdgePaths()
Database impact: infra-rivm.restriction upsert / delete
Other services:  none
Frontend impact: Restriction poly-lines + markers on the map; restriction list MFE
Error/retry:     Null/blank entityID → warn + return TRUE (drop).
                 Any other exception → service rethrows → handler catches → returns FALSE (NACK).
```

Sample (`RestrictionEvent_created_R01.json`, abbreviated):

```jsonc
{
  "baseEvent": { "eventID": "41a6eb9e-…", "sourceService": "de.hacon.tps.rids.restriction",
                 "businessClockTime": "2023-12-12T07:59:56Z",
                 "systemClockTime": "2023-12-12T07:59:56.123Z" },
  "baseEntityEvent": { "entityID": "R01", "triggerType": "ENTITY_UPDATED",
                       "triggeringCommand": { "userData": { "userID": "tps_live.bridge",
                                                            "userRoles": ["TECHNICAL_USER"] },
                                              "commandID": "41a6eb9e-…",
                                              "sourceService": "rise.bridge.tps_live",
                                              "result": { "result": "SUCCESS" } } },
  "baseEntityData": { "description": "Description of Restriction 1", "name": "Restriction 1",
                      "shortName": "R1", "lastModified": "2023-12-12T07:59:56.123Z" },
  "restrictionData": {
    "state": "ACTIVE",
    "effectiveTimePeriod": { "startTime": "2023-12-24T10:00:00Z",
                             "endTime":   "2023-12-31T08:00:00Z" },
    "impacts": [
      { "trainFilter": { "trainOperationFilter": { "operator": "AND",
            "conditions": [ { "path": "$.path.to.a.train.operation.property",
                              "valueString": "Match4711" } ] } },
        "blocking": {} },
      { "trainFilter": { "trainOperationFilter": { … "valueString": "Match4712" } },
        "speedReduction": { "absoluteMaxSpeedMillimetersPerHour": 80000000 } },
      { "trainFilter": { "trainCompositionFilter": { … "valueString": "Match4713" } },
        "speedReduction": { "relativeSpeedReductionMillimetersPerHour": 20000000 } },
      { "trainFilter": { "trainCompositionFilter": { … "valueString": "Match4714" } },
        "adhesion": { "adhesionLevel": "DRY_MEDIUM" } },
      { "trainFilter": { "trainCompositionFilter": { … "valueString": "Match4715" } },
        "adhesion": { "adhesionLevel": "EXTREMELY_LOW" } }
    ],
    "segments": [ { "kmRegion": "KMR01", "complement": "KMR01S01", … } ]
  }
}
```

Other fixtures: `RestrictionEvent_updated_R01.json`, `RestrictionEvent_deleted_R01.json`.

---

### EVENT 9 — Detection (AEM)

```
EVENT NAME:      Detection event
Exchange:        rise.events        Routing key: event.detection
Consumer:        NOT in this repository — belongs to the AEM backend behind @tps/rimfe-aem
Frontend impact: tps-aem-events-panel (left docked panel)
```

### EVENT 10 — Infra Location

```
EVENT NAME:      Infra location event
Exchange:        rise.events        Routing key: event.infra.location
Consumer:        NOT FOUND in this repository. Published by the E2E harness only
                 (14 station fixtures under events/common/infra-location/) — presumably consumed
                 by another RIVM module in the same environment.
```

## 10.12 Complete message flow

```
                                RISE upstream services
       ┌──────────────────────────────┬──────────────────────────┬────────────────────────┐
       │ de.hacon.tps.rids            │ de.hacon.tps.rids        │ de.hacon.tps.rids      │
       │ .business_clock              │ .train_operation         │ .restriction           │
       │                              │                          │  + bridge.infra        │
       └──────────────┬───────────────┴───────────┬──────────────┴───────────┬────────────┘
                      │                           │                          │
                      ▼                           ▼                          ▼
        ══════════════════════════ EXCHANGE  rise.events (topic, durable) ════════════════════
          │                │                │                │              │            │
 event.business_clock      │  event.infra.microscopic_region  │  event.train_operation.*  │  (restriction key: ?)
          │                │        │            │            │        │        │         │
          ▼                ▼        ▼            ▼            ▼        ▼        ▼         ▼
 ┌─────────────────┐ ┌──────────┐┌──────────┐┌──────────────────────┐┌───────────────┐┌─────────────┐
 │ …businessclock  │ │…inframicro││…infrabase││ …infra.microscopic-  ││ …trainoperation││ …restriction │
 │ .event.consumer │ │ .event.  ││graph.    ││ region.event.consumer││ .event.consumer││ .event.     │
 │                 │ │ consumer ││event.con.││ (+ operational-period)││ (+ .forecast.) ││ consumer    │
 └────────┬────────┘ └────┬─────┘└────┬─────┘└──────────┬───────────┘└───────┬───────┘└──────┬──────┘
          ▼               ▼            ▼                 ▼ (competing)         ▼               ▼
 ┌─────────────────┐┌──────────┐┌────────────┐┌────────────────────────────────────┐┌──────────────┐
 │ business-clock  ││ micro-etl││ basegraph  ││ trainoperation-etl                 ││restriction-  │
 │ -etl            ││          ││ -etl       ││  MicroscopicInfraService (memory)  ││etl           │
 │ BusinessClock   ││ InfraMic-││ InfraBase- ││  InfraTrainOperationService        ││ Restriction  │
 │ Service         ││ roService││ GraphSvc   ││  DataTileService / MapConfigService ││ Service      │
 └────────┬────────┘└────┬─────┘└─────┬──────┘└──────────────┬─────────────────────┘└──────┬──────┘
          ▼              ▼            ▼                       ▼                             ▼
 ┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                                 MongoDB  (risedb)                                                │
 │  infra-rivm.business-clock  infra-rivm.track-coordinates  infra-rivm.basegraph                    │
 │  infra-rivm.train-position  infra-rivm.data-tile          infra-rivm.restriction                  │
 │  infra-rivm.map-config  (read-only here — written by an external process)                         │
 └───────────────────────────────────────────┬──────────────────────────────────────────────────────┘
                                             ▼
                                 infra-query-svc  (REST, :9101)
                                             ▼
                                 infra-webapp  (Angular + OpenLayers)
```

---

# 11 — EVENTS AND MESSAGE CONTRACTS

## 11.1 Common envelope

Every RISE event shares this outer structure (observed identically in all six fixture families):

| Field                                                    | Type                                                                         | Required                     | Meaning                                                      |
| -------------------------------------------------------- | ---------------------------------------------------------------------------- | ---------------------------- | ------------------------------------------------------------ |
| `baseEvent.eventID`                                      | UUID string                                                                  | ✔                            | Unique event id (`RIVMEventID`)                              |
| `baseEvent.sourceService`                                | string                                                                       | ✔                            | `RIVMServiceID` of the publisher                             |
| `baseEvent.businessClockTime`                            | `UTCTime`                                                                    | ✔                            | Business clock at publication                                |
| `baseEvent.systemClockTime`                              | `UTCTimeMillis`                                                              | ✔                            | Wall clock at publication                                    |
| `baseEntityEvent.entityID`                               | `RIVMEntityID`                                                               | ✔ (absent for BusinessClock) | Aggregate id                                                 |
| `baseEntityEvent.triggerType`                            | `ENTITY_CREATED` \| `ENTITY_UPDATED` \| `ENTITY_DELETED` \| `COMMAND_FAILED` | ✔                            | Change kind                                                  |
| `baseEntityEvent.triggeringCommand.userData.userID`      | string                                                                       | —                            | Who caused it                                                |
| `baseEntityEvent.triggeringCommand.userData.userRoles[]` | string[]                                                                     | —                            | e.g. `TECHNICAL_USER`                                        |
| `baseEntityEvent.triggeringCommand.commandID`            | UUID                                                                         | —                            | Originating command                                          |
| `baseEntityEvent.triggeringCommand.sourceService`        | string                                                                       | —                            | Command origin                                               |
| `baseEntityEvent.triggeringCommand.result.result`        | `RIVMCommandResultType`                                                      | —                            | Outcome                                                      |
| `baseEntityData.name` / `.shortName` / `.description`    | string                                                                       | —                            | Entity descriptors                                           |
| `baseEntityData.lastModified`                            | `UTCTimeMillis`                                                              | —                            | Entity version timestamp                                     |
| `baseEntityData.businessRefs[]`                          | `RIVMBusinessRef[]`                                                          | —                            | `{idType, value, validityFrom, validityUntil}`               |
| `entityType`                                             | string                                                                       | —                            | Present at least on `BusinessClockEvent` (`"BusinessClock"`) |
| `<entity>Data`                                           | object                                                                       | ✔                            | The payload (see below)                                      |

**Versioning:** there is **no version field in the envelope**. `RIVMDataVersion` exists in
`RIVMTypes.yaml` but is not used by any event consumed here. Compatibility is managed by the
`rise-api-utils` library version (`13.1.0`). **NOT FOUND: explicit event schema versioning.**

**Serialization:** JSON / UTF-8 / `application/json`, `persistent`, header `signature` = SHA-256 hex.

## 11.2 Event → payload → side-effect matrix

| Event                         | Payload root                 | Consumers                                    | DB writes                               | In-memory writes   | UI effect                                           |
| ----------------------------- | ---------------------------- | -------------------------------------------- | --------------------------------------- | ------------------ | --------------------------------------------------- |
| `BusinessClockEvent`          | `businessClockData`          | `infra-business-clock-etl`                   | `business-clock` (replace)              | —                  | Header clock; all time-driven queries               |
| `InfraMicroscopicRegionEvent` | `infraMicroscopicRegionData` | `infra-basegraph-etl`                        | `basegraph` (upsert)                    | —                  | Network geometry                                    |
| `InfraMicroscopicRegionEvent` | `infraMicroscopicRegionData` | `infra-micro-etl`                            | `track-coordinates` (upsert)            | —                  | Station/platform labels                             |
| `InfraMicroscopicRegionEvent` | `infraMicroscopicRegionData` | `trainoperation-etl` **/** `restriction-etl` | —                                       | `MicroscopicInfra` | Enables km→coordinate + segment→edgePath resolution |
| `InfraOperationalPeriodEvent` | _(NOT DETERMINED)_           | `trainoperation-etl` **/** `restriction-etl` | —                                       | `MicroscopicInfra` | as above                                            |
| `TrainOperationEvent`         | `trainOperationData`         | `trainoperation-etl`                         | `train-position`, `data-tile`           | —                  | Train icons                                         |
| `TrainOperationForecastEvent` | `trainOperationForecastData` | `trainoperation-etl`                         | `train-position` (del+ins), `data-tile` | —                  | Forecast icons                                      |
| `RestrictionEvent`            | `restrictionData`            | `restriction-etl`                            | `restriction` (upsert/delete)           | —                  | Restriction overlays + list                         |

## 11.3 `BusinessClockData`

| Field              | Type                          | Req. | Meaning       | Target                                                   |
| ------------------ | ----------------------------- | ---- | ------------- | -------------------------------------------------------- |
| `businessTime`     | `Instant`                     | ✔    | Simulated now | `BusinessClock.businessTime` (formatted, UTC, no millis) |
| `businessTimeZone` | string                        | ✔    | IANA zone     | `BusinessClock.businessTimeZone`                         |
| `systemTime`       | `Instant`                     | ✔    | Real now      | `BusinessClock.serverTime` (formatted, UTC, with millis) |
| `mode`             | enum `REALTIME`\|`CONTROLLED` | ✔    | Clock mode    | `BusinessClock.mode`                                     |

## 11.4 `InfraMicroscopicRegionData`

| Field                                                                         | Type        | Req. | Used by                  | Meaning                                            |
| ----------------------------------------------------------------------------- | ----------- | ---- | ------------------------ | -------------------------------------------------- |
| `baseGraph.nodes[].baseSubEntityData.{id,name,shortName,description}`         | object      | ✔    | basegraph-etl, micro-etl | Node identity                                      |
| `baseGraph.nodes[].nodeData.coordinates.graphical.{x,y}`                      | int         | ✔    | both                     | Drawing position                                   |
| `baseGraph.nodes[].nodeData.infraAddress.{kmRegion,kmValueMillimeters}`       | string/long | —    | basegraph-etl            | Km address → `infraNodeAddress.{kmRegion,kmValue}` |
| `baseGraph.edges[].baseSubEntityData.*`                                       | object      | ✔    | basegraph-etl            | Edge identity                                      |
| `baseGraph.edges[].edgeData.infraNodeRefs[]`                                  | list of 2   | ✔    | basegraph-etl            | Endpoints; `regionRef` is dropped                  |
| `baseGraph.edges[].edgeData.edgeLengthMillimeters`                            | `Long`      | —    | basegraph-etl            | → `int`                                            |
| `baseGraph.edges[].edgeData.direction`                                        | enum        | —    | basegraph-etl            | `FORWARD`/`REVERSE`/`BOTH`                         |
| `locationLayer.locations[].baseSubEntityData.*`                               | object      | ✔    | micro-etl                | Location identity                                  |
| `locationLayer.locations[].locationData.tracks[].baseSubEntityData.*`         | object      | ✔    | micro-etl                | Track identity                                     |
| `locationLayer.locations[].locationData.tracks[].trackData.subGraph.nodeRefs` | `Set`       | ✔    | micro-etl                | Node refs → coordinates                            |

## 11.5 `TrainOperationData`

```
trainOperationData
├── effectiveDate                : Date          (not used by the mapper)
└── currentPlan                                   (required by isValidTrainOperationData)
    ├── baseSubEntityData { id, name, shortName } (not used)
    └── planData                                  (required)
        ├── lastModified, planStatus, operationalStatus, changeDetails[]   (not used)
        └── activities[] : TrainOperationActivity (required, non-empty)
            ├── baseSubEntityData.id              → activityId  (null ⇒ skip)
            ├── baseOperationElementData.status.value  == "CANCELLED" ⇒ skip
            ├── activityData.departure|arrival|movement|runThrough → source type
            └── baseActivityData
                ├── actualEndTime  : Instant      ┐ ACTUAL branch (needs non-empty actualPlaces)
                ├── actualPlaces[] : InfraPlace   ┘
                ├── plannedTime.planned : Instant ┐ planned branch
                ├── plannedPlaces[]: InfraPlace   ┘
                └── (InfraPlace)
                    ├── infraEntityRef.entityID   → LocationReference.locationId
                    ├── infraAddress {kmRegion, kmValueMillimeters, complement} → KmReference
                    └── infraSubEntityRef {type=="tracks", subEntityID} → trackId
```

## 11.6 `TrainOperationForecastData`

| Field                                                      | Type                               | Req.        | Meaning                                                                    |
| ---------------------------------------------------------- | ---------------------------------- | ----------- | -------------------------------------------------------------------------- |
| `trainOperationRef`                                        | string                             | ✔           | **The train operation the forecast belongs to — used as `trainServiceId`** |
| `forecastedActivities[]`                                   | `TrainOperationForecastActivity[]` | ✔ non-empty | Forecast sequence                                                          |
| `…[].baseSubEntityData.id`                                 | string                             | ✔           | `activityId`                                                               |
| `…[].baseOperationElementData.status.value`                | string                             | —           | `CANCELLED` ⇒ skip                                                         |
| `…[].activityData.{departure,arrival,movement,runThrough}` | object                             | ✔ (one of)  | Source type                                                                |
| `…[].baseActivityData.forecastedEndTime`                   | `Instant`                          | ✔           | `fromTime` (null ⇒ skip)                                                   |
| `…[].baseActivityData.forecastedPlaces[]`                  | `InfraPlace[]`                     | ✔ non-empty | Position + track                                                           |

## 11.7 `RestrictionData` (event side)

| Field                                          | Type                                           | Req.           | Target                                                               |
| ---------------------------------------------- | ---------------------------------------------- | -------------- | -------------------------------------------------------------------- |
| `state`                                        | `RestrictionState`                             | ✔              | `restrictionData.state`                                              |
| `effectiveTimePeriod.startTime`/`endTime`      | `Instant`                                      | ✔              | ISO strings                                                          |
| `group.id`                                     | string                                         | —              | `restrictionData.group.id`                                           |
| `impacts[].trainFilter.trainOperationFilter`   | `PropertyFilter`                               | —              | mapped 1:1                                                           |
| `impacts[].trainFilter.trainCompositionFilter` | `PropertyFilter`                               | —              | mapped 1:1                                                           |
| `impacts[].blocking.dummyToNotHaveEmptyObject` | string                                         | —              | copied                                                               |
| `impacts[].speedReduction.*`                   | int                                            | —              | copied                                                               |
| `impacts[].adhesion.adhesionLevel`             | enum                                           | —              | copied                                                               |
| **`segments[]`**                               | `InfraSegment[]` (`{kmRegion, complement, …}`) | ✔ for geometry | **transformed** → `edgePaths[]` via `MicroscopicInfra.findEdgePaths` |
| `meta.ui.icon.{type,payload}`                  | string                                         | —              | copied                                                               |
| `meta.ui.style.{type,payload}`                 | string                                         | —              | copied                                                               |

## 11.8 Event flow diagrams

### Business clock

```mermaid
sequenceDiagram
    participant RISE as RISE Business Clock
    participant MQ as rise.events (topic)
    participant H as BusinessClockEventHandler
    participant S as BusinessClockService
    participant M as RiseToInfraMapper
    participant R as BusinessClockRepository
    participant DB as MongoDB business-clock
    participant API as infra-query-svc
    participant UI as infra-webapp

    RISE->>MQ: publish event.business_clock (+signature)
    MQ->>H: handleValidatedMessage(BusinessClockEvent)
    H->>S: setBusinessClock(event)
    S->>M: map(businessClockData)
    M-->>S: BusinessClock (serverTime ← systemTime)
    S->>R: deleteAll()
    S->>R: save(businessClock)
    R->>DB: replace single document
    UI->>API: GET /business-clock (every 10 s)
    API->>DB: findAll()
    DB-->>API: [BusinessClock]
    API-->>UI: { data: { businessTime, businessTimeZone, serverTime, mode } }
```

### Train operation (ACTUAL) vs forecast

```mermaid
sequenceDiagram
    participant MQ as rise.events
    participant HA as MovementEventHandler
    participant HF as ForecastEventHandler
    participant S as InfraTrainOperationService
    participant MA as RiseToInfraMapper
    participant MF as RiseToInfraForecastMapper
    participant U as TrainOperationUtil
    participant TC as TrackCoordinatesService
    participant MI as MicroscopicInfraService
    participant DT as DataTileService
    participant R as TrainPositionRepository
    participant DB as MongoDB

    MQ->>HA: TrainOperationEvent
    HA->>S: processTrainOperationMovementEvent
    S->>R: findByTrainServiceId(entityID)
    S->>MA: map(trainOperationData, …)
    MA->>U: createTrainPosition(params)
    U->>TC: getCachedCoordinates()  (location activities)
    U->>MI: findEdges(infraAddress) (km activities)
    U->>DT: createTileIds(trainPosition)
    MA-->>S: List<TrainPosition>
    S->>S: filterMovementPositions (MOVEMENT must be ACTUAL)
    S->>DT: createDataTiles(ids) + saveAll (new UUIDs)
    S->>R: saveAll(positions)
    R->>DB: upsert

    MQ->>HF: TrainOperationForecastEvent
    HF->>S: processTrainOperationMovementForecastEvent
    S->>R: findByTrainServiceId(trainOperationRef)
    S->>MF: map(forecastData, …)  (always FORECAST)
    S->>R: deleteAllById(existing FORECAST ids)
    S->>DT: bump versions of freed tiles
    S->>S: filter fromTime >= actualFrontier
    S->>R: saveAll(kept)
    S->>S: extendLastActualToForecast
```

### Restriction

```mermaid
sequenceDiagram
    participant MQ as rise.events
    participant H as RestrictionEventHandler
    participant S as RestrictionService
    participant M as RestrictionMapper
    participant MI as MicroscopicInfraService
    participant R as RestrictionRepository
    participant DB as MongoDB restriction

    MQ->>H: RestrictionEvent
    alt entityID null or blank
        H-->>MQ: return true (ACK, drop)
    else
        H->>S: processRestrictionEvent(event)
        alt ENTITY_CREATED / ENTITY_UPDATED
            S->>M: mapEventToRestriction(event)
            M->>MI: findEdgePaths(restrictionData.segments)
            MI-->>M: List<Types.EdgePath>
            M-->>S: Restriction (edgePaths + coordinates)
            S->>R: save(restriction)
            R->>DB: upsert _id = entityID
        else ENTITY_DELETED
            S->>R: deleteById(entityID)
            R->>DB: delete
        else other triggerType
            S->>S: log.warn "Unhandled trigger type"
        end
        S-->>H: (rethrows on error)
        H-->>MQ: true / false
    end
```

---

# 12 — TRAIN MANAGEMENT

## 12.1 What a "train" is in this system

There is **no `Train` entity**. The only train-shaped persisted object is
**`TrainPosition`** — one document per _(train, activity)_ pair, describing **where a train is
between two timestamps**.

```
TrainPosition._id = "{trainServiceId}-{activityId}"
```

The train itself (its plan, its composition, its number, its operating day) lives in the **train
operation domain**, which is external to this repository and reached only through
`@tps/mfe-train-operation` against `environment.mfeBaseUrl`.

## 12.2 Train creation

**There is no train creation in this repository.** Trains appear as a by-product of ingesting
`TrainOperationEvent` / `TrainOperationForecastEvent`:

```
event.baseEntityEvent.triggerType == ENTITY_CREATED
   → InfraTrainOperationService.processTrainOperationMovementEvent
       → RiseToInfraMapper.map(...)  → n × TrainPosition
       → savePositionsAndTiles(...)  → upsert into infra-rivm.train-position
```

No REST endpoint, no UI action and no message publication creates a train.
Ribbon items `new_train`, `cancel_train`, `divert_train`, `splitting`, `coupling`, … are all
`disabled: true` in `EDIT_SECTION`.

## 12.3 Train editing

| Layer              | Detail                                                                                                                                                                                                                                                                                               |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Entry points**   | Ribbon `Edit` section (`arrival_time`, `departure_time`, `change_track`) — only these three are enabled and only when `panelContext().trainNumber` is set; map right-click context menu (`TRAIN_LIST_CONTEXT_MENU` has exactly the same three actions); `(editTrain)` output of `tps-mfe-train-list` |
| **State**          | `PanelStateStore.openEditPanel({trainServiceId, trainNumber, operatingDay, editType})` → `overlayPanel='edit-panel'`, `ribbonAction=editType`, `isEditPanelDirty=false`                                                                                                                              |
| **Panel**          | `<tps-mfe-train-edit-panel [baseUrl] [trainServiceId] [businessClockTimezone] [ribbonAction] [editTrainApiPayload] [containerManaged] [containerWidthPercent] [containerMaxWidthPercent]>`                                                                                                           |
| **Dirty tracking** | `(editedTrainData)` → `handleEditPanelDataChanged` → `isEditedField(data)` (`'previousValue' in data && 'currentValue' in data`) → `lastEditedField.set(...)`, `setEditPanelDirty(true)`                                                                                                             |
| **Apply**          | Ribbon `apply` → `panelState.requestApply()` → `effect` → `submitPendingEdit` → `buildEditPayload` → `editTrainApiPayload.set(payload)`                                                                                                                                                              |
| **Payload**        | `EditableTrainDetails` — see §2.6 table                                                                                                                                                                                                                                                              |
| **HTTP**           | **Performed inside `@tps/mfe-train-operation`** — verb/path **NOT DETERMINED**                                                                                                                                                                                                                       |
| **Result**         | `(editedTrainApiResponse)` → `'success'` ⇒ `bumpTrainDataVersion()` + `closeOverlay()`; `'error'` ⇒ `snackbarAlertService.showError(COMMON_ERROR_MESSAGES)`                                                                                                                                          |
| **Cancel**         | Ribbon `cancel` → `closeOverlay()`, `isApplyEditsSection=false`, `selectedEditAction=null`                                                                                                                                                                                                           |
| **Guard**          | `navigateHome` and `closeDockedLists` refuse to act while `isEditPanelDirty()`                                                                                                                                                                                                                       |

> **The edit never touches `infra-rivm.train-position` directly.** It goes to the train-operation
> command service, which will eventually publish a new `TrainOperationEvent`, which the ETL ingests,
> which changes the tile version, which the SPA picks up on its next poll. Full round-trip:
>
> `UI edit → MFE PUT → train-operation cmd svc → rise.events → infra-trainoperation-etl → Mongo → GET /trainpositions → map`

## 12.4 Train deletion

**NOT FOUND.** No deletion endpoint or UI action exists.
The only deletes are internal to the forecast flow:
`trainPositionRepository.deleteAllById(existingForecastIds)` inside
`processMovementForecastEventForCreateOrUpdate`.
`TrainPositionRepository.deleteAll()` exists but is used only by tests.

## 12.5 Train movement / status

| Concept                                       | Representation                                                                                                    |
| --------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| **Movement**                                  | A sequence of `TrainPosition` rows with `activityType == MOVEMENT`, each a km-based point between stations        |
| **Stop**                                      | `activityType == ARRIVAL` / `DEPARTURE` at a location track                                                       |
| **Pass-through**                              | `activityType == RUNTHROUGH`                                                                                      |
| **Confirmed vs predicted**                    | `runningType == ACTUAL` vs `FORECAST`                                                                             |
| **Cancelled activity**                        | Filtered out at ingest (`baseOperationElementData.status.value == "CANCELLED"`) — never becomes a `TrainPosition` |
| **Validity window**                           | `[fromTime, toTime)` — `toTime` = next activity's time, or `fromTime + 10 min` for the last                       |
| **"Current" position**                        | Computed client-side by `TimeCalculationService.filterPositionsByTime`                                            |
| **Heading/direction**                         | **Hard-coded `90°`** in `OpenLayerClusterUtility.createTrainPositionFeatures`                                     |
| **Speed / weight / length / dangerous goods** | **Not modelled** in `TrainPosition`; the popover shows `'-'`                                                      |

Activity-type derivation at ingest (`determineOutputActivityType`):

```
source MOVEMENT   → MOVEMENT
source RUNTHROUGH → RUNTHROUGH
otherwise         → first location activity ? DEPARTURE : ARRIVAL
```

Combined with `shouldSkipIntermediateDeparture` (drop every `DEPARTURE` after the first), a journey
becomes: `DEPARTURE(origin) → MOVEMENT* → ARRIVAL → MOVEMENT* → ARRIVAL(destination)`.

## 12.6 Train schedules

**Not stored here.** The nearest equivalents are:

- `TrainPosition.fromTime` / `toTime` — the derived time window per activity.
- `trainOperationData.currentPlan.planData.activities[]` in the event — the actual plan, consumed
  and discarded.
- The **train list MFE** (`tps-mfe-train-list`) which fetches schedules itself using
  `[operatingDay]` derived from the business clock.

Operating-day derivation (`master-layout.operating-day.ts`):

```typescript
toOperatingDay(clock) {
  if (!clock?.businessTime) return { day: null, timeZone: 'UTC' };
  const timeZone = clock.businessTimeZone || 'UTC';
  const m = moment.tz(clock.businessTime, timeZone);
  if (m.isValid()) return { day: m.format('YYYY-MM-DD'), timeZone };
  const prefix = clock.businessTime.substring(0, 10);
  return { day: /^\d{4}-\d{2}-\d{2}$/.test(prefix) ? prefix : null, timeZone };
}
```

## 12.7 Train routes

A route is implicit in the **ordered activity sequence** of one event. It is materialised as:

- `TrainPosition.origin` — location id of the **first** ARRIVAL/DEPARTURE activity;
- `TrainPosition.destination` — location id of the **last** ARRIVAL/DEPARTURE activity;
- the set of `TrainPosition` rows themselves (one per activity), forming the traversed points.

**No poly-line route geometry is stored or drawn for trains** — only the current point.

## 12.8 Train metadata

| Field                           | Where                                                                                                                |
| ------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `trainServiceId`                | `TrainPosition.trainServiceId` (from `baseEntityEvent.entityID` or `trainOperationForecastData.trainOperationRef`)   |
| Train **type**                  | Derived client-side from `trainServiceId.charAt(0)` (§4.8)                                                           |
| Display name                    | `extractTrainDisplayName` — all `_`-segments except the last                                                         |
| Head code / business refs       | In the event's `baseEntityData.businessRefs[]` — **discarded** at ingest                                             |
| Name / short name / description | In `baseEntityData` — **discarded**; `RiseToInfraMapper` receives `baseEntityData` as a parameter but never reads it |

## 12.9 Train ↔ track relationship

```
InfraPlace.infraSubEntityRef where type == "tracks"  →  subEntityID  →  ActivityContext.trackId
LocationReference.locationId + "_" + trackId          →  TrackCoordinates._id
TrackCoordinates.nodeCoordinates[0]                   →  TrainPosition.coordinates
```

So the platform a train stops at determines its drawn position — but **the track id itself is not
persisted on `TrainPosition`**. Only the resulting `{x, y}` survives.

## 12.10 Train ↔ platform relationship

Identical to §12.9 — "platform" is the `platforms` map layer rendered from `LocationWithTracks.tracks`.
`Change Track` edits go to the train-operation service, not to any collection here.

## 12.11 Train restrictions

`RestrictionImpact.trainFilter.trainOperationFilter` / `trainCompositionFilter` describe **which
trains a restriction applies to**, using JSON-path property filters.

> **No component in this repository evaluates those filters.** They are ingested, stored, returned
> to the browser, and used only to compute the popover's "Impact Type" label from the _keys_ of the
> impact objects. Restriction-to-train matching is **NOT FOUND / NOT DETERMINED**.

## 12.12 Train events

Inbound only: `TrainOperationEvent`, `TrainOperationForecastEvent` (§10.11, §11.5, §11.6).
No train event is published by this repository.

## 12.13 Train visualisation

Fully covered in §4.8. Summary:

| Aspect       | Value                                                                                           |
| ------------ | ----------------------------------------------------------------------------------------------- |
| Geometry     | `Point([coordinates.x, coordinates.y])`                                                         |
| Icon         | `public/icons/train_directional.svg` with `{{FILL_COLOR}}` / `{{STROKE_COLOR}}` substituted     |
| Colour       | by first digit of `trainServiceId`                                                              |
| Rotation     | `rotateWithView: true`, direction constant `90°`                                                |
| Scale        | `0.75`, ×1.75 when selected                                                                     |
| Selected     | white stroke + larger scale                                                                     |
| Label        | `trainServiceId` at zoom > 18, placed by `LabelPlacementEngine`, with a coloured connector line |
| Cluster      | green donut (`#51E4A4` ring, `#25252D` centre) + `cluster_train.svg` + count                    |
| Visibility   | `zoom >= trainsLayer.minZoom && filterStateStore.showTrains()`                                  |
| Hover        | popover + `cursor: pointer`                                                                     |
| Click        | select                                                                                          |
| Double-click | open TIP                                                                                        |
| Right-click  | context menu (only if already selected)                                                         |

## 12.14 Train APIs

| API                                    | Owner                      | Purpose               |
| -------------------------------------- | -------------------------- | --------------------- |
| `POST /api/infra/query/trainpositions` | **this repo**              | tile-scoped positions |
| train list / TIP / edit endpoints      | `@tps/mfe-train-operation` | **NOT DETERMINED**    |

## 12.15 Train database tables

`infra-rivm.train-position` (§7.6) and `infra-rivm.data-tile` (§7.7).

## 12.16 Train frontend models

`TrainPosition`, `TileVersion`, `RunningType`, `InfraGraphicalCoordinates`,
`TrainPositionsResponse` (`models/train-position.model.ts`);
`TrainPanelRequest`, `TrainEditRequest`, `EditAction`, `ApplyEditAction` (`models/master-layout.model.ts`);
`EditedField<T>`, `EditRunningLocationTrack`, `EditRunningTime`, `EditableTrainDetails`, `Track`
(`models/train-edit.model.ts`); `TrainPopoverData` (`utility/train-popover.mapper.ts`);
`TrainRun`, `TrainEditPanelData<Track>` (imported from `@tps/mfe-train-operation`).

## 12.17 End-to-end train workflows

### T1 — A train appears on the map

```
TrainOperationEvent (ENTITY_CREATED)
 → InfraTrainOperationMovementEventHandler.handleValidatedMessage
 → InfraTrainOperationService.processTrainOperationMovementEvent
 → processEventWithErrorHandling (triggerType switch)
 → processMovementEventForCreateOrUpdate
     trainPositionRepository.findByTrainServiceId(entityID)
     RiseToInfraMapper.map(...)
        isMapConfigAvailable()  ── false ⇒ abort with a warning
        extractAndFilterActivitySequence(activities)
        buildTrainPositionsWithSlidingWindow → TrainOperationUtil.createTrainPosition
            resolveCoordinates(...)  ── null ⇒ position dropped
            setTimeWindows(...)
            DataTileService.createTileIds(...)
     filterMovementPositions(...)
     savePositionsAndTiles(...)
        DataTileService.createDataTiles → saveAll   (data-tile versions change)
        trainPositionRepository.saveAll             (train-position upsert)
 → [client] TrainPositionStore poll sees a changed version
 → POST /trainpositions returns the new rows
 → store merge → filterPositionsByTime → MapService.updateTrainPositions
 → OpenLayers renders the icon
```

### T2 — A dispatcher inspects a train

```
Double-click on the icon (or (openTrainInfo) from the train list)
 → InfraContentComponent.handleTrainDoubleClick
     guard: overlay must not already be TIP/edit
     MapService.resolveTrainServiceIdAtPixel  (null for multi-train clusters)
     MapService.setSelectedTrain(id)
     PanelStateStore.openTIP({trainServiceId, trainNumber})
 → effect → handlePanelStateChange
     mapCenterBeforeTip = MapService.getViewCenter()
     mapResizeSubject.next({panTo: MapService.getSelectedTrainCoordinate()})
     [debounce 350 ms] map.updateSize() + MapService.panToKeepVisible(coord, 0.5)
 → master-layout.component.html renders <tps-mfe-train-info-panel>
 → the MFE loads its own data from mfeBaseUrl
 → close → PanelStateStore.closeOverlay() → MapService.restoreViewCenter(mapCenterBeforeTip)
```

### T3 — A dispatcher changes an arrival time

See §2.6. Round trip ends with a fresh `TrainOperationEvent` re-entering flow **T1**.

### T4 — A train is selected from the list

```
tps-mfe-train-list (selectedTrainData) → MasterLayoutComponent.onTrainSelected(train)
 → handleTrainSelected
     train == null → MapService.setSelectedTrain(null); panelState.updatePanelContext({})
     else          → MapService.setSelectedTrain(train.id)
                     MapService.focusSelectedTrain()      (animate 500 ms, zoom ≥ 19)
                     panelState.updatePanelContext({trainServiceId: train.id,
                                                    trainNumber: train.trainNumber,
                                                    operatingDay: train.operatingDay})
 → ribbon `editSectionItems` recomputes: arrival_time / departure_time / change_track become enabled
```

---

# 13 — TRACK / NETWORK MANAGEMENT

## 13.1 Internal representation of the railway network

The network is a **microscopic node–edge graph in a Cartesian drawing plane**, plus a
**location layer** that groups nodes into stations and platform tracks.

```
BaseGraph (one document per region)
 ├── nodes[]  — a point in the plane, optionally carrying a km address
 └── edges[]  — a pair of node references, a length in millimetres and a direction
```

There is **no separate section/block/signal collection**. Everything that exists is either a node,
an edge, a location, or a track (a named sub-graph of nodes belonging to a location).

## 13.2 Tracks

| Concept                       | Where                                                                                                                                                                                                                                                                      |
| ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Location track (platform)** | `LocationTrack.yaml` — `{id*, name*, description*, shortName*, sequence, effectiveLengthMeters, isElectrified, hasPassengerPlatform, nodes[]}` — **defined in the schema library but NOT part of `infra-model.yaml`, so no Java class is generated and nothing reads it.** |
| **Persisted track**           | `TrackCoordinates` — `{ id: "{locationId}_{trackId}", nodeCoordinates[], locationSubEntityData, trackSubEntityData }`                                                                                                                                                      |
| **API projection**            | `LocationWithTracks.tracks[]` (`TrackWithCoordinates`)                                                                                                                                                                                                                     |
| **Rendering**                 | Track **labels only**. The track's own geometry is not drawn — the base-graph edges under it are.                                                                                                                                                                          |

> `isElectrified`, `hasPassengerPlatform`, `effectiveLengthMeters` and `sequence` exist in the schema
> library but are **never ingested, stored, transported or displayed**.

## 13.3 Track sections

**NOT FOUND** as a first-class concept. The closest constructs are:

- `EdgeWithOffsets { edgeRef, startPercentage, endPercentage }` — a _fraction_ of an edge, used only
  by restrictions.
- `InfraSegment` (`restrictionData.segments[]` on the event) — km-range segments, converted to
  edge paths at ingest and then discarded.
- `LocationTrack.yaml` contains a commented-out `infraSegments` property.

## 13.4 Nodes

`InfraMicroscopicNode`:

```
baseSubEntityData { id*, name, shortName, description, businessRefs[] }
nodeData {
   infraNodeAddress { kmRegion*, kmValue* }     // km marker
   coordinates { graphical { x*, y* } }          // int32 drawing coordinates
}
```

Constraints: 2 … 1 048 575 nodes per region.
Rendering: a `Point` feature carrying `nodeData`; styled with a **text-only** style (node id) that
only activates at zoom ≥ 18 — and, because zoom is not forwarded by `createMainVectorLayer`, is in
practice never shown (§4.6).

Frontend model `InfraNode` also carries `signalInfo` and `isBoundaryNode` — **neither exists in the
backend schema**, so both are always `undefined`.

## 13.5 Stations (locations)

| Aspect        | Detail                                                                                                                                                                                                                                                  |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Source        | `infraMicroscopicRegionData.locationLayer.locations[]`                                                                                                                                                                                                  |
| Persisted as  | `TrackCoordinates.locationSubEntityData` (`{id, name, shortName, description}`), one copy per track                                                                                                                                                     |
| API           | `LocationWithTracks { id, name, shortName, tracks[] }` — reconstructed by aggregation                                                                                                                                                                   |
| Rendered as   | A single white text label with a dark halo at the centre of the bounding box of all its tracks' coordinates, `+3` on Y, on a `declutter: true` layer                                                                                                    |
| Zoom gate     | `locations` layer `minZoom` (reference config: 14) / `maxZoom` (100)                                                                                                                                                                                    |
| Richer schema | `LocationDataTile.yaml` → `LocationData { locationId*, name*, shortName*, uicCountryCode*, isAuxiliary, level, nodes[], tracks* }` — generated as `LocationDataTile` but **never used**; `uicCountryCode`, `isAuxiliary` and `level` never reach the UI |

## 13.6 Signals

**NOT FOUND.** There is no signal entity, no signal collection, no signal rendering.

Traces that suggest a _planned_ feature:

- `infra-region.model.ts` declares `SignalInfo { startNodeRef?, signalTypeName?, securitySections?: string[][] }`
  and `RawNode.signalInfo?`, `InfraNode.signalInfo`;
- `infra-query-svc/README.md` says the service should provide "Nodes, Edges, Locations, Signals etc."

Neither the OpenAPI schemas nor any Java class contains a signal. `signalInfo` is always `undefined`.

## 13.7 Blocks

**NOT FOUND.** No block/section/interlocking concept exists anywhere.
`RestrictionImpactBlocking` is a _train impact_ ("this restriction blocks matching trains"), **not**
a track block.

## 13.8 Routes (network paths)

| Concept          | Status                                                                                                     |
| ---------------- | ---------------------------------------------------------------------------------------------------------- |
| Train route      | Implicit activity sequence (§12.7)                                                                         |
| Restriction path | `EdgePath { pathEdges[], pathCoordinates[] }` — the only explicit path object                              |
| Path-finding     | **Not in this repository** — `MicroscopicInfra.findEdges()` / `.findEdgePaths()` inside `rise-infra-utils` |
| Route rendering  | Only restrictions are drawn as poly-lines                                                                  |

## 13.9 Network topology

- **Directed-ish:** `InfraEdgeDirection` = `FORWARD` (default) / `REVERSE` / `BOTH`, meaning
  "first→second node", "second→first", or both.
- **Exactly two endpoints per edge**, `uniqueItems: true`, "the referenced nodes may not be the same".
- **Cross-region references** are modelled (`regionRef` / `infraMicroscopicRegionRef`) but
  `BaseGraphMapper.mapNodeRef` **explicitly drops `infraMicroscopicRegionRef`**, so persisted node
  references are region-local only.
- **Edge length** in millimetres (`LengthMillimeters`, min 0).
- The frontend model `EdgeRecord` declares `angleDeg?` and `isOctilinear?` — **never populated**
  (leftovers from an octolinear-layout feature).

## 13.10 Track editing

**NOT FOUND.** No infrastructure editing exists:
no OpenLayers `Draw`/`Modify`/`Translate` interaction, no infra write endpoint, no infra command
message. All infrastructure is read-only, sourced from upstream events.

Ribbon items that hint at future editing (`add_area`, `addView`, `savedViews`, `edit_bar`,
`edit_panel`, `dynamic_simplifier`) are all `disabled`.

## 13.11 Track restrictions

See §14. Restrictions attach to **edge paths**, i.e. to fractions of base-graph edges.

## 13.12 Track availability

**NOT FOUND.** There is no availability/occupancy model. The nearest signal is a restriction with a
`blocking` impact, which the SPA does not evaluate.

## 13.13 Track visualisation

| Element                      | Layer                                     | Style                                                                          |
| ---------------------------- | ----------------------------------------- | ------------------------------------------------------------------------------ |
| Edges (the visible "tracks") | `vectorLayer` (z from `baseGraph.zindex`) | `Stroke #898995`, width 1, round cap/join                                      |
| Nodes                        | same layer                                | text-only style (id) at zoom ≥ 18 — effectively never shown                    |
| Station labels               | `locationLabelLayer` (z 30, declutter)    | `800 10px "Public Sans"`, white fill, `#111118` stroke w1, padding `[2,4,2,4]` |
| Track labels                 | `trackLabelLayer` (z 40)                  | `400 10px "Public Sans"`, white fill, `#111118` stroke w1                      |
| Location bbox                | `locationLabelLayer`                      | empty style (debug only; stroke commented out)                                 |
| Overview map                 | `OverviewMap` control                     | same node/edge styles, frozen                                                  |

## 13.14 Track APIs

| Endpoint                          | Returns                       | Consumer                     |
| --------------------------------- | ----------------------------- | ---------------------------- |
| `GET /basegraph`                  | `BaseGraph[]` — nodes + edges | SPA (network geometry)       |
| `GET /location-track-coordinates` | `LocationWithTracks[]`        | SPA (labels)                 |
| `GET /track-coordinates`          | `TrackCoordinates[]` (flat)   | **no consumer in this repo** |

## 13.15 Track database collections

`infra-rivm.basegraph`, `infra-rivm.track-coordinates` (§7.4, §7.5).

## 13.16 Track events

- `InfraMicroscopicRegionEvent` → three different consumers (base graph, track coordinates,
  in-memory graph).
- `InfraOperationalPeriodEvent` → in-memory graph initialisation.
- `event.infra.location` → published by the E2E harness, **no consumer here**.

---

# 14 — RESTRICTIONS

## 14.1 What a restriction is

> _"One or more geographic regions in combination with a time interval and an impact on matching
> trains."_ — `components/schemas/infra/RestrictionData.yaml`

Concretely: a **state**, a **time window**, a set of **impacts** (each with a train filter), a set of
**edge paths** describing the affected geography, and optional **UI metadata** (icon + style).

## 14.2 Types of restriction (by impact)

| Impact              | Schema object                     | Fields                                                                             | Meaning                               |
| ------------------- | --------------------------------- | ---------------------------------------------------------------------------------- | ------------------------------------- |
| **Blocking**        | `RestrictionImpactBlocking`       | `dummyToNotHaveEmptyObject?`                                                       | Matching trains cannot travel through |
| **Speed reduction** | `RestrictionImpactSpeedReduction` | `absoluteMaxSpeedMillimetersPerHour?`, `relativeSpeedReductionMillimetersPerHour?` | Absolute cap or relative cut          |
| **Adhesion**        | `RestrictionImpactAdhesion`       | `adhesionLevel: DRY_MEDIUM \| DRY_LOW \| LOW \| VERY_LOW \| EXTREMELY_LOW`         | Reduced traction force                |

A single restriction may carry **0 … 255** impacts, each with its own `trainFilter`
(`trainOperationFilter` and/or `trainCompositionFilter`, both `PropertyFilter`s).

Restriction **states**: `ACTIVE`, `INACTIVE`, `CANCELLED` (`RestrictionTypes.yaml`).

## 14.3 How restrictions are created

**Not in this repository.** They arrive as `RestrictionEvent` with
`triggerType == ENTITY_CREATED`, published by `de.hacon.tps.rids.restriction`.

The UI's `RESTRICTIONS_SECTION` ribbon (`newRestriction`, `edit`, `copyRestriction`,
`deleteRestriction`) is entirely `disabled: true`.

## 14.4 How restrictions are edited

Two distinct notions:

1. **Content edit** — upstream only, via `ENTITY_UPDATED`.
   `RestrictionService.processEntityForCreateOrUpdate` re-maps the whole event and calls
   `repository.save(...)`, i.e. a **full replace** of `restrictionData`.
2. **State toggle (Activate / Deactivate)** — available in the UI (§2.7). The HTTP PATCH is issued
   **inside `@tps/rimfe-restriction`**; the host only:
   - tracks the selected row (`RibbonStateStore.selectedRestriction`),
   - tracks the MFE's `selectionActionable` verdict,
   - computes button enablement (`buildRestrictionActionItems`),
   - calls `MfeViewRestrictionListComponent.requestRestrictionStateChange(id, 'ACTIVE' | 'INACTIVE')`
     (duck-typed; returns `of(false)` if the library method is missing),
   - shows a snackbar on failure.

## 14.5 How restrictions are stored

`infra-rivm.restriction`, `_id = baseEntityEvent.entityID`.
The full document shape is in §7.8.

Ingest transformation highlights (`RestrictionMapper`):

- `Instant` → `String` for `lastModified`, `effectiveTimePeriod.startTime/endTime`,
  `condition.valueDate`, `condition.valueDateTime`.
- Every enum via `EnumType.valueOf(dto.name())`.
- **`segments[]` → `edgePaths[]`** via `MicroscopicInfraService.findEdgePaths(segments)`.
- `startPercentage` / `endPercentage` → `BigDecimal.setScale(2, HALF_UP)`.
- `meta.ui.icon` and `meta.ui.style` copied as `{type, payload}` (both through `mapUiIcon`).

## 14.6 How restrictions are validated

| Layer     | Validation                                                                                                                                                          |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Broker    | Signature (`sha256`) + schema, inside `rise-api-utils`                                                                                                              |
| Handler   | `entityID` must be non-null and non-blank, else **ACK-and-drop**                                                                                                    |
| Service   | `triggerType` must be one of `ENTITY_CREATED`/`ENTITY_UPDATED`/`ENTITY_DELETED`, else `log.warn`                                                                    |
| Mapper    | Null-guard on every nested object; missing `segments` ⇒ `edgePaths = []`                                                                                            |
| Query API | `effectiveAt` required + ISO parseable; `pageNumber >= 0`; `1 <= pageSize <= 1000`                                                                                  |
| Frontend  | `normalizeApiResponse` defaults `impacts`, `edgePaths`, `pathEdges`, `pathCoordinates` to `[]`; `createRestrictionFeatures` skips coordinate sets with `< 2` points |

**No business validation** (e.g. `startTime < endTime`, overlapping restrictions, valid edge refs)
exists anywhere in this repository.

## 14.7 How restrictions affect trains and tracks

**In this repository: they do not.** The effect is purely visual.

- No service evaluates `trainFilter` against a `TrainPosition`.
- No `TrainPosition` field references a restriction.
- No re-routing, re-timing or blocking logic exists.

The impacts are ingested and displayed so that a **human dispatcher** can act on them.

## 14.8 APIs involved

| API                                                                 | Direction | Owner                                                             |
| ------------------------------------------------------------------- | --------- | ----------------------------------------------------------------- |
| `GET /api/infra/query/restrictions?effectiveAt&pageNumber&pageSize` | read      | **this repo**                                                     |
| Restriction list fetch                                              | read      | `@tps/rimfe-restriction` (baseUrl = `mfeBaseUrl`)                 |
| Restriction state PATCH                                             | write     | `@tps/rimfe-restriction` — exact contract **NOT DETERMINED** here |

## 14.9 RabbitMQ events involved

`RestrictionEvent` — queue `de.hacon.tps.rise.client.restriction.event.consumer`;
routing key **NOT DETERMINED** (§10.3).
Also, indirectly, `InfraMicroscopicRegionEvent` + `InfraOperationalPeriodEvent`, because
`findEdgePaths` cannot resolve geometry without them.

## 14.10 Database impact

| Trigger          | Effect                                        |
| ---------------- | --------------------------------------------- |
| `ENTITY_CREATED` | insert (upsert) into `infra-rivm.restriction` |
| `ENTITY_UPDATED` | full replace of the document                  |
| `ENTITY_DELETED` | `deleteById(entityID)`                        |
| anything else    | nothing (`log.warn`)                          |

No other collection is touched.

## 14.11 Frontend behaviour

| Concern                 | Implementation                                                                                                                                                                        |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Fetch                   | `RestrictionApiService.getRestrictionData(effectiveAt, 0, 100)`                                                                                                                       |
| Polling                 | `RestrictionsStore.startPolling(businessTime)`, interval from `restrictions` layer `updateFrequencySecs` (fallback 2 000 ms)                                                          |
| Poll gate               | `zoom > restrictionsLayer.minZoom && mapStateStore.isGraphLoaded() && !!baseBusinessTime`                                                                                             |
| Time sync               | `setCurrentBusinessTime(adjustedUtcTime)` on every slider/clock change; the next tick uses it                                                                                         |
| Client-side time filter | **Intentionally bypassed** — `getVisibleRestrictions()` returns the input array unchanged with the comment _"backend effectiveAt already applies time window"_ (`void businessTime;`) |
| Active test             | `restrictionData.state === 'EFFECTIVE'` (⚠ §4.9)                                                                                                                                      |
| Colour                  | active → icon `<circle fill>` / first usable `fill` / CSS `color:` from the style payload; inactive → `#999`                                                                          |
| List panel              | `app-mfe-view-restriction-list` wrapping `tps-mfe-restriction-list`; `minimizedColumns = 'name,state'`                                                                                |
| Selection               | `(restrictionSelected)` → `RibbonStateStore.setSelectedRestriction({id, state})`; `(selectionActionable)` → `setRestrictionActionable(bool)`                                          |
| Ribbon                  | `restrictionActionsSection` (Activate / Deactivate / Cancel-disabled) + `exportSection`                                                                                               |
| Errors                  | `snackbarAlertService.showError(COMMON_ERROR_MESSAGES)`                                                                                                                               |
| Cleanup                 | `ngOnDestroy` → `setSelectedRestriction(null)`                                                                                                                                        |

## 14.12 Map visualisation

Fully described in §4.9. Summary of the visual language:

| Visual                                                         | Meaning                                                                                          |
| -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| Thick (4 px) coloured line                                     | active restriction                                                                               |
| Thin (2 px) grey (`#999`) line                                 | inactive restriction                                                                             |
| Wider translucent halo (`+8 px`, alpha `66`)                   | same colour, ~40 % opacity                                                                       |
| Circular icon at the line midpoint                             | the restriction's own SVG icon, recoloured (background = restriction colour, foreground = white) |
| White under-stroke (`+12 px`) + icon lifted 6 px + radius `+2` | hover state                                                                                      |
| Icon radius                                                    | scales linearly 4 → 18 px between zoom 2.5 and 20                                                |

## 14.13 End-to-end restriction workflow

```
[upstream] Restriction created/updated/deleted
   ↓ rise.events  (routing key NOT DETERMINED)
   ↓ queue de.hacon.tps.rise.client.restriction.event.consumer
RestrictionEventHandler.handleValidatedMessage
   ↓ (entityID blank ⇒ ACK-drop)
RestrictionService.processRestrictionEvent
   ├ ENTITY_CREATED / ENTITY_UPDATED
   │    RestrictionMapper.mapEventToRestriction
   │       state / effectiveTimePeriod / group / impacts   → 1:1
   │       segments  → MicroscopicInfraService.findEdgePaths → edgePaths (+ pathCoordinates)
   │       meta.ui.icon / .style                            → 1:1
   │    RestrictionRepository.save
   └ ENTITY_DELETED → RestrictionRepository.deleteById
   ↓
MongoDB infra-rivm.restriction
   ↓
GET /api/infra/query/restrictions?effectiveAt=<adjusted business time>
   RestrictionService.getRestrictionsByEffectiveTime (Sort DESC lastModified)
   MongoRestrictionRepository.findByEffectiveTime (startTime ≤ t ≤ endTime, string compare)
   ↓
RestrictionApiService.normalizeApiResponse
   ↓
RestrictionsStore.restrictions → visibleRestrictionInfos (computed)
   RestrictionDisplayUtility.getVisibleRestrictionInfo
      isActive, pathCoordinateSets, pathLocations, meta, color
   ↓
InfraContentComponent.updateRestrictionsDisplay(infos)
   guard: graph loaded; zoom > restrictionsMinZoom
   MapService.updateRestrictions(infos)
   ↓
OpenLayerRestrictionUtility.updateRestrictionFeatures
   one LineString feature per edgePath with ≥ 2 coordinates
   ↓
Style function → white hover stroke? + colour stroke + translucent stroke + midpoint icon
   ↓
CANVAS
   ↓
Hover → TooltipPositionService.tryRenderRestrictionTooltip
   → MapService.setHoveredRestriction(id)  (white halo)
   → mapRestrictionFeatureToPopoverData    (ID, Name, State, Affected Trains, From, To, Impact Type)
```

---

# 15 — AUTHENTICATION & AUTHORIZATION

## 15.1 Executive summary

**Neither authentication nor authorization is implemented in this repository.**

| Check                                              | Result                                           |
| -------------------------------------------------- | ------------------------------------------------ |
| Spring Security dependency                         | **Absent** from every `build.gradle.kts`         |
| `SecurityFilterChain` / `WebSecurityConfigurer`    | **NOT FOUND**                                    |
| `@PreAuthorize` / `@Secured` / `@RolesAllowed`     | **NOT FOUND**                                    |
| JWT / OAuth2 / OIDC resource-server config         | **NOT FOUND**                                    |
| Angular auth guard                                 | **NOT FOUND**                                    |
| Angular auth interceptor / `Authorization` header  | **NOT FOUND**                                    |
| Token storage (localStorage/sessionStorage/cookie) | **NOT FOUND**                                    |
| Login screen / login route                         | **NOT FOUND**                                    |
| Role checks in the UI                              | **NOT FOUND**                                    |
| Gateway permissions                                | `permissions: null` on every registered endpoint |

## 15.2 Login flow

There is **no login flow in this application**.

Evidence of an _external_ SSO in front of it:

- `app.config.ts`:
  ```typescript
  // App initializer for pre-boot logic (e.g. authentication)
  // Currently commented out to bypass Keycloak login
  { provide: APP_INITIALIZER, useFactory: initializeApp, deps: [ConfigService], multi: true }
  ```
  `initializeApp` merely calls `ConfigService.loadConfig()`, which resolves a hard-coded empty user.
- `module-tests/playwright/e2e/common/pages/locators/LoginLocators.js` — _"Locators for the
  login/authentication page (Keycloak SSO)"_.
- `module-tests/playwright/e2e/common/stepDefinitions/CommonSteps.js` — _"Handles Keycloak SSO login
  for modulemode/systemmode"_.
- `module-tests/.github/playwright/playwright-locators-rules.md` — `authSetup.js  # Keycloak authentication`.
- `module-tests/playwright/utility/credentialsHelper.js` — test credential loading
  `[SECRET / CREDENTIAL PRESENT — VALUE OMITTED]`.

**Conclusion:** authentication is terminated by a **Keycloak-backed gateway/reverse proxy** in front
of `/ui/infra` and `/api/infra/**`. That component is **NOT part of this repository**.

## 15.3 Tokens

**NOT FOUND.** The SPA never reads, stores, refreshes or sends a token. All requests rely on
whatever the browser already carries (most plausibly a session cookie set by the SSO proxy) —
and even that is implicit: `withCredentials` is **never** set on any `HttpClient` call.

## 15.4 Sessions

**NOT FOUND** server-side. `infra-query-svc` is stateless (no `HttpSession` usage, no session
configuration).

Client-side persistence that is _not_ a session:

- IndexedDB `RIVM-INFRA` → base graph, map config, location tracks (TTL 1 h)
- `localStorage['infra-filter-state']` → layer visibility

`models/session-mgmt-model.ts` (`LocationTab`, `TabPreferences`, zoom transforms) and
`SESSION_MGMT_DB_NAME = 'RIVM-INFRA'` are **unused leftovers**.

## 15.5 Roles

Roles exist only as **data**:

- `RIVMUserRole` (`basic/RIVMTypes.yaml`) — examples `TECHNICAL_USER`, `ADMINISTRATOR`.
- Sample events carry `triggeringCommand.userData.userRoles: ["TECHNICAL_USER"]` and
  `["TPS_USER"]`.
- `ConfigService.UserInfo.roles: string` — a **string**, always `''`.

**No code branches on a role.**

## 15.6 Permissions

`deployment/helm/templates/endpoints.yaml` declares `permissions: null` for all nine registered
routes (seven API + two UI). The gateway therefore applies **no permission requirement**.

## 15.7 Guards

**No Angular route guard exists.** The only "guards" in the codebase are UI-state guards:

| Guard                                                                      | Location                                                                     | Effect                                           |
| -------------------------------------------------------------------------- | ---------------------------------------------------------------------------- | ------------------------------------------------ |
| `if (overlay === OVERLAY.TIP \|\| overlay === OVERLAY.EDIT_PANEL) return;` | `handleTrainSingleClick`, `handleTrainDoubleClick`, `handleTrainContextMenu` | Ignore map interactions while an overlay is open |
| `if (ctx.panelState.isEditPanelDirty()) return;`                           | `navigateHome`, `closeDockedLists`                                           | Prevent navigating away from unsaved edits       |
| `if (item.disabled) return;`                                               | `handleShowHideAction`, `onRestrictionActionClick`                           | Ignore disabled ribbon buttons                   |
| `if (!panelContext?.trainNumber \|\| !item.action) return;`                | `handleEditActionClick`                                                      | Require a selected train                         |

## 15.8 Backend security

| Aspect                                        | Finding                                                                                                                                                 |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Transport                                     | Plain HTTP inside the cluster; TLS termination is the gateway's job (**NOT DETERMINED**)                                                                |
| CORS                                          | Hard-coded `registry.addMapping("/**").allowedOrigins("http://localhost:4200")` in `QueryServiceApplication`                                            |
| CSRF                                          | **Not applicable / not configured** — no Spring Security, and the only state-changing endpoint (`POST /trainpositions`) is a read operation in disguise |
| Input validation                              | Bean Validation on request params/body only                                                                                                             |
| Rate limiting                                 | **NOT FOUND**                                                                                                                                           |
| Security headers (HSTS, CSP, X-Frame-Options) | **NOT FOUND**                                                                                                                                           |
| Actuator                                      | **NOT FOUND** (no `spring-boot-starter-actuator` anywhere)                                                                                              |
| Message security                              | SHA-256 `signature` header validated by `rise-api-utils`; `RIVMErrorType.INVALID_SIGNATURE` documents the failure mode                                  |
| MongoDB auth                                  | Username/password properties present, defaults `guest/guest` — `[SECRET / CREDENTIAL PRESENT — VALUE OMITTED]`                                          |
| RabbitMQ auth                                 | Username/password properties present, defaults `guest/guest` — `[SECRET / CREDENTIAL PRESENT — VALUE OMITTED]`                                          |

## 15.9 API authorization

**None.** Every endpoint is anonymous from the service's point of view.

## 15.10 Frontend authorization

**None.** Feature availability is driven by static `disabled` flags in `infra.config.ts` and by UI
state (train selected? panel dirty? restriction actionable?) — never by identity.

## 15.11 Service-to-service security

- HTTP: no service-to-service HTTP calls exist.
- AMQP: message-level SHA-256 signature (validated by `rise-api-utils`) plus broker credentials.
- MongoDB: shared credentials per service via environment variables.

## 15.12 Trace

```
LOGIN
   → [EXTERNAL Keycloak SSO — not in this repository]
TOKEN / SESSION
   → [EXTERNAL — the SPA is unaware of it]
FRONTEND
   → HttpClient request with NO Authorization header and NO withCredentials flag
API REQUEST
   → gateway (endpoints.yaml: permissions: null, method + param + header allow-list)
AUTHORIZATION
   → none performed by infra-query-svc
RESPONSE
   → data returned unconditionally

SIGN OUT
   → MasterLayoutComponent.signOut()
   → handleSignOut(ctx)
   → LogoutApiService.logout()
   → POST {environment.baseAuthUrl}/logout   body {}  responseType 'text'
   → .subscribe()   // no success handler, no redirect, no local state cleanup
```

Production `baseAuthUrl` = `../../auth`; development = `http://localhost:8081/tps/auth`.

---

# 16 — ERROR HANDLING

## 16.1 Backend exception hierarchy

| Exception                   | Package             | Carries       | Thrown by                                                                 |
| --------------------------- | ------------------- | ------------- | ------------------------------------------------------------------------- |
| `BadRequestException`       | `…common.exception` | `String code` | `TrainPositionService.validateDataTiles` (`code = "20001"`)               |
| `ResourceNotFoundException` | `…common.exception` | message only  | `BusinessClockService.getBusinessClock`, `ConfigService.getAllMapConfigs` |

## 16.2 Global exception handler

`de.hacon.tps.rise.infra.common.exception.GlobalExceptionHandler`
(`@ControllerAdvice @Slf4j final class extends ResponseEntityExceptionHandler`):

| Handled exception              | HTTP status                 | `code` in body                               |
| ------------------------------ | --------------------------- | -------------------------------------------- |
| `BadRequestException`          | `400 BAD_REQUEST`           | `String.valueOf(ex.getCode())`               |
| `ResourceNotFoundException`    | `404 NOT_FOUND`             | `ErrorCodes.DATA_NOT_FOUND` = `"404"`        |
| `ConstraintViolationException` | `400 BAD_REQUEST`           | `ErrorCodes.BAD_REQUEST` = `"400"`           |
| `IllegalArgumentException`     | `400 BAD_REQUEST`           | `"400"`                                      |
| `Exception` (catch-all)        | `500 INTERNAL_SERVER_ERROR` | `ErrorCodes.INTERNAL_SERVER_ERROR` = `"500"` |

Builder:

```java
public ResponseEntity<ApiErrorResponse> buildResponseEntity(Exception ex, String errorCode, HttpStatus status) {
  log.error(ex.getMessage(), ex);                       // full stack trace at ERROR
  ErrorResponse errorResponse = new ErrorResponse();
  errorResponse.setMessage(ex.getMessage());            // ← raw exception message is exposed
  errorResponse.setCode(errorCode);
  ApiErrorResponse response = new ApiErrorResponse();
  response.getErrors().add(errorResponse);
  return new ResponseEntity<>(response, status);
}
```

> Because it extends `ResponseEntityExceptionHandler`, standard Spring MVC exceptions
> (`MethodArgumentNotValidException`, `HttpMessageNotReadableException`,
> `MissingServletRequestParameterException`, …) are handled by the **base class**, which produces
> the Spring default `ProblemDetail`/`ErrorResponse` body — **a different shape** from
> `ApiErrorResponse`. Two error shapes therefore exist on the wire.
>
> The catch-all also means an internal `IllegalStateException` (e.g. duplicate tile ids in the
> `POST /trainpositions` body reaching `Collectors.toMap`) surfaces as **500 with the raw message**.

Registration: `QueryServiceApplication` component-scans `de.hacon.tps.rise.infra.common.exception`.
**None of the ETL applications scan that package**, so the handler is a query-service-only concern.

## 16.3 Standard error-response map

```jsonc
// ApiErrorResponse — produced by GlobalExceptionHandler
{ "errors": [{ "code": "<string>", "message": "<exception message>" }] }
```

| Scenario                                | Status | Body                                                                                                          |
| --------------------------------------- | ------ | ------------------------------------------------------------------------------------------------------------- |
| `pageSize` above the max                | 400    | `{"errors":[{"code":"400","message":"getAllBaseGraphDetails.pageSize: must be less than or equal to 1000"}]}` |
| Tile id null/empty                      | 400    | `{"errors":[{"code":"20001","message":"Tile ID must not be null or empty"}]}`                                 |
| No clock document                       | 404    | `{"errors":[{"code":"404","message":"No clock data found"}]}`                                                 |
| No map config                           | 404    | `{"errors":[{"code":"404","message":"No map configuration data found"}]}`                                     |
| Anything unexpected                     | 500    | `{"errors":[{"code":"500","message":"<raw message>"}]}`                                                       |
| Missing `effectiveAt` / empty POST body | 400    | Spring default `ErrorResponse` shape (**not** `ApiErrorResponse`)                                             |

## 16.4 ETL error handling (per service)

| Service                                     | Failure behaviour                                                                                                                                                      | Message outcome                                                   |
| ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| `infra-business-clock-etl`                  | `BusinessClockService` catches `Exception` → `log.error("Failed to convert and save message " + e)`; handler catches `RuntimeException` → `log.error` → `return false` | Service-level failures are **swallowed** (handler returns `true`) |
| `infra-micro-etl`                           | `InfraMicroService` catches `Exception` → `log.error("Failed to convert and handle infra micro event", e)`; handler → `false` on `RuntimeException`                    | swallowed                                                         |
| `infra-basegraph-etl`                       | Mapper returns `null` on validation failure (`log.warn`); service catches `Exception` → `log.error`; handler → `false` on `RuntimeException`                           | swallowed                                                         |
| `infra-trainoperation-etl`                  | `processEventWithErrorHandling` catches `Exception` → `log.error("Failed to process {}", eventTypeName, e)`; handlers → `false` on `RuntimeException`                  | swallowed                                                         |
| `infra-restriction-etl`                     | Handler drops blank-`entityID` messages with `return true`; `RestrictionService` **rethrows** → handler catches `Exception` → `log.error(…)` → `return false`          | **NACK possible**                                                 |
| `MicroscopicInfra*EventHandler` (both ETLs) | catch `RuntimeException` → `log.error` → `return false`                                                                                                                | NACK possible                                                     |

> Net effect: **only restriction and infra-graph events can be negatively acknowledged.**
> Clock, base-graph, micro and train-operation failures are logged and the message is consumed.

## 16.5 Database failure handling

**No explicit handling.** There is no `@Transactional` anywhere, no retry template, no circuit
breaker. A `MongoException` propagates:

- in the query service → caught by `GlobalExceptionHandler` → `500`;
- in an ETL → caught by the surrounding `catch (Exception)` → logged → message consumed.

Notable non-atomic sequences:

1. `BusinessClockService`: `deleteAll()` then `save()`.
2. `InfraTrainOperationService.processMovementForecastEventForCreateOrUpdate`:
   `deleteAllById(...)` → tile version bump → `saveAll(...)` → `extendLastActualToForecast(...)`.
3. `savePositionsAndTiles`: tiles are versioned **before** positions are written.

## 16.6 Frontend error handling

| Location                                                                                                      | Mechanism                                                      | User feedback                                                                    |
| ------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| `BusinessClockApiService`                                                                                     | `catchError → throwError(new Error('Error fetching data: …'))` | none directly                                                                    |
| `BusinessClockEffects`                                                                                        | `catchError → of(loadBusinessClockDataFailure({error}))`       | none — the `error` field is never rendered                                       |
| `EdgeDataEffects`                                                                                             | `catchError → of(loadEdgeDataFailure({error}))`                | `error$` is exposed by `InfraContentComponent` but **not bound in the template** |
| `MapConfigStore.loadMapConfig`                                                                                | `catchError → patchState({loading:false, error}); of([])`      | none                                                                             |
| `LocationsStore.loadLocations`                                                                                | `catchError → patchState({loading:false, error}); of([])`      | none                                                                             |
| `LocationTrackCoordinatesApiService.fetchPage`                                                                | `retry({count:3, delay:1000})`                                 | none                                                                             |
| `InfraCacheDbService.get$`                                                                                    | `catchError → of(null)`                                        | silent cache miss                                                                |
| `InfraCacheDbService.set/remove`                                                                              | `.catch(() => {})`                                             | silent (comment: _"IndexedDB unavailable — silently ignore"_)                    |
| `TrainPositionStore.startPolling`                                                                             | `catchError → patchState({error, loading:false}); EMPTY`       | none — polling continues                                                         |
| `RestrictionsStore.loadRestrictions` / `startPolling`                                                         | same pattern                                                   | none                                                                             |
| `LogoutApiService.logout`                                                                                     | `catchError → throwError(...)`, `.subscribe()` with no handler | **unhandled RxJS error**                                                         |
| `handleEditPanelSaved('error')`                                                                               | `snackbarAlertService.showError(COMMON_ERROR_MESSAGES)`        | **snackbar**                                                                     |
| `handleRestrictionAction` (no request / `ok === false`)                                                       | `snackbarAlertService.showError(COMMON_ERROR_MESSAGES)`        | **snackbar**                                                                     |
| `RestrictionDisplayUtility.buildRestrictionMarkerDataUri` / `getRestrictionColor` / `getRestrictionIconColor` | `try { atob(...) } catch { return null }`                      | icon/colour silently falls back                                                  |
| `TooltipPositionService.resolveRestrictionIconName`                                                           | `try/catch` → returns `'restriction'`                          | generic icon                                                                     |
| `RestrictionDisplayUtility.formatTime`                                                                        | `try/catch` → returns the raw string                           | raw text                                                                         |
| `FilterStateStore.loadPersistedState`                                                                         | `try/catch` → defaults                                         | silent                                                                           |
| `mapFeatureToPopoverData` / `mapRestrictionFeatureToPopoverData`                                              | `moment(...).isValid()` checks                                 | shows the raw value                                                              |
| `main.ts`                                                                                                     | `.catch(err => console.error(err))`                            | console only                                                                     |

**The only two user-visible error messages in the entire application** are the two snackbars, both
showing the same generic text:

```typescript
export const COMMON_ERROR_MESSAGES = $localize`:@@commonError:An error occurred! Please try again.`;
```

`SnackbarAlertService` uses `MatSnackBar` with `SnackbarContentComponent`.

## 16.7 Retry mechanisms

| Mechanism                     | Where                                                                                           | Parameters                                                             |
| ----------------------------- | ----------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| HTTP page retry               | `LocationTrackCoordinatesApiService.fetchPage`                                                  | `retry({ count: 3, delay: 1000 })`                                     |
| Polling as implicit retry     | `TrainPositionStore`, `RestrictionsStore`, `BusinessClockEffects`                               | interval from config / 10 s; `catchError → EMPTY` keeps the loop alive |
| Deferred map focus            | `MapService.focusSelectedTrain` → `pendingFocusSelectedTrain` retried in `updateTrainPositions` | one-shot                                                               |
| AMQP redelivery               | inside `rise-api-utils`                                                                         | **NOT DETERMINED**                                                     |
| Backend retry/circuit breaker | **NOT FOUND**                                                                                   | —                                                                      |

## 16.8 Logging

**Backend** — SLF4J via Lombok `@Slf4j`:

| Level   | Typical use                                                                                                                                                                                                                             |
| ------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ERROR` | every caught exception; `GlobalExceptionHandler.buildResponseEntity` logs `ex.getMessage(), ex`                                                                                                                                         |
| `WARN`  | unhandled trigger types, missing MapConfig, unresolvable coordinates, multiple matching edges, skipped CANCELLED activities, blank `entityID`, `RiseToInfraMapper.filterMovementsBetweenStations` ("Processing activities - total: {}") |
| `INFO`  | event received / processed, counts, restriction query stats, cache load sizes                                                                                                                                                           |
| `DEBUG` | per-activity skip decisions, `TrainPosition` creation details                                                                                                                                                                           |

Configuration: `logging.level.org.springframework=WARN` in every ETL.
`infra-query-svc` sets **no** logging level (Spring defaults).
**No structured logging, no correlation id, no MDC, no log appender configuration** anywhere.

**Frontend** — ESLint forbids `console` (`no-console: warn` per the workspace convention);
the only console call is `main.ts`'s bootstrap `catch`, with an explicit
`// eslint-disable-next-line no-console`. A commented-out
`// console.log('Train positions API request:', requestBody)` remains in
`train-position-api.service.ts`.

## 16.9 Validation summary

| Layer             | Mechanism                                                                                 |
| ----------------- | ----------------------------------------------------------------------------------------- |
| Message           | signature + schema (`rise-api-utils`)                                                     |
| ETL               | null/empty guards, enum `valueOf`, CANCELLED filter, MapConfig availability               |
| REST params       | `@Validated` + `@Min`/`@Max`/`@Valid`/`@NotEmpty` + `@DateTimeFormat`                     |
| REST body         | `@Valid @NotEmpty List<@Valid DataTile>` + `validateDataTiles`                            |
| Domain            | Bean Validation annotations generated from the OpenAPI schema (`useBeanValidation: true`) |
| Frontend forms    | **NOT FOUND** — the only form control is the range slider (`[min]`, `[max]`, `[step]`)    |
| Frontend response | `Array.isArray(...)` guards, `?? []` defaults, `normalizeApiResponse`                     |

---

# 17 — CONFIGURATION

> Every credential below is reported as
> `[SECRET / CREDENTIAL PRESENT — VALUE OMITTED]`. The literal defaults visible in the repository are
> the well-known placeholder `guest`, which is recorded only as "a default exists".

## 17.1 Backend application configuration (per service)

### `infra-common-lib`

```properties
spring.application.name=infra-common-lib
app.db.collection.business-clock=infra-rivm.business-clock
app.db.collection.location=infra-rivm.location          # declared, never used
app.db.collection.basegraph=infra-rivm.basegraph
app.db.collection.train-position=infra-rivm.train-position
app.db.collection.data-tile=infra-rivm.data-tile
app.db.collection.track-coordinates=infra-rivm.track-coordinates
app.db.collection.restriction=infra-rivm.restriction
# NOTE: app.db.collection.map-config is NOT declared here
```

### `infra-query-svc`

See §5.2 for the full listing. Distinctive keys:
`server.port=${SERVER_PORT:9101}`, `server.servlet.context-path=/api/infra/query`,
`testcontainers.reuse.enable=true`, `app.feature.dataTileVersion.isActive=false` (**unused**),
`app.db.collection.map-config=infra-rivm.map-config`.

### `infra-business-clock-etl`

```properties
spring.application.name=infra-business-clock-etl
spring.mongodb.{host,port,database,username,password}=${MONGO_*:…}
spring.rabbitmq.{host,port,username,password}=${RABBITMQ_*:…}
rise.api.utils.event_handling.business_clock.queue_name=de.hacon.tps.rise.client.businessclock.event.consumer
rise.api.utils.service.name=de.hacon.tps.rise.infra.businessclock
spring.devtools.restart.enabled=false
logging.level.org.springframework=WARN
app.db.collection.business-clock=infra-rivm.business-clock
```

### `infra-micro-etl`

Same skeleton, plus
`rise.api.utils.event-handling.infra.microscopic-region.queue-name=de.hacon.tps.rise.client.inframicro.event.consumer`,
`rise.api.utils.service.name=de.hacon.tps.rise.infra.micro`,
`app.db.collection.track-coordinates=infra-rivm.track-coordinates`.

### `infra-basegraph-etl`

Same skeleton, plus
`rise.api.utils.event-handling.infra.microscopic-region.queue-name=de.hacon.tps.rise.client.infrabasegraph.event.consumer`,
`rise.api.utils.service.name=de.hacon.tps.rise.infra.basegraph`,
`app.db.collection.basegraph=infra-rivm.basegraph`.

### `infra-trainoperation-etl`

Same skeleton, plus four queue names, `rise.api.utils.service.name=de.hacon.tps.rise.infra.trainoperation`,
four collection names (`map-config`, `train-position`, `track-coordinates`, `data-tile`) and:

```properties
scheduler.trackcoordinates.load.interval=${TRACKCOORDINATES_LOAD_INTERVAL:3600000}
scheduler.mapconfig.load.interval=${MAPCONFIG_LOAD_INTERVAL:60000}
```

### `infra-restriction-etl`

Same skeleton, plus three queue names,
`rise.api.utils.service.name=de.hacon.tps.rise.infra.restriction`,
`app.db.collection.restriction=infra-rivm.restriction`.

## 17.2 Environment variables (complete list)

| Variable                            | Default                                        | Used by                    | Purpose                                         |
| ----------------------------------- | ---------------------------------------------- | -------------------------- | ----------------------------------------------- |
| `SERVER_PORT`                       | `9101`                                         | `infra-query-svc`          | HTTP port                                       |
| `MONGO_HOST`                        | `localhost`                                    | all Java services          | Mongo host                                      |
| `MONGO_PORT`                        | `27017`                                        | all Java services          | Mongo port                                      |
| `MONGO_DATABASE`                    | `risedb`                                       | all Java services          | Mongo database                                  |
| `MONGO_USERNAME`                    | _(default present)_                            | all Java services          | `[SECRET / CREDENTIAL PRESENT — VALUE OMITTED]` |
| `MONGO_PASSWORD`                    | _(default present)_                            | all Java services          | `[SECRET / CREDENTIAL PRESENT — VALUE OMITTED]` |
| `RABBITMQ_HOST`                     | `localhost`                                    | all ETLs                   | Broker host                                     |
| `RABBITMQ_PORT`                     | `5672`                                         | all ETLs                   | Broker port                                     |
| `RABBITMQ_USERNAME`                 | _(default present)_                            | all ETLs                   | `[SECRET / CREDENTIAL PRESENT — VALUE OMITTED]` |
| `RABBITMQ_PASSWORD`                 | _(default present)_                            | all ETLs                   | `[SECRET / CREDENTIAL PRESENT — VALUE OMITTED]` |
| `TRACKCOORDINATES_LOAD_INTERVAL`    | `3600000`                                      | `infra-trainoperation-etl` | Track-coordinate cache refresh (ms)             |
| `MAPCONFIG_LOAD_INTERVAL`           | `60000`                                        | `infra-trainoperation-etl` | Map-config cache refresh (ms)                   |
| `RABBITMQ_URL` / `AMQP_URL`         | `amqp://localhost`                             | `module-tests`             | E2E broker URL                                  |
| `MONGODB_URI` / `MONGO_URI`         | `mongodb://guest:guest@localhost:27017/risedb` | `module-tests`             | `[SECRET / CREDENTIAL PRESENT — VALUE OMITTED]` |
| `MONGODB_DB_NAME` / `MONGO_DB_NAME` | `risedb`                                       | `module-tests`             | E2E database                                    |
| `TAGS`                              | —                                              | `module-tests`             | Cucumber tag filter (`@smoke`, `@regression`)   |

Build-time Gradle properties (`settings.gradle.kts`): `artifactory.url`, `artifactory.user`,
`artifactory.password` — `[SECRET / CREDENTIAL PRESENT — VALUE OMITTED]`.

## 17.3 Frontend environment configuration

| File                         | `production` | `demo`  | `baseUrl`                               | `baseAuthUrl`                    | `mfeBaseUrl`            | `interceptors`          |
| ---------------------------- | ------------ | ------- | --------------------------------------- | -------------------------------- | ----------------------- | ----------------------- |
| `environment.ts`             | `true`       | `false` | `../../api/infra/query`                 | `../../auth`                     | `../../api/infra`       | `[]`                    |
| `environment.development.ts` | `false`      | `false` | `http://localhost:8080/api/infra/query` | `http://localhost:8081/tps/auth` | `http://localhost:9199` | `[]`                    |
| `environment.demo.ts`        | `false`      | `true`  | `http://localhost:8080/api/infra/query` | `http://localhost:8081/tps/auth` | `http://localhost:9199` | `[httpMockInterceptor]` |

Both non-production files also export `providers: [provideStoreDevtools({maxAge: 25})]` — **which is
never consumed**; `app.config.ts` registers `provideStoreDevtools` unconditionally instead.

Selected by `angular.json` `fileReplacements` for the `development`, `demo` and `demo-fr`
configurations; `production` is the default.

## 17.4 Angular build configurations

| Configuration          | Optimisation                      | Source maps | Environment file             | Locale                 |
| ---------------------- | --------------------------------- | ----------- | ---------------------------- | ---------------------- |
| `production` (default) | on, `outputHashing: all`, budgets | off         | `environment.ts`             | all (`localize: true`) |
| `fr`                   | inherits production               | —           | `environment.ts`             | `fr`                   |
| `development`          | off                               | on          | `environment.development.ts` | all                    |
| `demo`                 | off                               | on          | `environment.demo.ts`        | all                    |
| `demo-fr`              | off                               | on          | `environment.demo.ts`        | `fr`                   |

i18n: `sourceLocale en-US` with `baseHref /tps/ui/infra/`; locale `fr` → `src/locale/messages.fr.xlf`,
same `baseHref`.

## 17.5 Feature flags

| Flag                                         | Location             | Effect                                                                  |
| -------------------------------------------- | -------------------- | ----------------------------------------------------------------------- |
| `environment.demo`                           | frontend             | Enables `httpMockInterceptor` (all HTTP served from fixtures)           |
| `environment.production`                     | frontend             | Declared; **not branched on** anywhere in `src/app`                     |
| `app.feature.dataTileVersion.isActive=false` | `infra-query-svc`    | **Dead** — no Java code reads it                                        |
| `MapLayer.defaultVisibility` (`SHOW`/`HIDE`) | MongoDB `map-config` | **Not read** by the SPA                                                 |
| `spring.devtools.restart.enabled=false`      | every ETL            | Disables DevTools restart (documented workaround for autowiring issues) |
| `testcontainers.reuse.enable=true`           | `infra-query-svc`    | Test container reuse                                                    |

No dedicated feature-flag framework exists.

## 17.6 Runtime (data-driven) configuration

`MapConfig` in MongoDB is the real runtime control surface:

| Setting                                                  | Consumer                                                                      | Effect                                |
| -------------------------------------------------------- | ----------------------------------------------------------------------------- | ------------------------------------- |
| `layers[id=baseGraph].zindex`                            | `MapService.setInfraLayerZIndex`                                              | Infrastructure stacking               |
| `layers[id=trains].minZoom`                              | `InfraContentComponent.selectedZoomLevel`                                     | Train visibility threshold            |
| `layers[id=trains].tileSize.{width,height,timeSpanSecs}` | `TileManagementService`, `TimeCalculationService`, backend `DataTileService`  | Tile grid + time rounding             |
| `layers[id=trains].updateFrequencySecs`                  | `TrainPositionStore.setPollingInterval`                                       | Train poll period                     |
| `layers[id=restrictions].minZoom`                        | `restrictionsMinZoom`                                                         | Restriction visibility + polling gate |
| `layers[id=restrictions].updateFrequencySecs`            | `RestrictionsStore.setPollingInterval`, restriction MFE `pollingIntervalSecs` | Restriction poll period               |
| `layers[id=locations].{minZoom,maxZoom,zindex}`          | `MapService.loadLocationLabels`                                               | Station label layer                   |
| `layers[id=platforms].{minZoom,maxZoom,zindex}`          | `MapService.loadLocationLabels`                                               | Track label layer                     |
| `layerDataType == 'train'` + `tileSize != null`          | backend `DataTileService.isMapConfigAvailable`                                | **Gate on all train ingest**          |
| `mapType == OCTOLINEAR`                                  | backend `MapConfigService.refresh`                                            | Which config is used by the ETL       |

## 17.7 Ports

| Component                  | Port    | Source                                                                       |
| -------------------------- | ------- | ---------------------------------------------------------------------------- |
| `infra-query-svc`          | `9101`  | `application.properties` + `values.yaml` `querySvc.service.port`             |
| `infra-webapp` (container) | `80`    | `values.yaml` `webapp.service.port`, `infra-webapp.yaml` `containerPort: 80` |
| Angular dev server         | `4200`  | Angular CLI default; matches the CORS allow-list                             |
| Dev API assumption         | `8080`  | `environment.development.ts`                                                 |
| Dev auth assumption        | `8081`  | `environment.development.ts`                                                 |
| Dev MFE assumption         | `9199`  | `environment.development.ts`                                                 |
| MongoDB                    | `27017` | defaults                                                                     |
| RabbitMQ                   | `5672`  | defaults                                                                     |

## 17.8 Profiles / environments

**No Spring profiles are used** — there is no `application-{profile}.properties`, no
`spring.profiles.active`, no `@Profile` annotation anywhere. Environment differentiation is achieved
purely through environment variables and Helm values.

Frontend "profiles" are the Angular CLI configurations of §17.4.

## 17.9 Service discovery

**None.** No Eureka, Consul, Spring Cloud or DNS-SD. Services find each other via:

- Kubernetes DNS through the Helm template `rise.common.serviceHost` (in `endpoints.yaml`);
- relative URLs from the browser (`../../api/infra/query`).

## 17.10 Deployment configuration (Helm)

`Chart.yaml`

```yaml
apiVersion: v2
name: rivm-infra
version: 0.0.0-dev
appVersion: "dev"
dependencies:
  - name: rise-common          repository: oci://tps-helm.repo.imscloud.de  version: ^2.x
  - name: mfe-train-operation  repository: oci://tps-helm.repo.imscloud.de  version: 2.7.3
  - name: rimfe-restriction    repository: oci://tps-helm.repo.imscloud.de  version: 0.7.0
```

`values.yaml`

```yaml
global:
  imageRegistry: ""
  mongodb: { host: "" }
  rabbitmq: { host: "" }
image: { repository: rise/rivm-infra, pullPolicy: IfNotPresent }
querySvc: { replicas: 1, service: { port: 9101 } }
webapp: { replicas: 1, service: { port: 80 } }
microEtl: { replicas: 1 }
baseGraphEtl: { replicas: 1 }
trainOperationEtl: { replicas: 1 }
businessClockEtl: { replicas: 1 }
restrictionEtl: { replicas: 1 }
mfe-train-operation:
  { deploymentType: "infra-rivm", endpoints: { apiPrefix: "infra" } }
rimfe-restriction:
  { deploymentType: "infra-rivm", endpoints: { apiPrefix: "infra" } }
```

Container env injection is delegated to `rise.common.connection.mongodb` and
`rise.common.connection.rabbitmq`; the query service additionally receives
`SERVER_PORT = {{ .Values.querySvc.service.port }}`. **No secret is referenced in-repo** — the
`rise-common` library chart supplies them.

## 17.11 Tooling configuration files

| File                                                            | Purpose                                                                                                        |
| --------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| `components/infra-webapp/.eslintrc.json`                        | ESLint (Angular + TypeScript + Prettier)                                                                       |
| `components/infra-webapp/.prettierrc`, `.prettierignore`        | Prettier                                                                                                       |
| `components/infra-webapp/.editorconfig`                         | Editor defaults                                                                                                |
| `components/infra-webapp/.npmrc`, `.yarnrc.yml`                 | Registry + Yarn 4 config — may contain a registry auth token → `[SECRET / CREDENTIAL PRESENT — VALUE OMITTED]` |
| `components/infra-webapp/karma.conf.js`                         | Karma (Chromium headless, coverage, JUnit reporter)                                                            |
| `components/infra-webapp/tsconfig{,.app,.spec}.json`            | TypeScript                                                                                                     |
| `module-tests/playwright.config.js`                             | Playwright + playwright-bdd                                                                                    |
| `module-tests/config/db.config.js`, `config/rabbitmq.config.js` | E2E infrastructure config                                                                                      |
| `gradle/libs.versions.toml`                                     | Gradle version catalogue                                                                                       |
| `CODEOWNERS`                                                    | Ownership                                                                                                      |
| `commitlint.config.js`                                          | Commit message linting                                                                                         |

---

# 18 — COMPLETE FEATURE INVENTORY

Legend: ✔ = present, ✖ = not present, ⚠ = present but external/partial.

| Feature                                                | Frontend                                                                                      | Backend                                                      | DB                             | RabbitMQ                                                     | APIs                                     | Main Files                                                                                                               |
| ------------------------------------------------------ | --------------------------------------------------------------------------------------------- | ------------------------------------------------------------ | ------------------------------ | ------------------------------------------------------------ | ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| **Rail network rendering (nodes + edges)**             | `InfraContentComponent`, `MapService`, `OpenLayerInfraUtility`                                | `BaseGraphController` → `BaseGraphService`                   | `infra-rivm.basegraph`         | `InfraMicroscopicRegionEvent` → `infra-basegraph-etl`        | `GET /basegraph`                         | `open-layer-infra.utility.ts`, `map.service.ts`, `BaseGraphMapper.java`, `InfraBaseGraphService.java`                    |
| **Station (location) labels**                          | `OpenLayerLocationLabelUtility`, `LocationsStore`                                             | `LocationTrackCoordinatesController` → `…Service`            | `infra-rivm.track-coordinates` | `InfraMicroscopicRegionEvent` → `infra-micro-etl`            | `GET /location-track-coordinates`        | `open-layer-location-label.utility.ts`, `locations.store.ts`, `MongoTrackCoordinatesRepositoryCustomImpl.java`           |
| **Platform (track) labels**                            | same as above                                                                                 | same                                                         | same                           | same                                                         | same                                     | same                                                                                                                     |
| **Train position rendering**                           | `OpenLayerClusterUtility`, `TrainPositionStore`                                               | `TrainPositionController` → `TrainPositionService`           | `infra-rivm.train-position`    | `TrainOperationEvent` → `infra-trainoperation-etl`           | `POST /trainpositions`                   | `open-layer-cluster.utility.ts`, `train-position.store.ts`, `InfraTrainOperationService.java`, `TrainOperationUtil.java` |
| **Train forecast positions**                           | same store, no visual distinction                                                             | same                                                         | same                           | `TrainOperationForecastEvent`                                | same                                     | `RiseToInfraForecastMapper.java`                                                                                         |
| **Dynamic train clustering**                           | `OpenLayerClusterUtility.getClusteringDistanceForZoom`, `MapService.updateClusteringDistance` | ✖                                                            | ✖                              | ✖                                                            | ✖                                        | `open-layer-cluster.utility.ts`, `open-layer.config.ts` (`CLUSTER_CONFIG`)                                               |
| **Clustering on/off toggle**                           | `InfraContentComponent.toggleClustering`, `MapService.setClusteringEnabled`                   | ✖                                                            | ✖                              | ✖                                                            | ✖                                        | `infra-content.component.html/.ts`                                                                                       |
| **Train label collision avoidance**                    | `LabelPlacementEngine`                                                                        | ✖                                                            | ✖                              | ✖                                                            | ✖                                        | `label-placement.engine.ts`                                                                                              |
| **Train colour by type**                               | `train-type.utility.ts`                                                                       | ✖                                                            | ✖                              | ✖                                                            | ✖                                        | `train-type.utility.ts` (`TRAIN_TYPES`, `extractTrainColor`)                                                             |
| **Train hover popover**                                | `TooltipPositionService`, `mapFeatureToPopoverData`, `RivmTrainInformationPopoverComponent`   | ✖                                                            | ✖                              | ✖                                                            | ✖                                        | `tooltip-position.service.ts`, `train-popover.mapper.ts`                                                                 |
| **Train selection & focus**                            | `MapService.setSelectedTrain/focusSelectedTrain`                                              | ✖                                                            | ✖                              | ✖                                                            | ✖                                        | `map.service.ts`, `train-edit.handlers.ts`                                                                               |
| **Train context menu**                                 | `RivmContextMenuComponent`, `handleTrainContextMenu`                                          | ✖                                                            | ✖                              | ✖                                                            | ✖                                        | `infra-content.component.ts`, `infra-view.config.ts` (`TRAIN_LIST_CONTEXT_MENU`)                                         |
| **Train Information Panel (TIP)**                      | `PanelStateStore.openTIP`, `tps-mfe-train-info-panel`                                         | ⚠ external MFE backend                                       | ⚠                              | ✖                                                            | ⚠ `NOT DETERMINED`                       | `master-layout.component.html`, `panel-state.store.ts`                                                                   |
| **Train list panel**                                   | `tps-mfe-train-list`, `MfeViewTrainListComponent` (unused wrapper)                            | ⚠ external                                                   | ⚠                              | ✖                                                            | ⚠                                        | `master-layout.component.html`, `mfe-view-train-list.component.ts`                                                       |
| **Train edit (arrival/departure/track)**               | `tps-mfe-train-edit-panel`, `train-edit.handlers.ts`, ribbon `editSection`                    | ⚠ external MFE backend                                       | ⚠                              | ✖ (indirect via re-ingest)                                   | ⚠ `NOT DETERMINED`                       | `train-edit.handlers.ts`, `ribbon.handlers.ts`, `master-layout.ribbon-sections.ts`                                       |
| **Restriction rendering**                              | `OpenLayerRestrictionUtility`, `RestrictionsStore`, `RestrictionDisplayUtility`               | `RestrictionController` → `RestrictionService`               | `infra-rivm.restriction`       | `RestrictionEvent` → `infra-restriction-etl`                 | `GET /restrictions`                      | `open-layer-restriction.utility.ts`, `restriction-display.utility.ts`, `RestrictionMapper.java`                          |
| **Restriction hover popover + halo**                   | `TooltipPositionService.tryRenderRestrictionTooltip`, `mapRestrictionFeatureToPopoverData`    | ✖                                                            | ✖                              | ✖                                                            | ✖                                        | `restriction-popover.mapper.ts`, `tooltip-position.service.ts`                                                           |
| **Restriction list panel**                             | `MfeViewRestrictionListComponent` → `tps-mfe-restriction-list`                                | ⚠ external                                                   | ⚠                              | ✖                                                            | ⚠                                        | `mfe-view-restriction-list.component.ts`                                                                                 |
| **Restriction activate/deactivate**                    | `RibbonStateStore`, `buildRestrictionActionItems`, `handleRestrictionAction`                  | ⚠ PATCH inside the MFE                                       | ⚠                              | ✖ (indirect)                                                 | ⚠ `NOT DETERMINED`                       | `ribbon.handlers.ts`, `master-layout.ribbon-sections.ts`                                                                 |
| **Business clock (live)**                              | `BusinessClockEffects`, `businessClockReducer`, header                                        | `BusinessClockController` → `BusinessClockService`           | `infra-rivm.business-clock`    | `BusinessClockEvent` → `infra-business-clock-etl`            | `GET /business-clock`                    | `business-clock.effect.ts`, `business-clock.reducer.ts`, `BusinessClockService.java`                                     |
| **Custom clock (date/time pickers)**                   | `customClockReducer`, `header.handlers.ts`                                                    | ✖                                                            | ✖                              | ✖                                                            | ✖                                        | `business-clock.reducer.ts`, `header.handlers.ts`                                                                        |
| **Time-offset slider (time travel)**                   | `InfraContentComponent`, `TimeCalculationService`                                             | ✖                                                            | ✖                              | ✖                                                            | ✖ (drives tile ids + `effectiveAt`)      | `infra-content.component.ts/.html`, `time-calculation.service.ts`                                                        |
| **3D data tiling (X, Y, Time)**                        | `TileManagementService`, `TrainPollingCoordinatorService`                                     | `DataTileService`                                            | `infra-rivm.data-tile`         | ✖                                                            | `POST /trainpositions`                   | `tile-management.service.ts`, `DataTileService.java`                                                                     |
| **Tile version delta transfer**                        | `TrainPositionStore` (version bookkeeping)                                                    | `TrainPositionService.hasTileVersionChanged`                 | `infra-rivm.data-tile`         | ✖                                                            | `POST /trainpositions`                   | `TrainPositionService.java`, `APIMapper.java`, `train-position.store.ts`                                                 |
| **Viewport-scoped polling**                            | `TrainPollingCoordinatorService.handleZoomChange/handleViewportChange`                        | ✖                                                            | ✖                              | ✖                                                            | ✖                                        | `train-polling-coordinator.service.ts`                                                                                   |
| **Map configuration (data-driven)**                    | `MapConfigStore`, `MapConfigService`                                                          | `ConfigController` → `ConfigService`; ETL `MapConfigService` | `infra-rivm.map-config`        | ✖                                                            | `GET /configs`                           | `configs.store.ts`, `map-config-api.service.ts`, `MapConfigService.java`                                                 |
| **Overview mini-map (frozen)**                         | `OpenLayerInfraUtility.createOverviewMapControl/setupFrozenOverview`                          | ✖                                                            | ✖                              | ✖                                                            | ✖                                        | `open-layer-infra.utility.ts`                                                                                            |
| **Layer show/hide filter panels**                      | `InfraElementsPanelComponent`, `TrainOperationsPanelComponent`, `FilterStateStore`            | ✖                                                            | ✖ (localStorage)               | ✖                                                            | ✖                                        | `filter-panel.handlers.ts`, `filter-state.store.ts`, `panels/**`                                                         |
| **Panel geometry state machine**                       | `PanelStateStore`, `LeftPanelStore`, `AemPanelStore`, `RivmFrameComponent`                    | ✖                                                            | ✖                              | ✖                                                            | ✖                                        | `panel-state.store.ts`, `panel.handlers.ts`, `sidebar.handlers.ts`                                                       |
| **Ribbon bar (mode-dependent)**                        | `MasterLayoutComponent.ribbonSections`, `master-layout.ribbon-sections.ts`                    | ✖                                                            | ✖                              | ✖                                                            | ✖                                        | `infra.config.ts`, `master-layout.ribbon-sections.ts`                                                                    |
| **AEM events panel**                                   | `AemPanelStore`, `tps-aem-events-panel`                                                       | ⚠ external                                                   | ⚠                              | ⚠ `event.detection` (external consumer)                      | ⚠ `/aem/query/**`                        | `aem-panel.store.ts`, `sidebar.handlers.ts`                                                                              |
| **IndexedDB caching**                                  | `InfraCacheDbService` (Dexie)                                                                 | ✖                                                            | IndexedDB `RIVM-INFRA`         | ✖                                                            | ✖                                        | `infra-cache-db.service.ts`, `cache.config.ts`                                                                           |
| **i18n (en-US + fr)**                                  | `$localize`, `messages.xlf`, `messages.fr.xlf`                                                | ✖                                                            | ✖                              | ✖                                                            | ✖                                        | `angular.json`, `src/locale/**`                                                                                          |
| **Demo / offline mode**                                | `httpMockInterceptor` + `src/app/mocks/**`                                                    | ✖                                                            | ✖                              | ✖                                                            | ✖                                        | `http-mock.interceptor.ts`, `mocks/data/**`, `public/mocks/**`                                                           |
| **Snackbar error notification**                        | `SnackbarAlertService`, `SnackbarContentComponent`                                            | ✖                                                            | ✖                              | ✖                                                            | ✖                                        | `snackbar-alert.service.ts`                                                                                              |
| **Sign out**                                           | `LogoutApiService`                                                                            | ⚠ external auth service                                      | ✖                              | ✖                                                            | `POST {baseAuthUrl}/logout`              | `logout-api.service.ts`, `header.handlers.ts`                                                                            |
| **Global exception handling**                          | ✖                                                                                             | `GlobalExceptionHandler`                                     | ✖                              | ✖                                                            | all                                      | `GlobalExceptionHandler.java`, `ErrorCodes.java`                                                                         |
| **Swagger / OpenAPI UI**                               | ✖                                                                                             | springdoc                                                    | ✖                              | ✖                                                            | `/swagger-ui/index.html`, `/v3/api-docs` | `build.gradle.kts` (`springdoc-openapi-starter-webmvc-ui`)                                                               |
| **MongoDB index provisioning**                         | ✖                                                                                             | `IndexConfig` (`@PostConstruct`)                             | `infra-rivm.train-position`    | ✖                                                            | ✖                                        | `IndexConfig.java`                                                                                                       |
| **Track coordinate cache (backend)**                   | ✖                                                                                             | `TrackCoordinatesService` (`@Scheduled` 1 h)                 | reads `track-coordinates`      | ✖                                                            | ✖                                        | `TrackCoordinatesService.java`                                                                                           |
| **Microscopic infra in-memory graph**                  | ✖                                                                                             | `MicroscopicInfraService` (×2 services)                      | ✖ (memory only)                | `InfraOperationalPeriodEvent`, `InfraMicroscopicRegionEvent` | ✖                                        | `MicroscopicInfraService.java` (trainoperation + restriction)                                                            |
| **OpenAPI model code generation**                      | ✖                                                                                             | `openApiGenerate` task                                       | ✖                              | ✖                                                            | ✖                                        | `infra-common-lib/build.gradle.kts`, `infra-model.yaml`, `components/schemas/**`                                         |
| **E2E test harness**                                   | Playwright page objects + BDD features                                                        | RabbitMQ publisher + Mongo seeding                           | seeds `map-config`             | publishes to `rise.events`                                   | drives the UI                            | `module-tests/**`                                                                                                        |
| **Geographic / schematic / octolinear view switching** | ✖ (ribbon `panesSection` all `disabled`)                                                      | ✖                                                            | `MapConfig.mapType` exists     | ✖                                                            | ✖                                        | `infra.config.ts`                                                                                                        |
| **Saved views / add view**                             | ✖ (`disabled`)                                                                                | ✖                                                            | ✖                              | ✖                                                            | ✖                                        | `infra.config.ts` (`LOCATIONS_SECTION`)                                                                                  |
| **Find / filter (ribbon)**                             | ✖ (`disabled`)                                                                                | ✖                                                            | ✖                              | ✖                                                            | ✖                                        | `infra.config.ts` (`BASIC_SECTION`)                                                                                      |
| **Replay**                                             | ✖ (`disabled`)                                                                                | ✖                                                            | ✖                              | ✖                                                            | ✖                                        | `infra.config.ts` (`REPLAY_SECTION`)                                                                                     |
| **Export PDF / CSV / XLSX**                            | ✖ (`disabled`)                                                                                | ✖                                                            | ✖                              | ✖                                                            | ✖                                        | `infra.config.ts` (`EXPORT_SECTION`)                                                                                     |
| **Restriction create / copy / delete (UI)**            | ✖ (`disabled`)                                                                                | ✖                                                            | ✖                              | ✖                                                            | ✖                                        | `infra.config.ts` (`RESTRICTIONS_SECTION`)                                                                               |
| **Signals / blocks / track availability**              | ✖                                                                                             | ✖                                                            | ✖                              | ✖                                                            | ✖                                        | `NOT FOUND`                                                                                                              |
| **Authentication / authorization**                     | ✖                                                                                             | ✖                                                            | ✖                              | ✖                                                            | ✖                                        | `NOT FOUND` (external SSO)                                                                                               |
| **Tabs (multi-view)**                                  | ✖ (reducer exists, not registered)                                                            | ✖                                                            | ✖                              | ✖                                                            | ✖                                        | `store/{actions,reducers,selectors,state}/tabs.*` — dead code                                                            |

---

# 19 — COMPLETE SERVICE INVENTORY

| Service                        | Technology                                                                                                                                                            | Purpose                                                                                                                                                                | APIs                                                          | DB                                                                                                                   | RabbitMQ                                                                              | Dependencies                                                                                                                  |
| ------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| **`platform`**                 | Gradle `java-platform` (BOM)                                                                                                                                          | Central dependency constraints (Spring Boot 4.1.0, Jackson 2.19.2, Testcontainers 1.21.4, springdoc 3.0.3, swagger 2.2.28, openapi-generator 7.20.0, awaitility 4.2.0) | —                                                             | —                                                                                                                    | —                                                                                     | —                                                                                                                             |
| **`infra-common-lib`**         | Java 21, Spring Boot 4.1.0, OpenAPI Generator (spring), Spring Data MongoDB, Lombok, `rise-api-utils`                                                                 | Generated domain model + pure repository interfaces + Mongo adapters + `APIResponse`/`APIPaginatedResponse` + `GlobalExceptionHandler`                                 | — (library)                                                   | All 7 collections (definitions)                                                                                      | —                                                                                     | `platform`, `rise-api-utils`, swagger/jackson annotations                                                                     |
| **`infra-query-svc`**          | Java 21, Spring Boot Web MVC, springdoc, Spring Data MongoDB, Lombok                                                                                                  | Read-only REST API for the SPA                                                                                                                                         | 7 endpoints under `/api/infra/query` (§6)                     | reads `business-clock`, `basegraph`, `track-coordinates`, `train-position`, `data-tile`, `restriction`, `map-config` | **none**                                                                              | `platform`, `infra-common-lib`                                                                                                |
| **`infra-business-clock-etl`** | Java 21, Spring Boot, Spring AMQP (via `rise-api-utils`), Spring Data MongoDB                                                                                         | Ingest the platform business clock                                                                                                                                     | —                                                             | writes `business-clock` (delete-all + save)                                                                          | consumes `de.hacon.tps.rise.client.businessclock.event.consumer`                      | `platform`, `infra-common-lib`, `rise-api-utils`                                                                              |
| **`infra-micro-etl`**          | same stack                                                                                                                                                            | Flatten microscopic regions into per-track coordinate documents                                                                                                        | —                                                             | writes `track-coordinates`                                                                                           | consumes `…client.inframicro.event.consumer`                                          | `platform`, `infra-common-lib`, `rise-api-utils`                                                                              |
| **`infra-basegraph-etl`**      | same stack                                                                                                                                                            | Persist the microscopic node/edge base graph per region                                                                                                                | —                                                             | writes `basegraph`                                                                                                   | consumes `…client.infrabasegraph.event.consumer`                                      | `platform`, `infra-common-lib`, `rise-api-utils`                                                                              |
| **`infra-trainoperation-etl`** | Java 21, Spring Boot, `@EnableScheduling`, Spring AMQP, Spring Data MongoDB, `rise-infra-utils`                                                                       | Convert train operations + forecasts into tiled train positions                                                                                                        | —                                                             | writes `train-position`, `data-tile`; reads `track-coordinates`, `map-config`; creates 3 indexes                     | consumes 4 queues (train-operation, forecast, operational-period, microscopic-region) | `platform`, `infra-common-lib`, `rise-api-utils`, `rise-infra-utils`                                                          |
| **`infra-restriction-etl`**    | Java 21, Spring Boot, Spring AMQP, Spring Data MongoDB, `rise-infra-utils`                                                                                            | Convert restriction events (segments → edge paths) into restriction documents                                                                                          | —                                                             | writes `restriction`                                                                                                 | consumes 3 queues (restriction, operational-period, microscopic-region)               | `platform`, `infra-common-lib`, `rise-api-utils`, `rise-infra-utils`                                                          |
| **`infra-webapp`**             | Angular 21.2, TypeScript 5.9, OpenLayers 10.10, NgRx 21 (Store/Effects/Signals/DevTools), Angular Material 21, ag-grid 32.3, Dexie 4.4, moment-timezone 0.5, Yarn 4.5 | The single-page dispatcher UI                                                                                                                                          | consumes all 7 query APIs + `{baseAuthUrl}/logout` + MFE APIs | IndexedDB `RIVM-INFRA`, `localStorage`                                                                               | — (no direct broker access)                                                           | `@tps/rivm-common-components 2.9.1`, `@tps/mfe-train-operation 2.7.3`, `@tps/rimfe-restriction 0.7.0`, `@tps/rimfe-aem 1.1.1` |
| **`module-tests`**             | Node ESM, Playwright 1.59.1, playwright-bdd 9.2.0, Cucumber 13, amqplib 0.10.9, mongodb 7.0, `@tps/mfe-train-operation-qa 2.7.1`                                      | Event-driven E2E / smoke / regression suite with canvas pixel validation                                                                                               | drives the UI                                                 | seeds/reads `risedb`                                                                                                 | **publishes** to `rise.events`                                                        | —                                                                                                                             |

### External services (referenced, not implemented here)

| Service                                  | Role                                                           |
| ---------------------------------------- | -------------------------------------------------------------- |
| RISE `de.hacon.tps.rids.business_clock`  | Publishes `BusinessClockEvent`                                 |
| RISE `de.hacon.tps.rids.train_operation` | Publishes `TrainOperationEvent`, `TrainOperationForecastEvent` |
| RISE `de.hacon.tps.rids.restriction`     | Publishes `RestrictionEvent`                                   |
| `bridge.infra` / `rise.bridge.tps_live`  | Publishes infra events / originates commands                   |
| `mfe-train-operation` backend            | Train list, TIP, edit (PUT)                                    |
| `rimfe-restriction` backend              | Restriction list, state PATCH                                  |
| `rimfe-aem` backend                      | Detection events, describers, unread counts                    |
| Keycloak SSO + API gateway               | Authentication, routing, endpoint allow-listing                |
| MongoDB `risedb`                         | Shared datastore                                               |
| RabbitMQ                                 | Shared event bus                                               |
| Artifactory / OCI Helm registry          | Build & deploy artefacts                                       |

---

# 20 — COMPLETE DATA-FLOW MAP

## 20.1 Synchronous read — map bootstrap (base graph)

```
USER opens /ui/infra
  ↓
main.ts → bootstrapApplication(AppComponent, appConfig)
  ↓
Router: '' → 'home' → MasterLayoutComponent → InfraContentComponent
  ↓
InfraContentComponent.ngOnInit() → loadConfigurations() → loadEdgeDataAndSubscribe()
  ↓
NgRx: store.dispatch(loadEdgeData())
  ↓
EdgeDataEffects.loadEdgeData$   (withLatestFrom selectEdgeDataLoaded, filter !loaded)
  ↓
BaseGraphApiService.getEdgeData()
  ↓
InfraCacheDbService.get$('infra_basegraph_cache')   ── HIT (age < 1 h) ⇒ skip HTTP
  ↓ MISS
HttpClient GET  {baseUrl}/basegraph
  ↓
[API GATEWAY]  endpoints.yaml: GET /api/infra/query/basegraph, params pageNumber/pageSize, permissions null
  ↓
BaseGraphController.getAllBaseGraphDetails(pageNumber=0, pageSize=1000)   @Valid @Min/@Max
  ↓
BaseGraphService.getAllBaseGraphs → PageRequest.of(0, 1000)
  ↓
BaseGraphRepository.findAll(Pageable)                       [pure interface]
  ↓
MongoBaseGraphRepositoryCustomImpl.findAll                  [@Component adapter]
  ↓
MongoBaseGraphRepository.findAll                            [Spring Data]
  ↓
MongoDB  risedb.infra-rivm.basegraph
  ↑ Page<MongoBaseGraphEntity>
PageImpl<BaseGraph>
  ↑
APIMapper.mapPageToMetaPage(page) → Meta{ page }
  ↑
APIPaginatedResponse<BaseGraph>{ data, meta }
  ↑
Jackson (@JsonInclude NON_NULL) → JSON
  ↑
BaseGraphApiService  map(r => Array.isArray(r.data) ? r.data : [])
                     tap(d => cacheDb.set('infra_basegraph_cache', d))
  ↑
loadEdgeDataSuccess({ edgeData })
  ↑
edgeDataReducer → state.edgeData
  ↑
selectAllEdgeData → InfraContentComponent.edgeData$.subscribe
  ↓
OpenLayerInfraUtility.extractNodes(edgeData)  → InfraNode[]
OpenLayerInfraUtility.extractEdges(edgeData)  → EdgeRecord[]
  ↓
TrainPollingCoordinatorService.initializeTiles(nodes, trainsLayer, currentTimestamp)
  ↓
MapService.loadGraphData(nodes, edges)
   vectorSource.clear()
   MapStateStore.setLoadedNodes(nodes)
   createNodeFeatures → Feature(Point)
   createEdgeFeatures → Feature(LineString)
  ↓
MapService.fitViewToData() → View.fit(extent, padding [50,50,50,50], maxZoom 10)
                           → View.setMinZoom(fittedZoom)
  ↓
MapService.loadOverviewMapData() → setupFrozenOverview()
  ↓
OpenLayers canvas: grey (#898995) 1-px polylines
  ↓
USER sees the rail network
```

## 20.2 Synchronous read — train position poll

```
USER pans / zooms the map
  ↓
OL 'moveend' / 'change:resolution'
  ↓
InfraContentComponent.handleMoveEnd / handleResolutionChange
  ↓
TrainPollingCoordinatorService.handleViewportChange / handleZoomChange
   shouldPoll = zoom >= selectedZoomLevel (trainsLayer.minZoom)
  ↓
TileManagementService.getVisibleTiles(extent, tileResult, timestamp)
   tileId = `${tileMinX + i*xSize}_${tileMinY + j*ySize}_${roundedTimestamp}`
  ↓
TrainPositionStore.setActiveTileIds(visibleTileIds)   (preserves known versions)
TrainPositionStore.startPolling()                     (merge(interval, fetchNow$))
  ↓
TrainPositionService.getTrainPositions(tiles, 0, 1000)
  ↓
HTTP POST {baseUrl}/trainpositions?pageNumber=0&pageSize=1000
Body: [{ id }, { id, version }, …]
  ↓
[GATEWAY] POST allowed, headers Content-Type/Content-Length
  ↓
TrainPositionController.getPositions   @Valid @NotEmpty List<@Valid DataTile>
  ↓
TrainPositionService.getModifiedTrainPositionsByTiles
   validateDataTiles → BadRequestException("…", "20001") on a null/empty id
   tileMap = toMap(DataTile::getId, identity)
   DataTileRepository.findAllById(ids) ────────────► MongoDB infra-rivm.data-tile
   filter hasTileVersionChanged(stored, requested)
   ├─ nothing changed → Page.empty()      (no train-position query at all)
   └─ changed → TrainPositionRepository.findByDataTileIdsIn(
                  changedIds, PageRequest.of(p, s, Sort.by(ASC, "id", "trainServiceId")))
                                        ────────────► MongoDB infra-rivm.train-position
                                                       index { dataTileIds, _id, trainServiceId }
   APIMapper.mapPageToMetaPage(page, updatedTileVersions)
  ↑
APIPaginatedResponse<TrainPosition>{ data, meta.page, meta.dataTileVersions[0] }
  ↑
TrainPositionStore
   versionsMap = meta.dataTileVersions[0]
   tiles      = tiles.map(t => ({ id: t.id, version: versionsMap[t.id] ?? t.version }))
   positions  = merge existing by id + append new
  ↑
toObservable(store.positions) → InfraContentComponent.updateTrainDisplay()
  ↓
TimeCalculationService.filterPositionsByTime(positions, adjustedTimestamp)
   keep fromTime <= t <= toTime, then per train keep the earliest toTime
  ↓
MapService.updateTrainPositions(filtered)
   trainPositionsVectorSource.clear()
   OpenLayerClusterUtility.createTrainPositionFeatures(...)
   trainPositionsClusterSource.refresh()
  ↓
Layer style fn → getClusterStyle / resolveTrainStyles
   size === 1 → Icon(buildTrainIconDataUri(colour)) [+ connector line + label at zoom > 18]
   size  >  1 → hit circle + donut renderer + cluster_train.svg + count text
  ↓
InfraContentComponent.updateTrainVisibility()
   setTrainLayerVisible(zoom >= selectedZoomLevel && filterStateStore.showTrains())
  ↓
USER sees trains
```

## 20.3 Synchronous read — restriction poll

```
InfraContentComponent.handleRestrictionsZoomChange(zoom)
   shouldPoll = zoom > restrictionsMinZoom && isGraphLoaded() && !!baseBusinessTime
  ↓
RestrictionsStore.startPolling(baseBusinessTime)
   interval(pollingIntervalMs).pipe(startWith(0), takeUntil(stopPolling$))
  ↓
RestrictionApiService.getRestrictionData(store.currentBusinessTime(), 0, 100)
  ↓
HTTP GET {baseUrl}/restrictions?effectiveAt=…&pageNumber=0&pageSize=100
  ↓
RestrictionController.getRestrictionsByTime(Instant effectiveAt, …)
  ↓
RestrictionService.getRestrictionsByEffectiveTime
   PageRequest.of(p, s, Sort.by(DESC, "lastModified"))
  ↓
RestrictionRepository.findByEffectiveTime
  ↓
MongoRestrictionRepository @Query
   { 'restrictionData.effectiveTimePeriod.startTime': { $lte: "<t>" },
     'restrictionData.effectiveTimePeriod.endTime':   { $gte: "<t>" } }
  ↓
MongoDB infra-rivm.restriction   (collection scan — no index)
  ↑
APIPaginatedResponse<Restriction>
  ↑
RestrictionApiService.normalizeApiResponse
   id = id ?? _id ; impacts ?? [] ; edgePaths ?? [] ; pathEdges ?? [] ; pathCoordinates ?? []
  ↑
RestrictionsStore.restrictions
  ↑
computed visibleRestrictionInfos
   RestrictionDisplayUtility.getVisibleRestrictionInfo
      isActive = state === 'EFFECTIVE'
      pathCoordinateSets = edgePaths.map(pathCoordinates → [x,y][]) filtered length >= 2
      pathLocations      = "x0, y0 → xN, yN"
      colour             = isActive ? icon/style colour : '#999'
  ↑
toObservable → InfraContentComponent.updateRestrictionsDisplay(infos)
  ↓
MapService.updateRestrictions(infos)
  ↓
OpenLayerRestrictionUtility.updateRestrictionFeatures
   one LineString Feature per coordinate set
  ↓
Style fn → [hover white stroke] + colour stroke + translucent stroke + midpoint composite Icon
  ↓
updateRestrictionsVisibility()
   showRestrictions && zoom > restrictionsMinZoom && infos.length > 0
  ↓
USER sees restriction overlays
```

## 20.4 Asynchronous write — train operation ingest

```
RISE de.hacon.tps.rids.train_operation
  ↓ publish (JSON, header signature=sha256, persistent)
RABBITMQ EXCHANGE  rise.events   (topic, durable)
  ↓ ROUTING KEY  event.train_operation.train_operation
QUEUE  de.hacon.tps.rise.client.trainoperation.event.consumer
  ↓ rise-api-utils listener + signature/schema validation
InfraTrainOperationMovementEventHandler.handleValidatedMessage(TrainOperationEvent)
  ↓ RISEApplicationContext.getComponent(InfraTrainOperationService)
InfraTrainOperationService.processTrainOperationMovementEvent
  ↓ processEventWithErrorHandling  (ENTITY_CREATED | ENTITY_UPDATED)
processMovementEventForCreateOrUpdate
  ├─ TrainPositionRepository.findByTrainServiceId(entityID) ──► MongoDB train-position
  ├─ RiseToInfraMapper.map(trainOperationData, trainServiceId, baseEntityData, existing)
  │     TrainOperationUtil.isMapConfigAvailable()
  │        └─ DataTileService.isMapConfigAvailable()
  │              └─ MapConfigService.getMapConfig()  (cached OCTOLINEAR, refreshed every 60 s)
  │     extractAndFilterActivitySequence(activities)
  │        skip !valid | CANCELLED | unknown type | intermediate DEPARTURE
  │             | MOVEMENT without actual | no places | no position ref | no activityId
  │     buildTrainPositionsWithSlidingWindow
  │        TrainOperationUtil.createTrainPosition(params)
  │           resolveCoordinates
  │              LocationReference → [infraAddress first] → TrackCoordinatesService cache
  │                                                          (hourly refresh of ALL track-coordinates)
  │              KmReference       → MicroscopicInfraService.findEdges(infraAddress)
  │                                   └─ rise-infra-utils MicroscopicInfra (in-memory)
  │           setTimeWindows(current, next | +10 min)
  │           DataTileService.createTileIds(trainPosition)
  ├─ filterMovementPositions(new, existing)
  │     MOVEMENT   → keep only ACTUAL
  │     LOCATION   → keep if new OR ACTUAL
  └─ savePositionsAndTiles(positionsToSave)
        DataTileService.createDataTiles(ids) → new UUID per tile
        DataTileRepository.saveAll           ──► MongoDB infra-rivm.data-tile
        TrainPositionRepository.saveAll      ──► MongoDB infra-rivm.train-position
  ↓
[next client poll]
POST /trainpositions → version mismatch → rows returned
  ↓
TrainPositionStore → InfraContentComponent → MapService → OpenLayers
  ↓
USER sees the train move
```

## 20.5 Asynchronous write — forecast ingest

```
RISE train_operation (forecast stream)
  ↓ rise.events / event.train_operation.forecast
QUEUE de.hacon.tps.rise.client.trainoperation.forecast.event.consumer
  ↓
InfraTrainOperationMovementForecastEventHandler
  ↓
InfraTrainOperationService.processTrainOperationMovementForecastEvent
  ↓
processMovementForecastEventForCreateOrUpdate
  trainServiceId = trainOperationForecastData.trainOperationRef        ← not the entity ID
  existing       = repo.findByTrainServiceId(trainServiceId)
  new            = RiseToInfraForecastMapper.map(...)   (runningType always FORECAST)
  ─ delete phase
      existingForecasts = existing.filter(FORECAST)
      repo.deleteAllById(ids)                       ──► MongoDB train-position (delete)
      dataTileService.saveAll(createDataTiles(freedTileIds))  ──► data-tile (version bump)
  ─ actual-frontier phase
      actualFrontier = max(existing.filter(ACTUAL).fromTime)
      keep new rows with fromTime >= actualFrontier
  ─ save phase
      savePositionsAndTiles(kept)                   ──► data-tile + train-position
  ─ gap-closing phase
      extendLastActualToForecast(trainServiceId, kept)
         lastActual.toTime = firstForecast.fromTime  (if earlier)
         savePositionsAndTiles([lastActual])
  ↓
[client poll] → forecast icons refreshed
```

## 20.6 Asynchronous write — restriction ingest

```
RISE de.hacon.tps.rids.restriction
  ↓ rise.events / <routing key NOT DETERMINED>
QUEUE de.hacon.tps.rise.client.restriction.event.consumer
  ↓
RestrictionEventHandler.handleValidatedMessage
   entityID null/blank → log.warn + return true   (ACK & drop)
  ↓
RestrictionService.processRestrictionEvent
  ├ ENTITY_CREATED / ENTITY_UPDATED
  │    RestrictionMapper.mapEventToRestriction
  │       state / effectiveTimePeriod (Instant→String) / group / impacts  → 1:1
  │       segments[] → MicroscopicInfraService.findEdgePaths(segments)
  │                      └─ rise-infra-utils MicroscopicInfra (needs operational-period
  │                         + microscopic-region events already applied)
  │                    → EdgePath{ pathEdges[EdgeWithOffsets], pathCoordinates[{x,y}] }
  │       meta.ui.icon/style (base64) → 1:1
  │    RestrictionRepository.save                 ──► MongoDB infra-rivm.restriction
  ├ ENTITY_DELETED → RestrictionRepository.deleteById ──► delete
  └ default        → log.warn "Unhandled trigger type"
  ↓ (rethrows on error → handler returns false → NACK)
[client poll] GET /restrictions?effectiveAt=…
  ↓
RestrictionsStore → MapService.updateRestrictions → OpenLayers
  ↓
USER sees the restriction
```

## 20.7 Asynchronous write — infrastructure ingest (three consumers of one event)

```
bridge.infra
  ↓ rise.events / event.infra.microscopic_region
  ├──────────────────────────────┬────────────────────────────┬─────────────────────────────┐
  ▼                              ▼                            ▼                             │
QUEUE …inframicro.event.       QUEUE …infrabasegraph.       QUEUE …infra.microscopic-       │
      consumer                       event.consumer                region.event.consumer     │
  ▼                              ▼                            ▼ (competing: trainoperation  │
InfraMicroEventHandler         InfraBaseGraphEventHandler        -etl vs restriction-etl)    │
  ▼                              ▼                            ▼                             │
InfraMicroService              InfraBaseGraphService         MicroscopicInfraService         │
  .setInfraRicro(event)          .processBaseGraphEvent        .addMicroscopicRegion(event)  │
  ▼                              ▼                            ▼                             │
RiseToInfraMapper.map          BaseGraphMapper.map           MicroscopicInfra                │
  indexBaseGraphNodes            validate + rename             .addMicroscopicRegionData     │
  per location × track:          infraAddress→infraNodeAddress (IN-MEMORY, not persisted)    │
   id = loc_track                kmValueMillimeters→kmValue                                  │
   nodeCoordinates ← nodeRefs    List→LinkedHashSet                                          │
  ▼                              ▼                                                           │
TrackCoordinatesRepository     BaseGraphRepository.save                                      │
  .saveAll                                                                                   │
  ▼                              ▼                                                           │
MongoDB track-coordinates      MongoDB basegraph                                             │
  ▼                              ▼                                                           │
GET /location-track-coordinates GET /basegraph                                               │
  ▼                              ▼                                                           │
station + platform labels      network polylines           ── enables km→coordinate and ─────┘
                                                              segment→edgePath resolution
```

## 20.8 Time-travel data flow

```
USER drags the time slider (or picks a date/time in the header)
  ↓ (a) slider
InfraContentComponent.onTimeOffsetChange() → updateTimestamps()
  ↓ (b) header
MasterLayoutComponent.onClockChange → handleDateChange/handleTimeChange
  → store.dispatch(setCustomClockDateTime({date, time, businessTimeZone}))
  → customClockReducer (moment parse → UTC → recompute timeWindow, customClockEnabled = true)
  → selectEffectiveClock  → InfraContentComponent.subscribeToBusinessClock → updateTimestamps()
  ↓
updateTimestamps()
  timeSpanSecs    = trainsLayer.tileSize.timeSpanSecs ?? 900
  adjustedUtcTime = applyTimeOffsetInUtc(baseBusinessTime, offsetSeconds / 60)
  RestrictionsStore.setCurrentBusinessTime(adjustedUtcTime)     → next restriction poll uses it
  roundedTimestamp = roundToInterval(adjustedUtcTime, timeSpanSecs / 60)  → "yyyy-MM-ddTHH:mm"
  ↓ if roundedTimestamp changed
recalculateTiles()
  TrainPollingCoordinatorService.recalculateTiles(nodes, trainsLayer, ts, getExtent)
     TileManagementService.calculateAndStoreTiles(...)
     if polling → updateVisibleTiles(ts, getExtent) → setActiveTileIds(newIds) → fetchNow$
  ↓
POST /trainpositions with the NEW tile ids (all versions undefined ⇒ full payload)
  ↓
updateTrainDisplay() → filterPositionsByTime(positions, adjustedTimestamp)
  ↓
USER sees the network at a different point in time
```

## 20.9 Panel / UI-state flow

```
USER clicks the sidebar "train" item
  ↓
RivmFrameComponent (sidebar) → MasterLayoutComponent.onMenuSelected(SidebarMenuItem)
  ↓
handleMenuSelected(ctx, event)
  key 'messages'     → toggleAemPanel(ctx)
  otherwise          → aemPanelStore.close()
  key 'train'        → toggleDockedList(ctx, isTrainListVisible, openTrainListCollapsed)
  key 'restrictions' → toggleDockedList(...) + setSelectedRestriction(null)
  key 'home'         → navigateHome(ctx)   (blocked while isEditPanelDirty)
  ↓
PanelStateStore.openTrainListCollapsed()  → trainListState='collapsed', restrictionListState='none'
clearPanelContextWhenNoOverlay(ctx)       → updatePanelContext({}), MapService.setSelectedTrain(null)
RibbonStateStore.setRibbonExpanded(true) + resetRibbonAction()
  ↓
MasterLayoutComponent computed leftSlotConfig / selectedSidebarMenuKey / ribbonSections recompute
  ↓
Template renders <tps-mfe-train-list [isMinimized]="true" …> in frameLeftPushingSlot
  ↓
InfraContentComponent effect → handlePanelStateChange(trainList, restrictionList, overlay)
  mapResizeSubject.next({...})  → debounceTime(350) → map.updateSize() (+ pan / restore centre)
  ↓
USER sees the panel and a correctly resized map
```

---

# 21 — FILE / CLASS / FUNCTION REFERENCE

> Paths are relative to the repository root `c:\Users\z0059stn\Projects\work\infra\`.
> **None of these files were modified.**

## 21.1 Root & build

| File                                                           | Contents                                                                                                                                  |
| -------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `settings.gradle.kts`                                          | `rootProject.name = "rivm-infra"`; 9 `include(":components:…")`; Artifactory plugin repository                                            |
| `build.gradle.kts`                                             | `de.hacon.tps.convention.root.product` (3.+), `org.openapi.generator` (7.20.0, `apply false`)                                             |
| `gradle/libs.versions.toml`                                    | `tps-convention 3.+`, `org-openapi-generator 7.20.0`, `rise-utils 13.1.0`; libraries `rise-api-utils`, `rise-infra-utils`; plugin aliases |
| `components/platform/build.gradle.kts`                         | `java-platform` BOM (§5.0)                                                                                                                |
| `README.md`                                                    | GitLab template boilerplate + "RIVM Infra … copier template"                                                                              |
| `CODEOWNERS`, `commitlint.config.js`, `gradlew`, `gradlew.bat` | Repo tooling                                                                                                                              |

## 21.2 `components/infra-common-lib`

| File                                                       | Class                       | Key members                                                                                             |
| ---------------------------------------------------------- | --------------------------- | ------------------------------------------------------------------------------------------------------- |
| `build.gradle.kts`                                         | —                           | `openApiGenerate` block (§5.1)                                                                          |
| `infra-model.yaml`                                         | —                           | 13 model `$ref`s                                                                                        |
| `src/main/resources/application.properties`                | —                           | 7 collection names                                                                                      |
| `…/api/response/APIResponse.java`                          | `APIResponse<T>`            | `T data`                                                                                                |
| `…/api/response/APIPaginatedResponse.java`                 | `APIPaginatedResponse<T>`   | `List<T> data`, `Meta meta`, `MIN_PAGE_SIZE=1`, `MAX_PAGE_SIZE=1000`, `COORDINATES_MAX_PAGE_SIZE=10000` |
| `…/exception/ErrorCodes.java`                              | `ErrorCodes`                | `DATA_NOT_FOUND`, `INTERNAL_SERVER_ERROR`, `BAD_REQUEST`, `INVALID_DATA_TILE_ID`                        |
| `…/exception/BadRequestException.java`                     | `BadRequestException`       | `getCode()`                                                                                             |
| `…/exception/ResourceNotFoundException.java`               | `ResourceNotFoundException` | —                                                                                                       |
| `…/exception/GlobalExceptionHandler.java`                  | `GlobalExceptionHandler`    | 5 `@ExceptionHandler`s + `buildResponseEntity`                                                          |
| `…/repository/BaseGraphRepository.java`                    | interface                   | `findAll`, `deleteAll`, `saveAll`, `save`                                                               |
| `…/repository/BusinessClockRepository.java`                | interface                   | `save`, `findAll`, `deleteAll`                                                                          |
| `…/repository/DataTileRepository.java`                     | interface                   | `saveAll`, `findAllById`, `deleteAll`                                                                   |
| `…/repository/MapConfigRepository.java`                    | interface                   | `findAll`                                                                                               |
| `…/repository/RestrictionRepository.java`                  | interface                   | `findByEffectiveTime`, `saveAll`, `deleteAll`, `deleteById`, `save`, `findById`                         |
| `…/repository/TrackCoordinatesRepository.java`             | interface                   | `saveAll`, `findAll(Pageable)`, `findAll()`, `findLocationsWithTracks`, `deleteAll`                     |
| `…/repository/TrainPositionRepository.java`                | interface                   | `findByTrainServiceId`, `saveAll`, `findAllById`, `findByDataTileIdsIn`, `deleteAll`, `deleteAllById`   |
| `…/repository/mongodb/MongoRepositoryConfiguration.java`   | `@EnableMongoRepositories`  | base package                                                                                            |
| `…/repository/mongodb/Mongo*Entity.java` (7)               | entities                    | `@Document(collection="${app.db.collection.*}")`                                                        |
| `…/repository/mongodb/Mongo*Repository.java` (7)           | Spring Data                 | derived + `@Query` methods (§5.1)                                                                       |
| `…/repository/mongodb/Mongo*RepositoryCustomImpl.java` (7) | adapters                    | copy-conversion + `findLocationsWithTracks` aggregation                                                 |

## 21.3 `components/infra-query-svc`

| File                                                       | Class                                | Methods                                                                                                                    |
| ---------------------------------------------------------- | ------------------------------------ | -------------------------------------------------------------------------------------------------------------------------- |
| `…/query/QueryServiceApplication.java`                     | `QueryServiceApplication`            | `main`, `corsConfigurer`                                                                                                   |
| `…/controller/api/BaseGraphController.java`                | `BaseGraphController`                | `getAllBaseGraphDetails`                                                                                                   |
| `…/controller/api/BusinessClockController.java`            | `BusinessClockController`            | `getBusinessClock`                                                                                                         |
| `…/controller/api/ConfigController.java`                   | `ConfigController`                   | `getAllMapConfigs`                                                                                                         |
| `…/controller/api/LocationTrackCoordinatesController.java` | `LocationTrackCoordinatesController` | `getLocationTrackCoordinates`                                                                                              |
| `…/controller/api/RestrictionController.java`              | `RestrictionController`              | `getRestrictionsByTime`                                                                                                    |
| `…/controller/api/TrackCoordinatesController.java`         | `TrackCoordinatesController`         | `getTrackCoordinates`                                                                                                      |
| `…/controller/api/TrainPositionController.java`            | `TrainPositionController`            | `getPositions`                                                                                                             |
| `…/service/BaseGraphService.java`                          | `BaseGraphService`                   | `getAllBaseGraphs`                                                                                                         |
| `…/service/BusinessClockService.java`                      | `BusinessClockService`               | `getBusinessClock`                                                                                                         |
| `…/service/ConfigService.java`                             | `ConfigService`                      | `getAllMapConfigs`                                                                                                         |
| `…/service/LocationTrackCoordinatesService.java`           | `LocationTrackCoordinatesService`    | `getLocationTrackCoordinates`, `DEFAULT_SORT`                                                                              |
| `…/service/RestrictionService.java`                        | `RestrictionService`                 | `getRestrictionsByEffectiveTime`                                                                                           |
| `…/service/TrackCoordinatesService.java`                   | `TrackCoordinatesService`            | `getTrackCoordinates`, `DEFAULT_SORT`                                                                                      |
| `…/service/TrainPositionService.java`                      | `TrainPositionService`               | `getModifiedTrainPositionsByTiles`, `hasTileVersionChanged`, `validateDataTiles`                                           |
| `…/util/APIMapper.java`                                    | `APIMapper<T>`                       | `mapPageToMetaPage(Page)`, `mapPageToMetaPage(Page, Map)`                                                                  |
| `src/main/resources/application.properties`                | —                                    | §5.2                                                                                                                       |
| `src/test/java/**`                                         | 16 test classes                      | controller tests, service tests, 7 `*EndToEndTest` (Testcontainers Mongo)                                                  |
| `src/test/resources/*.json`                                | 7 fixtures                           | `baseGraph`, `data-tiles`, `location-track-coordinates`, `location`, `restriction`, `track-coordinates`, `train-positions` |

## 21.4 ETL services

| File                                                                   | Class   | Key methods                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ---------------------------------------------------------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **business-clock**                                                     |         |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `…/businessclock/etl/InfraBusinessClockEtlApplication.java`            | boot    | `main`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `…/eventhandling/BusinessClockEventHandler.java`                       | handler | `handleValidatedMessage`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `…/service/BusinessClockService.java`                                  | service | `setBusinessClock`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `…/util/RiseToInfraMapper.java`                                        | mapper  | `map`, `convertDate`, `createFormatter`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| **micro**                                                              |         |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `…/micro/etl/InfraMicroEtlApplication.java`                            | boot    | `main`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `…/eventhandling/InfraMicroEventHandler.java`                          | handler | `handleValidatedMessage`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `…/service/InfraMicroService.java`                                     | service | `setInfraMicro`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `…/util/RiseToInfraMapper.java`                                        | mapper  | `map`, `indexBaseGraphNodes`, `toTrackCoordinates`, `mapBaseSubEntityData`, `toNodes`, `toNode`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| **basegraph**                                                          |         |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `…/basegraph/etl/InfraBaseGraphEtlApplication.java`                    | boot    | `main`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `…/eventhandling/InfraBaseGraphEventHandler.java`                      | handler | `handleValidatedMessage`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `…/service/InfraBaseGraphService.java`                                 | service | `processBaseGraphEvent`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| `…/util/BaseGraphMapper.java`                                          | mapper  | `map`, `isValidEvent`, `isValidEntityId`, `mapBaseGraph`, `mapNodes`, `mapEdges`, `mapList`, `mapNode`, `mapNodeData`, `mapNodeCoordinates`, `mapGraphicalCoordinates`, `mapNodeAddress`, `mapEdge`, `mapEdgeData`, `mapDirection`, `mapNodeRef`, `mapBaseSubEntityData`                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| **trainoperation**                                                     |         |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `…/trainoperation/etl/InfraTrainOperationEtlApplication.java`          | boot    | `main`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `…/config/IndexConfig.java`                                            | config  | `initIndexes`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `…/dto/ActivitiesDTO.java`                                             | DTO     | _(unused)_                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `…/dto/ActivityContext.java`                                           | DTO     | `PositionReference`, `LocationReference`, `KmReference`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| `…/eventhandling/InfraTrainOperationMovementEventHandler.java`         | handler | `handleValidatedMessage`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `…/eventhandling/InfraTrainOperationMovementForecastEventHandler.java` | handler | `handleValidatedMessage`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `…/eventhandling/InfraMicroscopicRegionEventHandler.java`              | handler | `handleValidatedMessage`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `…/eventhandling/InfraOperationalPeriodEventHandler.java`              | handler | `handleValidatedMessage`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `…/service/InfraTrainOperationService.java`                            | service | `processTrainOperationEvent`, `processTrainOperationMovementEvent`, `processTrainOperationMovementForecastEvent`, `hasEntityChangedForEvent`, `hasCoordinatesChanged`, `processEventWithErrorHandling`, `processMovementEventForCreateOrUpdate`, `processMovementForecastEventForCreateOrUpdate`, `extendLastActualToForecast`, `isMovementActivity`, `isActualRunningType`, `isForecastRunningType`, `shouldSaveForecastMovement`, `shouldSaveForecastLocation`, `shouldSaveMovementActivity`, `shouldSaveLocationActivity`, `logMovementFilteringSummary`, `logSkippedMovement`, `logMissingLocation`, `filterMovementPositions`, `findExistingPosition`, `countExistingLocationActivities`, `savePositionsAndTiles`, inner `FilteredPositions` |
| `…/service/DataTileService.java`                                       | service | `isMapConfigAvailable`, `saveAll`, `createDataTiles`, `createTileIds`, `validateAndGetTileSize`, `parseTimeRange`, record `TimeRange`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| `…/service/MapConfigService.java`                                      | service | `getMapConfig`, `refresh`, `init` (`@PostConstruct @Scheduled`)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `…/service/MicroscopicInfraService.java`                               | service | `init`, `addMicroscopicRegion`, `findEdges`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `…/service/TrackCoordinatesService.java`                               | service | `init` (`@PostConstruct @Scheduled`), `getCachedCoordinates`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `…/util/RiseToInfraMapper.java`                                        | mapper  | `map`, `isValidTrainOperationData`, `extractAndFilterActivitySequence`, `extractActivityContext`, `isValidActivity`, `isCancelledActivity`, `shouldSkipIntermediateDeparture`, `shouldSkipMovementWithoutActual`, `isValidTimeAndPlaces`, `extractTimeAndPlaces`, `hasActualData`, `hasPlannedData`, `extractActivityId`, `determineOutputActivityType`, `determineActivityType`, `extractPositionReference`, `extractTrackId`, `extractInfraAddressFromActualPlaces`, `filterMovementsBetweenStations`, `isDeparture`, `isArrival`, `isArrivalOrDeparture`, `createTrainPositions`, `extractOriginId`, `extractDestinationId`, `buildTrainPositionsWithSlidingWindow`, `getNextActivity`, `extractLocationId`, inner `TimeAndPlaces`             |
| `…/util/RiseToInfraForecastMapper.java`                                | mapper  | same surface, forecast variants (`extractForecastedTimeAndPlaces`, `extractInfraAddressFromForecastedPlaces`)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `…/util/TrainOperationUtil.java`                                       | util    | `isMapConfigAvailable`, `createFormatter`, `createTrainPosition`, `createTrainPositionForForecast`, `createTrainPositionWithRunningType`, `createBaseTrainPosition`, `setTimeWindows`, `resolveCoordinates`, `resolveLocationCoordinates`, `resolveKmCoordinates`, `formatInstant`, inner `TrainPositionParams`                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `…/util/LocationAttributes.java`                                       | DTO     | _(unused)_                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| **restriction**                                                        |         |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `…/restriction/RestrictionEtlApplication.java`                         | boot    | `main`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `…/eventhandling/RestrictionEventHandler.java`                         | handler | `handleValidatedMessage`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `…/eventhandling/InfraMicroscopicRegionEventHandler.java`              | handler | `handleValidatedMessage`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `…/eventhandling/InfraOperationalPeriodEventHandler.java`              | handler | `handleValidatedMessage`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `…/service/RestrictionService.java`                                    | service | `processRestrictionEvent`, `processEntityForCreateOrUpdate`, `processEntityForDelete`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| `…/service/MicroscopicInfraService.java`                               | service | `init`, `addMicroscopicRegion`, `findEdgePaths`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `…/util/RestrictionMapper.java`                                        | mapper  | `mapEventToRestriction`, `mapRestrictionData`, `mapState`, `mapEffectiveTimePeriod`, `mapGroup`, `mapImpacts`, `mapImpact`, `mapTrainFilter`, `mapTrainOperationFilter`, `mapTrainCompositionFilter`, `mapFilterConditionOperatorToOperationFilter`, `mapFilterConditionOperatorToCompositionFilter`, `mapPropertyFilterConditions`, `mapPropertyFilterCondition`, `mapPropertyValueFilterOperator`, `mapBlocking`, `mapSpeedReduction`, `mapAdhesion`, `mapAdhesionLevel`, `mapEdgePaths`, `mapInfraEdgePath`, `mapInfraEdgeWithOffsets`, `mapInfraMicroscopicEdgeRef`, `mapInfraMicroscopicNodeRefRegionRef`, `mapInfraMicroscopicNodeRefInfraMicroscopicNodeRef`, `mapGraphicalCoordinates`, `mapMeta`, `mapUi`, `mapUiIcon`                   |

Each ETL also has `src/main/resources/application.properties` and
`src/main/resources/META-INF/spring.factories` (§10.7), plus `src/test/**` fixtures (§11).

## 21.5 Frontend — full file map

_(Only non-spec `.ts`/`.html` files; every one has a colocated `.spec.ts` unless noted.)_

| File                                                                         | Symbol(s)                                                                                                                                                                                                                                                         |
| ---------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/main.ts`                                                                | bootstrap                                                                                                                                                                                                                                                         |
| `src/index.html`                                                             | shell                                                                                                                                                                                                                                                             |
| `src/app/app.component.ts/.html/.scss`                                       | `AppComponent`                                                                                                                                                                                                                                                    |
| `src/app/app.config.ts`                                                      | `appConfig`                                                                                                                                                                                                                                                       |
| `src/app/app.routes.ts`                                                      | `routes`                                                                                                                                                                                                                                                          |
| `src/app/app-initializer.ts`                                                 | `initializeApp`                                                                                                                                                                                                                                                   |
| `src/app/app-constant.ts`                                                    | `DATE_FORMAT`, `TIME_FORMAT`, `BUSINESS_CLOCK_API_POLLING_TIMER`, `TILE_API_POLLING_TIMER`, `PAGE_SIZE`                                                                                                                                                           |
| `src/app/config/cache.config.ts`                                             | `CACHE_TTL_MS`, 3 cache keys                                                                                                                                                                                                                                      |
| `src/app/config/filter-panels.config.ts`                                     | `INFRA_ELEMENTS_PANEL_CONFIG`, `TRAIN_OPERATIONS_PANEL_CONFIG`                                                                                                                                                                                                    |
| `src/app/config/infra-view.config.ts`                                        | `INFRA_VIEW`, `INFRA_ZOOM_CONFIG`, `MAP_VIEW_CONFIG`, `INFRA_COLOR_CONFIG`, `ISO_DATE_PATTERN`, `OPERATING_DAY_FORMAT`, `DEFAULT_TIMEZONE`, `INFRA_URLS`, `RESTRICTION_MINIMIZED_COLUMNS`, `TRAIN_LIST_CONTEXT_MENU`                                              |
| `src/app/config/infra.config.ts`                                             | `HEADER_APPS_AND_MENU_LIST`, `ICONS_PATH`, `ICONS`, 10 ribbon arrays, `RIBBON_SECTIONS_COLLECTIONS`, `SESSION_MGMT_DB_NAME`, `MAXIMUM_ALLOWED_COUNT_FOR_ADD_INFRA`, `COMMON_ERROR_MESSAGES`                                                                       |
| `src/app/config/open-layer.config.ts`                                        | `CLUSTER_CONFIG`, `RESTRICTION_STYLE_CONFIG`, `MAP_LAYER_ZINDEX`                                                                                                                                                                                                  |
| `src/app/config/tooltip.config.ts`                                           | `TOOLTIP_CONFIG`                                                                                                                                                                                                                                                  |
| `src/app/master-layout/master-layout.component.ts/.html/.scss`               | `MasterLayoutComponent`                                                                                                                                                                                                                                           |
| `src/app/master-layout/master-layout.operating-day.ts`                       | `toOperatingDay`, `hasOperatingDay`, `OperatingDayInfo`                                                                                                                                                                                                           |
| `src/app/master-layout/master-layout.ribbon-sections.ts`                     | `toRibbonSection`, `buildApplyEditsItems`, `buildEditItems`, `buildShowHideItems`, `buildRestrictionActionItems`                                                                                                                                                  |
| `src/app/master-layout/event-handlers/*.ts`                                  | see §3.9                                                                                                                                                                                                                                                          |
| `src/app/master-layout/infra-content/infra-content.component.ts/.html/.scss` | `InfraContentComponent`                                                                                                                                                                                                                                           |
| `src/app/master-layout/mfe-view-restriction-list/*`                          | `MfeViewRestrictionListComponent`                                                                                                                                                                                                                                 |
| `src/app/master-layout/mfe-view-train-list/*`                                | `MfeViewTrainListComponent` _(unused)_                                                                                                                                                                                                                            |
| `src/app/master-layout/panels/infra-elements-panel/*`                        | `InfraElementsPanelComponent`                                                                                                                                                                                                                                     |
| `src/app/master-layout/panels/train-operations-panel/*`                      | `TrainOperationsPanelComponent`                                                                                                                                                                                                                                   |
| `src/app/master-layout/panels/models/infra-checkbox-group.model.ts`          | `InfraCheckboxItem`, `InfraCheckboxGroup`, `InfraPanelSelectionEvent`                                                                                                                                                                                             |
| `src/app/models/*.ts`                                                        | see §3.6                                                                                                                                                                                                                                                          |
| `src/app/services/**/*.ts`                                                   | see §3.5                                                                                                                                                                                                                                                          |
| `src/app/signal-store/*.ts`                                                  | see §3.5                                                                                                                                                                                                                                                          |
| `src/app/store/**/*.ts`                                                      | see §3.5                                                                                                                                                                                                                                                          |
| `src/app/shared/components/snackbar-content/*`                               | `SnackbarContentComponent` _(no spec)_                                                                                                                                                                                                                            |
| `src/app/utility/label-placement.engine.ts`                                  | `LabelPlacement`, `LabelPlacementEngine`                                                                                                                                                                                                                          |
| `src/app/utility/open-layer-cluster-utility/open-layer-cluster.utility.ts`   | `OpenLayerClusterUtility`                                                                                                                                                                                                                                         |
| `src/app/utility/open-layer-utility/open-layer-infra.utility.ts`             | `OpenLayerInfraUtility`                                                                                                                                                                                                                                           |
| `src/app/utility/open-layer-utility/open-layer-location-label.utility.ts`    | `OpenLayerLocationLabelUtility`                                                                                                                                                                                                                                   |
| `src/app/utility/open-layer-utility/open-layer-restriction.utility.ts`       | `OpenLayerRestrictionUtility`                                                                                                                                                                                                                                     |
| `src/app/utility/restriction-display.utility.ts`                             | `RestrictionDisplayUtility`, `ActiveRestrictionInfo`, `RestrictionDisplayInfo`, `RESTRICTION_STATE_LABEL`                                                                                                                                                         |
| `src/app/utility/restriction-popover.mapper.ts`                              | `mapRestrictionFeatureToPopoverData`, `RestrictionPopoverData`                                                                                                                                                                                                    |
| `src/app/utility/train-popover.mapper.ts`                                    | `mapFeatureToPopoverData`, `TrainPopoverData`                                                                                                                                                                                                                     |
| `src/app/utility/train-type.utility.ts`                                      | `TRAIN_COLORS`, `TRAIN_HIGHLIGHT_COLORS`, `TrainTypeCategory`, `extractTrainColor`, `extractTrainHighlightColor`, `getTrainTypeName`, `getTrainTypeCategory`, `extractTrainDisplayName`, `loadTrainIconTemplate`, `_resetTrainIconCache`, `buildTrainIconDataUri` |
| `src/app/mocks/http-mock.interceptor.ts`                                     | `httpMockInterceptor`                                                                                                                                                                                                                                             |
| `src/app/mocks/aem-mock-handler.ts`                                          | `handleAemCategories`, `handleAemDetections`, `handleAemUnreadCounts`                                                                                                                                                                                             |
| `src/app/mocks/data/*.ts`                                                    | 12 fixture modules                                                                                                                                                                                                                                                |
| `src/environments/environment{,.development,.demo}.ts`                       | `environment`                                                                                                                                                                                                                                                     |
| `src/scss/infra-constants.scss`, `src/scss/m3-theme.scss`, `src/styles.scss` | styling                                                                                                                                                                                                                                                           |
| `src/locale/messages.xlf`, `messages.fr.xlf`                                 | i18n                                                                                                                                                                                                                                                              |
| `public/icons/*.svg` (~100)                                                  | icon assets (incl. `train_directional.svg`, `cluster_train.svg`, `toggle_on/off.svg`)                                                                                                                                                                             |
| `public/mocks/infra-rivm.basegraph.mock.part1..5.json`                       | demo base graph                                                                                                                                                                                                                                                   |

## 21.6 Deployment & tests

| File                                                                      | Contents                                                                                                                                                                                                                                                         |
| ------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `deployment/helm/Chart.yaml`                                              | chart + 3 dependencies                                                                                                                                                                                                                                           |
| `deployment/helm/values.yaml`                                             | image, replicas, ports, sub-chart values                                                                                                                                                                                                                         |
| `deployment/helm/templates/endpoints.yaml`                                | 9 gateway routes                                                                                                                                                                                                                                                 |
| `deployment/helm/templates/infra-*.yaml` (7)                              | Deployments (+ Services for query-svc and webapp)                                                                                                                                                                                                                |
| `module-tests/playwright.config.js`                                       | Playwright/BDD config                                                                                                                                                                                                                                            |
| `module-tests/config/db.config.js`                                        | Mongo URI, `collections.mapConfig`                                                                                                                                                                                                                               |
| `module-tests/config/rabbitmq.config.js`                                  | exchange, 6 routing keys, fixture folders                                                                                                                                                                                                                        |
| `module-tests/playwright/plugins/rabbitmq.js`                             | `connect`, `publishJson`, `close`, `generateSignature`                                                                                                                                                                                                           |
| `module-tests/playwright/plugins/mongodb.js`                              | Mongo helper                                                                                                                                                                                                                                                     |
| `module-tests/playwright/e2e/common/pages/*.js`                           | `BasePage`, `MapPage`, `InfraLayerPage`, `TrainLayerPage`, `RibbonBarPage`, `SideBarPage`, `TopBarPage`                                                                                                                                                          |
| `module-tests/playwright/e2e/common/pages/locators/*.js`                  | 9 locator modules incl. `LoginLocators` (Keycloak)                                                                                                                                                                                                               |
| `module-tests/playwright/e2e/common/stepDefinitions/*.js`                 | `CommonSteps`, `InfraGridSteps`, `RibbonBarSteps`, `TopBarSteps`, `TrainPositionClusteringSteps`                                                                                                                                                                 |
| `module-tests/playwright/e2e/{component,module,smoke}/features/*.feature` | 9 Gherkin features                                                                                                                                                                                                                                               |
| `module-tests/playwright/utility/*.js`                                    | `canvasHelper`, `OLEvaluator`, `screenshotHelper`, `eventSetup`, `fixtures`, `globalSetup`, `helpers`, `mongoDBHelpers`, `rabbitMQHelpers`, `testDataHelper`, `testLogger`, `trainConfigReader`, `credentialsHelper`, `fileUtils`, `locators/OpenLayersLocators` |
| `module-tests/playwright/data/**`                                         | event fixtures, baseline screenshots (17 PNGs), `infra-rivm.map-config.json`                                                                                                                                                                                     |
| `module-tests/scripts/*.js`                                               | `extractMapData`, `extractMapDataDemo`, `inspectDOM`, `inspectPage`, `syncTrainPositions`                                                                                                                                                                        |

## 21.7 Documentation already in the repository

| File                                                                                                                                                    | Note                                                                                               |
| ------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| `components/doc/features/infra-data-tile-concept.md`                                                                                                    | **Accurate** — the canonical tiling explanation                                                    |
| `components/doc/features/infra-tiling-concept.drawio` (+ 2 SVGs)                                                                                        | Diagrams                                                                                           |
| `components/infra-webapp/AGENTS.md`                                                                                                                     | Partially stale (Angular 20, `@tps/rivm-common-components 1.6.1`, `infra-ribbon-bar.component.ts`) |
| `components/infra-webapp/doc/architecture.md`                                                                                                           | Partially stale (see the header note of this document)                                             |
| `components/infra-webapp/doc/detailed-frontend-architecture.md`, `style.md`, `dynamic-clustering.md`, `train-icon-rendering.md`, `angular-migration.md` | Frontend guides                                                                                    |
| `components/infra-trainoperation-etl/AGENTS.md`, `docs/architecture.md`, `docs/TrainOperationMovementFlow.md`, `docs/testing.md`                        | Partially stale                                                                                    |
| `components/infra-query-svc/README.md`                                                                                                                  | Stale Swagger path                                                                                 |
| `components/infra-micro-etl/README.md`, `infra-business-clock-etl/README.md`                                                                            | RISE-API-UTILS integration how-to                                                                  |
| `components/platform/README.md`, `module-tests/README.md`                                                                                               | —                                                                                                  |

---

# 22 — ARCHITECTURE DIAGRAMS

## 22.1 Overall architecture

```mermaid
flowchart TB
    subgraph EXT["External RISE platform"]
        RIDS_BC["de.hacon.tps.rids.business_clock"]
        RIDS_TO["de.hacon.tps.rids.train_operation"]
        RIDS_R["de.hacon.tps.rids.restriction"]
        BRIDGE["bridge.infra / rise.bridge.tps_live"]
        KC["Keycloak SSO + API Gateway"]
        MFEBE["MFE backends<br/>train-operation · restriction · aem"]
    end

    subgraph MQ["RabbitMQ"]
        EX(["exchange rise.events<br/>topic · durable"])
    end

    subgraph ETL["ETL consumers (Spring Boot)"]
        BCE["infra-business-clock-etl"]
        ME["infra-micro-etl"]
        BGE["infra-basegraph-etl"]
        TOE["infra-trainoperation-etl<br/>@EnableScheduling"]
        RE["infra-restriction-etl"]
    end

    subgraph DB["MongoDB — risedb"]
        C1[("infra-rivm.business-clock")]
        C2[("infra-rivm.basegraph")]
        C3[("infra-rivm.track-coordinates")]
        C4[("infra-rivm.train-position")]
        C5[("infra-rivm.data-tile")]
        C6[("infra-rivm.restriction")]
        C7[("infra-rivm.map-config<br/>no writer in this repo")]
    end

    QS["infra-query-svc<br/>Spring Boot Web · :9101<br/>/api/infra/query"]
    WEB["infra-webapp<br/>Angular 21 · OpenLayers 10 · :80"]
    USER(("Dispatcher"))

    LIB["infra-common-lib<br/>generated model + repositories"]
    PLAT["platform (BOM)"]

    RIDS_BC --> EX
    RIDS_TO --> EX
    RIDS_R --> EX
    BRIDGE --> EX

    EX -->|event.business_clock| BCE
    EX -->|event.infra.microscopic_region| ME
    EX -->|event.infra.microscopic_region| BGE
    EX -->|event.infra.microscopic_region<br/>+ operational-period| TOE
    EX -->|event.train_operation.*| TOE
    EX -->|restriction key: NOT DETERMINED<br/>+ infra events| RE

    BCE --> C1
    ME --> C3
    BGE --> C2
    TOE --> C4
    TOE --> C5
    TOE -.reads.-> C3
    TOE -.reads.-> C7
    RE --> C6

    C1 --> QS
    C2 --> QS
    C3 --> QS
    C4 --> QS
    C5 --> QS
    C6 --> QS
    C7 --> QS

    QS -->|REST JSON| KC
    KC --> WEB
    MFEBE --> KC
    WEB --> USER
    USER -->|clicks| WEB

    LIB -.compile.-> QS
    LIB -.compile.-> BCE
    LIB -.compile.-> ME
    LIB -.compile.-> BGE
    LIB -.compile.-> TOE
    LIB -.compile.-> RE
    PLAT -.BOM.-> LIB
```

## 22.2 Frontend architecture

```mermaid
flowchart TB
    subgraph BOOT["Bootstrap"]
        MAIN["main.ts"] --> APPC["AppComponent"]
        CFG["app.config.ts<br/>provideHttpClient · provideRouter(withHashLocation)<br/>provideStore · provideEffects · provideStoreDevtools<br/>APP_INITIALIZER · icon providers"]
    end

    subgraph SHELL["Shell"]
        ML["MasterLayoutComponent<br/>tps-rivm-frame"]
        IC["InfraContentComponent (OnPush)<br/>the map view"]
    end

    subgraph HANDLERS["event-handlers/*"]
        HH["header.handlers"]
        SH["sidebar.handlers"]
        PH["panel.handlers"]
        RH["ribbon.handlers"]
        TH["train-edit.handlers"]
        FH["filter-panel.handlers"]
    end

    subgraph NGRX["NgRx classic store"]
        A1["businessClock"]
        A2["customClock"]
        A3["polling"]
        A4["edgeData"]
        E1["BusinessClockEffects"]
        E2["EdgeDataEffects"]
    end

    subgraph SIG["Signal stores"]
        S1["TrainPositionStore"]
        S2["RestrictionsStore"]
        S3["MapConfigStore"]
        S4["LocationsStore"]
        S5["MapStateStore"]
        S6["PanelStateStore"]
        S7["RibbonStateStore"]
        S8["FilterStateStore"]
        S9["AemPanelStore"]
        S10["LeftPanelStore"]
    end

    subgraph SVC["Services"]
        API1["BaseGraphApiService"]
        API2["BusinessClockApiService"]
        API3["MapConfigService"]
        API4["LocationTrackCoordinatesApiService"]
        API5["RestrictionApiService"]
        API6["TrainPositionService"]
        API7["LogoutApiService"]
        CACHE["InfraCacheDbService (Dexie)"]
        MAPS["MapService (OpenLayers owner)"]
        TILE["TileManagementService"]
        POLL["TrainPollingCoordinatorService"]
        TIME["TimeCalculationService"]
        TIP["TooltipPositionService"]
        SNACK["SnackbarAlertService"]
        ICON["IconService"]
    end

    subgraph UTIL["OpenLayers utilities"]
        U1["OpenLayerInfraUtility"]
        U2["OpenLayerClusterUtility"]
        U3["OpenLayerLocationLabelUtility"]
        U4["OpenLayerRestrictionUtility"]
        U5["LabelPlacementEngine"]
        U6["RestrictionDisplayUtility"]
        U7["train-type.utility"]
    end

    subgraph MFE["npm MFE libraries"]
        M1["@tps/rivm-common-components"]
        M2["@tps/mfe-train-operation"]
        M3["@tps/rimfe-restriction"]
        M4["@tps/rimfe-aem"]
    end

    MAIN --> CFG
    APPC --> ML
    ML --> IC
    ML --> HANDLERS
    ML --> M1
    ML --> M2
    ML --> M3
    ML --> M4
    IC --> M1

    E1 --> API2
    E2 --> API1
    API1 --> CACHE
    API3 --> CACHE
    API4 --> CACHE

    IC --> S1
    IC --> S2
    IC --> S3
    IC --> S4
    IC --> S5
    IC --> S6
    IC --> S8
    IC --> MAPS
    IC --> POLL
    IC --> TIME
    IC --> TIP

    S1 --> API6
    S2 --> API5
    S3 --> API3
    S4 --> API4

    POLL --> TILE
    POLL --> S1
    MAPS --> U1
    MAPS --> U2
    MAPS --> U3
    MAPS --> U4
    U2 --> U5
    U2 --> U7
    U4 --> U6
    TIP --> U6
    TIP --> ICON
    HANDLERS --> SNACK
    HANDLERS --> API7
    NGRX --> IC
    NGRX --> ML
```

## 22.3 Backend architecture

```mermaid
flowchart LR
    subgraph READ["Read side — infra-query-svc"]
        direction TB
        CT1["BaseGraphController"] --> SV1["BaseGraphService"]
        CT2["BusinessClockController"] --> SV2["BusinessClockService"]
        CT3["ConfigController"] --> SV3["ConfigService"]
        CT4["LocationTrackCoordinatesController"] --> SV4["LocationTrackCoordinatesService"]
        CT5["RestrictionController"] --> SV5["RestrictionService"]
        CT6["TrackCoordinatesController"] --> SV6["TrackCoordinatesService"]
        CT7["TrainPositionController"] --> SV7["TrainPositionService"]
        SV1 & SV5 & SV6 & SV7 --> MAP["APIMapper&lt;T&gt;"]
        GEH["GlobalExceptionHandler<br/>@ControllerAdvice"]
    end

    subgraph COMMON["infra-common-lib"]
        direction TB
        PURE["Pure repository interfaces<br/>BaseGraph · BusinessClock · DataTile<br/>MapConfig · Restriction · TrackCoordinates · TrainPosition"]
        ADAPT["Mongo*RepositoryCustomImpl<br/>@Component adapters"]
        SD["Mongo*Repository<br/>Spring Data"]
        ENT["Mongo*Entity extends generated model<br/>@Document(collection=\"${app.db.collection.*}\")"]
        GEN["generated.rivm.*<br/>OpenAPI Generator (spring) from infra-model.yaml"]
        PURE --> ADAPT --> SD --> ENT --> GEN
    end

    subgraph WRITE["Write side — ETL consumers"]
        direction TB
        H["*EventHandler<br/>(META-INF/spring.factories)"] --> SVX["*Service"] --> MPX["*Mapper"]
        SVX --> AUX["DataTileService · MapConfigService<br/>TrackCoordinatesService · MicroscopicInfraService"]
    end

    MONGO[("MongoDB risedb")]

    SV1 & SV2 & SV3 & SV4 & SV5 & SV6 & SV7 --> PURE
    SVX --> PURE
    ENT --> MONGO
    GEH -.wraps.-> READ
    RISEUTILS["rise-api-utils 13.1.0<br/>AMQP listener + DTOs + signature"] --> H
    RISEINFRA["rise-infra-utils 13.1.0<br/>MicroscopicInfra · Types"] --> AUX
```

## 22.4 Database relationship overview

```mermaid
erDiagram
    MAP_CONFIG {
        string id PK
        string mapType
        string coordinateSystem
        int minZoomLevel
        int maxZoomLevel
        int defaultZoom
        array layers
    }
    BASEGRAPH {
        string id PK
        object baseGraph "nodes[] + edges[]"
    }
    TRACK_COORDINATES {
        string id PK "locationId_trackId"
        array nodeCoordinates
        object locationSubEntityData
        object trackSubEntityData
    }
    TRAIN_POSITION {
        string id PK "trainServiceId-activityId"
        string trainServiceId
        string activityId
        string activityType
        array dataTileIds FK
        string fromTime
        string toTime
        string runningType
        string origin
        string destination
        object coordinates
    }
    DATA_TILE {
        string id PK "x_y_timeslot"
        string version
    }
    RESTRICTION {
        string id PK
        string name
        string shortName
        string description
        string lastModified
        object restrictionData
    }
    BUSINESS_CLOCK {
        string businessTime
        string businessTimeZone
        string serverTime
        string mode
    }

    MAP_CONFIG ||..o{ DATA_TILE : "tileSize drives tile ids"
    TRAIN_POSITION }o--o{ DATA_TILE : "dataTileIds[] (logical, unenforced)"
    TRAIN_POSITION }o--|| TRACK_COORDINATES : "origin/destination + trackId → coordinates"
    TRACK_COORDINATES }o--|| BASEGRAPH : "nodeCoordinates resolved from nodes"
    RESTRICTION }o--|| BASEGRAPH : "edgePaths → edges (via rise-infra-utils)"
```

## 22.5 RabbitMQ architecture

```mermaid
flowchart LR
    P1["business_clock"] --> EX
    P2["train_operation"] --> EX
    P3["restriction"] --> EX
    P4["bridge.infra"] --> EX

    EX{{"rise.events<br/>topic · durable<br/>header: signature = sha256(body)"}}

    EX -->|event.business_clock| Q1[["…businessclock.event.consumer"]]
    EX -->|event.infra.microscopic_region| Q2[["…inframicro.event.consumer"]]
    EX -->|event.infra.microscopic_region| Q3[["…infrabasegraph.event.consumer"]]
    EX -->|event.infra.microscopic_region| Q4[["…infra.microscopic-region.event.consumer"]]
    EX -->|NOT DETERMINED| Q5[["…infra.operational-period.event.consumer"]]
    EX -->|event.train_operation.train_operation| Q6[["…trainoperation.event.consumer"]]
    EX -->|event.train_operation.forecast| Q7[["…trainoperation.forecast.event.consumer"]]
    EX -->|NOT DETERMINED| Q8[["…restriction.event.consumer"]]

    Q1 --> S1["infra-business-clock-etl"]
    Q2 --> S2["infra-micro-etl"]
    Q3 --> S3["infra-basegraph-etl"]
    Q4 --> S4["infra-trainoperation-etl"]
    Q4 --> S5["infra-restriction-etl"]
    Q5 --> S4
    Q5 --> S5
    Q6 --> S4
    Q7 --> S4
    Q8 --> S5

    S1 --> D1[("business-clock")]
    S2 --> D2[("track-coordinates")]
    S3 --> D3[("basegraph")]
    S4 --> D4[("train-position")]
    S4 --> D5[("data-tile")]
    S5 --> D6[("restriction")]

    note1["Q4 and Q5 are shared by two services<br/>⇒ competing consumers"]
    note1 -.-> Q4
    note1 -.-> Q5
```

## 22.6 Main map data flow

```mermaid
flowchart TB
    DBB[("infra-rivm.basegraph")] --> BGC["BaseGraphController<br/>GET /basegraph"]
    DBL[("infra-rivm.track-coordinates")] --> LTC["LocationTrackCoordinatesController<br/>GET /location-track-coordinates"]
    DBM[("infra-rivm.map-config")] --> CFC["ConfigController<br/>GET /configs"]
    DBT[("infra-rivm.train-position")] --> TPC["TrainPositionController<br/>POST /trainpositions"]
    DBD[("infra-rivm.data-tile")] --> TPC
    DBR[("infra-rivm.restriction")] --> RSC["RestrictionController<br/>GET /restrictions"]

    BGC --> ASG["BaseGraphApiService<br/>+ IndexedDB cache"]
    LTC --> ASL["LocationTrackCoordinatesApiService<br/>all pages + retry 3"]
    CFC --> ASC["MapConfigService<br/>+ IndexedDB cache"]
    TPC --> AST["TrainPositionService"]
    RSC --> ASR["RestrictionApiService<br/>+ normalizeApiResponse"]

    ASG --> ST1["NgRx edgeData slice"]
    ASL --> ST2["LocationsStore"]
    ASC --> ST3["MapConfigStore"]
    AST --> ST4["TrainPositionStore"]
    ASR --> ST5["RestrictionsStore"]

    ST1 --> ICC["InfraContentComponent"]
    ST2 --> ICC
    ST3 --> ICC
    ST4 --> ICC
    ST5 --> ICC

    ICC --> MS["MapService"]

    MS --> L1["vectorLayer<br/>Point(node) + LineString(edge)"]
    MS --> L2["locationLabelLayer<br/>Point + Text (declutter)"]
    MS --> L3["trackLabelLayer<br/>Point + Text"]
    MS --> L4["trainPositionsVectorLayer<br/>ClusterSource → donut / icon"]
    MS --> L5["trainPositionsNonClusteredLayer"]
    MS --> L6["restrictionsVectorLayer<br/>LineString + midpoint Icon"]
    MS --> L7["OverviewMap (frozen)"]

    L1 & L2 & L3 & L4 & L5 & L6 & L7 --> CANVAS["OpenLayers canvas"]
    CANVAS --> USER(("Dispatcher"))
```

## 22.7 Train workflow

```mermaid
sequenceDiagram
    autonumber
    actor U as Dispatcher
    participant UI as InfraContentComponent
    participant PS as PanelStateStore
    participant MS as MapService
    participant TPS as TrainPositionStore
    participant API as infra-query-svc
    participant DB as MongoDB
    participant ETL as infra-trainoperation-etl
    participant MQ as rise.events

    MQ->>ETL: TrainOperationEvent
    ETL->>DB: upsert train-position + new data-tile versions
    UI->>TPS: startPolling (viewport tiles)
    TPS->>API: POST /trainpositions [{id, version?}]
    API->>DB: findAllById(data-tile) → changed?
    API->>DB: findByDataTileIdsIn(train-position)
    API-->>TPS: { data, meta.dataTileVersions[0] }
    TPS->>UI: positions signal
    UI->>UI: filterPositionsByTime(adjustedTimestamp)
    UI->>MS: updateTrainPositions(filtered)
    MS-->>U: train icons rendered

    U->>UI: single click on a train
    UI->>MS: setSelectedTrain(id)
    UI->>PS: updatePanelContext({trainServiceId, trainNumber})

    U->>UI: double click
    UI->>PS: openTIP({trainServiceId, trainNumber})
    PS-->>U: tps-mfe-train-info-panel opens (right slot)

    U->>PS: ribbon Edit → arrival_time
    PS->>PS: openEditPanel({..., editType})
    U->>PS: Apply
    PS->>PS: requestApply()
    Note over PS: submitPendingEdit → buildEditPayload → editTrainApiPayload
    PS-->>U: MFE issues the write (contract NOT DETERMINED)
    Note over MQ,ETL: upstream publishes a new TrainOperationEvent → loop repeats
```

## 22.8 Track workflow

```mermaid
sequenceDiagram
    autonumber
    participant MQ as rise.events
    participant BGE as infra-basegraph-etl
    participant ME as infra-micro-etl
    participant DB as MongoDB
    participant API as infra-query-svc
    participant WEB as infra-webapp
    actor U as Dispatcher

    MQ->>BGE: InfraMicroscopicRegionEvent (queue …infrabasegraph…)
    BGE->>BGE: BaseGraphMapper.map (rename, narrow, List→Set)
    BGE->>DB: save BaseGraph (_id = region entityID)

    MQ->>ME: InfraMicroscopicRegionEvent (queue …inframicro…)
    ME->>ME: index nodes; per location×track resolve nodeRefs → {x,y}
    ME->>DB: saveAll TrackCoordinates (_id = locationId_trackId)

    WEB->>API: GET /basegraph
    API->>DB: findAll(Pageable) on basegraph
    API-->>WEB: BaseGraph[]
    WEB->>WEB: extractNodes / extractEdges → Point + LineString features
    WEB->>WEB: fitViewToData → setMinZoom(fitted)

    WEB->>API: GET /location-track-coordinates (all pages)
    API->>DB: aggregation group by locationSubEntityData.id + $in fetch
    API-->>WEB: LocationWithTracks[]
    WEB->>WEB: loadLocationLabels → station + platform label layers
    WEB-->>U: network + labels rendered (zoom-gated per MapConfig)
```

## 22.9 Restriction workflow

```mermaid
sequenceDiagram
    autonumber
    participant MQ as rise.events
    participant RE as infra-restriction-etl
    participant MI as MicroscopicInfra (memory)
    participant DB as MongoDB
    participant API as infra-query-svc
    participant RS as RestrictionsStore
    participant MS as MapService
    actor U as Dispatcher

    MQ->>RE: InfraOperationalPeriodEvent
    RE->>MI: initialize
    MQ->>RE: InfraMicroscopicRegionEvent
    RE->>MI: addMicroscopicRegionData

    MQ->>RE: RestrictionEvent (ENTITY_CREATED)
    RE->>RE: RestrictionMapper.mapEventToRestriction
    RE->>MI: findEdgePaths(restrictionData.segments)
    MI-->>RE: EdgePath[] (pathEdges + pathCoordinates)
    RE->>DB: save Restriction (_id = entityID)

    RS->>API: GET /restrictions?effectiveAt=<adjusted business time>
    API->>DB: startTime ≤ t ≤ endTime, sort lastModified DESC
    API-->>RS: Restriction[]
    RS->>RS: visibleRestrictionInfos (isActive, colour, pathCoordinateSets)
    RS->>MS: updateRestrictions(infos)
    MS-->>U: coloured poly-lines + midpoint icons

    U->>MS: hover
    MS->>MS: setHoveredRestriction(id) → white halo + lifted icon
    MS-->>U: restriction popover (ID, Name, State, From, To, Impact Type)

    U->>U: expand list, select a row, click Activate
    Note over U: handleRestrictionAction → MFE requestRestrictionStateChange(id,'ACTIVE')
    Note over MQ,RE: upstream publishes ENTITY_UPDATED → loop repeats
```

## 22.10 Complete request/response flow

```mermaid
sequenceDiagram
    autonumber
    actor U as Dispatcher
    participant C as Angular component
    participant S as Angular service / signal store
    participant H as HttpClient
    participant G as API gateway
    participant CTL as Spring @RestController
    participant SVC as Spring @Service
    participant REPO as Pure repository interface
    participant ADP as Mongo adapter
    participant DB as MongoDB

    U->>C: interaction (pan, zoom, slider, click)
    C->>S: method call / rxMethod
    S->>H: GET | POST {baseUrl}/...
    H->>G: HTTP request (no Authorization header)
    G->>CTL: forwarded (permissions: null, param/header allow-list)
    CTL->>CTL: Bean Validation (@Min/@Max/@Valid/@NotEmpty/@DateTimeFormat)
    CTL->>SVC: delegate
    SVC->>SVC: pagination + sort + domain rules
    SVC->>REPO: findAll / findByX / aggregation
    REPO->>ADP: adapter
    ADP->>DB: query
    DB-->>ADP: documents
    ADP-->>REPO: domain models
    REPO-->>SVC: Page<T> / List<T>
    SVC->>SVC: APIMapper.mapPageToMetaPage
    SVC-->>CTL: APIPaginatedResponse<T> | APIResponse<T>
    CTL-->>G: ResponseEntity (Jackson, NON_NULL)
    G-->>H: JSON
    H-->>S: typed response
    S->>S: patchState / dispatch success action
    S-->>C: signal / observable
    C->>C: map to OpenLayers features
    C-->>U: canvas update

    alt exception
        SVC-->>CTL: BadRequestException / ResourceNotFoundException / Exception
        CTL-->>G: GlobalExceptionHandler → { errors: [{ code, message }] } (400/404/500)
        G-->>H: error response
        H-->>S: catchError → patchState({error}) or throwError
        S-->>C: (usually silent; two flows show a snackbar)
    end
```

## 22.11 Complete asynchronous event flow

```mermaid
sequenceDiagram
    autonumber
    participant SRC as RISE producer
    participant EX as rise.events (topic)
    participant Q as Configured queue
    participant LIB as rise-api-utils listener
    participant HND as *EventHandler
    participant CTX as RISEApplicationContext
    participant SVC as ETL *Service
    participant MPR as *Mapper
    participant AUX as DataTile / MapConfig / TrackCoordinates / MicroscopicInfra
    participant REPO as Repository
    participant DB as MongoDB
    participant API as infra-query-svc
    participant UI as infra-webapp

    SRC->>EX: publish JSON + header signature=sha256(body), persistent
    EX->>Q: route by routing key
    Q->>LIB: deliver
    LIB->>LIB: validate signature + schema
    LIB->>HND: handleValidatedMessage(<X>Event)
    HND->>CTX: getComponent(<X>Service)
    CTX-->>HND: service bean
    HND->>SVC: processX(event)
    SVC->>SVC: switch on baseEntityEvent.triggerType
    SVC->>MPR: map(dto)
    MPR->>AUX: coordinates / tile ids / edge paths
    AUX-->>MPR: resolved values
    MPR-->>SVC: domain model(s)
    SVC->>REPO: save / saveAll / deleteById / deleteAllById
    REPO->>DB: write
    SVC-->>HND: return (or throw)
    alt success
        HND-->>LIB: true  (ACK)
    else failure surfaced
        HND-->>LIB: false (NACK — restriction & infra-graph handlers only)
    else failure swallowed
        Note over SVC,HND: clock / micro / basegraph / train-operation services<br/>catch Exception internally → handler still returns true
        HND-->>LIB: true (message consumed, nothing persisted)
    end

    UI->>API: next poll (business clock 10 s / trains & restrictions per MapConfig)
    API->>DB: read
    DB-->>API: data
    API-->>UI: JSON
    UI-->>UI: store → OpenLayers → canvas
```

---

# 23 — FINAL SYSTEM SUMMARY

## 23.A Technology stack

| Layer                | Technology                                                                              | Version                         |
| -------------------- | --------------------------------------------------------------------------------------- | ------------------------------- |
| Build (JVM)          | Gradle Kotlin DSL + `de.hacon.tps.convention.*`                                         | plugin `3.+`                    |
| Language (backend)   | Java                                                                                    | 21 (`dateLibrary: java21`)      |
| Framework (backend)  | Spring Boot                                                                             | **4.1.0** (via `platform` BOM)  |
| Web                  | Spring Boot Web MVC + springdoc-openapi                                                 | springdoc `3.0.3`               |
| Messaging client     | Spring AMQP via `de.hacon.tps.rise:rise-api-utils`                                      | `13.1.0`                        |
| Infra geometry       | `de.hacon.tps.rise:rise-infra-utils`                                                    | `13.1.0`                        |
| Persistence          | Spring Data MongoDB                                                                     | Boot-managed                    |
| Database             | MongoDB (`risedb`)                                                                      | —                               |
| Model generation     | OpenAPI Generator (`spring`, models only)                                               | `7.20.0`                        |
| JSON                 | Jackson (+ `jackson-databind-nullable 0.2.6`)                                           | `2.19.2`                        |
| Boilerplate          | Lombok                                                                                  | Boot-managed                    |
| Backend testing      | JUnit 5, Testcontainers (`mongodb`, `rabbitmq`), Awaitility                             | TC `1.21.4`, Awaitility `4.2.0` |
| Framework (frontend) | Angular                                                                                 | `^21.2.0`                       |
| Language (frontend)  | TypeScript                                                                              | `~5.9.0`                        |
| Map                  | OpenLayers (`ol`)                                                                       | `^10.10.0`                      |
| State                | NgRx Store / Effects / Signals / DevTools + `@angular-architects/ngrx-toolkit`          | `^21.0.0`                       |
| UI kit               | Angular Material + CDK                                                                  | `^21.2.0`                       |
| Grid                 | ag-grid-angular / ag-grid-community                                                     | `^32.3.3`                       |
| Client storage       | Dexie (IndexedDB)                                                                       | `^4.4.2`                        |
| Date/time            | moment-timezone                                                                         | `^0.5.46`                       |
| Reactive             | RxJS                                                                                    | `~7.8.0`                        |
| i18n                 | `@angular/localize` (`en-US`, `fr`)                                                     | `^21.2.0`                       |
| Package manager      | Yarn                                                                                    | `4.5.0`                         |
| Frontend testing     | Karma + Jasmine + `jasmine-marbles` + karma-junit-reporter                              | Jasmine `~5.6.0`                |
| Lint/format          | ESLint 9 + `@angular-eslint` 21 + Prettier 3.9.4 (+ organize-imports)                   | —                               |
| E2E                  | Playwright `1.59.1` + playwright-bdd `9.2.0` + Cucumber 13 + amqplib + mongodb driver 7 | —                               |
| Packaging            | Docker images + Helm chart `rivm-infra` (`rise-common ^2.x`)                            | chart `0.0.0-dev`               |

## 23.B All services

1. `components/platform` — Gradle BOM
2. `components/infra-common-lib` — shared model, repositories, error handling
3. `components/infra-query-svc` — REST read API (`:9101`, `/api/infra/query`)
4. `components/infra-business-clock-etl` — clock ingest
5. `components/infra-micro-etl` — track-coordinate ingest
6. `components/infra-basegraph-etl` — base-graph ingest
7. `components/infra-trainoperation-etl` — train position + data tile ingest (scheduled caches, index provisioning)
8. `components/infra-restriction-etl` — restriction ingest (segment → edge-path resolution)
9. `components/infra-webapp` — Angular SPA (`:80`)
10. `module-tests` — Playwright/BDD E2E harness (not deployed)

## 23.C All frontend MFEs / modules

- **Application:** `infra-webapp` (single SPA, single screen, hash routing)
- **Consumed MFE libraries (npm, not Module Federation):**
  - `@tps/rivm-common-components 2.9.1` — frame, ribbon, popovers, filter panel, context menu, checkbox
  - `@tps/mfe-train-operation 2.7.3` — train list, train info panel, train edit panel
  - `@tps/rimfe-restriction 0.7.0` — restriction list (+ state PATCH)
  - `@tps/rimfe-aem 1.1.1` — AEM events panel
- **In-repo wrappers:** `MfeViewRestrictionListComponent` (used), `MfeViewTrainListComponent` (unused)
- **Helm sub-charts:** `mfe-train-operation 2.7.3`, `rimfe-restriction 0.7.0`

## 23.D All databases

| Store                                             | Purpose                                                            |
| ------------------------------------------------- | ------------------------------------------------------------------ |
| **MongoDB `risedb`**                              | The only server-side database (7 `infra-rivm.*` collections)       |
| **IndexedDB `RIVM-INFRA`** (Dexie, store `cache`) | Client cache for base graph, map config, location tracks (TTL 1 h) |
| **localStorage `infra-filter-state`**             | Client layer-visibility + checkbox persistence                     |

No relational database, no migration tooling, no cache server (Redis etc.).

## 23.E All important collections

| Collection                     | Key                             | Written by                  | Read by                       |
| ------------------------------ | ------------------------------- | --------------------------- | ----------------------------- |
| `infra-rivm.business-clock`    | implicit `_id` (singleton)      | business-clock-etl          | query-svc                     |
| `infra-rivm.basegraph`         | region entityID                 | basegraph-etl               | query-svc                     |
| `infra-rivm.track-coordinates` | `{locationId}_{trackId}`        | micro-etl                   | query-svc, trainoperation-etl |
| `infra-rivm.train-position`    | `{trainServiceId}-{activityId}` | trainoperation-etl          | query-svc                     |
| `infra-rivm.data-tile`         | `{x}_{y}_{yyyy-MM-ddTHH:mm}`    | trainoperation-etl          | query-svc                     |
| `infra-rivm.restriction`       | restriction entityID            | restriction-etl             | query-svc                     |
| `infra-rivm.map-config`        | e.g. `INFRA_MAP_01`             | **external / NOT FOUND**    | query-svc, trainoperation-etl |
| `infra-rivm.location`          | —                               | **nothing** (dead property) | —                             |

Indexes: three on `train-position` (created by `IndexConfig`); none anywhere else.

## 23.F All important APIs

| #   | Method | Path (after `/api/infra/query`)          | Purpose                                                            |
| --- | ------ | ---------------------------------------- | ------------------------------------------------------------------ |
| 1   | GET    | `/basegraph`                             | Network nodes + edges (paged, ≤ 1000)                              |
| 2   | GET    | `/business-clock`                        | Current platform time                                              |
| 3   | GET    | `/configs`                               | Map + layer configuration                                          |
| 4   | GET    | `/location-track-coordinates`            | Stations with their tracks (paged, ≤ 1000)                         |
| 5   | GET    | `/restrictions?effectiveAt`              | Restrictions effective at a time (paged, ≤ 1000)                   |
| 6   | GET    | `/track-coordinates`                     | Flat track coordinates (paged, ≤ 10000) — **no frontend consumer** |
| 7   | POST   | `/trainpositions`                        | Train positions for tiles, version-delta (paged, ≤ 1000)           |
| 8   | POST   | `{baseAuthUrl}/logout`                   | Sign out (external auth service)                                   |
| 9   | —      | `/swagger-ui/index.html`, `/v3/api-docs` | springdoc                                                          |

## 23.G All RabbitMQ exchanges / queues / events

**Exchange:** `rise.events` (topic, durable). Message header `signature = sha256(body)`.

| Queue                                                              | Event                         | Service                                  |
| ------------------------------------------------------------------ | ----------------------------- | ---------------------------------------- |
| `de.hacon.tps.rise.client.businessclock.event.consumer`            | `BusinessClockEvent`          | business-clock-etl                       |
| `de.hacon.tps.rise.client.inframicro.event.consumer`               | `InfraMicroscopicRegionEvent` | micro-etl                                |
| `de.hacon.tps.rise.client.infrabasegraph.event.consumer`           | `InfraMicroscopicRegionEvent` | basegraph-etl                            |
| `de.hacon.tps.rise.client.infra.microscopic-region.event.consumer` | `InfraMicroscopicRegionEvent` | trainoperation-etl **&** restriction-etl |
| `de.hacon.tps.rise.client.infra.operational-period.event.consumer` | `InfraOperationalPeriodEvent` | trainoperation-etl **&** restriction-etl |
| `de.hacon.tps.rise.client.trainoperation.event.consumer`           | `TrainOperationEvent`         | trainoperation-etl                       |
| `de.hacon.tps.rise.client.trainoperation.forecast.event.consumer`  | `TrainOperationForecastEvent` | trainoperation-etl                       |
| `de.hacon.tps.rise.client.restriction.event.consumer`              | `RestrictionEvent`            | restriction-etl                          |

**Known routing keys:** `event.business_clock`, `event.infra.location`,
`event.infra.microscopic_region`, `event.train_operation.train_operation`,
`event.train_operation.forecast`, `event.detection`.
**NOT DETERMINED:** routing keys for `RestrictionEvent` and `InfraOperationalPeriodEvent`.

**No producer exists in this repository.**

## 23.H All major features

Network rendering · station labels · platform labels · train rendering · train clustering ·
train label collision avoidance · train colouring by type · train hover popover · train selection ·
train context menu · TIP · train list · train edit (3 actions) · restriction rendering ·
restriction hover popover · restriction list · restriction activate/deactivate ·
business clock · custom clock · time-offset slider · 3D data tiling · tile-version delta ·
viewport-scoped polling · data-driven map config · frozen overview map · layer show/hide panels ·
panel state machine · mode-dependent ribbon · AEM events panel · IndexedDB caching ·
i18n (en/fr) · demo mode · snackbar errors · sign out · global exception handling · Swagger UI ·
index provisioning · backend caches · in-memory microscopic graph · OpenAPI code generation ·
E2E harness.

**Declared but disabled/absent:** view switching (geographic/schematic/octolinear), saved views,
find/filter, replay, export (PDF/CSV/XLSX), restriction create/copy/delete, signals, blocks,
track availability, track editing, authentication/authorization, tabs.

## 23.I Main data flows

1. **Infrastructure ingest** — `InfraMicroscopicRegionEvent` → 3 consumers → `basegraph`,
   `track-coordinates`, in-memory `MicroscopicInfra`.
2. **Clock ingest** — `BusinessClockEvent` → `business-clock` (replace).
3. **Train ingest** — `TrainOperationEvent` → activity sequence → coordinates → tiles →
   `train-position` + `data-tile`.
4. **Forecast ingest** — `TrainOperationForecastEvent` → delete-all-forecast → actual-frontier
   filter → save → gap closing.
5. **Restriction ingest** — `RestrictionEvent` → segments → edge paths → `restriction`.
6. **Map bootstrap** — `/business-clock` + `/configs` + `/location-track-coordinates` + `/basegraph`
   → OpenLayers layers → `fitViewToData`.
7. **Train polling** — viewport → tile ids → `POST /trainpositions` (version delta) → store merge →
   time filter → cluster/icon rendering.
8. **Restriction polling** — `GET /restrictions?effectiveAt` → store → poly-lines + markers.
9. **Time travel** — slider/header → adjusted time → rounded tile timestamp → new tile ids →
   new data + re-filter.
10. **Panel/UI state** — sidebar/ribbon → `PanelStateStore`/`LeftPanelStore`/`AemPanelStore` →
    frame slots → debounced `map.updateSize()` + pan.

## 23.J Main user workflows

1. Open the app and see the whole rail network fitted to the viewport.
2. Zoom in past the trains layer's `minZoom` to see live trains (clustered, then individual).
3. Hover a train for a popover; hover a restriction for a popover + halo.
4. Click a train to select it; double-click to open the Train Information Panel.
5. Right-click a selected train → context menu → edit arrival time / departure time / track.
6. Apply or cancel the edit from the ribbon's _Apply Edits_ section.
7. Open the train list from the sidebar; select a train (the map focuses on it).
8. Open the restriction list; expand it; select a row; Activate / Deactivate.
9. Open the AEM events panel from the sidebar.
10. Toggle map layers via the _Show/Hide_ ribbon → Infrastructure Elements / Train Operations panels.
11. Scrub the time-offset slider (‑10 min … +50 min) or pick a date/time in the header; reset to live.
12. Toggle clustering on/off.
13. Sign out.

## 23.K Critical dependencies

| Dependency                                                                 | Why critical                                                                                                                                                                                       |
| -------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`rise-api-utils 13.1.0`**                                                | Owns _all_ AMQP wiring, DTOs, signature validation and `RISEApplicationContext`. Without it no ETL can consume anything, and none of that behaviour is visible/overridable in this repository.     |
| **`rise-infra-utils 13.1.0`**                                              | `MicroscopicInfra.findEdges` / `.findEdgePaths` — the only way km addresses and restriction segments become coordinates.                                                                           |
| **`infra-rivm.map-config` document**                                       | A `MapConfig` with `mapType == OCTOLINEAR` and a layer `layerDataType == 'train'` **with** `tileSize` is required or **no train position is ever ingested**. Nothing in this repository writes it. |
| **`InfraOperationalPeriodEvent` + `InfraMicroscopicRegionEvent` ordering** | The in-memory graph must be populated before movement/restriction events, or coordinates and edge paths silently resolve to nothing.                                                               |
| **`infra-common-lib` OpenAPI generation**                                  | Every service compiles against `build/generated`; a schema break breaks all six Java modules at once.                                                                                              |
| **`components/schemas/**` YAML library\*\*                                 | Single source of truth for the whole domain model.                                                                                                                                                 |
| **MongoDB**                                                                | Sole persistence and the _only_ coupling between ETLs and the query service.                                                                                                                       |
| **RabbitMQ `rise.events`**                                                 | Sole ingress for all data.                                                                                                                                                                         |
| **`@tps/*` MFE libraries**                                                 | Train list, TIP, train edit, restriction list and AEM panel are entirely external.                                                                                                                 |
| **API gateway (`endpoints.yaml` + `rise-common`)**                         | Provides routing, path rewriting and (elsewhere) authentication.                                                                                                                                   |
| **`@tps/rivm-common-components` frame**                                    | The whole layout/slot geometry model.                                                                                                                                                              |

## 23.L Important implementation patterns

1. **Pure repository interface + Mongo adapter** — `…common.repository.X` (framework-free) implemented
   by `…repository.mongodb.MongoXRepositoryCustomImpl`, which delegates to a Spring Data interface
   and hand-copies fields.
2. **Entity extends generated model** — `MongoXEntity extends X`, so DB ≡ DTO ≡ JSON field names.
3. **Schema-first code generation** — YAML → OpenAPI Generator → `@lombok.Data @JsonInclude(NON_NULL)` POJOs.
4. **`spring.factories` handler registration** — ETL handlers are contributed to `rise-api-utils` by
   interface FQN, not by Spring component scanning.
5. **`RISEApplicationContext.getComponent(...)`** — a service-locator workaround for autowiring inside
   the library's listener context (documented in `infra-business-clock-etl/README.md`).
6. **3D tiling with UUID versions** — `{x}_{y}_{time}` identity + per-tile UUID enables cheap
   "nothing changed" responses.
7. **Envelope types** — `APIResponse<T>` / `APIPaginatedResponse<T>` with `Meta{page, dataTileVersions}`.
8. **Two-stage aggregation for grouping** — count-group then page-group then `$in` fetch
   (`findLocationsWithTracks`).
9. **In-memory scheduled caches** — `AtomicReference` + `@PostConstruct @Scheduled` for map config
   (60 s) and track coordinates (1 h).
10. **Actual-frontier reconciliation** — forecasts are never allowed to overwrite confirmed data.
11. **Context-object event handlers (frontend)** — pure functions over `MasterLayoutEventContext`
    instead of fat component methods.
12. **Signal stores for new state, classic NgRx for legacy** — deliberate coexistence.
13. **`rxMethod` polling with `merge(interval, fetchNow$)` + `takeUntil(stopPolling$)`**.
14. **Root-scoped `MapService` with re-attach** — `setTarget()` instead of rebuilding the map.
15. **Style caching + quantisation** — train icon styles keyed by `colour|directionBucket|selected`.
16. **Greedy collision-avoiding label placement** with a `Float64Array` occupancy buffer.
17. **Composite SVG data-URI markers** — decode base64 → rewrite fills → `encodeURIComponent`.
18. **Cache-through services** — `cacheDb.get$` → `switchMap` → HTTP → `tap(set)`.
19. **Sequential paged fetch** — `fetchPage(0)` → `totalPages` → `concatMap` + `reduce`, `retry(3)`.
20. **Interceptor-based demo mode** — one interceptor replaces the entire backend.
21. **`@JsonInclude(NON_NULL)` + optional TS fields** — null fields vanish from the wire.
22. **`@Validated` + `@Min/@Max` constants from `APIPaginatedResponse`** — page-size limits live with
    the envelope.

## 23.M Important architectural decisions

| #   | Decision                                                                                  | Evidence / consequence                                                                         |
| --- | ----------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| 1   | **CQRS split** — five write-only ETLs, one read-only service                              | No shared service layer; MongoDB is the contract                                               |
| 2   | **Event sourcing at the boundary, not internally** — events are transformed and discarded | No event store; replay depends entirely on upstream                                            |
| 3   | **Schema-first, generated model**                                                         | `components/schemas/**` + `infra-model.yaml` are the single source of truth                    |
| 4   | **Denormalise for read speed**                                                            | `TrackCoordinates` duplicates location data per track; `TrainPosition` embeds resolved `{x,y}` |
| 5   | **Pre-resolve geometry at ingest**                                                        | Restriction `segments` → `edgePaths` with coordinates, so the browser only draws               |
| 6   | **3D tiling + version delta instead of streaming**                                        | Simple HTTP polling; no WebSocket/SSE anywhere                                                 |
| 7   | **Data-driven map behaviour**                                                             | Zoom thresholds, tile sizes and poll rates come from `MapConfig` in MongoDB                    |
| 8   | **Business clock as a first-class concept**                                               | Enables time travel; a client-side custom clock overlays it                                    |
| 9   | **Authentication delegated entirely to the platform**                                     | No security code in this repository at all                                                     |
| 10  | **MFEs as npm libraries, not Module Federation**                                          | Version-locked at build time; also pinned in Helm                                              |
| 11  | **Signal stores for new features, classic NgRx retained**                                 | Documented as policy in `AGENTS.md`; both are live                                             |
| 12  | **`MapService` as the single OpenLayers owner**                                           | Root-scoped, survives navigation, re-attaches to the DOM                                       |
| 13  | **Client-side "current position" selection**                                              | The server returns whole tiles; the browser filters by time                                    |
| 14  | **Positions accumulate in the store, filtering happens at render**                        | Cheap time scrubbing, unbounded memory growth                                                  |
| 15  | **Fail-soft ingest**                                                                      | Most ETLs swallow exceptions and ACK; only restriction/infra-graph handlers NACK               |
| 16  | **No transactions anywhere**                                                              | Accepted eventual/partial consistency (e.g. clock delete+save)                                 |
| 17  | **Index creation by the ETL, not the query service**                                      | `IndexConfig` runs in `infra-trainoperation-etl`                                               |
| 18  | **In-memory infrastructure graph**                                                        | Fast lookups, but lost on restart and split across two competing consumers                     |
| 19  | **IndexedDB for immutable payloads**                                                      | Base graph / map config / locations cached for 1 h                                             |
| 20  | **Single screen, panel state machine instead of routing**                                 | `PanelStateStore` replaces route-driven layout                                                 |
| 21  | **Demo mode as a first-class build configuration**                                        | Full offline development without any backend                                                   |
| 22  | **i18n from day one**                                                                     | `$localize` with explicit `@@ids` throughout                                                   |
| 23  | **Event-driven E2E testing**                                                              | `module-tests` publishes real AMQP events and validates canvas pixels                          |

## 23.N — Known unknowns / information not found

### N.1 Not determinable from this repository

| Item                                                                          | Status                                                                                                                                                                                       |
| ----------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| RabbitMQ **routing key for `RestrictionEvent`**                               | **NOT DETERMINED**                                                                                                                                                                           |
| RabbitMQ **routing key for `InfraOperationalPeriodEvent`**                    | **NOT DETERMINED**                                                                                                                                                                           |
| Queue/binding **declaration** (durable? exclusive? arguments? DLX? TTL?)      | **NOT DETERMINED** (inside `rise-api-utils`)                                                                                                                                                 |
| **ACK/NACK/requeue semantics**, retry counts, backoff, prefetch, concurrency  | **NOT DETERMINED**                                                                                                                                                                           |
| **Dead-letter queue** existence                                               | **NOT FOUND**                                                                                                                                                                                |
| `InfraOperationalPeriodEvent` **payload schema**                              | **NOT DETERMINED** (no fixture field list read; only the file name)                                                                                                                          |
| Train **edit** HTTP contract (verb/path/body/response)                        | **NOT DETERMINED** (inside `@tps/mfe-train-operation`)                                                                                                                                       |
| Restriction **state PATCH** contract                                          | **NOT DETERMINED** (inside `@tps/rimfe-restriction`); the `rivm-ui-components` docs suggest `PATCH {baseUrl}/api/restriction/cmd/restrictions/{id}` with `{id, state}` — **unverified here** |
| Train list / TIP / composition endpoints                                      | **NOT DETERMINED** (only demo-mode URL fragments observed)                                                                                                                                   |
| AEM backend contract                                                          | **NOT DETERMINED** (only demo-mode URL fragments observed)                                                                                                                                   |
| Who **writes `infra-rivm.map-config`** in production                          | **NOT FOUND**                                                                                                                                                                                |
| Keycloak realm/client configuration, token format, session handling           | **NOT FOUND**                                                                                                                                                                                |
| TLS termination, CSP/HSTS headers, rate limiting                              | **NOT FOUND**                                                                                                                                                                                |
| CI/CD pipeline definition (`.gitlab-ci.yml`)                                  | **NOT FOUND** in this repository                                                                                                                                                             |
| Dockerfiles                                                                   | **NOT FOUND** (images are produced by the `de.hacon.tps.convention.*` plugins)                                                                                                               |
| `rise-common` Helm library internals (env var names, secret references)       | **NOT DETERMINED**                                                                                                                                                                           |
| Monitoring / metrics / tracing (no actuator, no Micrometer, no OpenTelemetry) | **NOT FOUND**                                                                                                                                                                                |
| Backup/retention policy for `data-tile` growth                                | **NOT FOUND**                                                                                                                                                                                |

### N.2 Present but unused / dead code

| Item                                                                                                                                                                                                                  | Location                                              |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| `app.feature.dataTileVersion.isActive`                                                                                                                                                                                | `infra-query-svc/application.properties` — never read |
| `app.db.collection.location` / `infra-rivm.location`                                                                                                                                                                  | properties only — no entity                           |
| Generated models `Activity`, `Region`, `LocationDataTile`                                                                                                                                                             | never referenced                                      |
| Schemas `LocationTrack.yaml`, `basic/rest.yaml`                                                                                                                                                                       | not in `infra-model.yaml`                             |
| `InfraTrainOperationService.processTrainOperationEvent`                                                                                                                                                               | no handler calls it                                   |
| `InfraTrainOperationService.hasEntityChangedForEvent`, `shouldSaveForecastMovement`, `shouldSaveForecastLocation`, `countExistingLocationActivities`, `logSkippedMovement`, `logMissingLocation`, `FilteredPositions` | unreferenced                                          |
| `ActivitiesDTO`, `LocationAttributes`                                                                                                                                                                                 | unreferenced                                          |
| `RiseToInfraMapper.isDeparture` / `isArrival` (both mappers)                                                                                                                                                          | unreferenced                                          |
| `GET /track-coordinates`                                                                                                                                                                                              | no frontend consumer                                  |
| `MfeViewTrainListComponent`                                                                                                                                                                                           | not used by any template                              |
| `RibbonStateService`                                                                                                                                                                                                  | superseded by `RibbonStateStore`                      |
| `tabs` NgRx slice (actions/reducer/selectors/state)                                                                                                                                                                   | not registered in `provideStore`                      |
| `models/session-mgmt-model.ts`, `SESSION_MGMT_DB_NAME`, `MAXIMUM_ALLOWED_COUNT_FOR_ADD_INFRA`                                                                                                                         | unreferenced                                          |
| `TILE_API_POLLING_TIMER`, `PAGE_SIZE` (`app-constant.ts`)                                                                                                                                                             | unreferenced                                          |
| `environment.*.providers` (dev/demo)                                                                                                                                                                                  | never consumed                                        |
| `InfraContentComponent.error$`                                                                                                                                                                                        | exposed but not bound in the template                 |
| `TrainPositionStore.setTileIds`, `clearTrainPositions`; `TileManagementService.createAndStartPolling`, `calculateAndCreateTiles`; `OpenLayerInfraUtility.fitMapViewWithMinZoom`, `loadGraphData`                      | marked deprecated / unused                            |
| `EdgeRecord.angleDeg`, `.isOctilinear`; `InfraNode.signalInfo`, `.isBoundaryNode`                                                                                                                                     | never populated                                       |

### N.3 Observed inconsistencies (reported, not fixed)

| #   | Observation                                                                                                                                                                                                                                                                                                                                                                                                       |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | **Restriction state mismatch** — schema says `ACTIVE\|INACTIVE\|CANCELLED`; the frontend's `isRestrictionActive()` tests for `'EFFECTIVE'`, so restrictions always render as inactive grey. `ACTIVE_RESTRICTION_STATES` (ribbon) accepts `effective` and `active`.                                                                                                                                                |
| 2   | **`kmValue` never read** — backend emits `infraNodeAddress.kmValue`; the frontend reads `infraNodeAddress.kmValueMillimeters`. `InfraNode.kmValue` is always `undefined`.                                                                                                                                                                                                                                         |
| 3   | **Node labels never render** — `createMainVectorLayer` calls `getFeatureStyle(feature)` without a zoom argument, so the zoom-≥-18 node label branch is unreachable.                                                                                                                                                                                                                                               |
| 4   | **Shared queue names** — `infra-trainoperation-etl` and `infra-restriction-etl` configure identical queue names for `infra.operational-period` and `infra.microscopic-region`, making them competing consumers of the same in-memory-graph feed.                                                                                                                                                                  |
| 5   | **Restriction z-index** — `RESTRICTION_STYLE_CONFIG.zIndex = 50` contradicts `MAP_LAYER_ZINDEX.restrictions = 20` and its doc-comment; restrictions render above the label layers.                                                                                                                                                                                                                                |
| 6   | **Boundary tile loss** — `DataTileService.createTileIds` derives the spatial extent from a single point; when a coordinate lands exactly on a grid boundary, `floor == ceil` yields zero tiles.                                                                                                                                                                                                                   |
| 7   | **Duplicate tile ids ⇒ 500** — `Collectors.toMap` in `TrainPositionService` throws `IllegalStateException` on duplicate ids in the request body, surfacing as HTTP 500.                                                                                                                                                                                                                                           |
| 8   | **Two error-body shapes** — `GlobalExceptionHandler` produces `{errors:[…]}`, but inherited `ResponseEntityExceptionHandler` methods produce Spring's default shape.                                                                                                                                                                                                                                              |
| 9   | **Non-atomic clock replace** — `deleteAll()` + `save()` can leave the collection empty (→ 404).                                                                                                                                                                                                                                                                                                                   |
| 10  | **Tile version bumped before positions are written** — a poll in that window sees a new version with stale data (self-corrects on the next poll).                                                                                                                                                                                                                                                                 |
| 11  | **`SimpleDateFormat` static fields** — `RiseToInfraMapper` (clock) and `TrainOperationUtil` hold static, non-thread-safe formatters.                                                                                                                                                                                                                                                                              |
| 12  | **Missing indexes** — `restriction` (`effectiveTimePeriod.*`, `lastModified`) and `track-coordinates` (`locationSubEntityData.id`) are queried without indexes.                                                                                                                                                                                                                                                   |
| 13  | **`train-position` indexes created by the ETL** — running only the query service leaves them absent.                                                                                                                                                                                                                                                                                                              |
| 14  | **`app.db.collection.map-config` missing from `infra-common-lib`** — any consumer that scans the mongodb package must define it itself.                                                                                                                                                                                                                                                                           |
| 15  | **Train direction hard-coded to 90°** — all train icons point the same way.                                                                                                                                                                                                                                                                                                                                       |
| 16  | **`TrainPosition` store never evicts** — positions accumulate for the whole session.                                                                                                                                                                                                                                                                                                                              |
| 17  | **CORS hard-coded to `http://localhost:4200`** with no property override.                                                                                                                                                                                                                                                                                                                                         |
| 18  | **`LogoutApiService.logout().subscribe()`** has no error handler and performs no navigation or state cleanup.                                                                                                                                                                                                                                                                                                     |
| 19  | **Almost all errors are invisible to the user** — only two snackbar paths exist.                                                                                                                                                                                                                                                                                                                                  |
| 20  | **`filterMovementsBetweenStations` is now a no-op** in both mappers, while `docs/TrainOperationMovementFlow.md` still documents the removed filtering algorithm.                                                                                                                                                                                                                                                  |
| 21  | **`RiseToInfraMapper.filterMovementsBetweenStations` logs at `warn`** on every event ("Processing activities - total: {}").                                                                                                                                                                                                                                                                                       |
| 22  | **`RestrictionMapper.mapInfraEdgeWithOffsets`** assigns `startPercentage` twice (the second assignment is redundant).                                                                                                                                                                                                                                                                                             |
| 23  | **`TrackCoordinates.yaml` `required` list** names `nodes`, `locationBaseSubEntityData`, `trackBaseSubEntityData` — none of which are declared properties.                                                                                                                                                                                                                                                         |
| 24  | **`RestrictionData.yaml` re-declares `InfraMicroscopicEdgeData`**, duplicating `BaseGraph.yaml`.                                                                                                                                                                                                                                                                                                                  |
| 25  | **Repository docs are stale** — `doc/architecture.md`, `infra-trainoperation-etl/docs/*` and `AGENTS.md` reference classes (`MovementToInfraMapper`, `MovementUtil`, `TileCalculator`, `MapConfigController`, `SessionMgmtService`, `InfraTrainOperationEventHandler`), versions (Angular 20, Spring Boot 3.3.x, `@tps/rivm-common-components 1.6.1`) and paths (`/api/v1/infra-query/...`) that no longer exist. |

---

## Document provenance

- **Method:** exhaustive read-only inspection of `c:\Users\z0059stn\Projects\work\infra` —
  `settings.gradle.kts`, all `build.gradle.kts`, `gradle/libs.versions.toml`, every
  `application.properties`, every `META-INF/spring.factories`, all 60+ Java main sources, all 33
  schema YAMLs, `infra-model.yaml`, all non-spec Angular sources (`~8 000` lines), `angular.json`,
  `package.json`, all three `environment*.ts`, the Helm chart and templates, and the `module-tests`
  configuration.
- **Files created:** exactly one — this document.
- **Files modified / deleted / executed:** **none**. Only read-only shell commands
  (`Get-ChildItem`, `Get-Content`, `Select-Object`, `Measure-Object`) were used, plus two temporary
  concatenations written to `%TEMP%` for reading convenience.
- **Marking convention:** every fact is traceable to a named file/class/method; anything that could
  not be established from the code is explicitly marked **NOT FOUND / NOT DETERMINED**.
