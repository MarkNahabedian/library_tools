# Maybe we can use the dimensions of a word to characterize font and therefor text context/role.

from collections import defaultdict, namedtuple

WordSize = namedtuple('WordSize', ('width', 'height'))


class WordSizeCollector (object):
    def __init__(self):
        self.dictionary = defaultdict(list)

    def note_word(self, word):
        '''Note the width and height for this instance of the word.
        word should be an XML "WORD" element from the OCR file.'''
        left, bottom, right, top, baseline_right = tuple(
            [int(i) for i in word.attrib['coords'].split(',')])
        self.dictionary[word.text].append(WordSize(right - left, bottom - top))

    def __len__(self):
        return len(self.dictionary)

    def __getitem__(self, key):
        return self.dictionary[key]

