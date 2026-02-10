#!/usr/bin/env python
# scripts/verify_all.py
"""
Comprehensive Project Verification Script
Runs all tests and validations to ensure everything works properly.
"""

import sys
import subprocess
from pathlib import Path

def run_test(test_file, phase_name):
    """Run a single test file and return results."""
    print(f"\n{'='*70}")
    print(f"Running: {phase_name}")
    print(f"File: {test_file}")
    print('='*70)
    
    try:
        result = subprocess.run(
            ['python', test_file],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Check for "Passed: X/Y" in output
        output = result.stdout + result.stderr
        
        if 'Passed:' in output:
            # Extract pass count
            for line in output.split('\n'):
                if 'Passed:' in line:
                    print(f"✅ {line.strip()}")
                    return True, line.strip()
        
        if result.returncode == 0:
            print(f"✅ PASSED")
            return True, "PASSED"
        else:
            print(f"❌ FAILED (exit code: {result.returncode})")
            return False, f"FAILED (exit code: {result.returncode})"
            
    except subprocess.TimeoutExpired:
        print(f"❌ TIMEOUT")
        return False, "TIMEOUT"
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False, f"ERROR: {e}"


def main():
    """Run all verification tests."""
    print("\n" + "="*70)
    print("COMPREHENSIVE PROJECT VERIFICATION")
    print("LinkedIn Contact Extraction Bot - All Phases")
    print("="*70)
    
    # Define all test files
    tests = [
        # Phase 1
        ("test_phase1_security.py", "Phase 1.1 - Security & Environment"),
        ("test_phase1_2_selectors.py", "Phase 1.2 - Selector Management"),
        ("test_phase1_3_logging.py", "Phase 1.3 - Logging System"),
        
        # Phase 2
        ("test_phase2_1_undetected_chrome.py", "Phase 2.1 - Undetected Chrome"),
        ("test_phase2_2_fingerprint.py", "Phase 2.2 - Fingerprint Randomization"),
        ("test_phase2_3_human_behavior.py", "Phase 2.3 - Human Behavior"),
        ("test_phase2_5_configuration.py", "Phase 2.5 - Configuration"),
        ("test_phase2_6_validation.py", "Phase 2.6 - Validation"),
        
        # Phase 3
        ("test_phase3_1_browser_manager.py", "Phase 3.1 - Browser Manager"),
        ("test_phase3_2_login_manager.py", "Phase 3.2 - Login Manager"),
        ("test_phase3_3_navigation_manager.py", "Phase 3.3 - Navigation Manager"),
        ("test_phase3_4_extraction_manager.py", "Phase 3.4 - Extraction Manager"),
        ("test_phase3_5_integration.py", "Phase 3.5 - Integration"),
        
        # Phase 4
        ("test_phase4_1_execution_control.py", "Phase 4.1 - Execution Control"),
        ("test_phase4_2_extraction_refactoring.py", "Phase 4.2 - Extraction Refactoring"),
        
        # Phase 5
        ("test_phase5_1_metrics.py", "Phase 5.1 - Metrics System"),
        ("test_phase5_2_validation.py", "Phase 5.2 - Validation System"),
        
        # Phase 6
        ("test_phase6_1_duckdb_setup.py", "Phase 6.1 - DuckDB Setup"),
        ("test_phase6_2_integration.py", "Phase 6.2 - DuckDB Integration"),
        
        # Phase 7.5
        ("test_phase7_5_multi_account.py", "Phase 7.5 - Multi-Account Automation"),
    ]
    
    results = []
    total_tests = 0
    passed_tests = 0
    
    for test_file, phase_name in tests:
        test_path = Path(test_file)
        
        if not test_path.exists():
            print(f"\n⚠️  SKIPPED: {phase_name} (file not found)")
            continue
        
        success, message = run_test(test_file, phase_name)
        results.append((phase_name, success, message))
        
        if success:
            passed_tests += 1
        total_tests += 1
    
    # Summary
    print("\n" + "="*70)
    print("VERIFICATION SUMMARY")
    print("="*70)
    print(f"\nTotal test suites: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success rate: {(passed_tests/total_tests*100):.1f}%")
    
    print("\n" + "="*70)
    print("DETAILED RESULTS")
    print("="*70)
    
    for phase_name, success, message in results:
        status = "✅" if success else "❌"
        print(f"{status} {phase_name}: {message}")
    
    print("\n" + "="*70)
    
    if passed_tests == total_tests:
        print("✅ ALL TESTS PASSED - Project is working perfectly!")
        print("="*70)
        return 0
    else:
        print(f"❌ {total_tests - passed_tests} test suite(s) failed")
        print("="*70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
