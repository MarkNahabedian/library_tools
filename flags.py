
# PAGE_FIRST_LINE indicates that this is the first line of the page
PAGE_FIRST_LINE = 1 << 0
# PAGE_LAST_LINE indicates that this is the last line of a page
PAGE_LAST_LINE = 1 << 1

PARA_FIRST_LINE = 1 << 2

PARA_LAST_LINE = 1 << 3

# LINE_FULL_WIDTH indicates that the line extends the full width of
# the page
LINE_FULL_WIDTH = 1 << 4

# LINE_DESCENDS indicates that at least one character of the line
# descends below the text baseline.
LINE_DESCENDS = 1 << 5
# LINE_ASCENDS indicates that at least one character of the line
# ascends above the middle of the line or 'x' height.
LINE_ASCENDS = 1 << 6

LINE_HAS_UPPER_CASE = 1 << 7
LINE_HAS_LOWER_CASE = 1 << 8
LINE_HAS_DIGITS = 1 << 9


def bit_string(flags):
    return bin(flags | (1 << 10))[3:]
