# Do some simple checkiing and analysis of a JPEG2000 file.
#
# Resources:
#    http://www.file-recovery.com/jp2-signature-format.htm
#    https://sno.phy.queensu.ca/~phil/exiftool/TagNames/Jpeg2000.html

import os
import os.path


def scan_all(directory):
    for f in os.listdir(directory):
        fullpath = os.path.join(directory, f)
        print()
        print(fullpath)
        scan_jp2(fullpath)

def scan_jp2(filename):
    filelength = os.stat(filename).st_size
    print('Total size: %d' % filelength)
    with open(filename, 'rb') as f:
        while f.tell() < filelength:
            box = readBox(f)
            print('%8d: %8d %s  %s' % (
                box.box_start, box.box_size, box.box_type, box.__class__.__name__))
            f.seek(box.box_end, os.SEEK_SET)
        if f.tell() < filelength:
            print('Scan terminated abnormally.')

def get_tag(header):
    result = ''
    for index in range(4, 8):
        result += chr(header[index])
    return result

def big_endian_int(buffer, offset=0, bytecount = 4):
    result = 0
    for index in range(offset, offset + bytecount):
        result = result << 8
        result += buffer[index]
    return result

def readBox(f):
    box_start = f.tell()
    header = f.read(8)
    box_size = big_endian_int(header)
    if box_size == 1:
        xlbox = f.read(8)
        box_size = big_endian_int(xlbox, bytecount=8)
    elif box_size == 0:
        box_size = os.fstat(f.fileno()).st_size - box_start
    box_type = get_tag(header)
    return JP2Box.class_for_box_type(box_type)(box_type, box_start, box_size)


class JP2Box (object):
    '''JP2Box is both the superclass of all boxes and the defauklt
    imlementation for boxes we don't have a more specific
    implementation for,'''
    box_type = None
    isContainer = None

    @classmethod
    def class_for_box_type(cls, box_type):
        def walk(cls):
            if cls.box_type == box_type:
                return cls
            for sc in cls.__subclasses__():
                found = walk(sc)
                if found != None:
                    return found
            return None
        return walk(cls) or JP2Box

    def __init__(self, box_type, box_start, box_size):
        self.box_type = box_type
        self.box_start = box_start
        self.box_size = box_size

    @property
    def box_end(self):
        return self.box_start + self.box_size



