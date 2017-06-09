import os
from lxml import etree, objectify
from lxml.etree import XMLSyntaxError

from python_testspace_xml import testspace_xml


def create_simple_testspace_xml(self):
    self.annotation_tuple = [
        ('zannotation warning example', 'warn', 'to confirm order of annotations'),
        ('annotation info example', 'info', 'description of annotation'),
        ('aannotation error example', 'error', 'to confirm order of annotations')]

    testspace_report = testspace_xml.TestspaceReport()

    example_suite = testspace_report.get_or_add_test_suite('Example Suite')
    test_case = testspace_xml.TestCase('passing case 1', 'passed')
    for annotation in self.annotation_tuple:
        test_case.add_text_annotation(
            annotation[0], level=annotation[1], description=annotation[2])
    example_suite.add_test_case(test_case)

    test_case = testspace_xml.TestCase('passing case 2', 'passed')
    test_case.add_file_annotation('tests/report_v1.xsd', file_path='tests/report_v1.xsd')
    test_case.add_file_annotation('report_v1.xsd', file_path='/report_v1.xsd')
    test_case.add_link_annotation(file_path=r'\\machine/public')
    test_case.add_info_annotation(self.annotation_tuple[0][2])
    test_case.add_error_annotation(self.annotation_tuple[1][2])
    test_case.add_warning_annotation(self.annotation_tuple[2][2])
    example_suite.add_test_case(test_case)

    test_case = testspace_xml.TestCase('failing case 1')
    test_case.fail('failing testcase')  # adds annotation to testcase
    example_suite.add_test_case(test_case)
    test_annotation = test_case.add_text_annotation('annotation with comment')
    test_annotation.add_comment("comment", "annotation comment")
    testspace_report.write_xml('testspace.xml', to_pretty=True)

    xml_file = open('testspace.xml', 'r')
    self.testspace_xml_string = xml_file.read()
    xml_file.close()

    self.testspace_xml_root = etree.fromstring(self.testspace_xml_string)


class TestTestspaceXml:
    @classmethod
    def setup_class(cls):
        create_simple_testspace_xml(cls)

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

    def test_number_annotations(self):
        test_cases = self.testspace_xml_root.xpath("//test_suite/test_case/annotation")
        assert len(test_cases) is 11

    def test_number_file_annotations(self):
        test_cases = self.testspace_xml_root.xpath("//test_suite/test_case/annotation[@file]")
        assert len(test_cases) is 2

    def test_number_annotation_comments(self):
        test_cases = self.testspace_xml_root.xpath("//test_suite/test_case/annotation/comment")
        assert len(test_cases) is 1

    def test_annotation_order(self):
        annotations = self.testspace_xml_root.xpath(
            "//test_suite/test_case[@name='passing case 1']/annotation")
        for idx, annotation in enumerate(annotations):
            assert annotation.get('name') == self.annotation_tuple[idx][0]

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
