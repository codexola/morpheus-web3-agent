# API

## GET /

Service identity and endpoint index.

## GET /health

```json
{"status":"healthy","version":"1.0.0","state":"RUNNING"}
```

## GET /morpheus/verify

```json
{
  "status": "ok",
  "agent": {"name":"Web3Dev AI","version":"1.0.0","online":true},
  "capabilities": [
    "smart_contract_audit",
    "code_security_review",
    "blockchain_analytics",
    "web3_research"
  ]
}
```

## GET /capabilities

Human-readable capability catalog.

## POST /api/tasks

```json
{
  "task_id": "task_123",
  "capability": "smart_contract_audit",
  "description": "Audit this Solidity contract.",
  "input": {"source_code": "pragma solidity ^0.8.0; ...", "chain": "ethereum"}
}
```

Response includes `task_id`, `status`, and `result` when complete.

Versioned alias: `POST /api/v1/tasks`.

## GET /api/tasks/{task_id}

Poll by internal or external task id.

## POST /callbacks/morpheus

Optional inbound callback receiver. Protected by `X-Callback-Secret` when configured.

## GET /version

Deployment diagnostics (`version`, `commit`, `environment`).

## Errors

```json
{
  "success": false,
  "error": {"code":"INVALID_CONTRACT","message":"...","retryable":false}
}
```
