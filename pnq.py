# Imroving page number quality

from collections import defaultdict

def page_deltas(book):
    '''page_deltas returns a histogram (in the form of a dict) of the
    frequencey of each difference between sequence_number and
    page_number for each page of book.'''
    deltas = defaultdict(list)
    for p in book.pages:
        if p.sequence_number and p.page_number:
            deltas[p.sequence_number - p.page_number].append(p)
        else:
            deltas[None].append(p)
    return deltas


def best_delta(deltas):
    '''best_delta returns the mst frequent delta from deltas.'''
    best_k = None
    best_count = 0
    for k, pages in deltas.items():
        l = len(pages)
        if l > best_count:
            best_k = k
            best_count = l
    return best_k, best_count

# When I tested this approach on         
# single bad page -> fix it

# multiple bad page numbers:
# single digit missing?


def fix_page_numbers(book):
    deltas = page_deltas(book)
    best, best_count = best_delta(deltas)
    first_page_number = min([p.page_number for p in deltas[best]])
    for delta, pages in deltas.items():
        # If this delta is sufficiently common then don't correct it.
        # I don't know if this matters, but if it's an issue at least
        # we'll ee it.
        if delta and len(pages) >= best_count / 10:
            continue
        if delta == best:
            continue
        for p in pages:
            corrected = p.sequence_number - best
            if corrected >= first_page_number:
                p.page_number = corrected

