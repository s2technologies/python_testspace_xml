from python_testspace_xml import testspace_xml
import pytest
import os
from lxml import etree, objectify
from lxml.etree import XMLSyntaxError


def create_simple_testspace_xml(self):
    testspace_report = testspace_xml.TestspaceReport()
    example_suite = testspace_report.get_or_add_suite('Example Suite')
    test_case = testspace_xml.TestCase('passing case 1', 'passed')
    example_suite.add_test_case(test_case)
    test_case = testspace_xml.TestCase('passing case 2', 'passed')
    example_suite.add_test_case(test_case)
    test_case = testspace_xml.TestCase('failing case 1', 'failed')
    example_suite.add_test_case(test_case)
    testspace_report.xml_file('testspace.xml')

    xml_file = open('testspace.xml', 'r')
    self.testspace_xml_string = xml_file.read()
    xml_file.close()

    self.testspace_xml_root = etree.fromstring(self.testspace_xml_string)

class TestTestspaceXml:
    @pytest.fixture(autouse=True)
    def setup_class(self):
        create_simple_testspace_xml(self)

    @classmethod
    def teardown_class(cls):
        """ teardown any state that was previously setup with a call to
        setup_class.
        """
        os.remove('testspace.xml')

    def test_number_testcases(self):
        test_cases = self.testspace_xml_root.xpath("//test_suite/test_case")
        assert len(test_cases) is 3

    def test_number_passed_testcases(self):
        test_cases = self.testspace_xml_root.xpath("//test_suite/test_case[@status='passed']")
        assert len(test_cases) is 2

    def test_number_failed_testcases(self):
        test_cases = self.testspace_xml_root.xpath("//test_suite/test_case[@status='failed']")
        assert len(test_cases) is 1

    def test_validate_xsd(self):
        assert xml_validator(self.testspace_xml_string, 'tests/report_v1.xsd')


def xml_validator(some_xml_string, xsd_file):
    try:
        schema = etree.XMLSchema(file=xsd_file)
        parser = objectify.makeparser(schema=schema)
        objectify.fromstring(some_xml_string, parser)
    except XMLSyntaxError:
        # handle exception here
        return False
    return True
