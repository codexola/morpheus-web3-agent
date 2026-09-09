"""Deterministic Solidity vulnerability pattern detection."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.models.response import Finding


@dataclass(frozen=True)
class PatternRule:
    id: str
    title: str
    severity: str
    confidence: float
    regex: re.Pattern[str]
    description: str
    impact: str
    recommendation: str
    requires: re.Pattern[str] | None = None
    exclude: re.Pattern[str] | None = None


RULES: list[PatternRule] = [
    PatternRule(
        id="SC-REENTRANCY",
        title="Potential reentrancy",
        severity="high",
        confidence=0.82,
        regex=re.compile(
            r"\.call\{[^}]*value\s*:|\.call\.value\s*\(|\.transfer\s*\(|\.send\s*\(",
            re.I,
        ),
        requires=re.compile(r"function\s+\w+[^{]*\{[^}]*\}", re.I | re.S),
        description="External value transfer detected. Without checks-effects-interactions or a reentrancy guard, state may be manipulated mid-call.",
        impact="Attacker may recursively drain funds or corrupt accounting.",
        recommendation="Apply checks-effects-interactions, use ReentrancyGuard, and prefer pull-over-push payments.",
    ),
    PatternRule(
        id="SC-TX-ORIGIN",
        title="tx.origin authentication",
        severity="high",
        confidence=0.95,
        regex=re.compile(r"\btx\.origin\b"),
        description="Authorization uses tx.origin, which is vulnerable to phishing via intermediate contracts.",
        impact="Attacker-controlled contract can trick a victim into authenticating unintended actions.",
        recommendation="Use msg.sender for authorization checks.",
    ),
    PatternRule(
        id="SC-DELEGATECALL",
        title="Unsafe delegatecall usage",
        severity="high",
        confidence=0.78,
        regex=re.compile(r"\.delegatecall\s*\("),
        description="delegatecall executes callee code in the caller storage context.",
        impact="Malicious or incorrect target can overwrite critical storage and seize control.",
        recommendation="Restrict delegatecall targets, validate implementation addresses, and review proxy upgrade paths.",
    ),
    PatternRule(
        id="SC-SELFDESTRUCT",
        title="selfdestruct / obsolete suicide",
        severity="medium",
        confidence=0.9,
        regex=re.compile(r"\b(selfdestruct|suicide)\s*\("),
        description="Contract can be destroyed, potentially disrupting dependent integrations.",
        impact="Funds redirection and permanent loss of contract logic.",
        recommendation="Avoid selfdestruct unless strictly required; gate behind multi-sig and timelock.",
    ),
    PatternRule(
        id="SC-UNCHECKED-CALL",
        title="Unchecked low-level call return value",
        severity="medium",
        confidence=0.75,
        regex=re.compile(r"\.call\s*(\{[^}]*\})?\s*\([^;]*\);"),
        exclude=re.compile(r"\((?:bool|success|ok)[^)]*\)\s*=\s*[^\n]*\.call|\brequire\s*\(\s*(success|ok)"),
        description="Low-level call return value may be ignored.",
        impact="Failed calls can be treated as success, causing inconsistent state.",
        recommendation="Check return values and handle failures explicitly.",
    ),
    PatternRule(
        id="SC-TIMESTAMP",
        title="Block timestamp dependency",
        severity="low",
        confidence=0.7,
        regex=re.compile(r"\b(block\.timestamp|now)\b"),
        description="Logic depends on block.timestamp, which miners/validators can nudge slightly.",
        impact="Time-sensitive logic (lotteries, unlocks) may be biased.",
        recommendation="Avoid critical randomness from timestamps; use broader time windows where possible.",
    ),
    PatternRule(
        id="SC-INLINE-ASSEMBLY",
        title="Inline assembly present",
        severity="informational",
        confidence=0.85,
        regex=re.compile(r"\bassembly\s*\{"),
        description="Inline assembly bypasses Solidity safety checks.",
        impact="Increased risk of memory/storage mistakes.",
        recommendation="Minimize assembly and document invariants carefully.",
    ),
    PatternRule(
        id="SC-OWNER-TRANSFER",
        title="Unprotected ownership pattern",
        severity="medium",
        confidence=0.65,
        regex=re.compile(r"function\s+(transferOwnership|setOwner|changeOwner)\s*\(", re.I),
        exclude=re.compile(r"onlyOwner|onlyRole|require\s*\(\s*msg\.sender", re.I),
        description="Ownership transfer function may lack an access modifier in the matched snippet.",
        impact="Unauthorized ownership takeover.",
        recommendation="Protect owner-changing functions with onlyOwner / AccessControl and consider 2-step ownership.",
    ),
    PatternRule(
        id="SC-FLOATING-PRAGMA",
        title="Floating Solidity pragma",
        severity="low",
        confidence=0.9,
        regex=re.compile(r"pragma\s+solidity\s+\^"),
        description="Floating pragma allows compilation with unexpected compiler versions.",
        impact="Builds may differ from audited artifacts.",
        recommendation="Pin an exact compiler version for production contracts.",
    ),
]


def line_of(source: str, index: int) -> int:
    return source.count("\n", 0, index) + 1


def analyze_solidity(source: str, filename: str = "Contract.sol") -> list[Finding]:
    findings: list[Finding] = []
    seen: set[str] = set()
    for rule in RULES:
        for match in rule.regex.finditer(source):
            if rule.exclude and rule.exclude.search(source[max(0, match.start() - 120) : match.end() + 120]):
                continue
            key = f"{rule.id}:{line_of(source, match.start())}"
            if key in seen:
                continue
            seen.add(key)
            findings.append(
                Finding(
                    id=f"{rule.id}-{len(seen):03d}",
                    title=rule.title,
                    severity=rule.severity,  # type: ignore[arg-type]
                    confidence=rule.confidence,
                    location=f"{filename}:{line_of(source, match.start())}",
                    description=rule.description,
                    impact=rule.impact,
                    recommendation=rule.recommendation,
                    category="solidity-pattern",
                )
            )
    return findings


SECRET_PATTERNS = [
    (
        "SEC-AWS-KEY",
        "Possible AWS access key",
        "high",
        re.compile(r"AKIA[0-9A-Z]{16}"),
        "Hard-coded cloud credential detected.",
    ),
    (
        "SEC-PRIVATE-KEY",
        "Possible private key material",
        "critical",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        "Embedded private key material.",
    ),
    (
        "SEC-GENERIC-SECRET",
        "Hard-coded secret assignment",
        "high",
        re.compile(
            r"""(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][^'\"]{8,}['\"]"""
        ),
        "Possible hard-coded secret in source.",
    ),
]


CODE_RULES = [
    (
        "SEC-SQL-INJECTION",
        "Possible SQL injection sink",
        "high",
        0.7,
        re.compile(r"""(?i)(execute|cursor\.execute|query)\s*\(\s*(f['\"]|['\"].*\%|['\"].*\+)"""),
        "String-built SQL may allow injection.",
        "Use parameterized queries.",
    ),
    (
        "SEC-COMMAND-INJECTION",
        "Possible command injection",
        "high",
        0.75,
        re.compile(r"""(?i)(os\.system|subprocess\.(call|run|Popen)|child_process\.exec)\s*\("""),
        "Command execution sink detected.",
        "Avoid shell=True; sanitize/allowlist inputs.",
    ),
    (
        "SEC-EVAL",
        "Dynamic code evaluation",
        "high",
        0.85,
        re.compile(r"""(?i)\b(eval|Function)\s*\("""),
        "Dynamic evaluation can execute attacker-controlled code.",
        "Remove eval/Function or strictly constrain inputs.",
    ),
    (
        "SEC-PATH-TRAVERSAL",
        "Possible path traversal",
        "medium",
        0.65,
        re.compile(r"""(?i)(open|readFile|createReadStream)\s*\([^\)]*\+|path\.join\([^\)]*req\."""),
        "User-influenced filesystem path construction.",
        "Canonicalize paths and enforce a root directory allowlist.",
    ),
    (
        "SEC-XSS",
        "Possible XSS sink",
        "medium",
        0.65,
        re.compile(r"""(?i)(innerHTML|dangerouslySetInnerHTML|document\.write)\s*="""),
        "Untrusted HTML injection sink.",
        "Use safe templating and output encoding.",
    ),
]


def analyze_general_code(source: str, filename: str = "source") -> list[Finding]:
    findings: list[Finding] = []
    idx = 0
    for sid, title, severity, conf, regex, desc, rec in CODE_RULES:
        for match in regex.finditer(source):
            idx += 1
            findings.append(
                Finding(
                    id=f"{sid}-{idx:03d}",
                    title=title,
                    severity=severity,  # type: ignore[arg-type]
                    confidence=conf,
                    location=f"{filename}:{line_of(source, match.start())}",
                    description=desc,
                    impact="Security control bypass or code/data compromise depending on reachability.",
                    recommendation=rec,
                    category="code-pattern",
                )
            )
    for sid, title, severity, regex, desc in SECRET_PATTERNS:
        for match in regex.finditer(source):
            idx += 1
            findings.append(
                Finding(
                    id=f"{sid}-{idx:03d}",
                    title=title,
                    severity=severity,  # type: ignore[arg-type]
                    confidence=0.9,
                    location=f"{filename}:{line_of(source, match.start())}",
                    description=desc,
                    impact="Credential leakage can lead to unauthorized access.",
                    recommendation="Remove secrets from source; rotate exposed credentials; use a secret manager.",
                    category="secrets",
                )
            )
    return findings
