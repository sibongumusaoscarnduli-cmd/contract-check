# ContractCheck

ContractCheck is a small API regression runner that reads an OpenAPI 3 JSON document, makes bounded requests to a local service, and reports response contract failures. It is designed as a learning project: the bundled fixture API is safe to exercise, and the runner refuses non-local hosts.

**Stack:** Python 3.11+, `urllib`, JSON, `unittest`, HTML/CSS/JavaScript. No third-party runtime dependencies.

## Run the bundled example

In one terminal, from this directory:

```sh
python3 -m contractcheck.fixture --port 8070
```

In a second terminal:

```sh
python3 -m contractcheck run examples/orders.openapi.json --url http://127.0.0.1:8070 --json report.json
```

The runner generates one representative request for each supported `GET` or JSON `POST` operation, checks the documented status, content type and response schema, and writes a JSON report when requested. All generated data is synthetic. It never sends requests to the public internet.

## Safety boundary

The CLI accepts only loopback URLs (`localhost`, `127.0.0.1`, or `::1`), limits each response body to 1 MB, sets a request timeout, and does not follow redirects. Use a disposable local service. This first version supports OpenAPI 3 JSON documents, local component-schema references, path parameters, and `GET`/JSON `POST`; it does not implement authentication, multipart bodies, remote `$ref`s, or full JSON Schema semantics.

## Development

```sh
python3 -m unittest discover -v
python3 -m contractcheck --help
```

The static `docs/` page is an explanatory, client-side sample. It does not send requests. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), [`docs/TESTING.md`](docs/TESTING.md), [`docs/INTERVIEW_GUIDE.md`](docs/INTERVIEW_GUIDE.md), and [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

## Inspiration and attribution

The project explores contract-driven and generated API testing patterns documented by [Schemathesis](https://schemathesis.readthedocs.io/en/stable/quick-start/). ContractCheck is an independent, deliberately smaller implementation and does not copy Schemathesis code or brand. Created with AI assistance; the repository owner should run it and be ready to explain its design and limits.
