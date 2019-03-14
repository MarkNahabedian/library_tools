
from page import Page
from ocr_xml import text_bounds

# I think the hierarchy of elements in the djvu.xml file is OBJECT >
# HIDDENTEXT > PAGECOLUMN > REGION > PARAGRAPH > LINE > WORD.

class LineData (object):
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
        lines = []
        page_object = page.get_ocr_object_element()
        for ht_index, ht in enumerate(page_object.findall('HIDDENTEXT')):
            for pc_index, pc in enumerate(ht.findall('PAGECOLUMN')):
                for region_index, r in enumerate(pc.findall('REGION')):
                    for para_index, para in enumerate(r.findall('PARAGRAPH')):
                        for line_index, line in enumerate(para.findall('LINE')):
                            lines.append(LineData(
                                page, ht_index + 1, pc_index + 1,
                                region_index + 1, para_index + 1,
                                line_index + 1,
                                text_bounds(line, page.jp2_region),
                                ' '.join([w.text for w in line.findall('WORD')])
                            ))
        return lines

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

