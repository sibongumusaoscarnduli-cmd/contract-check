# Testing

Run the suite from the project root:

```sh
python3 -m unittest discover -v
```

Tests validate nested schema checks and missing fields, exercise all three documented operations against the synthetic HTTP fixture on an ephemeral localhost port, confirm status codes and report totals, and verify that a public host is rejected before a request is sent. A malformed OpenAPI 2 document must fail closed.

To run the example by hand, follow the two-terminal commands in the repository README. For an intentionally failing response, edit the local fixture response temporarily, rerun the command, inspect the failed check, then restore the fixture. Do not point the runner at a service you do not own.
