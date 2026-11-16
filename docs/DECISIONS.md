# SafeGate — Architecture Decision Records (ADRs)

## ADR-001: Monorepo Architecture with Dedicated Apps and Packages
- **Status:** Accepted
- **Context:** SafeGate comprises multiple deliverables: API service (`apps/api`), async processing worker (`apps/worker`), moderation dashboard (`apps/console`), integration mock (`apps/demo-host`), multi-language SDKs (`packages/sdk-python`, `packages/sdk-node`, `packages/sdk-react`), and ML pipeline definitions (`ml/`).
- **Decision:** Use a single monorepo layout with clean boundary isolation. Core data models and schemas are shared, preventing schema drift between the API, worker tasks, and client SDKs.
- **Consequences:** Centralizes CI/CD, dependency auditing, and contract testing. Requires disciplined build tooling to ensure independent deployments.

---

## ADR-002: Strict Fail-Closed Security Invariant
- **Status:** Accepted
- **Context:** Media firewall engines can fail due to decoder crashes, malformed codecs, OOM errors, worker disconnections, or inference timeouts. A "fail-open" design would allow potentially malicious deepfakes or illegal material to reach public consumers upon failure.
- **Decision:** SafeGate strictly enforces a fail-closed architecture. In any failure state (decompression, model exception, network failure, or downstream unavailability), the system returns `HUMAN_REVIEW` or `BLOCK`. `ALLOW` is mathematically unreachable without explicit, clean green verdicts on 100% of analyzed frames.
- **Consequences:** Prevents publishing of malicious/unverified content during outages. May increase reviewer queue load during degraded service states.

---

## ADR-003: Hierarchical Configuration via Pydantic Settings v2
- **Status:** Accepted
- **Context:** Production environments require runtime flexibility across YAML config files and environment variables, with strict type safety, threshold range checks, and security defaults.
- **Decision:** Adopt Pydantic Settings v2 with nested sub-models (`ServerConfig`, `DatabaseConfig`, `RedisConfig`, `StorageConfig`, `LimitsConfig`, `PolicyConfig`, `ThresholdsConfig`, `ChildSafetyConfig`, `AuditConfig`). The configuration validates threshold order ($\tau_{\text{yellow}} < \tau_{\text{red}}$) and ensures fail-closed flags cannot be disabled by accident.
- **Consequences:** Zero-cost validation at startup. Misconfigurations abort service initialization immediately.

---

## ADR-004: RFC 7807 Problem Details for HTTP APIs
- **Status:** Accepted
- **Context:** Client SDKs and host services require structured, machine-parsable error payloads that avoid leaking internal stack traces while providing precise diagnostic codes.
- **Decision:** Adopt RFC 7807 (`application/problem+json`) error specifications across all REST endpoints. Custom exceptions map directly into standard problem models with correlation IDs and timestamps.
- **Consequences:** Uniform client-side error handling across Python, Node.js, and browser runtimes.

---

## ADR-005: HMAC-SHA256 Hash-Chained Audit Ledger
- **Status:** Accepted
- **Context:** Decisions made by Trust & Safety systems (e.g. content blocking or approvals) require non-repudiation and tamper detection for regulatory compliance, appeals, and internal audits.
- **Decision:** Maintain an append-only audit ledger where each event record includes an HMAC-SHA256 signature calculated over the record's payload concatenated with the signature of the previous record ($S_n = \text{HMAC}(K, S_{n-1} \parallel \text{Event}_n)$).
- **Consequences:** Any retroactive modification, deletion, or reordering of audit records breaks the hash chain and triggers security alerts.
