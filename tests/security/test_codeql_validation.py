"""CodeQL Security Analysis Validation Tests.

IMPORTANT: This file contains INTENTIONAL security vulnerabilities for
testing purposes only. These vulnerabilities are designed to validate that
CodeQL security scanning is correctly configured and detecting common
Python security anti-patterns.

DO NOT use any patterns from this file in production code.
DO NOT run these tests in the normal test suite.

Purpose:
--------
This file ensures that the CodeQL security-extended query suite is:
1. Properly configured in the CI/CD pipeline
2. Actively detecting security vulnerabilities
3. Generating accurate SARIF reports for GitHub Security

CodeQL should flag every function in this file with appropriate severity.

Note: Variables prefixed with underscore are intentionally unused - they exist
solely to create detectable security patterns for CodeQL validation.
"""
# ruff: noqa: F841  # Intentionally unused variables for security testing

import pickle  # nosec B403 - required for security validation testing
import subprocess  # nosec B404 - required for security validation testing
import hashlib
import os
import sqlite3
from pathlib import Path


# Linter configuration for intentional security test file:
# pylint: disable=all
# mypy: ignore-errors
# type: ignore
# fmt: off


class CodeQLValidationTests:
    """Intentional security vulnerabilities for CodeQL validation.

    Each method demonstrates a specific vulnerability class that CodeQL
    should detect using the security-extended query suite.
    """

    def test_hardcoded_secrets(self) -> None:
        """Test: CodeQL should detect hardcoded secrets.

        Expected: CWE-798: Use of Hard-coded Credentials
        Severity: High
        """
        # Intentional hardcoded secrets - CodeQL should flag these
        # Using underscore prefix for intentionally unused variables
        _api_key = "sk-1234567890abcdef1234567890abcdef"  # nosec
        _database_password = "SuperSecretPassword123!"  # nosec
        _aws_secret_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"  # nosec
        _jwt_secret = "my-super-secret-jwt-key-do-not-share"  # nosec

        # CodeQL should detect credential usage
        _connection_string = f"postgresql://admin:{_database_password}@localhost/db"  # nosec
        _headers = {"Authorization": f"Bearer {_api_key}"}  # nosec

    def test_sql_injection(self) -> None:
        """Test: CodeQL should detect SQL injection vulnerabilities.

        Expected: CWE-89: SQL Injection
        Severity: Critical
        """
        user_input = "'; DROP TABLE users; --"

        # Intentional SQL injection - using string formatting
        conn = sqlite3.connect(":memory:")  # nosec
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE users (id INT, name TEXT)")  # nosec

        # VULNERABLE: Direct string interpolation in SQL
        query = f"SELECT * FROM users WHERE name = '{user_input}'"  # nosec
        cursor.execute(query)  # nosec - CodeQL should flag this

        # VULNERABLE: String concatenation in SQL
        query2 = "SELECT * FROM users WHERE id = " + user_input  # nosec
        cursor.execute(query2)  # nosec

        conn.close()

    def test_command_injection(self) -> None:
        """Test: CodeQL should detect command injection vulnerabilities.

        Expected: CWE-78: OS Command Injection
        Severity: Critical
        """
        user_filename = "../../../etc/passwd"

        # VULNERABLE: shell=True with untrusted input
        subprocess.run(f"cat {user_filename}", shell=True, check=False)  # nosec

        # VULNERABLE: Direct user input in command
        subprocess.Popen(["ls", "-la", user_filename], shell=False)  # nosec

        # VULNERABLE: os.system with user input
        os.system(f"echo {user_filename}")  # nosec

    def test_path_traversal(self) -> None:
        """Test: CodeQL should detect path traversal vulnerabilities.

        Expected: CWE-22: Path Traversal
        Severity: High
        """
        user_provided_path = "../../../../etc/passwd"

        # VULNERABLE: No path validation or sanitization
        file_path = f"/var/www/uploads/{user_provided_path}"  # nosec

        # VULNERABLE: Direct file access without validation
        try:
            with open(file_path, "r") as f:  # nosec
                _content = f.read()  # nosec - intentionally unused
        except FileNotFoundError:
            pass

        # VULNERABLE: Path.joinpath without validation
        base_dir = Path("/safe/directory")
        unsafe_path = base_dir / user_provided_path  # nosec
        if unsafe_path.exists():  # nosec
            unsafe_path.read_text()  # nosec

    def test_insecure_deserialization(self) -> None:
        """Test: CodeQL should detect insecure deserialization.

        Expected: CWE-502: Deserialization of Untrusted Data
        Severity: Critical
        """
        # Simulate untrusted data from user/network
        untrusted_data = b"malicious_pickle_payload"

        # VULNERABLE: pickle.loads on untrusted data
        try:
            _deserialized = pickle.loads(untrusted_data)  # nosec - intentionally unused
        except (pickle.UnpicklingError, EOFError, TypeError):
            pass

        # VULNERABLE: pickle.load from untrusted file
        try:
            with open("/tmp/untrusted_data.pkl", "rb") as f:  # nosec
                _data = pickle.load(f)  # nosec - intentionally unused
        except (FileNotFoundError, pickle.UnpicklingError):
            pass

    def test_weak_cryptography(self) -> None:
        """Test: CodeQL should detect weak cryptographic algorithms.

        Expected: CWE-327: Use of Weak Cryptographic Algorithm
        Severity: Medium
        """
        _password = "user_password_123"  # nosec B105 - test fixture password

        # VULNERABLE: MD5 is cryptographically broken
        _md5_hash = hashlib.md5(_password.encode()).hexdigest()  # nosec - intentionally unused

        # VULNERABLE: SHA1 is deprecated for security
        _sha1_hash = hashlib.sha1(_password.encode()).hexdigest()  # nosec - intentionally unused

        # CodeQL should recommend SHA-256 or better
        # Correct usage (not flagged):
        # sha256_hash = hashlib.sha256(password.encode()).hexdigest()

    def test_unsafe_eval(self) -> None:
        """Test: CodeQL should detect unsafe eval() usage.

        Expected: CWE-95: Eval Injection
        Severity: Critical
        """
        user_input = "__import__('os').system('cat /etc/passwd')"

        # VULNERABLE: eval() with untrusted input
        try:
            _result = eval(user_input)  # nosec - CodeQL should flag, intentionally unused
        except (SyntaxError, NameError):
            pass

        # VULNERABLE: exec() with untrusted input
        try:
            exec(user_input)  # nosec - CodeQL should flag
        except (SyntaxError, NameError):
            pass

        # VULNERABLE: compile() + eval() pattern
        try:
            code = compile(user_input, "<string>", "eval")  # nosec
            eval(code)  # nosec
        except (SyntaxError, ValueError):
            pass


# Validation Summary
"""
Expected CodeQL Findings:
--------------------------
1. Hardcoded Secrets (CWE-798): 4+ findings
2. SQL Injection (CWE-89): 2+ findings
3. Command Injection (CWE-78): 3+ findings
4. Path Traversal (CWE-22): 3+ findings
5. Insecure Deserialization (CWE-502): 2+ findings
6. Weak Cryptography (CWE-327): 2+ findings
7. Unsafe Eval (CWE-95): 3+ findings

Total Expected: 19+ security findings

If CodeQL does not flag these vulnerabilities, the security-extended
query suite may not be properly configured.

Verification:
-------------
1. Check GitHub Security tab → Code scanning alerts
2. Review SARIF report in workflow artifacts
3. Confirm all vulnerability types are detected
4. Validate severity levels match expectations
"""
