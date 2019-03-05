#!python3

import math
import os
import os.path
import re
import xml.etree.ElementTree as ET
import operator
from functools import reduce
from PIL import Image     # pip install Pillow


class Region (object):
    '''Region is used to describe any rectilinear area of a page.'''

    def __init__(self, left, right, top, bottom):
        self.left = left
        self.right = right
        self.top = top
        self.bottom = bottom

    @property
    def width(self):
        return self.right - self.left

    @property
    def height(self):
        return self.bottom - self.top

    @property
    def area(self):
        return self.width * self.height

    @property
    def rangeX(self):
        return range(self.left, self.right)

    @property
    def rangeY(self):
        return range(self.top, self.bottom)

    def inset(self, left, right, top, bottom):
        '''inset returns a new Region inset from self by the specified amount at each edge.'''
        return Region(self.left + left, self.right - right,
                      self.top + top, self.bottom - bottom)

    def __repr__(self):
        return('page.Region(%d, %d, %d, %d)' % (
            self.left, self.right, self.top, self.bottom))

    def distanceX(self, other):
        return min(abs(self.right - other.left),
                   abs(self.left - other.right))

    def distanceY(self, other):
        return min(abs(self.bottom - other.top),
                   abs(self.top - other.bottom))

    def overlapsX(self, other):
        return ranges_overlap(self.rangeX, other.rangeX)

    def overlapsY(self, other):
        return ranges_overlap(self.rangeY, other.rangeY)


def ranges_overlap(range1, range2):
    return max(range1[0], range2[0]) <= min(range1[-1], range2[-1])


class Book (object):
    '''Book represents a scanned book that was fetched using fetch_pages.py.'''

    def __init__(self, directory):
        '''directory is the directory that was created by fetch_pages.py.'''
        # assert os.path.isdir(directory)
        # ignore terminal slash.
        if os.path.basename(directory) == '':
            self.directory = directory[0:-1]
        else:
            self.directory = directory
        self.directory = os.path.abspath(self.directory)
        self.name_token = os.path.basename(self.directory)
        self.dc_metadata = DublinCoreMetadata(self)
        self.pages = []
        self.max_page_sequence = 0
        jp2dir = self.jp2_directory()
        for filename in os.listdir(jp2dir):
            p = Page(self, os.path.join(jp2dir, filename))
            self.pages.append(p)
            if p.sequence_number > self.max_page_sequence:
                self.max_page_sequence = p.sequence_number
        self.djvu_path = os.path.join(self.directory,
                                      self.name_token + '_djvu.xml')
        tree = ET.parse(self.djvu_path)
        for obj in tree.iter('OBJECT'):
            pm = PageMetadata(obj)
            if pm.sequence_number == None:
                raise Exception('No sequence number: %r', pm)
            p = self.page_for_sequence_number(pm.sequence_number)
            if p:
                p.metadata = pm
            else:
                raise Exception('No page %d' % pm.sequence)

    def __str__(self):
        return '<%s.%s %s>' % (
            self.__class__.__module__,
            self.__class__.__name__,
            self.name_token)

    def page_for_sequence_number(self, sequence):
        '''page_for_sequence_number finds and returns the Page with the specified sequence number.'''
        for page in self.pages:
            if page.sequence_number == sequence:
                return page
        return None

    def page_for_page_number(self, page_number):
        '''page_for_page_number currently only works with numbered pages.'''
        for page in self.pages:
            md = page.metadata
            if not md:
                continue
            if md.page_number == page_number:
                return page
        return None

    def jp2_directory(self):
        return os.path.join(self.directory, 'pages', self.name_token + '_jp2')

    def thumbnails_dir(self):
        return os.path.join(self.directory, 'thumbnails')

    def make_thumbnails(self):
        td = self.thumbnails_dir()
        try:
            os.mkdir(td)
        except OSError:
            pass
        for page in self.pages:
            img = page.load_image()
            img.thumbnail((128, 128))
            img.save(page.thumbnail_path(), 'JPEG')

    def make_image_highlite_thumbnails(self):
        td = self.thumbnails_dir()
        try:
            os.mkdir(td)
        except OSError:
            pass
        for page in self.pages:
            img = page.image
            for r in page.image_regions():
                hilite_region(img, r)
            img.thumbnail((128, 128))
            img.save(page.thumbnail_path('hli'), 'JPEG')        

    def list_pages(self):
        print('Book:  %s' % self.name_token)
        for page in self.pages:
            print('%4d %s:  %d(%r)w %d(%r)h' % (
                page.sequence_number,
                ('%4d' % page.page_number) if page.page_number else '    ',
                page.jp2_width, page.metadata_width,
                page.jp2_height, page.metadata_height))


class DublinCoreMetadata (object):
    '''DublinCoreMetadata holds the Dublin Core metadata for a Book.'''
    DUBLIN_CORE_NAMESPACE = 'http://purl.org/dc/elements/1.1/'

    def __init__(self, book):
        tree = ET.parse(os.path.join(book.directory,
                                     book.name_token + '_dc.xml'))
        def elts(tag):
            return tree.findall('.//{%s}%s' % (
                self.__class__.DUBLIN_CORE_NAMESPACE, tag))
        def maybe(elts):
            if len(elts) > 0:
                return elts[0].text
            return ''
        self.title = maybe(elts('title'))
        self.contributor = maybe(elts('contributor'))
        self.publisher = maybe(elts('publisher'))
        self.date = maybe(elts('date'))
        self.description = [d.text for d in elts('description')]
        self.subject = [s.text for s in elts('subject')]
        book.dc_metadata = self


class Page (object):
    '''Page is a repository for the information we can collect about one page of a book.'''

    def __init__(self, book, jp2filepath):
        self.book = book
        self.jp2filepath = jp2filepath
        self.metadata = None
        self.corrected_page_number = None
        # These properties are extracted from the jp2 file:
        m = SEQUENCE_NUMBER_JP2_REGEXP.search(os.path.basename(self.jp2filepath))
        self.sequence_number = None
        if m:
            self.sequence_number = int(m.group('seq'))
        # Pillow lazily loads images so it's cheap to open them now.
        # We call load_image each time we need it because many of the
        # operations we might use (like thumbnail) modify the image in
        # place and we want a 'clean' image each time.
        self.jp2_width, self.jp2_height = self.image.size

    def __str__(self):
        return '<%s.%s %04d>' % (
            self.__class__.__module__,
            self.__class__.__name__,
            self.sequence_number)

    def load_image(self):
        # Since most of the operations on an Image appear to modify it
        # in place, we don't cache the Image but reopen it when we
        # need it.
        return self.image.load()

    @property
    def jp2_region(self):
        return Region(0, self.jp2_width, 0, self.jp2_height)

    @property
    def image(self):
        return Image.open(self.jp2filepath)

    @property
    def page_number(self):
        if self.corrected_page_number:
            return self.corrected_page_number
        if self.metadata:
            return self.metadata.page_number
        return None

    @page_number.setter
    def page_number(self, pn):
        self.corrected_page_number = pn

    @property
    def metadata_width(self):
        if self.metadata:
            return self.metadata.image_width
        return None

    @property
    def metadata_height(self):
        if self.metadata:
            return self.metadata.image_height
        return None

    def thumbnail_path(self, tag=''):
        return os.path.join(self.book.thumbnails_dir(),
                            '%04d%s.jpg' % (self.sequence_number, tag))

    def get_ocr_object_element(self):
        '''get_ocr_object_element looks for and returns the page's OBJECT
        element from the book's djvu.xml document. '''
        if not self.metadata:
            return None
        key = self.metadata.page_file
        tree = ET.parse(self.book.djvu_path)
        # tree.find('''.//OBJECT[PARAM/@value='%s']''' % key)
        # doesn't work.
        for o in tree.iter('OBJECT'):
            for p in o.iter('PARAM'):
                if (p.attrib['name'] == "PAGE" and
                    p.attrib['value'] == key):
                    return o
        return None        

    def text_region(self):
        '''text_region returns a Region that surrounds all of the OCRed text
        on the page.'''
        obj = self.get_ocr_object_element()
        if obj == None:
            return None
        return text_bounds(obj, self.jp2_region)

    def image_regions(self):
        '''image_areas looks for areas of the page that are not text or margin
        that might be big enough to fit an image.'''
        all = self.jp2_region
        if self.metadata:
            s = int(round(self.metadata.dpi * 0.25))
            all = all.inset(s, s, s, s)
        enough_width = (all.right - all.left) / 4
        enough_height = (all.bottom - all.top) / 10
        candidates = []
        vstart = all.top
        obj = self.get_ocr_object_element()
        if not obj:
            return [all]
        for p in obj.iter('PARAGRAPH'):
            r = text_bounds(p, all)
            if r.top - vstart >= enough_height:
                candidates.append(Region(all.left, all.right, vstart, r.top))
            if r.height >= enough_height:
                if (r.left - all.left) >= enough_width:
                    candidates.append(Region(all.left, r.left - 1, r.top, r.bottom))
                if (all.right - r.right) >= enough_width:
                    candidates.append(Region(r.right + 1, all.right, r.top, r.bottom))
            vstart = r.bottom + 1
        if (all.bottom - vstart) >= enough_height:
            candidates.append(Region(all.left, all.right, vstart, all.bottom))
        return candidates

    def graphics_only(self):
        """graphics_only returns an image of the page with the background
        changed to white and any OCRed text erased."""
        img = self.image
        background = self.sample_background()
        whiten(img, background[0][0], background[1][0], background[2][0])
        obj = self.get_ocr_object_element()
        for p in obj.iter('PARAGRAPH'):
            r = text_bounds(p, self.jp2_region)
            for y in r.rangeY:
                for x in r.rangeX:
                    img.putpixel((x, y), (0xff, 0xff, 0xff))
        return img

    def sample_background(self):
        # The page gutter can be too dark to give a good sample, so we
        # lookat the right 1/4 inch and left 1/4 inch from each edge
        # and use the background color of the lighter.
        s = int(round(self.metadata.dpi * 0.25))
        left = range(0, s)
        right = range(self.jp2_width - s, self.jp2_width)
        image = self.image
        def edge_rgb_ranges(x_range):
            minR, maxR = 255, 0
            minG, maxG = 255, 0
            minB, maxB = 255, 0
            for y in range(image.size[1]):
                for x in x_range:
                    r, g, b = image.getpixel((x, y))
                    minR = min(minR, r)
                    maxR = max(maxR, r)
                    minG = min(minG, g)
                    maxG = max(maxG, g)
                    minB = min(minB, b)
                    maxB = max(maxB, b)
            return ((minR, maxR), (minG, maxG), (minB, maxB))
        # White is #xFF.  Greater is lighter.
        def lightness(rgb_ranges):
            return reduce(operator.add, [m * m for m in [ r[0] for r in rgb_ranges]])
        left_rgb = edge_rgb_ranges(left)
        right_rgb = edge_rgb_ranges(right)
        return left_rgb if lightness(left_rgb) > lightness(right_rgb) else right_rgb


class PageMetadata (object):
    '''PageMetadata represents the information for a given page that we
    have extracted from an OBLECT element in a djvu.xml file.
    '''
    
    def __init__(self, object_elt):
        self.image_width = int(object_elt.attrib['width'])
        self.image_height = int(object_elt.attrib['height'])
        self.line_count = count_lines(object_elt)
        self.page_file = None
        self.sequence_number = None
        self.dpi = None
        for param in object_elt.iter('PARAM'):
            if param.attrib['name'] == "PAGE":
                self.page_file = param.attrib['value']
                self.sequence_number = extract_sequence_number(SEQUENCE_NUMBER_DJVU_REGEXP, self.page_file)
            elif param.attrib['name'] == 'DPI':
                self.dpi = int(param.attrib['value'])
        self.page_number = infer_page_number(object_elt)

        
SEQUENCE_NUMBER_JP2_REGEXP = re.compile('_(?P<seq>[0-9]+).jp2')
SEQUENCE_NUMBER_DJVU_REGEXP = re.compile('_(?P<seq>[0-9]+).djvu')

def extract_sequence_number(regexp, filepath):
    '''extract_sequence_number extracts a page sequence number from filepath
    using the specified regular expression.  Returns an int or None.'''
    m = regexp.search(os.path.basename(filepath))
    if m:
        return int(m.group('seq'))
    return None


# We could interpolate page numbers for those pages where we don't find one.
def infer_page_number(object_elt):
    '''infer_page_number attempts to infer the page number (as printed
    on the page) from the page's OCR data. It is not clever.'''
    # We look for a WORD that can be parsed as an int in the first or
    # last OCRed line of the page.
    def try_line(line):
        for word in line.iter('WORD'):
            try:
                return int(word.text)
            except:
                pass
        return None
    lines = object_elt.findall('.//LINE')
    if len(lines) == 0:
        return None
    return try_line(lines[0]) or try_line(lines[-1])


def count_lines(paragraph):
    '''count_lines returns the number of lines of text in a paragraph.'''
    return len(paragraph.findall('.//LINE'))


def text_bounds(element, whole):
    '''text_bounds returns the bounding box computed from the coord
    attributes of all descendents of element as a Region.
    whole is a region encompassing the entire page.'''
    minX = whole.right
    maxX = whole.left
    minY = whole.bottom
    maxY = whole.top
    for elt in element.findall('.//*[@coords]'):
        left, bottom, right, top, baseline_right =  tuple(
            [int(i) for i in elt.attrib['coords'].split(',')])
        if left < minX: minX = left
        if right > maxX: maxX = right
        if top < minY: minY = top
        if bottom > maxY: maxY = bottom
    return Region(minX, maxX, minY, maxY)


def whiten(image, rThreshold, gThreshold, bThreshold):
    assert image.mode == 'RGB'
    total = 0
    changed = 0
    for y in range(image.size[1]):
        for x in range(image.size[0]):
            total += 1
            r, g, b = image.getpixel((x, y))
            if (r >= rThreshold) and (g >= gThreshold) and (b >= bThreshold):
                changed += 1
                image.putpixel((x, y), (0xff, 0xff, 0xff))


def outline_region(image, region):
    assert image.mode == 'RGB'
    for x in region.rangeX:
        image.putpixel((x, region.top), (0, 0, 0xff))
        image.putpixel((x, region.bottom), (0, 0, 0xff))
    for y in region.rangeY:
        image.putpixel((region.left, y), (0, 0, 0xff))
        image.putpixel((region.right, y), (0, 0, 0xff))


def hilite_region(image, region):
    assert image.mode == 'RGB'
    rThreshold = 0xff
    gThreshold = 0xff
    bThreshold = 0xff
    for x in region.rangeX:
        r, g, b = image.getpixel((x, region.top))
        if r < rThreshold: rThreshold = r
        if g < gThreshold: gThreshold = g
        if b < bThreshold: bThreshold = b
    for y in region.rangeY:
        for x in region.rangeX:
            r, g, b = image.getpixel((x, y))
            if (r > rThreshold) and (g > gThreshold) and (b > bThreshold):
                image.putpixel((x, y), (0xff, 0xff, 0xff))

