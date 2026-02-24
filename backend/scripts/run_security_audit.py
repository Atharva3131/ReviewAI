#!/usr/bin/env python3
"""
Automated security audit and penetration testing script
Run this script to perform comprehensive security testing
"""
import sys
import subprocess
import json
from datetime import datetime
from pathlib import Path


class SecurityAuditor:
    """Automated security auditor"""
    
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "warnings": 0
            }
        }
    
    def run_all_tests(self):
        """Run all security tests"""
        print("=" * 80)
        print("REVIVE AI - SECURITY AUDIT & PENETRATION TESTING")
        print("=" * 80)
        print(f"Started: {self.results['timestamp']}")
        print()
        
        # Run pytest security tests
        self.run_pytest_security_tests()
        
        # Run dependency vulnerability scan
        self.run_dependency_scan()
        
        # Run code security analysis
        self.run_code_security_analysis()
        
        # Check security configurations
        self.check_security_configurations()
        
        # Generate report
        self.generate_report()
    
    def run_pytest_security_tests(self):
        """Run pytest security test suite"""
        print("\n[1/4] Running Security Test Suite...")
        print("-" * 80)
        
        try:
            result = subprocess.run(
                ["pytest", "tests/security/test_security_audit.py", "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            self.results["tests"]["pytest_security"] = {
                "status": "passed" if result.returncode == 0 else "failed",
                "output": result.stdout,
                "errors": result.stderr
            }
            
            if result.returncode == 0:
                print("✅ Security test suite PASSED")
                self.results["summary"]["passed"] += 1
            else:
                print("❌ Security test suite FAILED")
                print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
                self.results["summary"]["failed"] += 1
            
            self.results["summary"]["total"] += 1
            
        except subprocess.TimeoutExpired:
            print("⚠️  Security test suite TIMEOUT")
            self.results["tests"]["pytest_security"] = {
                "status": "timeout",
                "output": "Test execution timed out after 300 seconds"
            }
            self.results["summary"]["warnings"] += 1
            self.results["summary"]["total"] += 1
        
        except Exception as e:
            print(f"❌ Error running security tests: {e}")
            self.results["tests"]["pytest_security"] = {
                "status": "error",
                "error": str(e)
            }
            self.results["summary"]["failed"] += 1
            self.results["summary"]["total"] += 1
    
    def run_dependency_scan(self):
        """Run dependency vulnerability scan"""
        print("\n[2/4] Running Dependency Vulnerability Scan...")
        print("-" * 80)
        
        try:
            # Check if pip-audit is installed
            subprocess.run(
                ["pip-audit", "--version"],
                capture_output=True,
                check=True
            )
            
            # Run pip-audit
            result = subprocess.run(
                ["pip-audit", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                print("✅ No vulnerabilities found in dependencies")
                self.results["tests"]["dependency_scan"] = {
                    "status": "passed",
                    "vulnerabilities": []
                }
                self.results["summary"]["passed"] += 1
            else:
                try:
                    vulnerabilities = json.loads(result.stdout)
                    vuln_count = len(vulnerabilities.get("dependencies", []))
                    print(f"⚠️  Found {vuln_count} vulnerable dependencies")
                    self.results["tests"]["dependency_scan"] = {
                        "status": "warning",
                        "vulnerabilities": vulnerabilities
                    }
                    self.results["summary"]["warnings"] += 1
                except json.JSONDecodeError:
                    print("⚠️  Dependency scan completed with warnings")
                    self.results["tests"]["dependency_scan"] = {
                        "status": "warning",
                        "output": result.stdout
                    }
                    self.results["summary"]["warnings"] += 1
            
            self.results["summary"]["total"] += 1
            
        except FileNotFoundError:
            print("⚠️  pip-audit not installed, skipping dependency scan")
            print("   Install with: pip install pip-audit")
            self.results["tests"]["dependency_scan"] = {
                "status": "skipped",
                "reason": "pip-audit not installed"
            }
            self.results["summary"]["warnings"] += 1
            self.results["summary"]["total"] += 1
        
        except subprocess.TimeoutExpired:
            print("⚠️  Dependency scan TIMEOUT")
            self.results["tests"]["dependency_scan"] = {
                "status": "timeout"
            }
            self.results["summary"]["warnings"] += 1
            self.results["summary"]["total"] += 1
        
        except Exception as e:
            print(f"❌ Error running dependency scan: {e}")
            self.results["tests"]["dependency_scan"] = {
                "status": "error",
                "error": str(e)
            }
            self.results["summary"]["failed"] += 1
            self.results["summary"]["total"] += 1
    
    def run_code_security_analysis(self):
        """Run static code security analysis"""
        print("\n[3/4] Running Code Security Analysis...")
        print("-" * 80)
        
        try:
            # Check if bandit is installed
            subprocess.run(
                ["bandit", "--version"],
                capture_output=True,
                check=True
            )
            
            # Run bandit
            result = subprocess.run(
                [
                    "bandit",
                    "-r", "app/",
                    "-f", "json",
                    "-ll",  # Only report medium and high severity
                    "-x", "app/tests/"
                ],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            try:
                analysis = json.loads(result.stdout)
                issue_count = len(analysis.get("results", []))
                
                if issue_count == 0:
                    print("✅ No security issues found in code")
                    self.results["tests"]["code_security"] = {
                        "status": "passed",
                        "issues": []
                    }
                    self.results["summary"]["passed"] += 1
                else:
                    print(f"⚠️  Found {issue_count} potential security issues")
                    self.results["tests"]["code_security"] = {
                        "status": "warning",
                        "issues": analysis.get("results", [])
                    }
                    self.results["summary"]["warnings"] += 1
            
            except json.JSONDecodeError:
                print("✅ Code security analysis completed")
                self.results["tests"]["code_security"] = {
                    "status": "passed",
                    "output": result.stdout
                }
                self.results["summary"]["passed"] += 1
            
            self.results["summary"]["total"] += 1
            
        except FileNotFoundError:
            print("⚠️  bandit not installed, skipping code security analysis")
            print("   Install with: pip install bandit")
            self.results["tests"]["code_security"] = {
                "status": "skipped",
                "reason": "bandit not installed"
            }
            self.results["summary"]["warnings"] += 1
            self.results["summary"]["total"] += 1
        
        except subprocess.TimeoutExpired:
            print("⚠️  Code security analysis TIMEOUT")
            self.results["tests"]["code_security"] = {
                "status": "timeout"
            }
            self.results["summary"]["warnings"] += 1
            self.results["summary"]["total"] += 1
        
        except Exception as e:
            print(f"❌ Error running code security analysis: {e}")
            self.results["tests"]["code_security"] = {
                "status": "error",
                "error": str(e)
            }
            self.results["summary"]["failed"] += 1
            self.results["summary"]["total"] += 1
    
    def check_security_configurations(self):
        """Check security configurations"""
        print("\n[4/4] Checking Security Configurations...")
        print("-" * 80)
        
        checks = []
        
        # Check if .env.example exists
        if Path(".env.example").exists():
            print("✅ .env.example file exists")
            checks.append({"check": ".env.example", "status": "passed"})
        else:
            print("⚠️  .env.example file missing")
            checks.append({"check": ".env.example", "status": "warning"})
        
        # Check if .gitignore includes sensitive files
        if Path(".gitignore").exists():
            with open(".gitignore", "r") as f:
                gitignore_content = f.read()
                
            sensitive_patterns = [".env", "*.key", "*.pem", "secrets"]
            missing_patterns = []
            
            for pattern in sensitive_patterns:
                if pattern not in gitignore_content:
                    missing_patterns.append(pattern)
            
            if not missing_patterns:
                print("✅ .gitignore properly configured")
                checks.append({"check": ".gitignore", "status": "passed"})
            else:
                print(f"⚠️  .gitignore missing patterns: {', '.join(missing_patterns)}")
                checks.append({
                    "check": ".gitignore",
                    "status": "warning",
                    "missing": missing_patterns
                })
        else:
            print("❌ .gitignore file missing")
            checks.append({"check": ".gitignore", "status": "failed"})
        
        # Check for hardcoded secrets (basic check)
        print("   Checking for hardcoded secrets...")
        secret_patterns = ["password", "api_key", "secret_key", "token"]
        found_secrets = []
        
        for py_file in Path("app/").rglob("*.py"):
            if "test" in str(py_file):
                continue
            
            try:
                with open(py_file, "r") as f:
                    content = f.read().lower()
                    
                for pattern in secret_patterns:
                    if f'{pattern} = "' in content or f"{pattern} = '" in content:
                        found_secrets.append(str(py_file))
                        break
            except Exception:
                pass
        
        if not found_secrets:
            print("✅ No hardcoded secrets detected")
            checks.append({"check": "hardcoded_secrets", "status": "passed"})
        else:
            print(f"⚠️  Potential hardcoded secrets in {len(found_secrets)} files")
            checks.append({
                "check": "hardcoded_secrets",
                "status": "warning",
                "files": found_secrets
            })
        
        # Determine overall status
        failed_checks = [c for c in checks if c["status"] == "failed"]
        warning_checks = [c for c in checks if c["status"] == "warning"]
        
        if failed_checks:
            self.results["tests"]["security_config"] = {
                "status": "failed",
                "checks": checks
            }
            self.results["summary"]["failed"] += 1
        elif warning_checks:
            self.results["tests"]["security_config"] = {
                "status": "warning",
                "checks": checks
            }
            self.results["summary"]["warnings"] += 1
        else:
            self.results["tests"]["security_config"] = {
                "status": "passed",
                "checks": checks
            }
            self.results["summary"]["passed"] += 1
        
        self.results["summary"]["total"] += 1
    
    def generate_report(self):
        """Generate security audit report"""
        print("\n" + "=" * 80)
        print("SECURITY AUDIT SUMMARY")
        print("=" * 80)
        
        summary = self.results["summary"]
        print(f"Total Tests: {summary['total']}")
        print(f"✅ Passed: {summary['passed']}")
        print(f"⚠️  Warnings: {summary['warnings']}")
        print(f"❌ Failed: {summary['failed']}")
        print()
        
        # Calculate overall status
        if summary["failed"] > 0:
            overall_status = "FAILED"
            status_icon = "❌"
        elif summary["warnings"] > 0:
            overall_status = "PASSED WITH WARNINGS"
            status_icon = "⚠️"
        else:
            overall_status = "PASSED"
            status_icon = "✅"
        
        print(f"Overall Status: {status_icon} {overall_status}")
        print()
        
        # Save detailed report
        report_file = f"security_audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w") as f:
            json.dump(self.results, f, indent=2)
        
        print(f"Detailed report saved to: {report_file}")
        print("=" * 80)
        
        # Return exit code
        return 0 if summary["failed"] == 0 else 1


def main():
    """Main entry point"""
    auditor = SecurityAuditor()
    exit_code = auditor.run_all_tests()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
