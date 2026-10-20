# MilestoneRemedy design / test plan

AI-assisted independent IC prototype, 2026-10-21. No assets are held or transferred.

Two counterparties agree to immutable milestone terms, abstract amount and accept/delivery/evidence deadlines. Supplier accepts the client's offer. Each party may register <=2 public evidence URLs before its deadline; URLs must pin a GitHub/gist commit and a SHA-256 digest. Registration independently fetches and verifies the exact bytes through consensus, storing a bounded receipt with caller and capture time. The supplier's evidence must be registered before the delivery deadline; the client's may continue until evidence close.

After delivery cutoff either party may dispute, before evidence close. After evidence close anyone may adjudicate: leader and validators independently re-fetch every registered source, verify the locked digests, judge the original terms plus claims and source text, validate exact quoted evidence, then compare outcome/reason/digests. Source-provided instructions are untrusted. FULL/HALF/NONE map deterministically to supplier 10000/5000/0 basis points; UNCERTAIN yields no allocation. A leader cannot submit arbitrary payout percentages.

The first ruling is provisional for a fixed appeal window. One party may register one new commit-pinned source and appeal; registration again uses source consensus. A fresh independent judgment uses all original and new evidence. Unresolved appeals block finalization; UNCERTAIN finalizes as UNRESOLVED with null allocations. Final determinate allocations sum to 10000. This is a coordination record for a separate consuming system, never legal arbitration or proof code actually ran.

TDD executes the deployable artifact with the official exact runner SDK. Cover bilateral caller authority; deadline boundaries; no URL/digest tampering; receipt source/time; bad HTTP/body/hash; changed validator bytes; model/citation forgery; forged derived allocation fields; deterministic total split; appeal and repeated-finalization guards; uncertainty. External web/model fixtures are explicit mocks, not fake deployment evidence.
