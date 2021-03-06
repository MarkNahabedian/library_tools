# Analyze the XML file containing the OCR data.

import xml.etree.ElementTree as ET
from region import Region


def get_page_boundaries(filename):
    '''get_page_boundaries determines page boundaries by looking at the
    coordinates of the extracted text from a djvu XML file.'''
    tree = ET.parse(filename)
    # TODO change to use text_bounds()
    minX = None
    minY = None
    maxX = None
    maxY = None
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
    for word in tree.iter('WORD'):
        left, bottom, right, top, baseline_right =  tuple([int(i) for i in word.attrib['coords'].split(',')])
        minX = min(minX, left)
        minY = min(minY, top)
        maxX = max(maxX, max(right, baseline_right))
        maxY = max(maxY, bottom)
    print('X: ', minX, maxX)
    print('Y: ', minY, maxY)


def page_by_page(filename):
    tree = ET.parse(filename)
    count = 0
    for page in tree.iter('OBJECT'):
        count += 1
        height = int(page.attrib['height'])
        width = int(page.attrib['width'])
        # Maybe also look at first and last REGION of page.
        # get file and DPI
        page_file = None
        dpi = None
        for param in page.iter('PARAM'):
            if param.attrib['name'] == "PAGE":
                page_file = param.attrib['value']
            elif param.attrib['name'] == 'DPI':
                dpi = int(param.attrib['value'])
        print("%dw %dh %ddpi %s" % (width, height, dpi, page_file))
    print('%d pages' % count)


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

