# python_testspace_xml

A python library for creating [Testspace XML format](https://help.testspace.com/reference:result-file-format) result files.

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

Feel free to clone, modify code and request a PR to this repository. All PRs and issues will be reviewed by the Testspace team.


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
