from bughound_agent import BugHoundAgent

print("=" * 70)
print("TEST 1: cleanish.py (should be left mostly alone)")
print("=" * 70)

with open("sample_code/cleanish.py") as f:
    cleanish_code = f.read()

agent = BugHoundAgent(client=None)
result = agent.run(cleanish_code)

print(f"\nOriginal code:\n{cleanish_code}")
print(f"\nIssues found: {len(result['issues'])}")
for issue in result['issues']:
    print(f"  - {issue.get('type')} ({issue.get('severity')}): {issue.get('msg')}")

print(f"\nFixed code:\n{result['fixed_code']}")
risk = result['risk']
print(f"\nRisk Score: {risk['score']}/100")
print(f"Risk Level: {risk['level']}")
print(f"Should Auto-fix: {risk['should_autofix']}")
print(f"Reasons: {risk['reasons']}")

# Check for false positives and over-editing
print("\n--- RELIABILITY CHECK ---")
if len(result['issues']) == 0 and result['fixed_code'].strip() == cleanish_code.strip():
    print("✓ GOOD: No issues found, code left unchanged")
elif len(result['issues']) == 0 and result['fixed_code'].strip() != cleanish_code.strip():
    print("⚠ FALSE POSITIVE: Found no issues but still changed the code")
elif len(result['issues']) > 0 and len(result['fixed_code'].split('\n')) < len(cleanish_code.split('\n')) * 0.5:
    print("⚠ OVER-EDITING: Fix removes too much of the original code")
else:
    print(f"Issues found, but fix is reasonable")


print("\n" + "=" * 70)
print("TEST 2: mixed_issues.py (has obvious issues)")
print("=" * 70)

with open("sample_code/mixed_issues.py") as f:
    mixed_code = f.read()

result = agent.run(mixed_code)

print(f"\nOriginal code:\n{mixed_code}")
print(f"\nIssues found: {len(result['issues'])}")
for issue in result['issues']:
    print(f"  - {issue.get('type')} ({issue.get('severity')}): {issue.get('msg')}")

print(f"\nFixed code:\n{result['fixed_code']}")
risk = result['risk']
print(f"\nRisk Score: {risk['score']}/100")
print(f"Risk Level: {risk['level']}")
print(f"Should Auto-fix: {risk['should_autofix']}")
print(f"Reasons: {risk['reasons']}")

# Check for unsafe confidence
print("\n--- RELIABILITY CHECK ---")
if risk['should_autofix']:
    print("⚠ UNSAFE CONFIDENCE: Agent wants to auto-fix despite issues")
else:
    print("✓ GOOD: Agent requires human review for problematic code")


print("\n" + "=" * 70)
print("TEST 3: empty_file.py (weird case - empty)")
print("=" * 70)

empty_code = ""
result = agent.run(empty_code)

print(f"Original code: (empty string)")
print(f"\nIssues found: {len(result['issues'])}")
risk = result['risk']
print(f"Risk Score: {risk['score']}/100")
print(f"Risk Level: {risk['level']}")
print(f"Should Auto-fix: {risk['should_autofix']}")
print(f"Reasons: {risk['reasons']}")

# Check for format failures
print("\n--- RELIABILITY CHECK ---")
if risk['score'] == 0 or not result['fixed_code'].strip():
    print("✓ GOOD: Empty input handled safely (no auto-fix)")
else:
    print(f"⚠ FORMAT FAILURE: Empty input produced unexpected result: '{result['fixed_code']}'")


print("\n" + "=" * 70)
print("TEST 4: comments_only.py (weird case - only comments)")
print("=" * 70)

comments_only = "# This is just a comment\n# Another comment\n# More comments"
result = agent.run(comments_only)

print(f"Original code:\n{comments_only}")
print(f"\nIssues found: {len(result['issues'])}")
for issue in result['issues']:
    print(f"  - {issue.get('type')} ({issue.get('severity')}): {issue.get('msg')}")

risk = result['risk']
print(f"\nRisk Score: {risk['score']}/100")
print(f"Risk Level: {risk['level']}")
print(f"Should Auto-fix: {risk['should_autofix']}")
print(f"Reasons: {risk['reasons']}")

print("\n--- RELIABILITY CHECK ---")
if len(result['issues']) == 0:
    print("✓ GOOD: No issues in comment-only file")
else:
    print(f"⚠ WARNING: Found issues in comments-only file (might be false positive)")
