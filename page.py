#!python3

import math
import os
import os.path
import re
import xml.etree.ElementTree as ET
from PIL import Image     # pip install Pillow


class Book (object):
    '''Book represents a scanned book that was fetched using fetch_pages.py.*'''

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
        jp2dir = self.jp2_directory()
        for filename in os.listdir(jp2dir):
            self.pages.append(Page(self, os.path.join(jp2dir, filename)))
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

    def load_image(self):
        # Since most of the operations on an Image appear to modify it
        # in place, we don't cache the Image but reopen it when we
        # need it.
        return self.image.load()

    @property
    def image(self):
        return Image.open(self.jp2filepath)

    @property
    def page_number(self):
        if self.metadata:
            return self.metadata.page_number
        return None

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

    def thumbnail_path(self):
        return os.path.join(self.book.thumbnails_dir(),
                            '%04d.jpg' % self.sequence_number)

    def get_ocr_object_element(self):
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

    def graphics_only(self):
        img = self.image
        background = self.sample_background()
        whiten(img, background[0][0], background[1][0], background[2][0])
        obj = self.get_ocr_object_element()
        for p in obj.iter('PARAGRAPH'):
            rangeX, rangeY = paragraph_bounds(p, img.size)
            for y in rangeY:
                for x in rangeX:
                    img.putpixel((x, y), (0xff, 0xff, 0xff))
        return img

    def sample_background(self):
        # Sample 1/4 inch from each corner.
        s = int(round(self.metadata.dpi * 0.25))
        left = range(0, s)
        top = range(0, s)
        right = range(self.jp2_width - s, self.jp2_width)
        bottom = range(self.jp2_height - s, self.jp2_height)
        minR, maxR = 255, 0
        minG, maxG = 255, 0
        minB, maxB = 255, 0
        def min(a, b): return a if a < b else b
        def max(a, b): return b if a < b else a
        image = self.image
        for rng in ((left, top), (right, top), (left, bottom), (right, bottom)):
            for y in rng[1]:
                for x in rng[0]:
                    r, g, b = image.getpixel((x, y))
                    minR = min(minR, r)
                    maxR = max(maxR, r)
                    minG = min(minG, g)
                    maxG = max(maxG, g)
                    minB = min(minB, b)
                    maxB = max(maxB, b)
        return (minR, maxR), (minG, maxG), (minB, maxB)


class PageMetadata (object):
    '''PageMetadata represents the information for a given page that we
    have extracted from an OBLECT element in a djvu.xml file.
    '''
    
    def __init__(self, object_elt):
        self.image_width = int(object_elt.attrib['width'])
        self.image_height = int(object_elt.attrib['height'])
        self.line_count = len(object_elt.findall('.//LINE'))
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
    '''infer_page_number attempts to infer the page number (ad printed
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


def paragraph_bounds(paragraph, size):
    '''paragraph_bounds returns the bounding box of the OCRed PARAGRAPH
    element as a range of X coordinates and a range of Y coordinates.
    '''
    def min(a, b):
        if a == None:
            return b
        if a < b:
            return a
        return b
    def max(a, b):
        if a == None:
            return b
        if a > b:
            return a
        return b
    minX = None
    minY = None
    maxX = None
    maxY = None
    lines = 0
    for line in paragraph.iter('LINE'):
        lines += 1
        for w in line.iter('WORD'):
            left, bottom, right, top, baseline_right =  tuple(
                [int(i) for i in w.attrib['coords'].split(',')])
            minX = min(minX, left)
            minY = min(minY, top)
            maxX = max(maxX, right)
            maxY = max(maxY, bottom)
    line_height = (maxY - minY) / lines
    # Pad the top and bottom of the paragraph
    ypad = 0   # int(math.ceil(line_height * 1))
    return (range(minX, maxX + 1),
            range(max(0, minY - ypad),
                  min(size[1], maxY + ypad + 1)))


# Sadly, whiten looses us part of the image.  Due to shadow, the
# gutter border is dark enough to loose us some of the image.
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



