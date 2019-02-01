# Do some simple checkiing and analysis of a JPEG2000 file.
#
# Resources:
#    http://www.file-recovery.com/jp2-signature-format.htm
#    https://sno.phy.queensu.ca/~phil/exiftool/TagNames/Jpeg2000.html
#    http://www.ece.drexel.edu/courses/ECE-C453/Notes/jpeg2000.pdf

import os
import os.path


def scan_all(directory):
    for f in os.listdir(directory):
        fbox = RootJP2Box(os.path.join(directory, f))
        print(fbox.filepath)
        fbox.read().show()


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
        data_size = box_size - 8
        if box_size == 1:
            xlbox = f.read(8)
            box_size = big_endian_int(xlbox, bytecount=8)
            daata_size -= 8
        elif box_size == 0:
            box_size = os.fstat(f.fileno()).st_size - box_start
        box_type = get_tag(header)
        box = JP2Box.class_for_box_type(box_type)(box_type, box_start, box_size, data_size)
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

    def __init__(self, box_type, box_start, box_size, data_size):
        self.containing_box = None    # Set by add_child
        self.box_type = box_type
        self.box_start = box_start
        self.box_size = box_size
        self.data_size = data_size
        self.boxes = None

    @property
    def box_end(self):
        return self.box_start + self.box_size

    def isContainer(self):
        return False

    def handle_data(self, f):
        '''handle_data receives a file stream with the input positioned at the
        start of the data for this box.  It must leave the file input
        positioned at the end of the box.
        '''
        # Default behavior is to skip oover the data
        f.seek(self.box_end, os.SEEK_SET)

    def add_child(self, box):
        if not self.isContainer:
            raise Exception('%s is not a container' % self)
        self.boxes.append(box)
        box.containing_box = self

    def show(self, indent=0):
        print('%8d: %8d %s%s %s' % (
            self.box_start,
            self.box_size,
            '  ' * indent,
            self.box_type,
            self.details()))
        if self.boxes != None:
            for child in self.boxes:
                child.show(indent + 1)

    def details(self):
        return ''


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

    def __len__(self):
        return len(self.boxes)

    def __getitem__(self, i):
        return self.boxes[i]


class  RootJP2Box (JP2ContainerBox):
    box_type = None
        
    def __init__(self, filepath):
        self.filepath = filepath
        file_size = os.stat(self.filepath).st_size
        super().__init__(None, 0, file_size, file_size)

    def read(self):
        with open(self.filepath, 'rb') as f:
            self.handle_data(f)
        return self


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

class JP2ImageHeader(JP2Box):
    box_type = 'ihdr'

    def handle_data(self, f):
        print('ihdr data start', f.tell())
        buffer = f.read(self.data_size)
        print(buffer)
        # self.major_version = buffer[0]
        # self.minor_version = buffer[1]
        # self.number_of_components = big_endian_int(buffer, 0, 2)
        self.image_height = big_endian_int(buffer, 0, 4)
        self.image_width = big_endian_int(buffer, 4, 4)
        # self.bits_per_component = buffer[10]
        # self.compression_type = buffer[11]
        # self.colorspace_unknown = buffer[12]
        # self.intelllectual_property = buffer[13]

    def details(self):
        return 'version %d.%d %dw %dh %0x %0x' % (
            0, # self.major_version,
            0, # self.minor_version,
            self.image_width,
            self.image_height,
            0, # self.bits_per_component,
            0, # self.compression_type
        )


class JP2ColorSpecification(JP2Box):
    box_type = 'colr'

    def handle_data(self, f):
        print('colr data start', f.tell())
        buffer = f.read(self.data_size)
        print(buffer)
        self.method = buffer[0]
        # 1 byte "precedence" value ignored
        self.approximation = buffer[2]
        self.enumerated_colorspace = big_endian_int(buffer, 3, 4)
        if self.method == 1:
            self.icc_profile = None
        else:
            self.icc_profile = buffer[7:]
            
