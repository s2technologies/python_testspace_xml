from __future__ import print_function
import base64
import gzip
import os
import os.path
import io
from io import BytesIO
import re
import sys
from xml.dom.minidom import parseString


class CustomData:
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def write_xml(self, parent_element, dom):
        d_elem = dom.createElement('custom_data')
        d_elem.setAttribute('name', XmlWriter.invalid_xml_remove(self.name))
        cdata = dom.createCDATASection(self.value)
        d_elem.appendChild(cdata)
        parent_element.appendChild(d_elem)


class AnnotationComment:
    def __init__(self, name, comment):
        self.name = name
        self.comment = comment


class Annotation:
    def __init__(self, name='unknown', level='info', description=''):
        self.name = name
        self.level = level
        self.description = description
        self.mime_type = None
        self.file_path = None
        self.link_file = False
        self.gzip_data = None
        self.comments = []

    def add_comment(self, name, comment):
        comment = AnnotationComment(name, comment)
        self.comments.append(comment)

    def set_file(self, file_path, mime_type='octet/stream'):
        self.link_file = False
        self.file_path = file_path
        self.mime_type = mime_type
        if file_path:
            if not os.path.isfile(self.file_path):
                self.level = 'error'
                self.description = 'File not found: {0} '.format(self.file_path)
                self.file_path = None
                return

            with io.open(self.file_path, 'rb') as in_file_obj:
                out = BytesIO()
                with gzip.GzipFile(fileobj=out, mode='wb') as out_file_obj:
                    out_file_obj.writelines(in_file_obj)
                self.gzip_data = out.getvalue()

    def set_buffer(self, buffer, mime_type='octet/stream', file_name=None):
        self.link_file = False
        self.file_path = file_name
        self.mime_type = mime_type
        out = BytesIO()
        with gzip.GzipFile(fileobj=out, mode='wb') as out_file_obj:
            out_file_obj.write(buffer)
        self.gzip_data = out.getvalue()

    def set_link(self, url):
        self.link_file = True
        self.gzip_data = None
        self.mime_type = None
        if re.match(r'^(https?|file)://', url):
            self.file_path = url
            return

        prefix = ''
        if url.startswith('\\'): # Windows network path
            url = url.replace('\\', '/')
        elif re.match(r'^[:alpha:]:', url): # Windows local path
            url = url.replace('\\', '/')
            prefix = '/'

        if not url.startswith('//'):
            prefix = '//'

        self.file_path = 'file:{0}{1}'.format(prefix, url)

    def write_xml(self, parent_element, dom):
        annotation = dom.createElement('annotation')
        annotation.setAttribute('name', XmlWriter.invalid_xml_remove(self.name))
        annotation.setAttribute('level', self.level)
        if self.description:
            annotation.setAttribute('description', XmlWriter.invalid_xml_remove(self.description))

        if self.gzip_data:
            annotation.setAttribute('link_file', 'false')
            if self.file_path:
                annotation.setAttribute('file_name', os.path.basename(self.file_path))
            annotation.setAttribute('mime_type', self.mime_type)
            b64_data = base64.b64encode(self.gzip_data)
            b64_data_string = b64_data.decode()
            cdata = dom.createCDATASection(b64_data_string)
            annotation.appendChild(cdata)
        elif self.link_file and self.file_path:
            annotation.setAttribute('link_file', 'true')
            annotation.setAttribute('file', self.file_path)

        # add comments
        for comment in self.comments:
            c_elem = dom.createElement('comment')
            c_elem.setAttribute('label', XmlWriter.invalid_xml_remove(comment.name))
            cdata = dom.createCDATASection(comment.comment)
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
        self.start_time = None
        self.duration = 0

    def set_description(self, description):
        self.description = description

    def set_start_time(self, gmt_string):
        self.start_time = gmt_string

    def set_duration(self, duration_ms):
        self.duration = duration_ms if duration_ms >= 0 else 0

    set_duration_ms = set_duration

    def set_status(self, status):
        self.status = status

    def fail(self, message):
        self.status = 'failed'
        self.add_text_annotation('Error', 'error', message)

    def block(self, message):
        self.status = 'errored'
        self.add_text_annotation('Fatal', 'fatal', message)

    def add_info_annotation(self, message):
        return self.add_text_annotation('Info', 'info', message)

    def add_warning_annotation(self, message):
        return self.add_text_annotation('Warning', 'warn', message)

    def add_error_annotation(self, message):
        return self.add_text_annotation('Error', 'error', message)

    def add_file_annotation(self, name, file_path, level='info', description='', mime_type='text/plain'):
        fa = self.add_text_annotation(name, level, description)
        fa.set_file(file_path, mime_type)
        return fa

    def add_string_buffer_annotation(self, name, string_buffer, level='info', description='', mime_type='text/plain'):
        ba = self.add_text_annotation(name, level, description)
        ba.set_buffer(string_buffer.encode(), mime_type)
        return ba

    def add_link_annotation(self, url, level='info', description='', name=None):
        if not name:
            name = url
        la = self.add_text_annotation(name, level, description)
        la.set_link(url)
        return la

    def add_text_annotation(self, name, level='info', description=''):
        text_annotation = Annotation(name, level, description)
        self.annotations.append(text_annotation)
        return text_annotation

    def add_custom_metric(self, name, value):
        custom_data = CustomData(name, value)
        self.custom_data.append(custom_data)
        return custom_data

    def add_annotation(self, annotation):
        self.annotations.append(annotation)


class TestSuite:
    def __init__(self, name):
        # optional sub-suites
        self.sub_suites = []
        self.is_root_suite = False
        self.name = name
        self.description = ''
        self.duration = 0
        self.start_time = None
        self.test_cases = []
        self.custom_data = []
        self.annotations = []

    def set_description(self, description):
        self.description = description

    def set_start_time(self, gmt_string):
        self.start_time = gmt_string

    def set_duration(self, duration_ms):
        self.duration = duration_ms if duration_ms >= 0 else 0

    set_duration_ms = set_duration

    def add_test_case(self, tc):
        self.test_cases.append(tc)
        return tc

    def get_or_add_test_suite(self, suite_name):
        if not suite_name:
            # write under root suite
            return self.get_or_add_test_suite('uncategorized')
        for suite in self.sub_suites:
            if suite_name == suite.name:
                return suite
        return self.add_test_suite(suite_name)

    def add_test_suite(self, ts_or_name):
        if isinstance(ts_or_name, str) or (sys.version_info < (3,0) and isinstance(ts_or_name, unicode)):
            ts_or_name = TestSuite(ts_or_name)
        self.sub_suites.append(ts_or_name)
        return ts_or_name

    def add_file_annotation(self, name, file_path, level='info', description='', mime_type='text/plain'):
        fa = self.add_text_annotation(name, level, description)
        fa.set_file(file_path, mime_type)
        return fa

    def add_string_buffer_annotation(self, name, string_buffer, level='info', description='', mime_type='text/plain'):
        ba = self.add_text_annotation(name, level, description)
        ba.set_buffer(string_buffer.encode(), mime_type)
        return ba

    def add_link_annotation(self, url, level='info', description='', name=None):
        if not name:
            name = url
        la = self.add_text_annotation(name, level, description)
        la.set_link(url)
        return la

    def add_text_annotation(self, name, level='info', description=''):
        text_annotation = Annotation(name, level, description)
        self.annotations.append(text_annotation)
        return text_annotation

    def add_custom_metric(self, name, value):
        d = CustomData(name, value)
        self.custom_data.append(d)
        return d

    def add_annotation(self, annotation):
        self.annotations.append(annotation)


class XmlWriter:
    def __init__(self, report):
        self.report = report

        if not report.product_version:
            reporter_string = '<reporter schema_version="1.0"/>'
        else:
            reporter_string = '<reporter schema_version="1.0" product_version="{0}"/>'\
                .format(report.product_version)

        self.dom = parseString(reporter_string)

    def write(self, out_file, to_pretty=False):
        doc_elem = self.dom.documentElement
        self._write_suite(doc_elem, self.report.get_root_suite())
        xml_attrs = {'encoding': 'utf-8'}
        if to_pretty:
            xml_attrs.update(indent='\t', newl='\n')

        if not out_file:
            out_file = sys.stdout

        if isinstance(out_file, str) or (sys.version_info < (3,0) and isinstance(out_file, unicode)):
            file_attrs = {}
            if sys.version_info > (3,0):
                file_attrs = {'encoding': 'utf-8'}
            with open(out_file, 'w', **file_attrs) as file_obj:
                self.dom.writexml(file_obj, **xml_attrs)
        else:
            self.dom.writexml(out_file, **xml_attrs)

    def _write_suite(self, parent_node, test_suite):
        # don't explicitly add suite for root suite
        suite_elem = parent_node
        if not test_suite.is_root_suite:
            suite_elem = self.dom.createElement('test_suite')
            suite_elem.setAttribute('name', XmlWriter.invalid_xml_remove(test_suite.name))
            if test_suite.description:
                suite_elem.setAttribute('description', XmlWriter.invalid_xml_remove(test_suite.description))
            if test_suite.start_time:
                suite_elem.setAttribute('start_time', test_suite.start_time)
            if test_suite.duration > 0:
                suite_elem.setAttribute('duration', str(test_suite.duration))
            parent_node.appendChild(suite_elem)

        for a in test_suite.annotations:
            a.write_xml(suite_elem, self.dom)

        for d in test_suite.custom_data:
            d.write_xml(suite_elem, self.dom)

        for tc in test_suite.test_cases:
            self._write_test_case(suite_elem, tc)

        # write child suites
        for sub_suite in test_suite.sub_suites:
            self._write_suite(suite_elem, sub_suite)

    def _write_test_case(self, parent_node, test_case):
        elem_tc = self.dom.createElement('test_case')

        elem_tc.setAttribute('name', XmlWriter.invalid_xml_remove(test_case.name))
        if test_case.description:
            elem_tc.setAttribute('description', XmlWriter.invalid_xml_remove(test_case.description))
        elem_tc.setAttribute('status', test_case.status)
        if test_case.start_time:
            elem_tc.setAttribute('start_time', test_case.start_time)
        elem_tc.setAttribute('duration', str(test_case.duration))
        parent_node.appendChild(elem_tc)

        for a in test_case.annotations:
            a.write_xml(elem_tc, self.dom)

        for d in test_case.custom_data:
            d.write_xml(elem_tc, self.dom)

    @staticmethod
    def invalid_xml_remove(string_to_clean):
        if not isinstance(string_to_clean, str):
            if sys.version_info > (3,0) or not isinstance(string_to_clean, unicode):
                return ''

        # http://stackoverflow.com/questions/1707890/fast-way-to-filter-illegal-xml-unicode-chars-in-python
        illegal_unichrs = [
            (0x00, 0x08), (0x0B, 0x1F), (0x7F, 0x84), (0x86, 0x9F),
            (0xD800, 0xDFFF), (0xFDD0, 0xFDDF), (0xFFFE, 0xFFFF),
            (0x1FFFE, 0x1FFFF), (0x2FFFE, 0x2FFFF), (0x3FFFE, 0x3FFFF),
            (0x4FFFE, 0x4FFFF), (0x5FFFE, 0x5FFFF), (0x6FFFE, 0x6FFFF),
            (0x7FFFE, 0x7FFFF), (0x8FFFE, 0x8FFFF), (0x9FFFE, 0x9FFFF),
            (0xAFFFE, 0xAFFFF), (0xBFFFE, 0xBFFFF), (0xCFFFE, 0xCFFFF),
            (0xDFFFE, 0xDFFFF), (0xEFFFE, 0xEFFFF), (0xFFFFE, 0xFFFFF),
            (0x10FFFE, 0x10FFFF)]

        if sys.version_info > (3,0):
            illegal_ranges = ['%s-%s' % (chr(low), chr(high))
                            for (low, high) in illegal_unichrs
                            if low < sys.maxunicode]

            illegal_xml_pattern = '[%s]' % ''.join(illegal_ranges)
        else:
            illegal_ranges = [u'%s-%s' % (unichr(low), unichr(high))
                            for (low, high) in illegal_unichrs
                            if low < sys.maxunicode]

            illegal_xml_pattern = u'[%s]' % u''.join(illegal_ranges)

        illegal_xml_re = re.compile(illegal_xml_pattern)
        return illegal_xml_re.sub('', string_to_clean)


class TestspaceReport(TestSuite):
    def __init__(self):
        TestSuite.__init__(self, '__root__')
        self.is_root_suite = True
        self.product_version = None

    def get_root_suite(self):
        return self

    def set_product_version(self, product_version):
        self.product_version = product_version

    def write_xml(self, out_file, to_pretty=False):
        writer = XmlWriter(self)
        writer.write(out_file, to_pretty)
