"""A bounded OpenAPI exerciser for local development services."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

MAX_BODY_BYTES = 1_000_000
TIMEOUT_SECONDS = 3
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
METHODS = {"get", "post"}


class ContractError(ValueError):
    """Raised when the document cannot be safely or meaningfully exercised."""


@dataclass
class CheckResult:
    method: str
    path: str
    case: str
    expected_status: str
    actual_status: int | None
    passed: bool
    findings: list[str]


def load_document(path: str | Path) -> dict[str, Any]:
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"Cannot read OpenAPI JSON: {exc}") from exc
    if not isinstance(document, dict) or not str(document.get("openapi", "")).startswith("3."):
        raise ContractError("Expected an OpenAPI 3.x JSON document.")
    if not isinstance(document.get("paths"), dict) or not document["paths"]:
        raise ContractError("OpenAPI document must define at least one path.")
    return document


def _resolve_ref(document: dict[str, Any], schema: dict[str, Any], depth: int = 0) -> dict[str, Any]:
    ref = schema.get("$ref")
    if ref is None:
        return schema
    if depth > 8 or not isinstance(ref, str) or not ref.startswith("#/components/schemas/"):
        raise ContractError(f"Unsupported or deeply nested schema reference: {ref}")
    value: Any = document
    for part in ref[2:].split("/"):
        value = value.get(part) if isinstance(value, dict) else None
    if not isinstance(value, dict):
        raise ContractError(f"Schema reference does not exist: {ref}")
    return _resolve_ref(document, value, depth + 1)


def _sample(schema: dict[str, Any], document: dict[str, Any], depth: int = 0) -> Any:
    if depth > 8:
        raise ContractError("Schema nesting is too deep to generate a sample.")
    schema = _resolve_ref(document, schema)
    for key in ("example", "default"):
        if key in schema:
            return schema[key]
    if isinstance(schema.get("enum"), list) and schema["enum"]:
        return schema["enum"][0]
    kind = schema.get("type")
    if kind == "object" or "properties" in schema:
        props = schema.get("properties", {})
        required = schema.get("required", list(props))
        return {name: _sample(props[name], document, depth + 1) for name in required if name in props}
    if kind == "array":
        return [_sample(schema.get("items", {}), document, depth + 1)]
    if kind == "integer":
        return schema.get("minimum", 1)
    if kind == "number":
        return schema.get("minimum", 1)
    if kind == "boolean":
        return True
    if kind == "string":
        if schema.get("format") == "date":
            return "2026-01-15"
        return "sample"
    return None


def _check_schema(value: Any, schema: dict[str, Any], document: dict[str, Any], where: str = "response", depth: int = 0) -> list[str]:
    if depth > 12:
        return [f"{where}: schema nesting exceeds 12 levels"]
    schema = _resolve_ref(document, schema)
    errors: list[str] = []
    kind = schema.get("type")
    types = {"object": dict, "array": list, "string": str, "integer": int, "number": (int, float), "boolean": bool}
    if kind in types:
        expected = types[kind]
        valid = isinstance(value, expected) and not (kind == "integer" and isinstance(value, bool))
        if not valid:
            return [f"{where}: expected {kind}, got {type(value).__name__}"]
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{where}: {value!r} is not in the allowed values")
    if kind == "object" or "properties" in schema:
        for name in schema.get("required", []):
            if name not in value:
                errors.append(f"{where}.{name}: required property is missing")
        for name, child in schema.get("properties", {}).items():
            if name in value:
                errors.extend(_check_schema(value[name], child, document, f"{where}.{name}", depth + 1))
    if kind == "array":
        for index, item in enumerate(value):
            errors.extend(_check_schema(item, schema.get("items", {}), document, f"{where}[{index}]", depth + 1))
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{where}: has fewer than {schema['minItems']} items")
    if kind in {"integer", "number"}:
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{where}: {value} is below minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{where}: {value} exceeds maximum {schema['maximum']}")
    if kind == "string":
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{where}: is shorter than {schema['minLength']} characters")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(f"{where}: exceeds {schema['maxLength']} characters")
    return errors


def _response_spec(operation: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    responses = operation.get("responses", {})
    if not isinstance(responses, dict) or not responses:
        raise ContractError("Each operation must document at least one response.")
    status = "200" if "200" in responses else next((key for key in responses if str(key).startswith("2") and str(key).isdigit()), None)
    if status is None:
        raise ContractError("Each operation must document a numeric success response.")
    return str(status), responses[status]


def _local_url(base_url: str, path: str) -> str:
    parsed = urllib.parse.urlsplit(base_url)
    if parsed.scheme != "http" or parsed.hostname not in LOCAL_HOSTS or parsed.username or parsed.password:
        raise ContractError("Safety stop: --url must be plain HTTP on localhost or a loopback IP.")
    if parsed.query or parsed.fragment:
        raise ContractError("Base URL must not include a query or fragment.")
    return base_url.rstrip("/") + "/" + path.lstrip("/")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def run(document: dict[str, Any], base_url: str) -> list[CheckResult]:
    results: list[CheckResult] = []
    opener = urllib.request.build_opener(_NoRedirect)
    for path, path_item in document["paths"].items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method.lower() not in METHODS or not isinstance(operation, dict):
                continue
            status, response_spec = _response_spec(operation)
            route = path
            for name in [segment[1:-1] for segment in path.split("/") if segment.startswith("{") and segment.endswith("}")]:
                parameter = next((p for p in operation.get("parameters", []) if p.get("name") == name), {})
                schema = parameter.get("schema", {})
                route = route.replace("{" + name + "}", urllib.parse.quote(str(_sample(schema, document))))
            url = _local_url(base_url, route)
            body = None
            headers = {"Accept": "application/json"}
            if method.lower() == "post":
                request_spec = operation.get("requestBody", {}).get("content", {}).get("application/json")
                if request_spec is None:
                    results.append(CheckResult(method.upper(), path, "positive", status, None, False, ["POST requires an application/json request body in this version."]))
                    continue
                body = json.dumps(_sample(request_spec.get("schema", {}), document)).encode("utf-8")
                headers["Content-Type"] = "application/json"
            request = urllib.request.Request(url, data=body, headers=headers, method=method.upper())
            findings: list[str] = []
            actual_status: int | None = None
            content_type = ""
            payload: Any = None
            try:
                with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
                    actual_status = response.status
                    content_type = response.headers.get("Content-Type", "")
                    raw = response.read(MAX_BODY_BYTES + 1)
                    if len(raw) > MAX_BODY_BYTES:
                        findings.append(f"Response exceeded {MAX_BODY_BYTES} bytes.")
                    elif raw:
                        try:
                            payload = json.loads(raw)
                        except (UnicodeDecodeError, json.JSONDecodeError):
                            findings.append("Response body is not valid JSON.")
            except urllib.error.HTTPError as exc:
                actual_status = exc.code
                content_type = exc.headers.get("Content-Type", "")
                raw = exc.read(MAX_BODY_BYTES + 1)
                if raw and len(raw) <= MAX_BODY_BYTES:
                    try:
                        payload = json.loads(raw)
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        findings.append("Error response body is not valid JSON.")
            except (OSError, TimeoutError, urllib.error.URLError) as exc:
                findings.append(f"Request failed: {exc}")
            if actual_status is not None and str(actual_status) != status:
                findings.append(f"Expected HTTP {status}, received {actual_status}.")
            content = response_spec.get("content", {}) if isinstance(response_spec, dict) else {}
            json_spec = content.get("application/json")
            if json_spec is not None:
                if "json" not in content_type.lower():
                    findings.append(f"Expected JSON content type, received {content_type or 'none'}.")
                if payload is not None:
                    findings.extend(_check_schema(payload, json_spec.get("schema", {}), document))
            results.append(CheckResult(method.upper(), path, "positive", status, actual_status, not findings, findings))
    if not results:
        raise ContractError("No supported GET or POST operations were found.")
    return results


def report(results: list[CheckResult]) -> dict[str, Any]:
    return {"summary": {"total": len(results), "passed": sum(r.passed for r in results), "failed": sum(not r.passed for r in results)}, "checks": [asdict(item) for item in results]}
