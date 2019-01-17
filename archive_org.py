#~python3

# Code to interact with archive.org.

import json
import urllib.request
import zipfile


# Template to construct the metadata URL for the named archived document.
# Suitable for use with string's format method.
METADATA_URL_TEMPLATE = 'https://archive.org/metadata/{NAME}'

# Template to construct the URL to fetch the file specified by the dir
# and name from the archived documents metadata.
FILE_FETCH_URL_TEMPLATE = 'https://archive.org{DIR}/{NAME}'

def fetch_url_to_file(url, filename, binary=False):
    print("Fetching", url)
    with urllib.request.urlopen(url) as input:
        with open(filename, 'wb' if binary else 'w') as out:
            if binary:
                out.write(input.read())
            else:
                info = input.info()
                charset = info.get_content_charset()   # info['Content-Type'].params['charset']
                out.write(input.read().decode(charset, 'replace'))

def fetch_metadata(name):
    uri = METADATA_URL_TEMPLATE.format(NAME=name)
    with urllib.request.urlopen(uri) as input:
        content = input.read().decode('utf-8')
    return json.loads(content)

# This is the the value of the "fgormat" attribute of a file entry in
# an archived document's metadata
PROCESSED_ZIP_FORMAT = 'Single Page Processed JP2 ZIP'

