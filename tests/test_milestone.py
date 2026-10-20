import hashlib
import json
from pathlib import Path
import re
import pytest

CONTRACT = str(Path(__file__).parents[1] / "milestone_remedy.py")
SUPPLIER = "0x" + "11"*20
STRANGER = "0x" + "22"*20
URL_A = "https://raw.githubusercontent.com/vendor/release/" + "a"*40 + "/report.txt"
URL_B = "https://raw.githubusercontent.com/client/review/" + "b"*40 + "/review.txt"
URL_C = "https://raw.githubusercontent.com/auditor/findings/" + "c"*40 + "/appeal.txt"
DOC_A = "The milestone delivered every requested function and public documentation."
DOC_B = "The client reproduced the public documentation example successfully."
DOC_C = "The appeal found one missing function in the agreed milestone."
SHA_A = hashlib.sha256(DOC_A.encode()).hexdigest()
SHA_B = hashlib.sha256(DOC_B.encode()).hexdigest()
SHA_C = hashlib.sha256(DOC_C.encode()).hexdigest()
FULL = {"outcome":"FULL","reason_code":"CONFORMING","citations":[{"source":0,"quote":DOC_A}]}
HALF = {"outcome":"HALF","reason_code":"PARTIAL_DELIVERY","citations":[{"source":2,"quote":DOC_C}]}

def deploy(direct_vm,direct_deploy):
    direct_vm.warp("2026-10-21T00:00:00Z")
    return direct_deploy(CONTRACT)

def offer(c):
    return c.offer(SUPPLIER,"Deliver the requested SDK example and public documentation.",100,60,120,180,60)

def serve(direct_vm, url, body, status=200):
    direct_vm.mock_web(re.escape(url),{"status":status,"body":body})

def accepted(direct_vm,c):
    cid=offer(c)
    from genlayer import Address
    with direct_vm.prank(Address(SUPPLIER)):
        c.accept(cid)
    return cid


@pytest.mark.parametrize('repo',['.','..'])
def test_dot_repository_cannot_change_the_commit_namespace(direct_vm,direct_deploy,repo):
    c=deploy(direct_vm,direct_deploy)
    cid=accepted(direct_vm,c)
    url='https://raw.githubusercontent.com/example/'+repo+'/'+'a'*40+'/main/evidence.txt'
    serve(direct_vm,url,DOC_A)
    with direct_vm.expect_revert('noncanonical'):
        c.submit_evidence(cid,url,SHA_A)

def disputed(direct_vm,c):
    cid=accepted(direct_vm,c)
    serve(direct_vm,URL_A,DOC_A)
    serve(direct_vm,URL_B,DOC_B)
    from genlayer import Address
    with direct_vm.prank(Address(SUPPLIER)):
        c.submit_evidence(cid,URL_A,SHA_A)
    c.submit_evidence(cid,URL_B,SHA_B)
    direct_vm.warp("2026-10-21T00:02:00Z")
    c.dispute(cid,"The parties disagree about delivery completeness.")
    return cid

def adjudicated(direct_vm,c):
    cid=disputed(direct_vm,c)
    direct_vm.warp("2026-10-21T00:03:00Z")
    direct_vm.mock_llm("MILESTONE_REMEDY_V1",json.dumps(FULL))
    c.adjudicate(cid)
    return cid

def test_consensus_ruling_and_deterministic_split(direct_vm,direct_deploy):
    """Catches absent source consensus, arbitrary split or missing final state."""
    c=deploy(direct_vm,direct_deploy)
    cid=adjudicated(direct_vm,c)
    assert direct_vm.run_validator() is True
    out=c.get_case(cid)
    assert out["status"]=="PROVISIONAL"
    assert out["terms_sha256"]==hashlib.sha256(b"Deliver the requested SDK example and public documentation.").hexdigest()
    assert out["evidence"][0]["sha256"]==SHA_A
    assert out["evidence"][0]["registered_at"]==1792540800
    with direct_vm.expect_revert("appeal window"):
        c.finalize(cid)
    direct_vm.warp("2026-10-21T00:04:00Z")
    c.finalize(cid)
    result=c.get_case(cid)
    assert result["status"]=="FINAL"
    assert (result["supplier_bp"],result["client_bp"])==(10000,0)
    assert c.get_remedy(cid)["amount_units"]==100
    with direct_vm.expect_revert("terminal"):
        c.finalize(cid)

def test_validator_refetches_source_bytes(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy)
    cid=adjudicated(direct_vm,c)
    direct_vm.clear_mocks()
    serve(direct_vm,URL_A,"Altered evidence after the agreed capture.")
    serve(direct_vm,URL_B,DOC_B)
    direct_vm.mock_llm("MILESTONE_REMEDY_V1",json.dumps(FULL))
    assert direct_vm.run_validator() is False

def test_validator_rejects_forged_outcome_and_derived_split(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy)
    cid=adjudicated(direct_vm,c)
    forged=dict(FULL,digests=[SHA_A,SHA_B],supplier_bp=999999)
    assert direct_vm.run_validator(leader_result=forged) is False
    forged={"outcome":"NONE","reason_code":"NONCONFORMING","digests":[SHA_A,SHA_B],"citations":[{"source":0,"quote":DOC_A}]}
    assert direct_vm.run_validator(leader_result=forged) is False
    forged=dict(FULL,digests=[SHA_A,SHA_B],citations=[{"source":0,"quote":"This quotation does not appear in the registered evidence."}])
    assert direct_vm.run_validator(leader_result=forged) is False

def test_only_named_supplier_accepts_and_party_authority(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy)
    cid=offer(c)
    with direct_vm.expect_revert("supplier only"):
        c.accept(cid)
    from genlayer import Address
    with direct_vm.prank(Address(SUPPLIER)):
        c.accept(cid)
        with direct_vm.expect_revert("not offered"):
            c.accept(cid)
    with direct_vm.prank(Address(STRANGER)):
        with direct_vm.expect_revert("party only"):
            c.submit_evidence(cid,URL_A,SHA_A)
        direct_vm.warp("2026-10-21T00:02:00Z")
        with direct_vm.expect_revert("party only"):
            c.dispute(cid,"Unrelated account cannot start the dispute.")

def test_offer_acceptance_expiry_boundary(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy)
    cid=offer(c)
    direct_vm.warp("2026-10-21T00:01:00Z")
    from genlayer import Address
    with direct_vm.prank(Address(SUPPLIER)):
        with direct_vm.expect_revert("acceptance closed"):
            c.accept(cid)
    c.expire_offer(cid)
    assert c.get_case(cid)["status"]=="EXPIRED"

def test_evidence_and_dispute_time_boundaries(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy)
    cid=accepted(direct_vm,c)
    with direct_vm.expect_revert("dispute window"):
        c.dispute(cid,"Too early to claim missed delivery.")
    direct_vm.warp("2026-10-21T00:02:00Z")
    from genlayer import Address
    with direct_vm.prank(Address(SUPPLIER)):
        with direct_vm.expect_revert("evidence closed"):
            c.submit_evidence(cid,URL_A,SHA_A)
    c.dispute(cid,"The delivery deadline has now passed.")
    with direct_vm.expect_revert("evidence window"):
        c.adjudicate(cid)
    direct_vm.warp("2026-10-21T00:03:00Z")
    with direct_vm.expect_revert("evidence closed"):
        c.submit_evidence(cid,URL_B,SHA_B)

@pytest.mark.parametrize("url",["https://raw.githubusercontent.com/vendor/release/main/report.txt","http://raw.githubusercontent.com/vendor/release/"+"a"*40+"/x","https://127.0.0.1/x","https://raw.githubusercontent.com.evil.com/vendor/release/"+"a"*40+"/x",URL_A+"?x=1"])
def test_only_commit_pinned_public_sources(direct_vm,direct_deploy,url):
    c=deploy(direct_vm,direct_deploy)
    cid=accepted(direct_vm,c)
    with direct_vm.expect_revert("source"):
        c.submit_evidence(cid,url,SHA_A)

@pytest.mark.parametrize("body,status",[(DOC_A,404),("x"*16001,200),("Changed source bytes do not match expected hash.",200)])
def test_registration_requires_real_bytes_and_hash(direct_vm,direct_deploy,body,status):
    c=deploy(direct_vm,direct_deploy)
    cid=accepted(direct_vm,c)
    serve(direct_vm,URL_A,body,status)
    with direct_vm.expect_revert():
        c.submit_evidence(cid,URL_A,SHA_A)
    assert c.get_case(cid)["evidence"]==[]

@pytest.mark.parametrize("result",[{"outcome":"FULL","reason_code":"CONFORMING","supplier_bp":10000},{"outcome":"FULL","reason_code":"CONFORMING","citations":[{"source":0,"quote":"Invented unsupported statement with enough characters."}]},{"outcome":"HALF","reason_code":"CONFORMING","citations":[{"source":0,"quote":DOC_A}]}])
def test_model_injection_or_bad_citation_cannot_settle(direct_vm,direct_deploy,result):
    c=deploy(direct_vm,direct_deploy)
    cid=disputed(direct_vm,c)
    direct_vm.warp("2026-10-21T00:03:00Z")
    direct_vm.mock_llm("MILESTONE_REMEDY_V1",json.dumps(result))
    with direct_vm.expect_revert("invalid ruling"):
        c.adjudicate(cid)
    assert c.get_case(cid)["status"]=="DISPUTED"

def test_uncertain_finalizes_without_default_allocation(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy)
    cid=disputed(direct_vm,c)
    direct_vm.warp("2026-10-21T00:03:00Z")
    direct_vm.mock_llm("MILESTONE_REMEDY_V1",json.dumps({"outcome":"UNCERTAIN","reason_code":"INSUFFICIENT_EVIDENCE","citations":[]}))
    c.adjudicate(cid)
    direct_vm.warp("2026-10-21T00:04:00Z")
    c.finalize(cid)
    assert c.get_case(cid)["status"]=="UNRESOLVED"
    assert c.get_remedy(cid)["supplier_bp"] is None
    assert c.get_remedy(cid)["client_bp"] is None

def test_appeal_adds_new_consensus_receipt_and_reassesses(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy)
    cid=adjudicated(direct_vm,c)
    serve(direct_vm,URL_C,DOC_C)
    c.appeal(cid,"A new public review documents a missing function.",URL_C,SHA_C)
    assert c.get_case(cid)["status"]=="APPEALED"
    direct_vm.warp("2026-10-21T00:04:00Z")
    with direct_vm.expect_revert("unresolved appeal"):
        c.finalize(cid)
    direct_vm.clear_mocks()
    for url,body in [(URL_A,DOC_A),(URL_B,DOC_B),(URL_C,DOC_C)]:
        serve(direct_vm,url,body)
    direct_vm.mock_llm("MILESTONE_REMEDY_V1",json.dumps(HALF))
    c.review_appeal(cid)
    assert direct_vm.run_validator() is True
    c.finalize(cid)
    assert (c.get_remedy(cid)["supplier_bp"],c.get_remedy(cid)["client_bp"])==(5000,5000)

def test_appeal_single_use_access_and_deadline(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy)
    cid=adjudicated(direct_vm,c)
    from genlayer import Address
    with direct_vm.prank(Address(STRANGER)):
        with direct_vm.expect_revert("party only"):
            c.appeal(cid,"A stranger cannot appeal.",URL_C,SHA_C)
    serve(direct_vm,URL_C,DOC_C)
    c.appeal(cid,"The first party appeal includes new public evidence.",URL_C,SHA_C)
    with direct_vm.expect_revert("appeal unavailable"):
        c.appeal(cid,"An appeal cannot be repeated.",URL_C,SHA_C)

def test_unfinalized_remedy_is_not_consumable(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy)
    cid=adjudicated(direct_vm,c)
    with direct_vm.expect_revert("not final"):
        c.get_remedy(cid)
