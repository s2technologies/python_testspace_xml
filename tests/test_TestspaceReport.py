from python_testspace_xml import testspace_xml
import pytest
import os
from lxml import etree, objectify
from lxml.etree import XMLSyntaxError

def create_simple_testspace_xml(self):
    testspace_report = testspace_xml.TestspaceReport()
    example_suite = testspace_report.GetOrAddSuite('Example Suite')
    test_case = testspace_xml.TestCase(example_suite, 'test a', 'passed')
    example_suite.AddTestCase(test_case)
    # writer = testspace_xml.XmlWriter(testspace_report)
    # writer.Write('testspace.xml')
    testspace_report.xml_file('testspace.xml')

    xml_file = open('testspace.xml', 'r')
    self.testspace_xml_string = xml_file.read()
    xml_file.close()


class TestTestspaceXml:
    @pytest.fixture(autouse=True)
    def setup_class(self):
        create_simple_testspace_xml(self)

    @classmethod
    def teardown_class(self):
        """ teardown any state that was previously setup with a call to
        setup_class.
        """
        os.remove('testspace.xml')

    def test_number_testcases(self):
        assert 'passed="1"' in self.testspace_xml_string

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







