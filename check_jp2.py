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
    root_container = RootJP2Box(filelength)
    with open(filename, 'rb') as f:
        root_container.handle_data(f)
    return root_container

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


class JP2Box (object):
    '''JP2Box is both the superclass of all boxes and the defauklt
    imlementation for boxes we don't have a more specific
    implementation for,'''
    box_type = None

    @classmethod
    def read_box(cls, f):
        box_start = f.tell()
        header = f.read(8)
        box_size = big_endian_int(header)
        if box_size == 1:
            xlbox = f.read(8)
            box_size = big_endian_int(xlbox, bytecount=8)
        elif box_size == 0:
            box_size = os.fstat(f.fileno()).st_size - box_start
        box_type = get_tag(header)
        box = JP2Box.class_for_box_type(box_type)(box_type, box_start, box_size)
        box.handle_data(f)
        return box

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
        self.containing_box = None    # Set by add_child
        self.box_type = box_type
        self.box_start = box_start
        self.box_size = box_size
        self.boxes = None

    @property
    def box_end(self):
        return self.box_start + self.box_size

    def isContainer(self):
        return False

    def handle_data(self, f):
        # Default behavior is to skip oover the data
        f.seek(self.box_end, os.SEEK_SET)

    def add_child(self, box):
        if not self.isContainer:
            raise Exception('%s is not a container' % self)
        self.boxes.append(box)
        box.containing_box = self

    def show(self, indent=0):
        print('%8d: %s%8d %s' % (
            self.box_start,
            '  ' * indent,
            self.box_size,
            self.box_type))
        if self.boxes != None:
            for child in self.boxes:
                child.show(indent + 1)


class JP2ContainerBox(JP2Box):
    '''JP2ContainerBox is the superclass of all boxes that can contain other boxes.'''
    def isContainer(self):
        return True

    def __init__(self, *args):
        super().__init__(*args)
        self.boxes = []

    def handle_data(self, f):
        # Read the contained boxes
        while f.tell() < self.box_end:
            box = JP2Box.read_box(f)
            self.add_child(box)


class RootJP2Box (JP2ContainerBox):
    box_type = None
        
    def __init__(self, file_size):
        super().__init__(None, 0, file_size)


class JP2SignatureBox(JP2Box):
    box_type = 'jP  '
    isContainerBox = False

    def handle_data(self, f):
        expect = b'\r\n\x87\n'
        data = f.read(4)
        if data != expect:
            raise Exception('Bad JP2 signature data: %r, expected %r' % (data, expect))
        

class JP2HeaderBox(JP2ContainerBox):
    box_type = 'jp2h'

