import sys
import nose
from pkg_resources import iter_entry_points

cover_packages = list()
all_tests = list()
pytests = list()

for entry_point in iter_entry_points(group='openregistry.tests'):
    cover_packages.append("openregistry.{}".format(entry_point.name))
    suite = entry_point.load()
    for tests in suite():
        all_tests.append(tests)

for entry_point in iter_entry_points(group='openregistry.pytests'):
    pytests.append(entry_point.load())

nose_env = {
    "NOSE_WITH_COVERAGE": 1,
    "NOSE_COVER_PACKAGE": cover_packages,
    "NOSE_COVER_ERASE": 1,
    "NOSE_COVER_HTML": 1
}

if __name__ == '__main__':
    sys.exit([suite() for suite in pytests],
             nose.run_exit(suite=all_tests, env=nose_env))
