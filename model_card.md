# BugHound Mini Model Card (Reflection)

Fill this out after you run BugHound in **both** modes (Heuristic and Gemini).

---

## 1) What is this system?

**Name:** BugHound  
**Purpose:** Analyze a Python snippet, propose a fix, and run reliability checks before suggesting whether the fix should be auto-applied.

**Intended users:** Students learning agentic workflows and AI reliability concepts.

---

## 2) How does it work?

Describe the workflow in your own words (plan → analyze → act → test → reflect).  
Include what is done by heuristics vs what is done by Gemini (if enabled).

**Workflow Stages:**

1. **PLAN:** Agent decides to scan the code for quality and reliability issues.

2. **ANALYZE:** Detects issues in the code. Two modes available:
   - **Heuristic Mode (default):** Uses regex patterns and simple string matching to find:
     - Print statements (suggests logging instead)
     - Bare `except:` blocks (suggests catching `Exception as e`)
     - TODO comments (suggests these are incomplete logic)
   - **Gemini Mode (if API key present):** Sends code to Google Gemini LLM with a structured prompt asking for JSON array of issues. Falls back to heuristics if JSON parsing fails or API errors occur.

3. **ACT:** Proposes a fix based on detected issues. Two modes:
   - **Heuristic Mode:** Applies simple transformations (print→logging, bare except→specific exception, adds import statements)
   - **Gemini Mode:** LLM generates a rewritten version of the code. Falls back to heuristics on parse errors.

4. **TEST:** Runs reliability checks via `assess_risk()`:
   - Validates fixed code has no syntax errors
   - Checks for dangerous structural changes (removed returns, dramatic code shrinkage)
   - Scores based on issue severity and structural risk
   - Generates human-readable risk report

5. **REFLECT:** Decides whether to auto-fix:
   - Score must be perfect (100) for auto-fix approval
   - Any detected issue (low/medium/high severity) blocks auto-fix
   - Requires explicit human review for any risk signal
   - Returns full report: issues, fixed code, risk assessment, and decision logs

---

## 3) Inputs and outputs

**Inputs:**

- What kind of code snippets did you try?
- What was the “shape” of the input (short scripts, functions, try/except blocks, etc.)?

**Tested Input Scenarios:**

1. **cleanish.py** (6 lines): Already clean, uses `logging.info()`, has proper return statement. No issues expected.

2. **mixed_issues.py** (10 lines): Contains three issues:
   - Print statements for debugging
   - Bare `except:` block
   - TODO comment indicating unfinished logic

3. **print_spam.py** (4 lines): Simple function with `print()` calls and return statement. Expected to detect print statements.

4. **flaky_try_except.py** (6 lines): Opens file in bare try, catches with bare except, returns None on error.

5. **Edge cases tested:**
   - Empty file (`""`)
   - Comments-only file (no executable code)
   - Syntactically broken code (missing closing paren)

**Outputs Generated:**

| Input | Issues Found | Fix Applied | Risk Score | Auto-fix? |
|-------|--------------|-------------|-----------|-----------|
| cleanish.py | 0 | None (code unchanged) | 100/100 | ✓ Yes |
| mixed_issues.py | 3 (print, bare except, TODO) | Added logging import, changed `except:` to `except Exception as e:` | 30/100 | ✗ No |
| print_spam.py | 1 (print statements) | Added logging import, replaced `print()` with `logging.info()` | 95/100 | ✗ No |
| empty file | 0 | No fix produced | 0/100 (no output) | ✗ No |
| comments-only | 0 | None | 100/100 | ✓ Yes |
| broken syntax | 0 detected by heuristics | Proposed fix with syntax error | 0/100 (syntax invalid) | ✗ No |

**Issue Types Detected:**
- **Code Quality:** Print statements, logging not used
- **Reliability:** Bare except clauses (catch-all exception handling)
- **Maintainability:** TODO comments indicating incomplete code

**Risk Report Contents:**
- Score (0-100)
- Risk level (low/medium/high)
- List of specific reasons for deductions
- Explicit should_autofix decision (True/False)

---

## 4) Reliability and safety rules

List at least **two** reliability rules currently used in `assess_risk`. For each:

- What does the rule check?
- Why might that check matter for safety or correctness?
- What is a false positive this rule could cause?
- What is a false negative this rule could miss?

---

### Rule 1: Syntax Error Detection (NEW GUARDRAIL)

**What it checks:** Uses `ast.parse()` to validate that fixed code is syntactically valid Python.

**Why it matters:** 
- A syntax error means the code cannot run at all
- An LLM or broken heuristic could produce syntactically invalid output
- Auto-fixing broken code is worse than leaving original alone (at least original runs)
- Prevents shipping unparseable code to users

**False positives:** 
- Valid Python 3.10+ features might fail to parse on older Python versions (e.g., match statements)
- Could falsely reject valid metaprogramming or generated code that constructs valid Python dynamically

**False negatives:** 
- Could miss semantic errors (code parses but crashes at runtime)
- Won't catch logic errors (code runs but produces wrong results)
- Runtime exceptions won't be detected until execution

**Severity:** CRITICAL - Syntax errors block ALL auto-fix attempts (score=0).

---

### Rule 2: Return Statement Removal Detection

**What it checks:** If original code has `return` statements but fixed code removes them, penalize -30 points.

**Why it matters:**
- Removing returns changes function behavior fundamentally
- Function that returned a value suddenly returns None (implicit)
- Callers expecting a value will get None instead
- Can cause downstream null pointer / type errors
- Suggests the fixer didn't understand the code's intent

**False positives:**
- Legitimate refactoring: `return x + 1` → `x + 1` in a builder pattern or context manager could be intentional
- Multiple returns consolidated: `if x: return a; else: return b` → `return a if x else b` removes one return syntactically but not semantically
- Multi-function case: Only first return removed intentionally, others remain

**False negatives:**
- Won't catch replacing `return x` with `return` (removed value but kept keyword)
- Won't detect `raise` being removed (different control flow)
- Won't catch implicit returns becoming explicit (adds `return None` unnecessarily)

**Severity:** HIGH - Always blocked in medium/high risk range, helps prevent behavior-altering fixes.

---

### Rule 3: Bare Except Modification (Existing Rule)

**What it checks:** If code has `except:` and it's modified, note this with -5 points.

**Why it matters:**
- Bare except is generally considered bad practice (catches SystemExit, KeyboardInterrupt)
- Changes to exception handling are high-risk behavioral modifications
- Even well-intentioned changes could mask or expose different errors
- Flags that an important control flow change occurred

**False positives:**
- Safe changes like `except:` → `except Exception as e: logging.error(e)` are still flagged with concern
- Valid improvement that catches fewer things (SystemExit flows through) still gets -5

**False negatives:**
- Won't catch `except Exception:` → bare `except:` (backwards improvement, missed)
- Won't detect exception type changing from broad to narrow, which might miss errors

**Severity:** LOW-MEDIUM - Informational flag, not blocking alone.

---

### Rule 4: Code Length Shrinkage Detection

**What it checks:** If fixed code is < 50% the length of original code (by line count), penalize -20 points.

**Why it matters:**
- Aggressive deletion might indicate:
  - Removing important error handling
  - Deleting multi-step logic and replacing with one-liner
  - Over-simplification that loses nuance
- Very short fixes can be suspicious (are we actually fixing or just removing?)

**False positives:**
- Legitimate simplification: 10-line verbose function → 2-line concise version using library functions
- Deleting dead code or removing comments to focus on logic
- Refactoring into a one-liner is sometimes correct

**False negatives:**
- Won't catch semantic deletions that don't reduce lines (e.g., removing important try block at same line count)
- A 5-line file becoming 2 lines seems aggressive, but might be legitimate removal of import

**Severity:** MEDIUM - Combined with other signals, contributes to risk score.

---

## 5) Observed failure modes

Provide at least **two** examples:

1. A time BugHound missed an issue it should have caught  
2. A time BugHound suggested a fix that felt risky, wrong, or unnecessary  

For each, include the snippet (or describe it) and what went wrong.

---

### Failure Mode 1: Syntax Error in LLM-Generated Fix (CRITICAL - FIXED)

**Scenario:**
```python
# Original
def compute(x, y):
    return x / y

# LLM attempted fix (simulated)
import logging
def compute(x, y):
    logging.info("computing"    # ← Missing closing paren!
    return x / y
```

**What went wrong:**
- The LLM (or heuristic) output syntactically invalid Python
- The code cannot parse or run at all
- **Before guardrail:** Would score 95/100 (one low-severity issue), and auto-fix would be triggered! ⚠️
- **Result:** Users would receive broken code as a "fix"

**Root cause:** 
- No validation that fixed code is actually valid Python
- Risk scorer only looked at severity classification, not code correctness
- LLM can hallucinate syntax or fail to balance brackets

**Resolution implemented:** Added `ast.parse()` validation that immediately returns score=0, level=high, should_autofix=False when syntax errors detected.

**Learning:** Always validate generated code parses before scoring it.

---

### Failure Mode 2: Over-Aggressive Print-to-Logging Conversion

**Scenario:**
```python
# Original
def debug_output():
    print("=" * 50)
    print("DEBUG START")
    for i in range(5):
        print(f"Item {i}")
    print("=" * 50)
    return True

# BugHound fix
import logging
def debug_output():
    logging.info("=" * 50)
    logging.info("DEBUG START")
    for i in range(5):
        logging.info(f"Item {i}")
    logging.info("=" * 50)
    return True
```

**What went wrong:**
- BugHound correctly identified print statements and converted them to logging
- However, the function's purpose was debugging, not production logging
- The fix is technically correct but changes the semantics:
  - `print()` output goes to stdout immediately (visible in terminal)
  - `logging.info()` goes through logger config, may not be visible, depends on log level
  - For debugging scripts, the original may have been intentional
- Risk score: 95/100 (one low-severity issue)
- **Auto-fix would trigger** (with new policy, score != 100, so blocked)

**Root cause:**
- Heuristic treat all prints as "bad practice"
- Doesn't distinguish debugging scripts from production code
- No semantic understanding of intent

**What should happen:** Require human review because:
- Output format changed (stdout → logging stream)
- Debug intent changed (immediate visibility → config-dependent)
- Script might be used for quick debugging

**Learning:** Code quality improvements can change behavior. Even "correct" fixes need human review when intent changes.

---

### Failure Mode 3: TODO Comment as a Code Issue (Minor)

**Scenario:**
```python
# TODO: Add input validation
def divide(x, y):
    return x / y
```

**What went wrong:**
- Heuristic detects TODO comment as "Maintainability" issue (medium severity, -20)
- BugHound suggests this is unfinished logic
- However, TODO comments are normal development practice
- Not all TODOs block code from being correct or safe

**Issue:** 
- Risk score drops to 80/100 just from a TODO comment
- This is informational but not necessarily a bug
- Creates noise in the risk assessment

**Severity:** Low - The system still blocks auto-fix (score < 100), so it's conservative, just noisy.

**Learning:** Distinguish between "things to improve" and "things that break."

---

## 6) Heuristic vs Gemini comparison

Compare behavior across the two modes:

- What did Gemini detect that heuristics did not?
- What did heuristics catch consistently?
- How did the proposed fixes differ?
- Did the risk scorer agree with your intuition?

---

**Testing Context:** System was tested in **Heuristic Mode (offline)** using MockClient to avoid API rate limits. Gemini mode not run in production, but analysis based on code structure.

### Heuristic Mode (What we tested):

**Strengths:**
- ✅ Consistent: Always finds same issues in same input
- ✅ Fast: No API latency
- ✅ Reliable: Regex patterns are predictable
- ✅ Catches: Print statements, bare except, TODO comments
- ✅ Safe fallback: Always available if API fails

**Detections:**
```python
# cleanish.py
Heuristics: 0 issues ✓ (correct - no prints, bare except, or TODOs)

# mixed_issues.py  
Heuristics: 3 issues ✓
  - Code Quality (print)
  - Reliability (bare except)
  - Maintainability (TODO)

# flaky_try_except.py
Heuristics: 2 issues ✓
  - Code Quality (no logging detected on error path)
  - Reliability (bare except)
```

**Fixes Generated:**
- Adds `import logging`
- Replaces `print()` with `logging.info()`
- Changes `except:` to `except Exception as e:`
- Preserves all original logic

**Limitations:**
- ✗ No semantic understanding (can't distinguish debug vs production prints)
- ✗ Pattern-based only (misses issues outside regex patterns)
- ✗ Over-eager on TODO (flags as issue without context)
- ✗ Can't suggest complex refactorings

### Gemini Mode (Theoretical, based on code):

**Expected Strengths:**
- 🔄 Semantic understanding: Could distinguish debug scripts from production
- 🔄 Context-aware: Understand when TODO is blocking vs informational
- 🔄 Creative fixes: Could suggest alternatives beyond simple transformations
- 🔄 More comprehensive: Might catch issues beyond regex scope

**Expected Limitations:**
- ⚠️ Latency: API call delays analysis
- ⚠️ Inconsistent: LLM can vary on same input (temperature, model version)
- ⚠️ Format fragility: Requires JSON parsing (can fail, causes fallback)
- ⚠️ Hallucination risk: Could invent false issues or false fixes
- ⚠️ Cost: API quota limits (20 requests)
- ⚠️ Syntax errors: LLM can generate invalid Python

### Risk Assessment Alignment:

**In Heuristic Mode:**
| Input | Detected | Score | Intuitive? |
|-------|----------|-------|-----------|
| cleanish.py | 0 issues | 100 | ✅ Yes - truly clean |
| mixed_issues.py | 3 issues | 30 | ✅ Yes - clearly problematic |
| print_spam.py | 1 issue | 95 | ⚠️ Maybe - low priority issue only |

**Risk scorer consensus:** Agrees with intuition when input has clear structural problems, but may over-penalize low-severity style issues.

### When Gemini Would Help Most:

1. **Business logic bugs:** Code runs but produces wrong output (heuristics can't detect)
2. **Context-dependent smells:** Print in debug script vs production logging (needs semantic analysis)
3. **API misuse:** Wrong library function called (requires knowledge of stdlib)
4. **Performance issues:** Inefficient algorithms (needs domain knowledge)

### When Heuristics are Better:

1. **Code style:** Print vs logging, consistent exception handling
2. **Reliability:** Bare except clauses (always problematic)
3. **Completeness:** TODO/FIXME markers indicating unfinished work
4. **Speed:** Immediate analysis without API calls
5. **Reproducibility:** Same input always → same output

---

## 7) Human-in-the-loop decision

Describe one scenario where BugHound should **refuse** to auto-fix and require human review.

- What trigger would you add?
- Where would you implement it (risk_assessor vs agent workflow vs UI)?
- What message should the tool show the user?

---

### Scenario: Bare Except Block in Production Error Handler

**Code Example:**
```python
# Original - production API endpoint
@app.route('/api/process', methods=['POST'])
def process_data(request):
    try:
        result = expensive_computation(request.json)
        return jsonify({"status": "success", "data": result})
    except:
        # Log to monitoring system
        log_error("Process failed")
        return jsonify({"status": "error"}), 500

# BugHound's "fix"
@app.route('/api/process', methods=['POST'])
def process_data(request):
    try:
        result = expensive_computation(request.json)
        return jsonify({"status": "success", "data": result})
    except Exception as e:
        log_error(f"Process failed: {e}")
        return jsonify({"status": "error"}), 500
```

**Why this needs human review:**

1. **Behavioral change:** Original catches ALL exceptions (including SystemExit, KeyboardInterrupt). Fix only catches Exception subclasses. This changes error handling semantics fundamentally.

2. **API contract violation:** The bare except might be intentional - service should never crash, even on shutdown signals. Changing this could cause cascading failures.

3. **Monitoring consequences:** Log message changes from static string to dynamic with error text. Could expose sensitive info in logs or change log parsing rules.

4. **Non-local effects:** This is in a framework route handler - changes propagate to all API clients.

**Current BugHound Behavior:**
- Detects "bare except" as Reliability issue (high severity, -40)
- Score: 60/100
- Risk level: HIGH
- Auto-fix: ✗ BLOCKED (score < 100)
- Status: ✅ Correctly requires human review

**Proposed Trigger Enhancement:**

Add context-aware detection: If bare except is in a:
- Web framework route handler (Flask/Django patterns)
- Long-running service/daemon
- Critical system code (signal handlers, shutdown hooks)

**Implementation Location:** **Agent workflow layer** (bughound_agent.py)

Add a `_is_critical_context()` check before proposing fix:

```python
def propose_fix(self, code_snippet, issues):
    # NEW: Detect critical context
    if self._is_critical_context(code_snippet):
        high_severity_issues = [i for i in issues if i.get('severity') == 'High']
        if high_severity_issues:
            self._log("ACT", "CRITICAL: Code appears to be in critical path. Refusing to auto-fix high-severity issues.")
            return code_snippet  # Return unchanged
```

**User Message (UI/CLI):**

```
⚠️  HUMAN REVIEW REQUIRED

This code appears to be in a critical system component (detected Flask route, 
long-running service, or shutdown handler).

Issues detected:
  • HIGH: Bare except clause - catches all exceptions including system signals

Risk Assessment: 60/100 (HIGH RISK)

Why we're refusing auto-fix:
  Changing exception handling in critical code could:
  - Alter system shutdown behavior
  - Allow bugs to propagate silently
  - Change API contract with clients
  - Affect monitoring and alerting

Recommendation:
  1. Review the bare except - is it intentional?
  2. If fixing, ensure you understand the error propagation consequences
  3. Test thoroughly in staging before deploying
  4. Update API documentation if error handling changes

[Continue without auto-fix] [Manual fix] [Force auto-fix (NOT RECOMMENDED)]
```

**Key Principles:**
- Trust human judgment over automatic fixes in critical code
- Provide clear reasoning for refusal
- Offer paths forward (manual review, staged testing)
- Make the stakes visible (why this matters)

---

## 8) Improvement idea

Propose one improvement that would make BugHound more reliable *without* making it dramatically more complex.

Examples:

- A better output format and parsing strategy
- A new guardrail rule + test
- A more careful “minimal diff” policy
- Better detection of changes that alter behavior

Write your idea clearly and briefly.
---

### Implemented Improvement: Dual-Layer Guardrail System

**Problem:** Original system could auto-fix code with syntax errors or after making any risky changes, as long as risk level ≥ 75 (too permissive).

**Solution:** Implement two independent guardrails:

#### Guardrail 1: Syntax Validation (NEW)

**What:** Check that fixed code is valid Python using `ast.parse()` before any risk scoring.

**Code:**
```python
try:
    ast.parse(fixed_code)
except SyntaxError as e:
    return {
        "score": 0,
        "level": "high",
        "reasons": [f"Fixed code has syntax error: {e.msg} at line {e.lineno}"],
        "should_autofix": False,
    }
```

**Why this works:**
- ✅ Catches broken output immediately (no way to bypass)
- ✅ Explicit and deterministic (not probabilistic like LLM)
- ✅ Early exit (before scoring logic wastes cycles)
- ✅ Clear failure message (tells user what's wrong)
- ✅ Defense-in-depth: Works regardless of scoring thresholds

**Impact:** Prevents shipping completely broken code.

---

#### Guardrail 2: Perfect Score Requirement (NEW)

**What:** Auto-fix only when score == 100 (no issues at all), not just when risk level is "low".

**Code change:**
```python
# BEFORE (permissive)
should_autofix = level == "low"  # Triggers at score >= 75

# AFTER (conservative)  
should_autofix = score == 100    # Only when perfect
```

**Why this works:**
- ✅ Reverses burden of proof: Must prove safe, not just "not risky"
- ✅ Blocks even low-severity issues (print statement alone blocks auto-fix)
- ✅ Simple policy (easy to understand and test)
- ✅ Measurable (score is explicit, not threshold-dependent)
- ✅ Future-proof: If scoring changes, this still requires zero issues

**Impact:** Requires human review for any detected problem.

---

### Combined Effect: Defense in Depth

```
Input Code
    ↓
[Syntax Check] ← Guardrail 1
    ↓
[Score == 100?] ← Guardrail 2
    ↓
[Auto-fix]
```

**Before:** Score 95 (one low-severity issue) → Auto-fix ✓ (DANGEROUS)  
**After:** Score 95 → Auto-fix ✗ (requires human review)

**Before:** Broken syntax (score would be 95 if checked) → Auto-fix ✓ (CATASTROPHIC)  
**After:** Broken syntax → Caught at Guardrail 1, score=0, Auto-fix ✗ (safe)

---

### Test Coverage Added

```python
def test_syntax_error_in_fixed_code_blocks_autofix():
    """Guardrail: Fixed code with syntax errors must never auto-fix."""
    original = "def compute(x, y):\n    return x / y\n"
    fixed_with_syntax_error = "import logging\ndef compute(x, y):\n    logging.info(\"computing\"\n    return x / y\n"
    
    risk = assess_risk(original_code=original, fixed_code=fixed_with_syntax_error,
                       issues=[{"type": "Code Quality", "severity": "Low", "msg": "no logging"}])
    
    assert risk["score"] == 0
    assert risk["level"] == "high"
    assert risk["should_autofix"] is False
    assert any("syntax error" in r.lower() for r in risk["reasons"])
```

**Result:** ✅ Test passes, confirms guardrails work.

---

### Why This Improvement is Low-Complexity:

- ✅ Only **2 changes** to risk_assessor.py
- ✅ **1 import** added (ast - standard library)
- ✅ **~20 lines of code**
- ✅ **1 test added**
- ✅ No changes to agent workflow, UI, or prompts
- ✅ Backward compatible (existing tests pass)

### Measurable Benefit:

| Metric | Before | After | Improvement |
|--------|--------|-------|------------|
| Syntax errors auto-fixed | ✗ Yes (dangerous) | ✓ No | Critical ✅ |
| Low-severity issues auto-fixed | ✓ Yes | ✗ No | More conservative ✅ |
| Test coverage | 8 tests | 9 tests | +12.5% ✅ |
| False sense of security | High | Low | Reduced ✅ |
| Human review required for | High-severity | Any issue | More careful ✅ |

---

### Alternative Improvements NOT Implemented (Future):

1. **Minimal diff analysis:** Only apply changes directly related to issue (requires diff parsing)
2. **Semantic equivalence check:** Verify fix doesn't change behavior (requires control flow analysis)
3. **API stability guarantee:** Track which fixes break client code (requires dependency analysis)
4. **Rollback capability:** Store original code for easy revert (requires versioning)

These are more complex. The implemented improvement gives maximum safety gain with minimal complexity.

---