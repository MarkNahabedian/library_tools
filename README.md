The goal of this project is to produce a tool to facilitate the
extraction of images and associated metatdata from scanned books on
archive.org.

The books are from the libraries of the Massachusetts Institute of
Technology.  They were scanned by an outside contractor once their
copyrights had expired.

# Fetching Data to Local File System

The documents I'm working with are found at https://archive.org/details/mitlibrariespublicdomain.

The command

<pre>
fetch_pages.py hartnessflatturr00unse
</pre>

will create a directory named hartnessflatturr00unse in the current
directory and download the book with that URI path component title to
that directory.  The download will include various forms of metadata
and the scanned images of each page, as well as a djvu XML file
containing the OCRed text.  Thumbnail images of each page and a
descriptive html file are also created.

# Requirements:

The code expects to run in some version of python3.

It also requires the yattag package:

<pre>
pip install yattag
</pre>


# Background About the Data and Notes by the Implementor

The remaining is probably not of interest to most users.

For some document,
e.g. https://archive.org/metadata/hartnessflatturr00unse, we can fetch
the document's metadata with

  fetch_metadata('hartnessflatturr00unse')

returns a JSON object that includes the book's title, keywords, data
about the scanning and archiving processes, and each of the files in
the archive that contain data associated with the book.

For the above example document the associaed files and their "format"s are:

  Abbyy GZ       hartnessflatturr00unse_abbyy.gz
  DjVuTXT        hartnessflatturr00unse_djvu.txt
  Djvu XML       hartnessflatturr00unse_djvu.xml
  Dublin Core    hartnessflatturr00unse_dc.xml
  Item Tile      __ia_thumb.jpg
  JSON           hartnessflatturr00unse_events.json
  Log            logs/hartnessflatturr00unse_iabdash_2018-11-2611:39:27.log
  Log            logs/hartnessflatturr00unse_scanning_2018-11-2611:39:23.log
  MARC           hartnessflatturr00unse_marc.xml
  MARC Binary    hartnessflatturr00unse_meta.mrc
  MARC Source    hartnessflatturr00unse_metasource.xml
  Metadata       hartnessflatturr00unse_files.xml
  Metadata       hartnessflatturr00unse_meta.sqlite
  Metadata       hartnessflatturr00unse_meta.xml
  Scandata       hartnessflatturr00unse_scandata.xml
  Single Page Original JP2 Tar   hartnessflatturr00unse_orig_jp2.tar
  Single Page Processed JP2 ZIP          hartnessflatturr00unse_jp2.zip
  Text PDF       hartnessflatturr00unse.pdf


FILE_FETCH_URL_TEMPLATE is a string template that will construct a URL
to fetch any of these files given the "dir" from the JSON object and
the "name" of any of these files.

  fetch_url_to_file('https://archive.org/34/items/hartnessflatturr00unse/hartnessflatturr00unse_djvu.xml',
                    'hartnessflatturr00unse_djvu.xml', True)

returns a djvu XML file of the OCRed text of the document.
Unfortunately that file doesn't contain any data concerning figures,
diagrams, photos or other images in the book.  It does include the
text and the text's bounding boxes.

This link provides some minimal information about the structure and
content of the djvu XML file:
http://djvu.sourceforge.net/doc/man/djvuxml.html

The leaf nodes of the djvu XML have a "coords" attribute which has
five numbers.  These appear to be the left, bottom, right, and top
coordinates of the bounding box for the text content of the element.
I think that the fifth element of the coordinates is also the bottom
coordinate, but at the end of the line rather than the beginning.

TODO: Verify that for a given page the slope from the left, bottom
point to the right second bottom point is consistent for every line,
suggesting that the page might be slightly rotated when placed on the
scanner.

I wonder if we can programatically read each page image and erase the
text (by clearing its bounding boxes), hopefully leaving only the
figures.


