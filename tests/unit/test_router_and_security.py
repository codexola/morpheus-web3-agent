"""Unit tests for router and validators."""

from app.agents.router import get_agent
from app.core.exceptions import UnsupportedCapabilityError
from app.core.security import assert_safe_url
from app.security.patterns import analyze_solidity
from app.security.solidity import validate_solidity_source
import pytest


def test_router_known_capabilities():
    assert get_agent("smart_contract_audit").capability == "smart_contract_audit"
    assert get_agent("web3_research").capability == "web3_research"


def test_router_unknown():
    with pytest.raises(UnsupportedCapabilityError):
        get_agent("moon_mining")


def test_ssrf_blocks_localhost():
    with pytest.raises(Exception):
        assert_safe_url("http://127.0.0.1/admin")
    with pytest.raises(Exception):
        assert_safe_url("http://169.254.169.254/latest/meta-data")


def test_ssrf_allows_https():
    assert assert_safe_url("https://example.com/docs") == "https://example.com/docs"


def test_reentrancy_detection():
    src = open("tests/fixtures/vulnerable_vault.sol", encoding="utf-8").read()
    findings = analyze_solidity(src)
    titles = {f.title for f in findings}
    assert "Potential reentrancy" in titles
    assert "tx.origin authentication" in titles


def test_validate_solidity():
    meta = validate_solidity_source("pragma solidity ^0.8.0; contract A {}")
    assert "A" in meta["contracts"]
