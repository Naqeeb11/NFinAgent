# Security Safety and Governance Boundaries

## Security controls

- OAuth2/OIDC authentication; RBAC plus tenant- and portfolio-scoped authorization.
- Secrets only in a secret manager; never logs, events, notebooks, or Git.
- Encrypt data in transit and at rest. Rotate API credentials and audit privileged access.
- Validate all provider data, API input, schemas, and model/strategy artifact signatures.
- Separate development, research, and production-like paper environments with distinct credentials and datasets.
- Apply rate limiting, dependency scanning, SBOM generation, code review, and supply-chain pinning.

## Agent safety controls

- Tool allow-lists and read-only data access by default.
- Structured output schemas, citation checks, token/cost budgets, timeouts, and retries.
- Treat retrieved web/news/document content as untrusted. Do not follow instructions embedded in it.
- Capture prompts, tool calls, response hashes, model IDs, and policy decisions in traces with sensitive-data redaction.
- Human approval is mandatory for model/strategy promotion and any later execution-capability proposal.

## Financial-product boundaries

- Clearly label forecasts and simulation results as uncertain research outputs.
- Do not present personalized advice, guaranteed returns, or suitability determinations.
- The risk engine has hard limits and fail-closed defaults: stale data, missing quality checks, missing version metadata, or unresolved policy violations reject simulation actions.
- Live execution is out of scope and needs separate legal, compliance, security, operational-resilience, and incident-response approvals.
