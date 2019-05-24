# Wriye an HTML file that describes the book and its pages.

import os.path
import yattag     # pip install yattag


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
.margins {
	padding: 3em;
	text-align: left;
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
            with tag('h2'):
                text('Doublin Core Metadata')
            with tag('dl'):
                def item(name, value):
                    with tag('dt'):
                        text(name)
                    with tag('dd'):
                        if isinstance(value, str):
                            text(value or '')
                        else:
                            for i in range(len(value)):
                                with tag('div'):
                                    text(value[i])
                item('Title', book.dc_metadata.title)
                item('Contributor', book.dc_metadata.contributor)
                item('Publisher', book.dc_metadata.publisher)
                item('Date', book.dc_metadata.date)
                item('Description', book.dc_metadata.description)
                item('Subject', book.dc_metadata.subject)
            with tag('h2'):
                text('Pages')
            with tag('table', style='pages'):
                with tag('tr', klass='headings'):
                    with tag('th'): text('page number')
                    with tag('th'): text('thumbnail')
                    with tag('th'): text('page dimensions')
                    with tag('th'): text('margins')
                    with tag('th'): text('number of lines')
                    with tag('th'): text('picture regions')
                    with tag('th'): text('hilited images')
                for page in book.pages:
                    with tag('tr', klass='page'):
                        with tag('td', klass='pagenumber'):
                            with tag('div'):
                                text('%04d' % page.sequence_number)
                            if page.page_number:
                                with tag('div'):
                                    text('%d' % page.page_number)
                        with tag('td', klass='thumbnail'):
                            with tag('img', src=os.path.relpath(page.thumbnail_path(), book.directory)):
                                pass
                        with tag('td', klass='dimension'):
                            try:
                                dpi= page.metadata.dpi
                                with tag('div'):
                                    text('dpi: %d' % dpi)
                            except:
                                pass
                            with tag('div'):
                                text('jp2 width: %d' % page.jp2_width)
                            with tag('div'):
                                text('jp2 height: %d' % page.jp2_height)
                            if page.metadata:
                                if page.metadata.image_width:
                                    with tag('div'):
                                        text('OCR width: %d' % page.metadata.image_width)
                                if page.metadata.image_height:
                                    with tag('div'):
                                        text('OCR height: %d' % page.metadata.image_height)
                        with tag('td', klass='margins'):
                            whole = page.jp2_region
                            txt = page.text_region()
                            if txt != None:
                                with tag('div'):
                                    text('left: %d' % (txt.left - whole.left))
                                with tag('div'):
                                    text('right: %d' % (whole.right - txt.right))
                                with tag('div'):
                                    text('top: %d' % (txt.top - whole.top))
                                with tag('div'):
                                    text('bottom: %d' % (whole.bottom - txt.bottom))
                        with tag('td', klass='line-count'):
                            if page.metadata:
                                text('%d' % page.metadata.line_count)
                                doc.stag('br')
                                text('%f' % page.text_coverage())
                        with tag('td'):
                            for r in page.picture_regions:
                                with tag('div'):
                                     text(repr(r))
                        with tag('td', klass='thumbnail'):
                            with tag('img', src=os.path.relpath(page.thumbnail_path('hli'), book.directory)):
                                pass
        with open(os.path.join(book.directory, 'pages.html'), 'w') as out:
            out.write(doc.getvalue())

