import unittest
import os
import sys

# Add Test directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def load_all_tests():
    test_dir = os.path.dirname(os.path.abspath(__file__))
    suite = unittest.TestSuite()
    for filename in os.listdir(test_dir):
        if filename.startswith('test_') and filename.endswith('.py') and filename != 'test_all.py':
            module_name = filename[:-3]
            module = __import__(module_name)
            suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
    return suite

if __name__ == '__main__':
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(load_all_tests())
