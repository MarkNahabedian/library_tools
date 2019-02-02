#!python3

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
        tree = ET.parse(os.path.join(self.directory,
                                     self.name_token + '_djvu.xml'))
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

    def cache_jp2_page_sizes(self):
        for page in self.pages:
            page.load_image()

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
        self.image = None
        self.jp2_width = None
        self.jp2_height = None

    def load_image(self):
        image = Image.open(self.jp2filepath)
        self.jp2_width, self.jp2_height = image.size
        return image

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
    '''infer_page_number attempts to infer the page number (ad printed on the page) from the page's OCR data.
    It is not clever.'''
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

