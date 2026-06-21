# Contract Target Model

Primary unit:

```text
ContractTarget(chain, address)
```

Required fields:

- `chain`
- `address`
- `target_id`

Optional enrichment:

- `abi`
- `source_bundle`
- `compiler`
- `bytecode_hash`
- `proxy_context`
- `creation_tx`
- `balances`
- `token_holdings`
- `event_windows`
- `storage_readers`
- `compile_context`

ContractTarget is not the same as a repository. A repository can contain many
contracts and deployment scripts. ContractTarget is the deployed object we can
prove against.
