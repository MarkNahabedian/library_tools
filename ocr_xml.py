# Analyze the XML file containing the OCr data.

import xml.etree.ElementTree as ET


def get_page_boundaries(filename):
    '''get_page_boundaries determines page boundaries by looking at the
    coordinates of the extracted tec=xt from a djvu XML file.'''
    tree = ET.parse(filename)
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


