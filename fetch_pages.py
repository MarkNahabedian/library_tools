#!python3

import argparse
import json
import sys
import os
import os.path
import archive_org
import zipfile
import gzip
import page
from collections import namedtuple
from write_html import write_html


parser = argparse.ArgumentParser(description='''
%(prog)s is a special purpose tool that was developed to
assist in the extraction of images (figures, diagrams, illustrations,
etc.) from scanned books on archive.org for eventual uploading to the
WikiMedia Commons.  It makes many assumptions about how the books were
scanned and uploaded to archive.org.

The positional arguments represent book titles as they appear in an
archive.org URI.  For example, for the book archived as

  https://archive.org/details/hartnessflatturr00unse

the command line argument would be "hartnessflatturr00unse".

A subdirectory with that name will be created in the working
directory and the page images and metadata will be downloaded there.

An HTML file will also be created in that directory that enumerates
the pages of the book and suggests metadata for each page.

It would be nice to extract individual diagrams and figures from each
page, but the available OCR data does not facilitate that.

''')

parser.add_argument('book_title_path_component', type=str, nargs='+')

def main():
    args = parser.parse_args()
    for book in args.book_title_path_component:
        fetch_book(book)
        b = page.Book(book)
        b.make_thumbnails()
        write_html(b)


DownloadFormat = namedtuple('DownLoadFormat', ('format', 'action'))


def extract_jp2_archive(file_metadata, fetched_file, target_directory):
    assert file_metadata['format'] == 'Single Page Processed JP2 ZIP'
    pages_dir = os.path.join(target_directory, 'pages')
    os.mkdir(pages_dir)
    zf = zipfile.ZipFile(fetched_file, 'r')
    for page in zf.namelist():
        zf.extract(page, path=pages_dir)


def unzib_abbyy(file_metadata, fetched_file, target_directory):
    print(fetched_file)
    assert file_metadata['format'] == 'Abbyy GZ'
    f = gzip.open(fetched_file, 'rb')
    directory, filename = os.path.split(fetched_file)
    base = filename.rsplit('.', 1)[0]
    outfile = os.path.join(directory, base + '.xml')
    with open(outfile, 'wb') as out:
        while True:
            buffer = f.read(10000)
            if len(buffer) == 0:
                break
            out.write(buffer)


DOWNLOAD_FORMATS = [
    DownloadFormat('Metadata', None),
    DownloadFormat('Djvu XML', None),
    DownloadFormat('Dublin Core', None),
    DownloadFormat('Abbyy GZ', unzib_abbyy),
    # ??? Should we be working with the processed or the original jp2 files?
    DownloadFormat('Single Page Processed JP2 ZIP', extract_jp2_archive)
    ]


def want_download(format):
    for df in DOWNLOAD_FORMATS:
        if df.format == format:
            return df
    return None


def fetch_book(book):
    d = os.path.join(os.path.abspath(os.curdir), book)
    os.mkdir(d)
    metadata_file = os.path.join(d, 'metadata.json')
    metadata = archive_org.fetch_metadata(book)
    with open(metadata_file, 'w') as output:
        json.dump(metadata, output, indent='  ')
    remote_dir = metadata['dir']
    remote_files = metadata['files']
    for f in remote_files:
        this_file = None
        download_format = want_download(f['format'])
        if download_format == None:
            continue
        this_file = os.path.join(d, f['name'])
        archive_org.fetch_url_to_file(
            archive_org.FILE_FETCH_URL_TEMPLATE.format(
                DIR=remote_dir,
                NAME=f['name']),
            this_file, binary=True)
        print('Wrote', this_file)
        if download_format.action != None:
            download_format.action(f, this_file, d)
    print('Book downloaded to', d)


if __name__ == '__main__':
    main()

