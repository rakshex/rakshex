"""Fail-closed contract event binding tests; no real repository scans."""
import copy
import pytest
from services.contract_analysis import analyze_contracts
from services.impact_event_provenance import ImpactEventRefused, bind_internal_impact_event

def candidate():
    before={"openapi":"3.0.3","paths":{"/v1/orders":{"post":{"responses":{"200":{"description":"ok"}}}}}}
    after={"openapi":"3.0.3","paths":{}}
    report=analyze_contracts(before,after)
    return dict(before=before,after=after,report=report,change=report["changes"][0],
                path="/v1/orders",workspace_id="workspace_1",
                repository="rakshex/rakshex",commit_sha="a"*40)

def test_bind_real_contract_pair_without_authorizing_scan():
    event=bind_internal_impact_event(**candidate())
    assert event["method"]=="POST"
    assert event["source_type"]=="internal_contract_analysis"
    assert event["authorization_status"]=="not_verified"
    assert event["scan_status"]=="not_started"
    assert event["before_hash"]!=event["after_hash"]

@pytest.mark.parametrize("field,value",[
    ("path","/v1/other"),("repository","../escape"),
    ("workspace_id","../../other"),("commit_sha","synthetic"),
    ("commit_sha","0"*39)])
def test_refuse_unverified_identity_or_fingerprint(field,value):
    c=candidate();c[field]=value
    with pytest.raises(ImpactEventRefused):
        bind_internal_impact_event(**c)

def test_refuse_forged_report_method_or_changed_contract():
    c=candidate();c["report"]=copy.deepcopy(c["report"]);c["report"]["before_hash"]="0"*64
    with pytest.raises(ImpactEventRefused):
        bind_internal_impact_event(**c)
    c=candidate();c["change"]=dict(c["change"],method="GET")
    with pytest.raises(ImpactEventRefused):
        bind_internal_impact_event(**c)
    c=candidate();c["after"]=copy.deepcopy(c["before"])
    with pytest.raises(ImpactEventRefused):
        bind_internal_impact_event(**c)
