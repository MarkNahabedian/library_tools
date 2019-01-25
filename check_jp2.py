# Do some simple checkiing and analysis of a JPEG2000 file.
#
# Resources:
#    http://www.file-recovery.com/jp2-signature-format.htm
#    https://sno.phy.queensu.ca/~phil/exiftool/TagNames/Jpeg2000.html

import os


def scan_jp2(filename):
    filelength = os.stat(filename).st_size
    print('Total size: %d' % filelength)
    with open(filename, 'rb') as f:
        while f.tell() < filelength:
            start = f.tell()
            header = f.read(8)
            section_length = big_endian_32(header)
            tag = get_tag(header)
            print('%8d: %8d %s    %r' % (start, section_length, tag, header))
            if section_length == 0:
                break
            f.seek(start + section_length, os.SEEK_SET)

def get_tag(header):
    result = ''
    for index in range(4, 8):
        result += chr(header[index])
    return result

def headerig_endian_32(header):
    result = 0
    for index in range(0, 4):
        result = result << 8
        result += header[index]
    return result
