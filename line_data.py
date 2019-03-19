
import operator
from functools import reduce
from region import Region
# from page import Page
from ocr_xml import text_bounds
from flags import *
from characters import CHARACTER_FLAGS


# I think the hierarchy of elements in the djvu.xml file is OBJECT >
# HIDDENTEXT > PAGECOLUMN > REGION > PARAGRAPH > LINE > WORD.

class LineData (object):
    '''LineData encapsulates data associated with a single line of OCRed
    text.  We hope it can be used to distinguish normal text from page
    headings, page footers, text within images and other text.'''

    def __init__(self, page, hiddentext_pos, pagecolumn_pos,
                 region_pos, paragraph_pos, line_pos, region, text):
        self.page = page
        # hiddentext_pos = 7 meand that the HIDDENTEXT ancestor of
        # this line is the seventh (1 based) HIDDENTEXT element within
        # its contaiing OBJECT element.
        self.hiddentext_pos = hiddentext_pos
        self.pagecolumn_pos = pagecolumn_pos
        self.region_pos = region_pos
        self.paragraph_pos = paragraph_pos
        self.line_pos = line_pos
        self.region = region
        self.text = text.encode('ascii', 'ignore')
        self.flags = 0
        if self.region.width >= 0.7 * self.page.jp2_width:
            self.flags |= LINE_FULL_WIDTH
        for c in text:
            self.flags |= CHARACTER_FLAGS[c]
   

    @classmethod
    def for_page(cls, page, page_object=None):
        # assert isinstance(page, Page)
        parablocks = []
        if page_object == None:
            page_object = page.get_ocr_object_element()
        first_line = None
        last_line = None
        for ht_index, ht in enumerate(page_object.findall('HIDDENTEXT')):
            for pc_index, pc in enumerate(ht.findall('PAGECOLUMN')):
                for region_index, r in enumerate(pc.findall('REGION')):
                    for para_index, para in enumerate(r.findall('PARAGRAPH')):
                        lines = []
                        for line_index, line in enumerate(para.findall('LINE')):
                            ld = LineData(
                                page, ht_index + 1, pc_index + 1,
                                region_index + 1, para_index + 1,
                                line_index + 1,
                                text_bounds(line, page.jp2_region),
                                ' '.join([w.text for w in line.findall('WORD')])
                            )
                            if first_line == None:
                                first_line = ld
                            last_line = ld
                            lines.append(ld)
                        if len(lines) > 0:
                            lines[0].flags |= PARA_FIRST_LINE
                            lines[-1].flags |= PARA_LAST_LINE
                        parablocks.append(ParaBlock(lines))
        if first_line:
            first_line.flags |= PAGE_FIRST_LINE
            last_line.flags |= PAGE_LAST_LINE
        return parablocks

    @property
    def page_sequence_number(self):
        return self.page.sequence_number

    @property
    def length(self):
        return len(self.text)

    @property
    def average_char_width(self):
        return self.region.width / self.length

    def position_string(self):
        return ('%d.%d.%d.%d.%d' % (
            self.hiddentext_pos,
            self.pagecolumn_pos,
            self.region_pos,
            self.paragraph_pos,
            self.line_pos))

    def __str__(self):
        return ('<%04d %s %r %s "%s">' % (
            self.page_sequence_number,
            self.position_string(),
            self.region,
            bit_string(self.flags),
            self.text))

    def same_paragraph(sef, other):
        '''same_paragraph returns true if the lines are in the same paragraph.'''
        return (self.page == other.page and
                self.hiddentext_pos == other.hiddentext_pos and
                self.pagecolumn_pos == other.pagecolumn_pos and
                self.region_pos == other.region_pos and
                self.paragraph_pos == other.paragraph_pos)


class ParaBlock (object):
    '''ParaBlock represents a sequence of lines that are contained in the
    same PARAGRAPH element.  We use it to determine if the contents of
    the ParaBlock are normal text or special in some way.
    
    Subclasses represent explicitly recognized paragraph roles.'''

    def __init__(self, lines):
        self.line_data = lines

    # ParaBlock is the default implementation if none of its
    # subclasses test_type methods is satisfied.
    @classmethod
    def test_type(cls, lines):
        return cls

    @classmethod
    def find_type(cls, lines):
        for subclass in cls.__subclasses__():
            t = subclass.find_type(lines)
            if t != None:
                return t
        return cls.test_type(lines)
    
    def region(self):
        return Region.rectangular_hull(
            [ld.region for ld in self.line_data])

    def show_lines(self):
        for l in self.line_data:
            print(str(l))

    def position_string(self):
        line = self.line_data[0]
        return ('%d.%d.%d.%d' % (
            line.hiddentext_pos,
            line.pagecolumn_pos,
            line.region_pos,
            line.paragraph_pos))

    def __str__(self):
        return('<%s %s, %d lines %r %d %d>' % (
            self.__class__.__name__,
            self.position_string(),
            len(self.line_data),
            self.region(),
            average_line_height(self.line_data),
            average_top_delta(self.line_data)))


class PageNumberParaBlock(ParaBlock):
    '''PageNumberParaBlock contains a page number.'''

    @classmethod
    def test_type(cls, lines):
        if len(lines) != 1:
            return None
        # ??? How dowe tell if it's the first or last line in the page?
        # Does it match the page number
        line = lines[0]
        if str(line.page.page_number) != line.text:
            return None
        return cls
    

class BodyTextParaBlock (ParaBlock):
    '''BodyTextParaBlock is a ParaBlock containing normal body text from
    the book.'''

    @classmethod
    def test_type(cls, lines):
        if len(lines) <= 1:
            return None
        line_spacings = [ lines[i + 1].region.top - lines[i].region.top
                          for i in range(len(lines) - 1) ]
        if len(line_spacings) > 0:
            average_line_spacing = (reduce(operator.add, line_spacings, 0) /
                                    len(line_spacings))
            for s in line_spacings:
                if abs(s - average_line_spacing) > .05 * average_line_spacing:
                    return None
        return cls


def average_top_delta(lines):
    return (lines[-1].region.top - lines[0].region.top) / len(lines)


def average_line_height(lines):
    l = len(lines)
    if l == 0:
        return None
    return (reduce(operator.add,
                   [ line.region.bottom - line.region.top
                     for line in lines], 0) /
            l)


