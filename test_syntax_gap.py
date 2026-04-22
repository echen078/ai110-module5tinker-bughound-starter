from bughound_agent import BugHoundAgent
from reliability.risk_assessor import assess_risk

print("=" * 70)
print("TESTING: What if fix produces syntactically invalid Python?")
print("=" * 70)

# Simulate a broken fix from the agent
original_code = """def compute(x, y):
    return x / y"""

broken_fix = """import logging
def compute(x, y):
    logging.info("computing"
    return x / y"""  # Missing closing paren - syntax error!

issues = [{"type": "Code Quality", "severity": "Low", "msg": "no logging"}]

risk = assess_risk(
    original_code=original_code,
    fixed_code=broken_fix,
    issues=issues
)

print(f"Original code:\n{original_code}")
print(f"\nBroken fix:\n{broken_fix}")
print(f"\nRisk Score: {risk['score']}/100")
print(f"Risk Level: {risk['level']}")
print(f"Should Auto-fix: {risk['should_autofix']}")
print(f"Reasons: {risk['reasons']}")

print("\n--- PROBLEM ---")
if risk['should_autofix']:
    print("⚠ DANGEROUS: Invalid syntax fix would be auto-applied!")
    print("The code won't run. This is a serious reliability problem.")
else:
    print("✓ SAFE: Auto-fix is blocked (but risk assessor didn't catch the syntax error)")
    print("   It's blocked because score != 100, not because of syntax validation")

# Try to actually parse it to confirm it's invalid
import ast
try:
    ast.parse(broken_fix)
    print("\n✓ Code parses OK")
except SyntaxError as e:
    print(f"\n✗ SYNTAX ERROR: {e}")
    print(f"   This is NOT being caught by risk_assessor!")
