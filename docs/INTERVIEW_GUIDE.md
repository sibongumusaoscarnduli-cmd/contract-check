# Interview guide

## What problem does ContractCheck solve?

It turns a small OpenAPI document into repeatable requests and checks whether a local API response matches the documented contract. That can catch a wrong status code, missing response field, invalid type, or unexpected enum value before a change is released.

## Why use a fixture API?

The fixture gives the runner a predictable target. Tests can start it on an ephemeral local port, check real HTTP behavior, and shut it down without depending on another team's service or internet access.

## Why reject non-local URLs?

Generated requests can create or alter data. This first version is intentionally a local learning tool, so it refuses non-loopback targets and does not follow redirects. A production-quality runner would need a stronger authorization model, explicit environment controls, authentication handling, rate limits, and auditability.

## What would you improve next?

Add broader JSON Schema support, query parameter generation, reusable security schemes, and a property-based case generator. Each addition should keep the network boundary explicit and add fixture-based tests. Explain which features are intentionally out of scope before describing future work.
