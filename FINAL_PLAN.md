# Productionization Plan For `website-generator` With Django Runtime

## Summary

Evolve `website-generator` from a learning SSG into a `static-first website platform` for paid client work, while staying `internal-first before 1.0`.

The platform is organized into 4 layers:

1. `Static Core`
- content
- routing
- themes
- blocks
- assets
- typed JSON export
- frontend islands

2. `Runtime Core`
- checkout
- payment callbacks/webhooks
- order persistence
- inventory reads/writes
- auth/sessions
- public order status
- runtime APIs

3. `Admin / Back Office`
- product and variant management
- stock management
- media management
- order/payment inspection
- basic catalog editing
- audit visibility

4. `Business Integrations`
- accounting export
- shipping
- email/SMS
- tax
- CRM
- analytics
- external data sources

Core decision update:
- use `Django` for runtime and admin
- use `PostgreSQL` as the primary operational database
- use `Django ORM + Django migrations`
- do **not** use MongoDB as the primary source of truth
- do **not** build a full CMS, ERP, or accounting suite yet

## Public Contracts

### Official supported path

- Official config for new projects: `version: 2`
- Official template engine: `django`
- Official product shape:
  - `wg` for static build/CLI
  - `wg-runtime` as a Django application
  - `wg-admin` initially implemented through Django admin and small custom admin views inside `wg-runtime`
- Keep legacy/v1 config readable until 1.0, but stop extending old shapes

### Public runtime contract

Keep the same runtime capability contract, but implement it in Django:

- `create_action_session(payload, config)`
- `handle_callback(request, config)`
- `verify_event(request, config)`
- `lookup_public_state(id, config)`

### Public provider contracts

Define stable interfaces for:

- `payment provider adapter`
- `inventory provider interface`
- `accounting export interface`
- `shipping provider interface`
- `notification provider interface`

### Config/API additions

- Make `runtime.targets[].type: django_service` the official runtime target type
- Keep `fastapi_service` as a deprecated compatibility alias until 1.0
- Add an official non-file data-source path for build-time ingestion of runtime-managed catalog data:
  - editorial content remains file-based
  - commerce catalog can be pulled from `wg-runtime` as published snapshot data

## Implementation Changes

### 1. Freeze the product boundary

The static core must own only:

- page generation
- typed content models
- routing
- theme and block rendering
- public JSON export
- frontend island mounting
- runtime manifest emission

The static core must **not** own:

- secrets
- mutable state
- payment verification
- inventory truth
- order management
- admin auth
- accounting/bookkeeping

Do not add:

- more template engines
- runtime business logic into build code
- a full CMS builder
- a separate admin SPA yet

### 2. Introduce Django runtime as the real backend

Replace the earlier FastAPI/Alembic/SQLAlchemy direction with:

- `Django`
- `Django REST Framework` for JSON APIs
- `PostgreSQL`
- `Django ORM`
- `Django migrations`

`wg-runtime` becomes a real Django application with these internal subsystems:

- `accounts`
- `catalog`
- `inventory`
- `orders`
- `payments`
- `media`
- `audit`
- `integrations`

Responsibilities:

- real persistence
- order lifecycle
- payment lifecycle
- inventory updates
- callback/webhook verification
- idempotency
- admin auth
- public order status
- admin APIs
- published catalog snapshot export for the static build

Keep the current mock gateway/runtime behavior as a `dev/test simulator`, but move the production path to Django.

### 3. Use PostgreSQL as the primary operational store

Use PostgreSQL from the start for:

- products and variants
- inventory
- orders and payments
- refunds
- admin users
- audit events
- media metadata

Reasoning baked into the design:

- relational data and transactions matter for orders/payments/stock
- constraints matter
- concurrent stock/payment updates matter
- reporting and reconciliation matter

To preserve flexibility while the schema evolves quickly:

- use additive migrations
- use nullable fields where appropriate
- use `JSONField` for provider-specific metadata, callback payloads, and evolving integration details

Do **not** use MongoDB as the primary DB for runtime truth.
If a document store is ever added later, it should be for secondary use cases like logs/search/integration payload archives, not for core commerce state.

### 4. Define source-of-truth rules clearly

Split content ownership deliberately:

- `filesystem source of truth`
  - pages
  - blog posts
  - docs
  - marketing content
- `runtime/PostgreSQL source of truth`
  - products
  - variants
  - stock
  - orders
  - payments
  - refunds
  - media metadata
  - admin users
  - audit events

Static build integration rule:

- the build core gains an official `runtime_export` or equivalent data-source path
- `wg-runtime` exposes a published catalog snapshot for build-time ingestion
- the static site renders product/catalog pages from published runtime data
- inventory and payment state remain runtime-only

This keeps merchandisers out of git while keeping storefront pages static.

### 5. Define the runtime domain model now

Create explicit entities:

- `Product`
- `ProductVariant`
- `InventoryItem`
- `InventoryAdjustment`
- `Order`
- `OrderLine`
- `PaymentAttempt`
- `Refund`
- `AdminUser`
- `AuditEvent`
- `MediaAsset`

Required order states:

- `draft`
- `pending_payment`
- `paid`
- `failed`
- `cancelled`
- `fulfilled`
- `refunded`
- `partially_refunded`

Required payment concepts:

- payment provider adapter
- payment attempt
- callback verification result
- authority/reference storage
- duplicate callback safety
- idempotency key handling
- audit trail

Required inventory concepts:

- SKU-level stock
- variant-level stock
- stock policy
- manual adjustments
- low-stock signal
- optional reservation/hold support

### 6. Keep accounting as an integration boundary

Do **not** build a full accounting engine first.

Build inside the platform:

- order ledger
- payment ledger
- refund ledger
- invoice/receipt metadata
- tax totals
- settlement/reference fields
- exportable accounting records

Do **not** build yet:

- double-entry bookkeeping
- journal engine
- accounting reports
- full finance suite

Boundary rule:

- platform records `commercial truth`
- accounting software records `bookkeeping truth`

### 7. Build a small admin, using Django admin first

`wg-admin` should initially be:

- Django admin
- custom admin forms/actions where needed
- a few targeted custom admin pages only if Django admin is not enough

First admin scope:

- admin login/auth
- product CRUD
- variant CRUD
- stock editing
- media upload/management
- order lookup
- payment status inspection
- audit event visibility
- basic product/catalog editing

Initial roles:

- `admin`
- `editor`
- `merchandiser`
- `support`

Do **not** build first:

- a full visual page builder
- a full WYSIWYG CMS
- full customer account suite
- advanced analytics
- marketing automation
- a custom admin frontend unless Django admin becomes a real blocker

### 8. Add the operational systems people forget

Plan these early:

- `Media management`
  - upload
  - storage abstraction
  - naming
  - cleanup
  - public URL generation
- `Preview/publish`
  - draft/published states for runtime-managed catalog data
  - publish step that updates the exported catalog snapshot
- `Notifications`
  - order confirmation
  - payment success/failure
  - low stock
  - admin alerts
- `Shipping foundation`
  - address model
  - delivery method model
  - shipment status fields
  - tracking link support
- `Pricing/tax foundation`
  - discounts later
  - tax inclusion/exclusion flags
  - shipping fee modeling
- `Auditability`
  - who changed stock
  - who changed price
  - who changed order/payment status
  - who issued refund
- `Durability`
  - migrations
  - backups
  - restore procedure
- `Observability`
  - structured logs
  - callback traces
  - admin action traces
  - error reporting

### 9. Strengthen quality gates and release discipline

Use production-oriented gates:

- `ruff`
- `ruff format --check`
- `mypy` on public/core/runtime modules
- `pytest`
- CI on:
  - Ubuntu
  - Windows
  - Python 3.10
  - Python 3.12

Release-blocking smoke tests:

- `wg init`
- `wg build`
- `wg serve`
- Django runtime startup
- Django migrations
- admin login
- storefront checkout flow
- callback verification flow
- order status flow
- published catalog export flow

### 10. Use real client work as the maturity ladder

Do not aim for 1.0 yet.

Dogfood in this order:

1. marketing/content site
2. docs/knowledge site
3. storefront or mixed static-plus-runtime site

After each real project, classify gaps into:

- correctness bug
- missing capability
- ergonomics/docs problem

Only broaden compatibility promises after those project types work cleanly.

## Implementation Phases

### Phase 1: Product Surface And Core Reliability

- document `config v2` as official
- tighten validation and error messages
- make build outputs deterministic
- normalize Windows/temp/build artifact handling
- document supported engine/platform/version matrix
- add changelog and deprecation policy

### Phase 2: Django Runtime Foundation

- turn `wg-runtime` into a real Django application
- add PostgreSQL support
- define models for catalog, inventory, orders, payments, media, audit
- add Django migrations
- add DRF or equivalent JSON API layer
- keep the current mock runtime as dev/test mode

### Phase 3: Catalog Source Integration

- add official runtime-backed catalog export
- let static builds ingest published product/catalog data from runtime
- keep editorial pages/docs/blog file-based
- keep mutable inventory/payment state runtime-only

### Phase 4: First Admin

- use Django admin as the first back office
- add product/variant/stock/media/order/payment admin flows
- add role/group permissions
- add audit views
- keep admin intentionally boring and operational

### Phase 5: Integration Interfaces

- payment adapters
- notification adapters
- shipping hooks
- accounting export
- tax/pricing hooks
- external data connectors later

### Phase 6: Pre-1.0 Hardening

- cross-platform CI
- stronger typing
- migration guide
- extension author guide
- theme author guide
- runtime integration guide
- release checklist
- real-project acceptance review

## Test Plan

- Config tests:
  - `version: 2` is the official shape
  - legacy/v1 config loads with warnings
  - invalid config fails with actionable output
- Build tests:
  - deterministic routes, JSON, and manifests
  - missing template/block/layout failures are readable
  - blog/docs/store fixtures build cleanly
- Runtime tests:
  - runtime startup
  - migrations apply cleanly
  - checkout session creation
  - callback verification
  - idempotent duplicate callback handling
  - order state transitions
  - inventory update behavior
  - published catalog export behavior
- Admin tests:
  - auth
  - role permissions
  - product/variant CRUD
  - stock adjustment logging
  - order/payment inspection
- Integration tests:
  - payment adapter contract
  - accounting export contract
  - shipping hook contract
  - notification delivery contract
- Cross-platform tests:
  - Windows path behavior
  - temp directory cleanup
  - output cleanup behavior
- CLI/runtime smoke tests:
  - init/build/serve
  - runtime startup
  - admin availability
  - starter project build + runtime integration

## Assumptions And Defaults

- Product posture: `internal-first OSS before 1.0`
- Business target: `mixed custom client work`
- Official template engine for now: `django`
- Official config for new work: `version: 2`
- Runtime stack: `Django + DRF + PostgreSQL + Django ORM + Django migrations`
- Admin stack: `Django admin first`
- Deployment default: `one site per project`, not multi-tenant first
- Commerce default: `physical products first`
- Customer default: `guest checkout first`, admin auth only by default
- Runtime is first-class for production use cases, but remains separate from the static build core
- Accounting is an integration target, not a first-party subsystem at first
- MongoDB is **not** the primary operational DB
- Flexible runtime metadata should use PostgreSQL `JSONField`, not a schemaless primary DB
- 1.0 should wait until the platform has successfully powered:
  - one serious content site
  - one docs site
  - one storefront or mixed runtime-backed site
