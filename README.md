# MilestoneRemedy

AI-assisted, unaudited prototype: a standalone GenLayer Intelligent Contract for a two-party software/documentation milestone dispute. It produces an independently assessed remedy record for another system to consume. Amounts are abstract integer units; this contract holds no assets and sends no transfers.

This is an independent IC contribution. Its bilateral agreement, evidence receipts, provisional remedy, one appeal and deterministic basis-point allocation form a different protocol from the profile02 proof and governance ICs. Only SDK/time/transport/testing primitives are reused.

## Why consensus changes the outcome

The client fixes terms, amount and deadlines; the named supplier must accept. Both parties register public, commit-pinned source URLs plus exact SHA-256 byte digests. Registration uses independent validator fetches before it records a party/timestamp receipt. At adjudication and appeal review, every validator fetches **all sources again**, verifies the locked digests, and independently assesses conformance under the original terms. It also checks the leader's exact quoted evidence against its own source bytes.

The model returns only FULL/CONFORMING, HALF/PARTIAL_DELIVERY, NONE/NONCONFORMING, or UNCERTAIN with INSUFFICIENT_EVIDENCE/CONFLICTING_EVIDENCE. The custom validator compares the independently derived outcome, reason and source digests. Leader-submitted percentages or extra keys are rejected. Deterministic code maps the final outcome to supplier basis points 10000, 5000 or 0; client basis points are `10000-supplier_bp`. UNCERTAIN gives null allocations and UNRESOLVED. Parties accept this fixed protocol schedule; free-form terms do not override the schedule.

## Source and API

`milestone_remedy.py` is the only deployable file. It pins the official concrete GenVM runner `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`. Constructor has **no arguments** (`[]`). No wallet secret, model key or RPC credential is an input.

| Method | Effect |
|---|---|
| `offer(supplier,terms,amount_units,accept_seconds,delivery_seconds,evidence_seconds,appeal_seconds) -> id` | Caller becomes client; immutable context binds contract, chain, sequence, parties, terms/hash, amount and deadlines. Distinct nonzero supplier; terms <=4000 characters; amount 1..10^12. Relative deadlines satisfy 60 <= accept < delivery < evidence <=30 days, appeal 60..86400 seconds. |
| `accept(id)` | Named supplier only, once before acceptance cutoff. OFFERED -> ACTIVE. |
| `expire_offer(id)` | Anyone after unaccepted offer cutoff. OFFERED -> EXPIRED. |
| `submit_evidence(id,url,sha256)` | Party only; <=2 initial sources per party, no duplicate URL. Supplier before delivery cutoff, client before evidence cutoff. Source digest is independently fetched and confirmed before receipt. |
| `dispute(id,claim)` | Either party once in `[delivery_deadline,evidence_deadline)`; claim <=3000 characters. ACTIVE -> DISPUTED. |
| `adjudicate(id)` | Anyone after evidence cutoff; at least one registered source. Independent assessment -> PROVISIONAL; opens fixed appeal window. |
| `appeal(id,claim,url,sha256)` | Either party, once, before appeal cutoff. New commit-pinned public source is independently captured; -> APPEALED. |
| `review_appeal(id)` | Anyone triggers fresh independent assessment of original terms plus all evidence; -> REVIEWED. Prior leader verdict is not the assessment input. |
| `finalize(id)` | After appeal cutoff, with no unresolved appeal. -> FINAL or UNRESOLVED; never repeatable. |
| `get_case(id)` | Full audit record, evidence receipts, ruling history and deadlines. |
| `get_remedy(id)` | Final record including parties, exact terms hash, amount, split and finalization time. Rejects provisional reads. |

For a demo offer, use a real second participant's public address and relative durations such as `60,120,180,60`. The tests use deterministic addresses and fictional fixture URLs; these are not live deployment/source evidence.

## Evidence and time policy

Only these HTTPS shapes are accepted:

```text
https://raw.githubusercontent.com/<account>/<repo>/<40-lowercase-hex-commit>/<path>
https://gist.githubusercontent.com/<account>/<32-lowercase-hex-gist>/raw/<40-lowercase-hex-version>/<path>
```

URLs are <=512 characters with safe ASCII path segments, no credentials, port, query, fragment, dot segments or mutable branch names. A source body must be nonempty UTF-8, <=16000 bytes, HTTP 200, and match the registered 64-lowercase-hex SHA-256. Up to four initial sources plus one appeal source bound work. A source change, removal or transport error aborts the transaction and cannot silently replace evidence.

Receipts bind the registering party and transaction time. They prove the requested bytes were retrieved under consensus at registration; they do not prove when an author created a document, when work happened, or whether its claims are true. The prompt includes deadline and receipt metadata and is instructed to return UNCERTAIN when evidence cannot establish a material fact. Commit-pinned locators and hashes prevent later substitution, while GitHub availability and transport remain dependencies.

The pinned SDK exposes status/headers/body and provides no final-URL, redirect-policy or pre-download size control. The host and body checks apply to requested locators and received bytes. Runtime TLS/DNS, redirects followed internally, and bandwidth limits remain transport trust boundaries.

## Threat model and integration

Parties and public documents can lie, quote misleadingly or contain prompt injection. Inputs are serialized as untrusted data; instructions embedded in case text or sources cannot change the intended assessment protocol. Every validator independently re-fetches and re-evaluates substance and validates leader citations. This reduces single-leader trust; correlated model errors and prompt injection remain risks. Citation substring checks establish source membership, not logical entailment by themselves; independent assessment provides the substantive check.

Client/supplier identities are addresses, not verified people. A party can withhold evidence or consent. ACTIVE cases with no dispute filed during the dispute window do not automatically award FULL or settle; this prototype makes no uncontested settlement inference. APPEALED cases may be reviewed after their deadline, and an unresolved appeal can block finalization indefinitely. No timely-resolution guarantee or source-recovery mechanism is claimed. Only one appeal is available across both parties, so an early appeal consumes that option.

A consuming integration should bind case ID, chain/contract, parties, exact terms hash, amount and finalized state; handle network appeals/finality and deduplicate execution by case ID. It should define currency, rounding and enforcement separately. The result is a protocol coordination record and does not assert legal liability, actual code execution, or audited damages.

## Verification

Python 3.12+, with a dedicated environment:

```text
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe tools/verify.py
```

On Linux/macOS use `.venv/bin/python`. The verifier downloads the official GenVM v0.2.12 artifact containing the exact pinned runner, uses the actual SDK contract/storage code, runs direct tests, semantic lint and schema extraction, and records the source hash in `evidence/verification.json`.

`evidence/tdd-red.log` records the initial real NOT_IMPLEMENTED failure. The final suite has **23 passing tests** covering bilateral authority, deadline boundaries, source registration/digest verification, altered validator bytes, independent outcomes, quote/extra payout forgery, deterministic total splits, uncertainty, appeal and terminal guards. `evidence/verification-tests.log`, `verification-lint.log` and `verification-schema.log` contain the final checks. The first nested-helper reachability lint warnings were resolved by exposing explicit helper call paths; full final lint is clean.

External HTTP/model calls are explicit fixtures. Captured validator functions execute and independently consume changed fixtures. Test-only `tests/conftest.py` addresses upstream gltest 0.29.2 Windows open-stdin cleanup and its `warp()` metadata refresh omission; it does not substitute contract or consensus algorithms. The constructor is deployed on GenLayer Studio (chain 61999) with FINALIZED / SUCCESS, normal majority consensus, and on-chain source bytes matching the locally tested SHA-256. See `evidence/deployment.json`. The deployment used zero native value and displayed zero GEN network fee. Live evidence retrieval/model assessments, a full bilateral case and appeal, production performance and non-Studio gas costs remain unverified. No users, audit or production results are claimed.

Official references checked on 2026-10-21: [boilerplate](https://github.com/genlayerlabs/genlayer-project-boilerplate), [equivalence principle](https://docs.genlayer.com/developers/intelligent-contracts/equivalence-principle), [storage](https://docs.genlayer.com/developers/intelligent-contracts/features/storage), [transaction context](https://docs.genlayer.com/developers/intelligent-contracts/features/transaction-context), [direct API](https://github.com/genlayerlabs/genlayer-testing-suite/blob/main/docs/direct-runner.md), [exact SDK release](https://github.com/genlayerlabs/genvm/releases/tag/v0.2.12). Pinned SDK signatures were inspected before implementation.

MIT licensed; see `LICENSE`.

## Source namespace correction

The v2 source rejects dot-only repository segments across the complete pinned source URL. Two public-API regression cases and the complete SDK checks pass. Content byte SHA256 binding was never bypassed. The corrected constructor is FINALIZED/SUCCESS at `0x72Ea300bA70e4fCa01279aEfD7509A08D6d22f86` on Studio 61999, with exact on-chain source SHA256 `066e7d73cb10d45df23c6cff21c27ca094ac40b6d8fa1d4c44ba800dcb5ac6f0`, zero native value, normal full consensus and majority agreement. The prior deployment is preserved in `evidence/deployment-v1.json`; this is a replacement revision of the same work, not an additional contribution. Full live business flows remain unverified.
