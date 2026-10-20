"""Trusted sandbox entry point; candidate source is mounted read-only at /work."""
import sys
import unittest
sys.path.insert(0,'/work')
suite=unittest.defaultTestLoader.discover('/work/tests',pattern='test_*.py')
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() and result.testsRun else 1)
