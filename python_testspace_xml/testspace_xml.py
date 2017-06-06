from __future__ import print_function
import base64
import gzip
import os
import io
from io import BytesIO
import os.path
import sys
from xml.dom.minidom import parseString


def make_file_href_link(file_path):
    return "<a href='file://" + file_path.replace('\\', '/') + "'>" + file_path + '</a>'


class CustomData:
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def write_xml(self, parent_element, dom):
        d_elem = dom.createElement('custom_data')
        d_elem.setAttribute('name', self.name)
        cdata = dom.createCDATASection(self.value)
        d_elem.appendChild(cdata)
        parent_element.appendChild(d_elem)


class AnnotationComment:
    def __init__(self, name, comment):
        self.name = name
        self.comment = comment


class Annotation:
    def __init__(self, name='unknown', level='info', description='',
                 file_path=None, mime_type='text/plain'):
        self.name = name
        self.level = level
        self.description = description
        self.mimeType = mime_type
        self.file_path = file_path
        self.comments = []

    def add_comment(self, name, comment):
        comment = AnnotationComment(name, comment)
        self.comments.append(comment)

    def write_xml(self, parent_element, dom):
        annotation = dom.createElement("annotation")
        annotation.setAttribute("description", self.description)
        annotation.setAttribute("level", self.level)
        annotation.setAttribute("name", self.name)

        if self.file_path is not None:
            if not os.path.isfile(self.file_path):
                ta = Annotation(self.file_path, level='error')
                ta.description = 'File: ' + self.file_path + ' not found.'
                for com in self.comments:
                    ta.comments.append(com)
                ta.write_xml(parent_element, dom)
                return
            else:
                annotation.setAttribute("link_file", "false")
                annotation.setAttribute("file", "file://" + self.file_path)
                annotation.setAttribute("mime_type", self.mimeType)
                with io.open(self.file_path, 'rb') as inFile:
                    out = BytesIO()
                    with gzip.GzipFile(fileobj=out, mode="wb") as f:
                        f.writelines(inFile)
                    f.close()
                    gzip_data = out.getvalue()
                    b64_data = base64.b64encode(gzip_data)
                    b64_data_string = b64_data.decode()
                    cdata = dom.createCDATASection(b64_data_string)
                    annotation.appendChild(cdata)

        # add comments
        for c in self.comments:
            c_elem = dom.createElement('comment')
            c_elem.setAttribute("label", c.name)
            cdata = dom.createCDATASection(c.comment)
            c_elem.appendChild(cdata)
            annotation.appendChild(c_elem)

        parent_element.appendChild(annotation)


class TestCase:
    def __init__(self, name, status='passed'):
        self.name = name
        self.description = ''
        self.status = status
        self.custom_data = []
        self.annotations = []
        self.start_time = ""
        self.duration = 0

    def set_description(self, description):
        self.description = description

    def set_duration_ms(self, duration):
        self.duration = duration

    def set_status(self, status):
        self.status = status

    def set_start_time(self, gmt_string):
        self.start_time = gmt_string

    def fail(self, message):
        self.status = 'failed'
        ta = self.add_text_annotation('FAIL', 'error')
        ta.description = message

    def add_info_annotation(self, message):
        ta = self.add_text_annotation('Info', 'info')
        ta.description = message

    def add_warning_annotation(self, message):
        ta = self.add_text_annotation('Warning', 'warn')
        ta.description = message

    def add_error_annotation(self, message):
        ta = self.add_text_annotation('Error', 'error')
        ta.description = message

    def add_custom_data(self, name, value):
        d = CustomData(name, value)
        self.custom_data.append(d)
        return d

    def add_file_annotation(self, name, level='info', description='',
                            file_path=None, mime_type='text/plain'):
        fa = Annotation(name, level, description, file_path, mime_type)
        self.annotations.append(fa)
        return fa

    def add_text_annotation(self, name, level='info', description=''):
        ta = Annotation(name, level, description)
        self.annotations.append(ta)
        return ta


class TestSuite:
    def __init__(self, name):
        # optional sub-suites
        self.sub_suites = {}
        self.is_root_suite = False
        self.name = name
        self.description = ''
        self.start_time = ''
        self.test_cases = []
        self.custom_data = []
        self.annotations = []

    def add_test_case(self, tc):
        self.test_cases.append(tc)
        return tc

    def get_or_add_test_suite(self, suite_name):
        if not suite_name:
            # write under root suite
            return self.get_or_add_test_suite('uncategorized')
        if suite_name in self.sub_suites.keys():
            return self.sub_suites[suite_name]
        return self.add_test_suite(suite_name)

    def add_test_suite(self, name):
        new_suite = TestSuite(name)
        self.sub_suites[str(name)] = new_suite
        return new_suite

    def add_custom_data(self, name, value):
        d = CustomData(name, value)
        self.custom_data.append(d)
        return d

    def add_file_annotation(self, name, level='info', description='',
                            file_path=None, mime_type='text/plain'):
        fa = Annotation(name, level, description, file_path, mime_type)
        self.annotations.append(fa)
        return fa

    def add_text_annotation(self, name, level='info', description=''):
        ta = Annotation(name, level, description)
        self.annotations.append(ta)
        return ta


class XmlWriter:
    def __init__(self, report):
        self.report = report
        self.dom = parseString('<reporter schema_version="1.0"/>')

    def write(self, target_file_path, to_pretty=False):
        doc_elem = self.dom.documentElement
        self._write_suite(doc_elem, self.report.get_root_suite())
        if target_file_path:
            with open(target_file_path, 'w') as f:
                if to_pretty:
                    f.write(self.dom.toprettyxml())
                else:
                    f.write(self.dom.toxml())
                f.flush()
        else:
            if to_pretty:
                sys.stdout.write(self.dom.toprettyxml())
            else:
                sys.stdout.write(self.dom.toxml())

    def _write_suite(self, parent_node, test_suite):
        # don't explicitly add suite for root suite
        suite_elem = parent_node
        if not test_suite.is_root_suite:
            suite_elem = self.dom.createElement('test_suite')
            suite_elem.setAttribute('name', test_suite.name)
            suite_elem.setAttribute('description', test_suite.description)
            suite_elem.setAttribute('start_time', str(test_suite.start_time))
            parent_node.appendChild(suite_elem)

        for a in test_suite.annotations:
            a.write_xml(suite_elem, self.dom)

        for d in test_suite.custom_data:
            d.write_xml(suite_elem, self.dom)

        for tc in test_suite.test_cases:
            self._write_test_case(suite_elem, tc)

        # write child suites, sort by name
        for ts in sorted(test_suite.sub_suites.keys()):
            self._write_suite(suite_elem, test_suite.sub_suites[ts])

    def _write_test_case(self, parent_node, test_case):
        elem_tc = self.dom.createElement('test_case')

        elem_tc.setAttribute('name', test_case.name)
        elem_tc.setAttribute('description', test_case.description)
        elem_tc.setAttribute('status', test_case.status)
        elem_tc.setAttribute('start_time', test_case.start_time)
        elem_tc.setAttribute('duration', str(test_case.duration))
        parent_node.appendChild(elem_tc)

        for a in test_case.annotations:
            a.write_xml(elem_tc, self.dom)

        for d in test_case.custom_data:
            d.write_xml(elem_tc, self.dom)


class TestspaceReport(TestSuite):
    def __init__(self):
        TestSuite.__init__(self, '__root__')
        self.is_root_suite = True

    def get_root_suite(self):
        return self

    def write_xml(self, outfile=None, to_pretty=False):
        writer = XmlWriter(self)
        writer.write(outfile, to_pretty)
