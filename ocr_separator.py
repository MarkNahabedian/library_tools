# Exploring what the separator elements in trhe djvu.xml files might mean.

# Apparently all the separator elements from the djvu.html files do is
# identify horizontal and vertical ligns in the page image.

from page import whiten


class Separator (object):
    '''Separator represents the contents of a separator element in the djvu XML.'''
    def __init__(self, elt):
        self.thickness = int(elt.attrib['thickness'])
        self.type = elt.attrib['type']
        start = elt.findall('start')[0]
        end = elt.findall('end')[0]
        self.start_x = int(start.attrib['x'])
        self.start_y = int(start.attrib['y'])
        self.end_x = int(end.attrib['x'])
        self.end_y = int(end.attrib['y'])
        if self.start_x == self.end_x:
            if self.start_y == self.end_y:
                self.direction = '.'
            else:
                self.direction = '|'
        else:
            if self.start_y == self.end_y:
                self.direction = '-'
            else:
                self.direction = '*'

    def __str__(self):
        return ('<Separator %d %s [%d,%d] %s [%d,%d]>' % (
            self.thickness, self.type,
            self.start_x, self.start_y, self.direction,
            self.end_x, self.end_y))

    def _eq__(self, other):
        return NotImplemented

    def __lt__(self, other):
        if self.start_y < other.start_y: return True
        if self.start_y > other.start_y: return False
        if self.start_x < other.start_y: return True
        if self.start_x > other.start_y: return False
        return False

    def __gt__(self, other):
        if self.start_y > other.start_y: return True
        if self.start_y < other.start_y: return False
        if self.start_x > other.start_y: return True
        if self.start_x < other.start_y: return False
        return False

    @classmethod
    def page_separators(cls, page):
        o = page.get_ocr_object_element()
        separators = []
        for s in o.iter('separator'):
            separators.append(Separator(s))
        separators.sort()
        return separators

    def draw(self, image, color = (0x00, 0x00, 0x00)):
        count = 0
        if self.direction == '-':
            for x in range(self.start_x, self.end_x):
                image.putpixel((x, self.start_y), color)
        elif self.direction == '|':
            for y in range(self.start_y, self.end_y):
                image.putpixel((self.start_x, y), color)
        else:
            raise Exception("Don't know how to draw separator direction %s" % self.direction)


def list_separators(page):
    separators = Separator.page_separators(page)
    for s in separators:
        print(s)


def show_separators(page):
    '''show_separators displays an image of page with the separators drawn in.'''
    separators = Separator.page_separators(page)
    image = page.image
    background = page.sample_background()
    whiten(image, background[0][0], background[1][0], background[2][0])
    for s in separators:
        s.draw(image, color=(0x00, 0x00, 0xff))
    image.show()

