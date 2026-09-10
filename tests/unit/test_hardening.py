"""Additional unit tests for hardened behavior."""

from app.core.config import Settings
from app.core.security import assert_safe_url, is_evm_address
from app.blockchain.ethereum import normalize_evm_chain
from app.models.response import Finding
from app.security.merge import merge_findings
from app.security.patterns import analyze_solidity
import pytest


def test_blank_rpc_env_keeps_default():
    s = Settings(eth_rpc_url="")
    assert s.eth_rpc_url.startswith("https://")
    s2 = Settings(ETH_RPC_URL="")  # type: ignore[call-arg]
    assert s2.eth_rpc_url.startswith("https://")


def test_unsupported_chain_rejected():
    with pytest.raises(Exception):
        normalize_evm_chain("optimism")


def test_supported_chain_aliases():
    assert normalize_evm_chain("eth") == "ethereum"
    assert normalize_evm_chain("matic") == "polygon"


def test_merge_keeps_static_findings():
    static = [
        Finding(
            id="S1",
            title="Potential reentrancy",
            severity="high",
            confidence=0.8,
            location="A.sol:1",
            description="static",
        )
    ]
    llm = [
        Finding(
            id="L1",
            title="Potential reentrancy",
            severity="high",
            confidence=0.9,
            location="A.sol:1",
            description="enriched",
            recommendation="fix it",
        )
    ]
    merged = merge_findings(static, llm)
    assert len(merged) == 1
    assert merged[0].description == "enriched"
    assert merged[0].id == "S1"


def test_reentrancy_still_detected():
    src = open("tests/fixtures/vulnerable_vault.sol", encoding="utf-8").read()
    findings = analyze_solidity(src)
    assert any(f.title == "Potential reentrancy" for f in findings)


def test_is_evm_address():
    assert is_evm_address("0x" + "a" * 40)
    assert not is_evm_address("0x123")


def test_ssrf_blocks_literal_metadata():
    with pytest.raises(Exception):
        assert_safe_url("http://169.254.169.254/latest/meta-data", resolve_dns=False)
