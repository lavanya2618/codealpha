"""
security.py
Simple, educational SQL-injection pattern detector.

This checks user-supplied text (username / password fields) against a
list of common SQL injection keywords and patterns. It is meant to
demonstrate detection concepts, not to replace parameterized queries
(which is what actually prevents injection at the database layer in
this project - see database.py).
"""

import re

# Common SQL injection keywords / patterns to flag.
SQLI_PATTERNS = [
    r"'\s*or\s*'?1'?\s*=\s*'?1",   # ' OR '1'='1
    r"\bor\b\s+1\s*=\s*1",         # OR 1=1
    r"\bdrop\s+table\b",           # DROP TABLE
    r"\bunion\b",                  # UNION
    r"\bselect\b.*\bfrom\b",       # SELECT ... FROM
    r"\binsert\s+into\b",          # INSERT INTO
    r"\bdelete\s+from\b",          # DELETE FROM
    r"\bupdate\b.*\bset\b",        # UPDATE ... SET
    r"--",                         # SQL comment
    r";\s*--",                     # statement terminator + comment
    r"/\*.*\*/",                   # block comment
    r"\bexec\b",                   # EXEC
    r"\bxp_cmdshell\b",            # xp_cmdshell
    r"'\s*;",                      # quote followed by semicolon
]

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in SQLI_PATTERNS]


def detect_sql_injection(text: str):
    """
    Check a string for SQL injection patterns.

    Returns a tuple (is_malicious: bool, matched_pattern: str | None)
    """
    if not text:
        return False, None

    for pattern in _COMPILED_PATTERNS:
        if pattern.search(text):
            return True, pattern.pattern

    return False, None


def check_inputs(*values):
    """
    Check multiple input values (e.g. username and password) at once.

    Returns (is_malicious: bool, offending_value: str | None, pattern: str | None)
    """
    for value in values:
        is_malicious, pattern = detect_sql_injection(value)
        if is_malicious:
            return True, value, pattern
    return False, None, None
