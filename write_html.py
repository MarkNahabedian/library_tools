# Wriye an HTML file that describes the book and its pages.

import os.path
import yattag


STYLESHEET = '''
body	{
	color: white;
	background-color: black;
	}
.pagenumber {
	padding: 3em;
	text-align: right;
	}
.dimension {
	padding: 3em;
	text-align: right;
	}
.line_count {
	padding: 3em;
	text-align: right;
	}
'''

def write_html(book):
    doc, tag, text = yattag.Doc().tagtext()
    with tag('html'):
        with tag('head'):
            with tag('title'):
                text(book.name_token)
            with tag('style', type='text/css'):
                text(STYLESHEET)
        with tag('body'):
            with tag('h1'):
                text(book.name_token)
            # TODO: book metadata
            with tag('table', style='pages'):
                with tag('tr', klass='headings'):
                    with tag('th'): text('page number')
                    with tag('th'): text('thumbnail')
                    with tag('th'): text('width')
                    with tag('th'): text('width')
                    with tag('th'): text('number of lines')
                for page in book.pages:
                    with tag('tr', klass='page'):
                        with tag('td', klass='pagenumber'):
                            text('%04d' % page.sequence_number)
                            if page.page_number:
                                with tag('br'): pass
                                text('%d' % page.page_number)
                        with tag('td', klass='thumbnail'):
                            with tag('img', src=os.path.relpath(page.thumbnail_path(), book.directory)):
                                pass
                        with tag('td', klass='dimension'):
                            text('%dw' % page.jp2_width)
                            if page.metadata and page.metadata.image_width:
                                with tag('br'): pass
                                text('%d' % page.metadata.image_width)
                        with tag('td', klass='dimension'):
                            text('%dw' % page.jp2_height)
                            if page.metadata and page.metadata.image_height:
                                with tag('br'): pass
                                text('%d' % page.metadata.image_height)
                        with tag('td', klass='line-count'):
                            if page.metadata:
                                text('%d' % page.metadata.line_count)
        with open(os.path.join(book.directory, 'pages.html'), 'w') as out:
            out.write(doc.getvalue())

