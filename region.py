
class Region (object):
    '''Region is used to describe any rectilinear area of a page.'''

    def __init__(self, left, right, top, bottom):
        self.left = left
        self.right = right
        self.top = top
        self.bottom = bottom

    @property
    def width(self):
        if self.right == None or self.left == None:
            return 0
        return self.right - self.left

    @property
    def height(self):
        if self.bottom == None or self.top == None:
            return 0
        return self.bottom - self.top

    @property
    def area(self):
        return self.width * self.height

    @property
    def rangeX(self):
        return range(self.left, self.right)

    @property
    def rangeY(self):
        return range(self.top, self.bottom)

    def inset(self, left, right, top, bottom):
        '''inset returns a new Region inset from self by the specified amount at each edge.'''
        return Region(self.left + left, self.right - right,
                      self.top + top, self.bottom - bottom)

    def __repr__(self):
        return('page.Region(%d, %d, %d, %d)' % (
            self.left, self.right, self.top, self.bottom))

    def distanceX(self, other):
        return min(abs(self.right - other.left),
                   abs(self.left - other.right))

    def distanceY(self, other):
        return min(abs(self.bottom - other.top),
                   abs(self.top - other.bottom))

    def overlapsX(self, other):
        return ranges_overlap(self.rangeX, other.rangeX)

    def overlapsY(self, other):
        return ranges_overlap(self.rangeY, other.rangeY)

    @classmethod
    def rectangular_hull(cls, regions):
        '''rectangular_hull returns the smallest Region that contains all of
        the specified regions.'''
        minX = None
        minY = None
        maxX = None
        maxY = None
        def min(a, b):
            if a == None:
                return b
            if a < b:
                return a
            return b
        def max(a, b):
            if a == None:
                return b
            if a > b:
                return a
            return b
        for r in regions:
            minX = min(minX, r.left)
            minY = min(minY, r.top)
            maxX = max(maxX, r.right)
            maxY = max(maxY, r.bottom)
        return Region(minX, maxX, minY, maxY)


