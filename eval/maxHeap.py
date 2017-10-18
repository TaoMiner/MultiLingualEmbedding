import heapq

class MaxHeap(object):
    def __init__(self, k):
        self.k = k
        self.data = []

    def clear(self):
        del self.data[:]

    def Push(self, elem):
        res = -1
        if len(self.data) < self.k:
            heapq.heappush(self.data, elem)
            res = 1
        else:
            topk_small = self.data[0]
            if elem > topk_small:
                heapq.heapreplace(self.data, elem)
                res = 1
        return res

    def topN(self):
        return [x for x in reversed([heapq.heappop(self.data) for x in xrange(len(self.data))])]

if __name__ == '__main__':
    topn = 3
    a = [2,45,3,1,213,10]

    bh = MaxHeap(topn)
    for i in range(len(a)):
        res = bh.Push(a[i])
        print "e:%d,res:%d" % (a[i], res)
    print bh.topN()

    bh.clear()
    print bh.topN()