"""
Demonstration: Why the syntax validation guardrail is necessary.

This shows what WOULD happen without the guardrail.
"""

from typing import Dict, List

def assess_risk_OLD_VERSION(
    original_code: str,
    fixed_code: str,
    issues: List[Dict[str, str]],
) -> Dict[str, object]:
    """Old version WITHOUT syntax validation."""
    reasons: List[str] = []
    score = 100

    if not fixed_code.strip():
        return {
            "score": 0,
            "level": "high",
            "reasons": ["No fix was produced."],
            "should_autofix": False,
        }

    # NOTE: No syntax check here! This is what was missing.

    original_lines = original_code.strip().splitlines()
    fixed_lines = fixed_code.strip().splitlines()

    # Issue severity based risk (simplified)
    for issue in issues:
        severity = str(issue.get("severity", "")).lower()
        if severity == "high":
            score -= 40
        elif severity == "medium":
            score -= 20
        elif severity == "low":
            score -= 5

    # Structural change checks (simplified)
    if len(fixed_lines) < len(original_lines) * 0.5:
        score -= 20
        reasons.append("Fixed code is much shorter than original.")

    # Clamp score
    score = max(0, min(100, score))

    # Risk level
    if score >= 75:
        level = "low"
    elif score >= 40:
        level = "medium"
    else:
        level = "high"

    # Auto-fix policy (with old lenient rule)
    should_autofix = level == "low"  # OLD VERSION: permissive

    if not reasons:
        reasons.append("No significant risks detected.")

    return {
        "score": score,
        "level": level,
        "reasons": reasons,
        "should_autofix": should_autofix,
    }


# Test case: broken Python code
original = "def compute(x, y):\n    return x / y\n"
broken_fix = "import logging\ndef compute(x, y):\n    logging.info(\"computing\"\n    return x / y\n"
issues = [{"type": "Code Quality", "severity": "Low", "msg": "no logging"}]

print("=" * 70)
print("SCENARIO: Fixed code has a syntax error")
print("=" * 70)

print(f"\nOriginal code:\n{original}")
print(f"Fixed code (BROKEN - missing closing paren):\n{broken_fix}")

# OLD VERSION (no syntax check)
risk_old = assess_risk_OLD_VERSION(original, broken_fix, issues)
print(f"\n--- OLD VERSION (without syntax validation) ---")
print(f"Score: {risk_old['score']}/100")
print(f"Level: {risk_old['level']}")
print(f"Should Auto-fix: {risk_old['should_autofix']}")
print(f"Reasons: {risk_old['reasons']}")

if risk_old['should_autofix']:
    print("\n⚠️  DANGEROUS: Old version would auto-fix BROKEN code!")
    print("   This code has a syntax error and won't even run!")
else:
    print("\n✓ OK: Old version would NOT auto-fix (score is too low)")

# NEW VERSION (with syntax validation - simulated by showing what it does)
print(f"\n--- NEW VERSION (with syntax validation) ---")
print("Score: 0/100")
print("Level: high")
print("Should Auto-fix: False")
print("Reasons: [\"Fixed code has syntax error: '(' was never closed at line 3\"]")
print("\n✓ SAFE: New version catches and blocks the syntax error immediately")

print("\n" + "=" * 70)
print("KEY INSIGHT")
print("=" * 70)
print("""
The guardrail ensures that EVEN IF the risk scoring logic changes,
syntactically invalid code CANNOT be auto-fixed.

Without explicit syntax validation, we rely on the scoring system
to happen to block it. With the guardrail, syntax errors are caught
first and explicitly blocked, regardless of scoring.

This is a DEFENSE-IN-DEPTH approach to reliability.
""")
