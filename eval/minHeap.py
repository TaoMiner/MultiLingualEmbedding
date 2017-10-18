import heapq

class MinHeap(object):
    def __init__(self, k):
        self.k = k
        self.data = []

    def Push(self, elem):
        # Reverse elem to convert to max-heap
        elem = -elem
        # Using heap algorighem
        if len(self.data) < self.k:
            heapq.heappush(self.data, elem)
        else:
            topk_small = self.data[0]
            if elem > topk_small:
                heapq.heapreplace(self.data, elem)

    def topN(self):
        return sorted([-x for x in self.data])

if __name__ == '__main__':
    topn = 3
    a = [2,45,3,1,213,10]

    bh = MinHeap(topn)
    for i in range(len(a)):
        bh.Push(a[i])
    print bh.topN()