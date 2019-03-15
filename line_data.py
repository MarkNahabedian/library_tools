
import operator
from functools import reduce
from region import Region
from page import Page
from ocr_xml import text_bounds

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

    @classmethod
    def for_page(cls, page):
        assert isinstance(page, Page)
        parablocks = []
        page_object = page.get_ocr_object_element()
        for ht_index, ht in enumerate(page_object.findall('HIDDENTEXT')):
            for pc_index, pc in enumerate(ht.findall('PAGECOLUMN')):
                for region_index, r in enumerate(pc.findall('REGION')):
                    for para_index, para in enumerate(r.findall('PARAGRAPH')):
                        lines = []
                        for line_index, line in enumerate(para.findall('LINE')):
                            lines.append(LineData(
                                page, ht_index + 1, pc_index + 1,
                                region_index + 1, para_index + 1,
                                line_index + 1,
                                text_bounds(line, page.jp2_region),
                                ' '.join([w.text for w in line.findall('WORD')])
                            ))
                        parablocks.append(ParaBlock.find_type(lines)(lines))
        return parablocks

    @property
    def page_sequence_number(self):
        return self.page.sequence_number

    def position_string(self):
        return ('%d.%d.%d.%d.%d' % (
            self.hiddentext_pos,
            self.pagecolumn_pos,
            self.region_pos,
            self.paragraph_pos,
            self.line_pos))

    def __str__(self):
        return ('<%04d %s %r "%s">' % (
            self.page_sequence_number,
            self.position_string(),
            self.region, self.text))

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

    def __str__(self):
        return('<%s %d lines %r>' % (
            self.__class__.__name__,
            len(self.line_data),
            self.region()))


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
        average_height = (reduce(operator.add,
                                 [ line.region.bottom - line.region.top
                                   for line in lines], 0) /
                          len(lines))
        line_spacings = [ lines[i + 1].region.top - lines[i].region.top
                          for i in range(len(lines) - 1) ]
        if len(line_spacings) > 0:
            average_line_spacing = (reduce(operator.add, line_spacings, 0) /
                                    len(line_spacings))
            for s in line_spacings:
                if abs(s - average_line_spacing) > .05 * average_line_spacing:
                    return None
        return cls

