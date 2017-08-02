import sys
import nose
import pkg_resources

suites = [ep.load() for ep in
          pkg_resources.iter_entry_points(group='openregistry.tests')]

all_tests = []
for suite in suites:
    for tests in suite():
        all_tests.append(tests)

if __name__ == '__main__':
    sys.exit(nose.run_exit(suite=all_tests))
