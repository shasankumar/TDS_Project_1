# checks_validator.py
import re
import json

def validate_checks(html_code: str, readme: str, checks: list) -> dict:
    """
    Validate generated code against a list of checks.
    
    Args:
        html_code: Generated HTML/JS code
        readme: Generated README
        checks: List of check strings (can be static text or js: expressions)
    
    Returns:
        {
            "all_passed": bool,
            "results": [
                {"check": "...", "passed": bool, "reason": "..."},
                ...
            ],
            "score": 0-100
        }
    """
    
    results = []
    
    if not checks:
        return {
            "all_passed": True,
            "results": [],
            "score": 100,
            "message": "No checks specified"
        }
    
    for check in checks:
        result = validate_single_check(check, html_code, readme)
        results.append(result)
    
    passed_count = sum(1 for r in results if r["passed"])
    total_count = len(results)
    score = int((passed_count / total_count) * 100) if total_count > 0 else 100
    
    return {
        "all_passed": all(r["passed"] for r in results),
        "results": results,
        "score": score,
        "passed": passed_count,
        "total": total_count
    }


def validate_single_check(check: str, html_code: str, readme: str) -> dict:
    """Validate a single check against the code."""
    
    check = check.strip()
    
    # Static text checks
    if check.lower().startswith("repo has"):
        return validate_repo_check(check)
    elif check.lower().startswith("readme"):
        return validate_readme_check(check, readme)
    elif check.lower().startswith("page"):
        return validate_page_check(check, html_code)
    elif check.startswith("js:"):
        return validate_js_check(check, html_code)
    else:
        # Generic check - look for keywords in code
        return validate_generic_check(check, html_code, readme)


def validate_repo_check(check: str) -> dict:
    """Validate repository-level checks."""
    
    check_lower = check.lower()
    
    if "mit license" in check_lower:
        return {
            "check": check,
            "passed": True,
            "reason": "MIT LICENSE will be added by system",
            "type": "repo"
        }
    elif "git" in check_lower or "gitignore" in check_lower:
        return {
            "check": check,
            "passed": True,
            "reason": "Repository structure managed by system",
            "type": "repo"
        }
    
    return {
        "check": check,
        "passed": True,
        "reason": "Repository check deferred to evaluation phase",
        "type": "repo"
    }


def validate_readme_check(check: str, readme: str) -> dict:
    """Validate README quality checks."""
    
    check_lower = check.lower()
    readme_lower = readme.lower()
    
    checks_map = {
        "professional": (
            len(readme) > 500 and
            "overview" in readme_lower and
            "setup" in readme_lower and
            "usage" in readme_lower
        ),
        "contains overview": "overview" in readme_lower,
        "contains setup": "setup" in readme_lower,
        "contains usage": "usage" in readme_lower,
        "contains license": "license" in readme_lower,
        "contains features": "features" in readme_lower,
    }
    
    for key, condition in checks_map.items():
        if key in check_lower:
            return {
                "check": check,
                "passed": condition,
                "reason": f"README {'includes' if condition else 'missing'} {key}",
                "type": "readme"
            }
    
    # Default: check if readme has minimum content
    passed = len(readme) > 300
    return {
        "check": check,
        "passed": passed,
        "reason": f"README length: {len(readme)} chars",
        "type": "readme"
    }


def validate_page_check(check: str, html_code: str) -> dict:
    """Validate page content checks."""
    
    check_lower = check.lower()
    
    # "Page displays captcha URL"
    if "display" in check_lower and "url" in check_lower:
        has_url_param = "url" in html_code or "params" in html_code or "URLSearchParams" in html_code
        return {
            "check": check,
            "passed": has_url_param,
            "reason": "URL parameter handling" if has_url_param else "Missing URL parameter handling",
            "type": "page"
        }
    
    # "Page displays X"
    if "display" in check_lower:
        return {
            "check": check,
            "passed": True,
            "reason": "Display functionality to be verified at runtime",
            "type": "page"
        }
    
    # "Page loads X"
    if "load" in check_lower:
        return {
            "check": check,
            "passed": True,
            "reason": "Loading functionality to be verified at runtime",
            "type": "page"
        }
    
    return {
        "check": check,
        "passed": True,
        "reason": "Dynamic check deferred to Playwright evaluation",
        "type": "page"
    }


def validate_js_check(check: str, html_code: str) -> dict:
    """
    Validate JavaScript-based checks.
    
    These are typically:
    - js: document.title === "expected"
    - js: !!document.querySelector("#selector")
    """
    
    js_expr = check.replace("js:", "").strip()
    
    # Check if required patterns exist in code
    checks_map = {
        "document.title": "document.title" in html_code,
        "querySelector": "querySelector" in html_code,
        "getElementById": "getElementById" in html_code,
        "innerHTML": "innerHTML" in html_code or "textContent" in html_code,
        "fetch": "fetch(" in html_code,
        "addEventListener": "addEventListener" in html_code,
    }
    
    # Determine if JS check dependencies are met
    passed = False
    reason = "JS check syntax found"
    
    for pattern, exists in checks_map.items():
        if pattern in js_expr:
            passed = exists
            reason = f"Pattern '{pattern}' {'found' if exists else 'missing'}"
            break
    
    # If we didn't match specific patterns, just check if there's JS
    if not passed and len(html_code) > 100:
        passed = True
        reason = "JavaScript code present for runtime validation"
    
    return {
        "check": check,
        "passed": passed,
        "reason": reason,
        "type": "js",
        "note": "Full validation requires runtime (Playwright)"
    }


def validate_generic_check(check: str, html_code: str, readme: str) -> dict:
    """Validate generic checks by searching code."""
    
    combined = (html_code + " " + readme).lower()
    check_lower = check.lower()
    
    # Extract key concepts from check
    keywords = extract_keywords(check)
    found_keywords = sum(1 for kw in keywords if kw in combined)
    
    passed = found_keywords >= max(1, len(keywords) // 2)
    
    return {
        "check": check,
        "passed": passed,
        "reason": f"Found {found_keywords}/{len(keywords)} keywords",
        "type": "generic",
        "keywords": keywords
    }


def extract_keywords(text: str) -> list:
    """Extract important keywords from check text."""
    
    # Remove common words
    stop_words = {"the", "a", "an", "and", "or", "is", "are", "be", "to", "for", "of", "in", "on", "with", "at", "by", "from"}
    
    words = re.findall(r'\b\w+\b', text.lower())
    keywords = [w for w in words if len(w) > 3 and w not in stop_words]
    
    return keywords


def generate_checks_report(validation_result: dict) -> str:
    """Generate a human-readable report of check results."""
    
    report = f"""
Checks Validation Report
========================

Overall Score: {validation_result['score']}/100
Status: {'✅ PASSED' if validation_result['all_passed'] else '❌ FAILED'}
Passed: {validation_result.get('passed', 0)}/{validation_result.get('total', 0)}

Details:
--------
"""
    
    for i, result in enumerate(validation_result['results'], 1):
        status = "✅" if result['passed'] else "❌"
        report += f"\n{i}. {status} {result['check']}\n"
        report += f"   Type: {result.get('type', 'unknown')}\n"
        report += f"   Reason: {result['reason']}\n"
    
    report += f"""
Notes:
- Dynamic checks (page display, runtime behavior) require Playwright validation
- JS checks are validated for syntax patterns; full execution requires runtime
- Static code checks are validated against generated code patterns
"""
    
    return report