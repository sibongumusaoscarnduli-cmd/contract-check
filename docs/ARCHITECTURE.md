# Architecture

ContractCheck has three small layers. The CLI loads an OpenAPI 3 JSON document and turns supported operations into representative requests. The runner sends requests through Python's standard library to a loopback-only base URL, then checks the documented status, JSON content type, and a useful subset of response-schema constraints. The report layer returns the same results as terminal text and optional JSON.

Schema samples use explicit examples, defaults, enum values, and then conservative values based on type. Local `#/components/schemas/...` references are resolved with a recursion limit. Response validation checks JSON types, required object properties, enum membership, numeric bounds, and basic array/string lengths.

The fixture API is a separate local HTTP server. Keeping it separate means the runner exercises real HTTP behavior while tests can start and stop a disposable service on an ephemeral port. The browser page is static and synthetic; it explains the output without running network requests.

## Safety and boundaries

Only plain HTTP loopback hosts are accepted. Requests have a three-second timeout, redirects are not followed, and response reads are capped at 1 MB. The implementation deliberately skips remote schema references, arbitrary hosts, authentication, mutations beyond the bundled sample, and complete JSON Schema support. It is a teaching tool, not a security audit or production test platform.
