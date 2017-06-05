from __future__ import print_function
import base64
import gzip
import ntpath
import os
import os.path
import sys
import tempfile
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
    def __init__(self, level, description):
        self.level = level
        self.description = description
        self.name = ''
        self.comments = []

    def add_comment(self, name, comment):
        comment = AnnotationComment(name, comment)
        self.comments.append(comment)


class FileAnnotation(Annotation):
    def __init__(self, file_path, level='info', description='',
                 mime_type='text/plain', delete_file=True):
        Annotation.__init__(self, level, description)
        self.mimeType = mime_type
        self.filePath = file_path
        # self.filePath = os.path.abspath(FilePath)
        # this covers the case where the path ends with a backslash
        self.fileName = ntpath.basename(file_path)
        self.deleteFile = delete_file

    def write_xml(self, parent_element, dom):
        if not os.path.isfile(self.filePath):
            # write as a warning text annotation
            ta = TextAnnotation(self.name or self.fileName, self.level)
            ta.description = 'File: ' + self.filePath + ' not found.'
            for com in self.comments:
                ta.comments.append(com)
            ta.write_xml(parent_element, dom)
            return

        # write as a file annotation
        anno = dom.createElement("annotation")
        anno.setAttribute("default_file_name", "true")
        anno.setAttribute("link_file", "false")
        anno.setAttribute("description", self.description)
        anno.setAttribute("level", self.level)
        anno.setAttribute("file", "file://" + self.filePath)
        anno.setAttribute("mime_type", self.mimeType)
        anno.setAttribute("name", self.name or self.fileName)

        if os.path.isfile(self.filePath):
            # gzip the file
            with open(self.filePath, 'rb') as inFile:
                out_file = tempfile.TemporaryFile()
                gzip_file_path = out_file.name
                out_file.close()
                out_file = gzip.open(gzip_file_path, 'wb')
                out_file.writelines(inFile)
                out_file.close()
                inFile.close()

                # base64 the file
                out_file = open(gzip_file_path, 'rb')
                gzip_data = out_file.read()
                b64_data = base64.standard_b64encode(gzip_data)
                out_file.close()
                os.remove(gzip_file_path)
                cdata = dom.createCDATASection(b64_data)
                anno.appendChild(cdata)

        # add comments
        for c in self.comments:
            c_elem = dom.createElement('comment')
            c_elem.setAttribute("label", c.name)
            cdata = dom.createCDATASection(c.comment)
            c_elem.appendChild(cdata)
            anno.appendChild(c_elem)

        parent_element.appendChild(anno)


class TextAnnotation(Annotation):
    def __init__(self, name, level='info', description=''):
        Annotation.__init__(self, level, description)
        self.name = name

    def write_xml(self, parent_element, dom):
        # write as a file annotation to the root suite
        anno = dom.createElement("annotation")
        anno.setAttribute("description", self.description)
        anno.setAttribute("level", self.level)
        anno.setAttribute("name", self.name)

        # add comments
        for c in self.comments:
            c_elem = dom.createElement('comment')
            c_elem.setAttribute("label", c.name)
            cdata = dom.createCDATASection(c.comment)
            c_elem.appendChild(cdata)
            anno.appendChild(c_elem)

        parent_element.appendChild(anno)


class TestCase:
    def __init__(self, name, status='passed'):
        self.name = name
        self.description = ''
        self.status = status
        self.custom_data = []
        self.annotations = []
        self.start_time = ""
        self.duration = 0
        # path to file with additional diagnostics
        self.diagnostic_file = None
        self.meta_info = ""

    def set_description(self, description):
        self.description = description

    def set_duration_ms(self, duration):
        self.duration = duration

    def fail(self, reason):
        self.status = 'failed'
        ta = self.add_text_annotation('FAIL', 'error')
        ta.description = reason

    def note_info(self, message):
        ta = self.add_text_annotation('Info', 'info')
        ta.description = message

    def note_warn(self, message):
        ta = self.add_text_annotation('Warning', 'warn')
        ta.description = message

    def note_error(self, message):
        ta = self.add_text_annotation('Error', 'error')
        ta.description = message

    def add_custom_data(self, name, value):
        d = CustomData(name, value)
        self.custom_data.append(d)
        return d

    def add_file_annotation(self, file_path, level='info', description='', mime_type='text/plain'):
        fa = FileAnnotation(file_path, level, description, mime_type)
        self.annotations.append(fa)
        return fa

    def add_text_annotation(self, name, level='info', description=''):
        ta = TextAnnotation(name, level, description)
        self.annotations.append(ta)
        return ta

    def set_status(self, status):
        self.status = status

    def set_start_time(self, gmt_string):
        self.start_time = gmt_string


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

    def get_or_add_suite(self, suite_name):
        if not suite_name:
            # write under root suite
            return self.get_or_add_suite('uncategorized')
        if suite_name in self.sub_suites.keys():
            return self.sub_suites[suite_name]
        return self.add_suite(suite_name)

    def add_suite(self, name):
        new_suite = TestSuite(name)
        self.sub_suites[str(name)] = new_suite
        return new_suite

    def add_custom_data(self, name, value):
        d = CustomData(name, value)
        self.custom_data.append(d)
        return d

    def add_file_annotation(self, file_path, level='info', description='',
                            mime_type='text/plain'):
        fa = FileAnnotation(file_path, level, description, mime_type)
        self.annotations.append(fa)
        return fa

    def add_text_annotation(self, name, level='info', description=''):
        ta = TextAnnotation(name, level, description)
        self.annotations.append(ta)
        return ta


class XmlWriter:
    def __init__(self, report):
        self.report = report
        self.dom = parseString('<reporter schema_version="1.0"/>')

    def write(self, target_file_path='', to_pretty=False):
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

    def write_xml(self, outfile, to_pretty=False):
        writer = XmlWriter(self)
        writer.write(outfile, to_pretty)
