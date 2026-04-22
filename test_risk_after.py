from bughound_agent import BugHoundAgent

agent = BugHoundAgent(client=None)
code = '''def greet(name):
    print("Hello", name)
    print("Welcome!")
    return True'''

result = agent.run(code)

print('=== AFTER CHANGE ===')
print('Issues found:', len(result['issues']))
for issue in result['issues']:
    print(f"  - {issue.get('type')}: {issue.get('severity')}")

risk = result['risk']
print(f"Risk Score: {risk['score']}")
print(f"Risk Level: {risk['level']}")
print(f"Should Auto-fix: {risk['should_autofix']}")
print(f"Risk Reasons: {risk['reasons']}")

print("\n=== COMPARISON ===")
print("Before: Should Auto-fix = True  (score=95, level=low)")
print("After:  Should Auto-fix = {}  (score={}, level={})".format(
    risk['should_autofix'], risk['score'], risk['level']))
print("\nImpact: Auto-fix is now DISABLED even though risk level is 'low'")
print("        because score (95) < 100. Any risk signal blocks auto-fix.")
