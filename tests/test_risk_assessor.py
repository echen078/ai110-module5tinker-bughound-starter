from reliability.risk_assessor import assess_risk


def test_no_fix_is_high_risk():
    risk = assess_risk(
        original_code="print('hi')\n",
        fixed_code="",
        issues=[{"type": "Code Quality", "severity": "Low", "msg": "print"}],
    )
    assert risk["level"] == "high"
    assert risk["should_autofix"] is False
    assert risk["score"] == 0


def test_low_risk_when_minimal_change_and_low_severity():
    original = "import logging\n\ndef add(a, b):\n    return a + b\n"
    fixed = "import logging\n\ndef add(a, b):\n    return a + b\n"
    risk = assess_risk(
        original_code=original,
        fixed_code=fixed,
        issues=[{"type": "Code Quality", "severity": "Low", "msg": "minor"}],
    )
    assert risk["level"] in ("low", "medium")  # depends on scoring rules
    assert 0 <= risk["score"] <= 100


def test_high_severity_issue_drives_score_down():
    original = "def f():\n    try:\n        return 1\n    except:\n        return 0\n"
    fixed = "def f():\n    try:\n        return 1\n    except Exception as e:\n        return 0\n"
    risk = assess_risk(
        original_code=original,
        fixed_code=fixed,
        issues=[{"type": "Reliability", "severity": "High", "msg": "bare except"}],
    )
    assert risk["score"] <= 60
    assert risk["level"] in ("medium", "high")


def test_missing_return_is_penalized():
    original = "def f(x):\n    return x + 1\n"
    fixed = "def f(x):\n    x + 1\n"
    risk = assess_risk(
        original_code=original,
        fixed_code=fixed,
        issues=[],
    )
    assert risk["score"] < 100
    assert any("Return" in r or "return" in r for r in risk["reasons"])


def test_syntax_error_in_fixed_code_blocks_autofix():
    """Guardrail: Fixed code with syntax errors must never auto-fix."""
    original = "def compute(x, y):\n    return x / y\n"
    # Missing closing paren - syntax error!
    fixed_with_syntax_error = "import logging\ndef compute(x, y):\n    logging.info(\"computing\"\n    return x / y\n"
    
    risk = assess_risk(
        original_code=original,
        fixed_code=fixed_with_syntax_error,
        issues=[{"type": "Code Quality", "severity": "Low", "msg": "no logging"}],
    )
    
    assert risk["score"] == 0, "Syntax error should result in score 0"
    assert risk["level"] == "high", "Syntax error should be high risk"
    assert risk["should_autofix"] is False, "Never auto-fix code with syntax errors"
    assert any("syntax error" in r.lower() for r in risk["reasons"]), "Should mention syntax error in reasons"
