import os
from lxml import etree, objectify
from lxml.etree import XMLSyntaxError

from python_testspace_xml import testspace_xml


class TestTestspaceReportXsd:
    testsuite_list = ['z testsuite',
                      '1 testsuite',
                      'Example Suite',
                      'A test suite',
                      'aa test suite']

    annotation_tuple = [
        ('zannotation warning example', 'warn', 'to confirm order of annotations'),
        ('annotation info example', 'info', 'description of annotation'),
        ('aannotation error example', 'error', 'to confirm order of annotations')]

    string_buffer = 'Text content to be displayed in Testspace\n' \
                    'Additional line of content'

    duration = 1055.93

    test_annotation = testspace_xml.Annotation('annotation with comment')
    test_annotation.add_comment("comment", "annotation comment")

    @classmethod
    def setup_class(cls):
        testspace_report = testspace_xml.TestspaceReport()

        for suite in cls.testsuite_list:
            testspace_report.add_test_suite(suite)

        example_suite = testspace_report.get_or_add_test_suite('Example Suite')
        example_suite.add_link_annotation(path='https://help.testspace.com')
        example_suite.add_string_buffer_annotation(
            'Suite string annotation as file', string_buffer=cls.string_buffer)
        example_suite.add_text_annotation(
            'Suite Text Annotation', description='This is a string annotation only')
        example_suite.add_file_annotation('tests/report_v1.xsd', file_path='tests/report_v1.xsd')
        example_suite.add_custom_metric('suite stats', '0, 3, 4')
        example_suite.add_annotation(cls.test_annotation)
        example_suite.set_duration_ms(cls.duration)

        test_case = testspace_xml.TestCase('passing case 1', 'passed')
        for annotation in cls.annotation_tuple:
            test_case.add_text_annotation(
                annotation[0], level=annotation[1], description=annotation[2])
        example_suite.add_test_case(test_case)

        test_case = testspace_xml.TestCase('passing case 2', 'passed')
        test_case.add_file_annotation('tests/report_v1.xsd', file_path='tests/report_v1.xsd')
        test_case.add_file_annotation('report_v1.xsd', file_path='/report_v1.xsd')
        test_case.add_string_buffer_annotation(
            'Case string annotation as file', string_buffer=cls.string_buffer)
        test_case.add_link_annotation(path=r'\\machine/public')
        test_case.add_info_annotation(cls.annotation_tuple[0][2])
        test_case.add_error_annotation(cls.annotation_tuple[1][2])
        test_case.add_warning_annotation(cls.annotation_tuple[2][2])
        test_case.set_duration_ms(cls.duration)
        example_suite.add_test_case(test_case)

        test_case = testspace_xml.TestCase('failing case 1')
        test_case.fail('failing testcase')  # adds annotation to testcase
        test_case.add_custom_metric('suite stats', '0, 3, 4')
        test_case.add_annotation(cls.test_annotation)
        example_suite.add_test_case(test_case)

        test_case = testspace_xml.TestCase('not_applicable 1')
        test_case.set_status('not_applicable')
        example_suite.add_test_case(test_case)

        testspace_report.write_xml('testspace.xml', to_pretty=True)

        xml_file = open('testspace.xml', 'r')
        testspace_xml_string = xml_file.read()
        xml_file.close()

        cls.testspace_xml_root = etree.fromstring(testspace_xml_string)

    @classmethod
    def teardown_class(cls):
        """ teardown any state that was previously setup with a call to
        setup_class.
        """
        os.remove('testspace.xml')

    def test_number_testsuites(self):
        test_suites = self.testspace_xml_root.xpath("//test_suite")
        assert len(test_suites) is 5

    def test_testsuites_order(self):
        test_suites = self.testspace_xml_root.xpath("//test_suite")
        for idx, tests_suite in enumerate(test_suites):
            assert tests_suite.get('name') == self.testsuite_list[idx]

    def test_number_testsuite_annotations(self):
        test_suites = self.testspace_xml_root.xpath("//test_suite/annotation")
        assert len(test_suites) is 5

    def test_testsuite_duration(self):
        suite_element = self.testspace_xml_root.xpath("//test_suite[@duration]")
        assert float(suite_element[0].attrib['duration']) == self.duration

    def test_number_testcases(self):
        test_cases = self.testspace_xml_root.xpath("//test_suite/test_case")
        assert len(test_cases) is 4

    def test_number_passed_testcases(self):
        test_cases = self.testspace_xml_root.xpath("//test_suite/test_case[@status='passed']")
        assert len(test_cases) is 2

    def test_number_failed_testcases(self):
        test_cases = self.testspace_xml_root.xpath("//test_suite/test_case[@status='failed']")
        assert len(test_cases) is 1

    def test_number_not_applicable_testcases(self):
        test_cases = self.testspace_xml_root.xpath(
            "//test_suite/test_case[@status='not_applicable']")
        assert len(test_cases) is 1

    def test_number_testcase_annotations(self):
        test_cases = self.testspace_xml_root.xpath("//test_suite/test_case/annotation")
        assert len(test_cases) is 12

    def test_number_testcase_file_annotations(self):
        test_cases = self.testspace_xml_root.xpath("//test_suite/test_case/annotation[@file]")
        assert len(test_cases) is 2

    def test_number_testcase_annotation_comments(self):
        test_cases = self.testspace_xml_root.xpath("//test_suite/test_case/annotation/comment")
        assert len(test_cases) is 1

    def test_annotation_order(self):
        annotations = self.testspace_xml_root.xpath(
            "//test_suite/test_case[@name='passing case 1']/annotation")
        for idx, annotation in enumerate(annotations):
            assert annotation.get('name') == self.annotation_tuple[idx][0]

    def test_testcase_duration(self):
        suite_element = self.testspace_xml_root.xpath(
            "//test_suite/test_case[@name='passing case 2']")
        assert float(suite_element[0].attrib['duration']) == self.duration

    def test_validate_xsd(self):
        assert xml_validator(etree.tostring(self.testspace_xml_root), 'tests/report_v1.xsd')


def xml_validator(some_xml_string, xsd_file):
    try:
        schema = etree.XMLSchema(file=xsd_file)
        parser = objectify.makeparser(schema=schema)
        objectify.fromstring(some_xml_string, parser)
    except XMLSyntaxError:
        return False
    return True
