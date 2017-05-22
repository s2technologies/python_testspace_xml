from __future__ import print_function
import base64
import gzip
import ntpath
import os
import os.path
import sys
import tempfile
from xml.dom.minidom import parseString


def MakeFileHrefLink(FilePath):
    return "<a href='file://" + FilePath.replace('\\', '/') + "'>" + FilePath + '</a>'


class CustomData:
    def __init__(self, Name, Value):
        self.name = Name
        self.value = Value

    def WriteXml(self, parentElement, dom):
        dElem = dom.createElement('custom_data')
        dElem.setAttribute('name', self.name)
        cdata = dom.createCDATASection(self.value)
        dElem.appendChild(cdata)
        parentElement.appendChild(dElem)


class AnnotationComment:
    def __init__(self, Name, Comment):
        self.name = Name
        self.comment = Comment


class Annotation:
    def __init__(self, Level, Description):
        self.level = Level
        self.description = Description
        self.name = ''
        self.comments = []

    def AddComment(self, Name, Comment):
        comment = AnnotationComment(Name, Comment)
        self.comments.append(comment)

    def CleanUp(self):
        pass


class FileAnnotation(Annotation):
    def __init__(self, FilePath, Level='info', Description='', MimeType='text/plain', DeleteFile=True):
        Annotation.__init__(self, Level, Description)
        self.mimeType = MimeType
        self.filePath = FilePath
        # self.filePath = os.path.abspath(FilePath)
        # this covers the case where the path ends with a backslash
        self.fileName = ntpath.basename(FilePath)
        self.deleteFile = DeleteFile

    def CleanUp(self):
        if self.deleteFile and os.path.isfile(self.filePath):
            os.remove(self.filePath)

    def WriteXml(self, parentElement, dom):
        if not os.path.isfile(self.filePath):
            # write as a warning text annotation
            ta = TextAnnotation(self.name or self.fileName, self.level)
            ta.description = 'File: ' + self.filePath + ' not found.'
            for com in self.comments:
                ta.comments.append(com)
            ta.WriteXml(parentElement, dom)
            return

        # write as a file annotation
        anno = dom.createElement("annotation")
        anno.setAttribute("default_file_name", "true")
        anno.setAttribute("link_file", "false")
        anno.setAttribute("description", XmlWriter.FixLineEnds(self.description))
        anno.setAttribute("level", self.level)
        anno.setAttribute("file", "file://" + self.filePath)
        anno.setAttribute("mime_type", self.mimeType)
        anno.setAttribute("name", self.name or self.fileName)

        if os.path.isfile(self.filePath):
            # gzip the file
            with open(self.filePath, 'rb') as inFile:
                outFile = tempfile.TemporaryFile()
                gzipFilePath = outFile.name
                outFile.close()
                outFile = gzip.open(gzipFilePath, 'wb')
                outFile.writelines(inFile)
                outFile.close()
                inFile.close()

                # base64 the file
                outFile = open(gzipFilePath, 'rb')
                gzipData = outFile.read()
                b64Data = base64.standard_b64encode(gzipData)
                outFile.close()
                os.remove(gzipFilePath)
                cdata = dom.createCDATASection(b64Data)
                anno.appendChild(cdata)

        # add comments
        for c in self.comments:
            cElem = dom.createElement('comment')
            cElem.setAttribute("label", c.name)
            cdata = dom.createCDATASection(c.comment)
            cElem.appendChild(cdata)
            anno.appendChild(cElem)

        parentElement.appendChild(anno)


class TextAnnotation(Annotation):
    def __init__(self, Name, Level='info', Description=''):
        Annotation.__init__(self, Level, Description)
        self.name = Name

    def WriteXml(self, parentElement, dom):
        # write as a file annotation to the root suite
        anno = dom.createElement("annotation")
        anno.setAttribute("description", XmlWriter.FixLineEnds(self.description))
        anno.setAttribute("level", self.level)
        anno.setAttribute("name", self.name)

        # add comments
        for c in self.comments:
            cElem = dom.createElement('comment')
            cElem.setAttribute("label", c.name)
            cdata = dom.createCDATASection(c.comment)
            cElem.appendChild(cdata)
            anno.appendChild(cElem)

        parentElement.appendChild(anno)


class TestCase:
    def __init__(self, ParentSuite, Name, Status='passed', NameDeduped=False):
        self.name = Name  # instance variable unique to each instance
        # true if name has split name appended to de-dupe
        self.nameDeduped = NameDeduped
        self.description = ''
        self.status = Status
        self.customData = []
        self.annotations = []
        self.parentSuite = ParentSuite
        self.startTime = ""
        self.duration = 0
        # path to file with additional diagnostics
        self.diagnosticFile = None
        self.splitName = ""
        self.metaInfo = ""

    def CleanUp(self):
        for a in self.annotations:
            a.CleanUp()

    # all chars up to first '_'
    # or None if no '_'
    def GetFirstNameSegment(self):
        n = self.name.split('_')[0]
        if n == self.name:
            return None
        else:
            # testspace does not differentiate on case; same name. different case
            # will be considered a duplicate
            return n.lower()

    def SetDescription(self, Description):
        self.description = Description

    def SetDurationMs(self, Duration):
        self.duration = Duration

    def Fail(self, Reason):
        self.status = 'failed'
        ta = self.AddTextAnnotation('FAIL', 'error')
        ta.description = Reason

    def NoteInfo(self, Message):
        ta = self.AddTextAnnotation('Info', 'info')
        ta.description = Message

    def NoteWarn(self, Message):
        ta = self.AddTextAnnotation('Warning', 'warn')
        ta.description = Message

    def NoteError(self, Message):
        ta = self.AddTextAnnotation('Error', 'error')
        ta.description = Message

    def AddCustomData(self, Name, Value):
        d = CustomData(Name, Value)
        self.customData.append(d)
        return d

    def AddFileAnnotation(self, FilePath, Level='info', Description='', MimeType='text/plain'):
        fa = FileAnnotation(FilePath, Level, Description, MimeType)
        self.annotations.append(fa)
        return fa

    def AddTextAnnotation(self, Name, Level='info', Description=''):
        ta = TextAnnotation(Name, Level, Description)
        self.annotations.append(ta)
        return ta

    def SetStatus(self, status):
        if status == 'passed':
            self.parentSuite.passed += 1
        elif status == 'failed':
            self.parentSuite.failed += 1
        elif status == 'not_applicable':
            self.parentSuite.notApplicable += 1
        elif status == 'in_progress':
            self.parentSuite.inProgress += 1
        else:
            raise Exception('unknown tests status')

        self.status = status

    def SetStartTime(self, GmtString):
        if not self.parentSuite.startTime:
            self.parentSuite.startTime = GmtString
        self._startTime = GmtString


class TestSuite:
    def __init__(self, Name):

        # optional sub-suites
        self.subSuites = {}

        self.isRootSuite = False
        self.name = Name
        self.description = ''
        self.passed = 0
        self.failed = 0
        self.notApplicable = 0
        self.inProgress = 0
        self.startTime = ''
        self.testCases = []
        self.customData = []
        self.annotations = []
        # used for efficiently de-duping testcase names
        self.tcNameDict = {}

    def CleanUp(self):
        for s in self.subSuites:
            self.GetOrAddSuite(s).CleanUp()
        for tc in self.testCases:
            tc.CleanUp()
        for a in self.annotations:
            a.CleanUp()

    def AddTestCase(self, tc):
        tc.name = self.GetUniqueTestCaseName(tc.name)
        self.UpdateRollUps(tc)
        self.testCases.append(tc)
        self.tcNameDict[tc.name] = ''
        return tc

    def GetUniqueTestCaseNamex(self, ProposedName):
        # check for duplicate name
        n = 0
        newName = ProposedName
        done = False
        while not done:
            done = True
            for t in self.testCases:
                if t.name == newName:
                    n += 1
                    newName = ProposedName + '(' + str(n) + ')'
                    done = False
                    break
        return newName

    def GetUniqueTestCaseName(self, ProposedName):
        newName = ProposedName
        n = 0
        while newName in self.tcNameDict:
            n += 1
            newName = ProposedName + '(' + str(n) + ')'
        return newName

    def UpdateRollUps(self, tc):
        if tc.status == 'passed':
            self.passed += 1
        elif tc.status == 'failed':
            self.failed += 1
        elif tc.status == 'not_applicable':
            self.notApplicable += 1
        elif tc.status == 'in_progress':
            self.inProgress += 1
        elif True:
            assert (False)

    def GetOrAddSuite(self, suiteName):
        if not suiteName:
            # write under root suite
            return self.GetOrAddSuite('uncategorized')
        if suiteName in self.subSuites.keys():
            return self.subSuites[suiteName]
        return self.AddSuite(suiteName)

    def AddSuite(self, Name):
        newSuite = TestSuite(Name)
        self.subSuites[str(Name)] = newSuite
        return newSuite

    def AddCustomData(self, Name, Value):
        d = CustomData(Name, Value)
        self.customData.append(d)
        return d

    def AddFileAnnotation(self, FilePath, Level='info', Description='', MimeType='text/plain', DeleteFile=True):
        fa = FileAnnotation(FilePath, Level, Description, MimeType, DeleteFile)
        self.annotations.append(fa)
        return fa

    def AddTextAnnotation(self, Name, Level='info', Description=''):
        ta = TextAnnotation(Name, Level, Description)
        self.annotations.append(ta)
        return ta


class XmlWriter:
    xmlTemplate = r'''
    <?xml-stylesheet type="text/xsl" xml version="1.0" encoding="UTF-8?>
    <reporter schema_version="1.0">
    </reporter>
    '''
    def __init__(self, Report):
        self.report = Report
        self.dom = parseString(self.xmlTemplate)

    @staticmethod
    def FixLineEnds(s):
        br = '<br/>'
        ss = str(s)
        sss = ss.replace('\r\n', br)
        return sss.replace('\n', br)

    def Write(self, TargetFilePath=''):
        docElem = self.dom.documentElement
        self.WriteSuite(docElem, self.report.GetRootSuite())
        if TargetFilePath:
            with open(TargetFilePath, 'w') as f:
                f.write(self.dom.toprettyxml())
                f.flush()
        else:
            sys.stdout.write(self.dom.toxml())
        # print(self.dom.toprettyxml())
        # print(self.dom.toxml())
        self.CleanUp()

    def CleanUp(self):
        self.report.GetRootSuite().CleanUp()

    def WriteSuite(self, ParentNode, TestSuite):
        # don't explicitly add suite for root suite
        suiteElem = ParentNode
        if not TestSuite.isRootSuite:
            suiteElem = self.dom.createElement('test_suite')
            suiteElem.setAttribute('name', TestSuite.name)
            suiteElem.setAttribute('description', TestSuite.description)
            suiteElem.setAttribute('passed', str(TestSuite.passed))
            suiteElem.setAttribute('failed', str(TestSuite.failed))
            suiteElem.setAttribute('not_applicable', str(TestSuite.notApplicable))
            suiteElem.setAttribute('in_progress', str(TestSuite.inProgress))
            suiteElem.setAttribute('start_time', str(TestSuite.startTime))
            ParentNode.appendChild(suiteElem)

        for a in TestSuite.annotations:
            a.WriteXml(suiteElem, self.dom)

        for d in TestSuite.customData:
            d.WriteXml(suiteElem, self.dom)

        for tc in TestSuite.testCases:
            self.WriteTestCase(suiteElem, tc)

        # write child suites, sort by name
        for ts in sorted(TestSuite.subSuites.keys()):
            self.WriteSuite(suiteElem, TestSuite.subSuites[ts])

    def WriteTestCase(self, ParentNode, TestCase):
        elemTC = self.dom.createElement('test_case')

        elemTC.setAttribute('name', TestCase.name)
        elemTC.setAttribute('description', self.FixLineEnds(TestCase.description))
        elemTC.setAttribute('status', TestCase.status)
        elemTC.setAttribute('start_time', TestCase.startTime)
        elemTC.setAttribute('duration', str(TestCase.duration))
        ParentNode.appendChild(elemTC)

        for a in TestCase.annotations:
            a.WriteXml(elemTC, self.dom)

        for d in TestCase.customData:
            d.WriteXml(elemTC, self.dom)


class TestspaceReport(TestSuite):
    def __init__(self):
        TestSuite.__init__(self, '__root__')
        self.isRootSuite = True

    # def AddTestCase(self, Name, Status='passed', NameDeduped=False):
    #     tc = TestCase(None, Name, Status, NameDeduped)
    #     return AddTestCase(tc)
    #     # todo: check for duplicate test case name and fix

    def GetRootSuite(self):
        return self
