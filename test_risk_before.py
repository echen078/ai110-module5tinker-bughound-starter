from bughound_agent import BugHoundAgent

agent = BugHoundAgent(client=None)
code = '''def greet(name):
    print("Hello", name)
    print("Welcome!")
    return True'''

result = agent.run(code)

print('=== BEFORE CHANGE ===')
print('Issues found:', len(result['issues']))
for issue in result['issues']:
    print(f"  - {issue.get('type')}: {issue.get('severity')}")

risk = result['risk']
print(f"Risk Score: {risk['score']}")
print(f"Risk Level: {risk['level']}")
print(f"Should Auto-fix: {risk['should_autofix']}")
print(f"Risk Reasons: {risk['reasons']}")
