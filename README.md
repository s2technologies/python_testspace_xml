# python_testspace_xml

A python library for creating [Testspace](https://signin.testspace.com/) xml result files. This is based on the Testspace result [xml format](https://help.testspace.com/reference:result-file-format).

## Getting Started

### Installing

Requires python 2.7 or 3.5 or later and its standard libraries and adding directory to your PYTHONPATH.

### Example
To retrieve a list or projects for an organization.
```

testspace_report = testspace_xml.TestspaceReport()

example_suite = testspace_report.get_or_add_test_suite('Example Suite')
test_case = testspace_xml.TestCase('passing case 1', 'passed')
example_suite.add_test_case(test_case)
testspace_report.write_xml('testspace.xml')

```
## Running the tests

The tests cases are creating using pytest and as part of running tox both code coverage and static analysis are done.

```
pip install tox
tox -e py
```


## Contributing

All pull request are built with [travisci.org](https://travis-ci.org/s2technologies/python_testspace_xml), with the test, code coverage and static analysis results reports at [Testspace](https://travis-ci.org/s2technologies/python_testspace_xml)


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
