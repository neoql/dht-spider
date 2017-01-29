import time
import random

from bitstring import BitArray


k = 8


class RouteTable(object):
    def __init__(self, node_id):
        self.node_id = BitArray(node_id)
        self.root = Bucket(self.node_id)
        self.__nodes = {}

    def insert(self, node):
        if node not in self:
            try:
                self.root = self.root.insert(node)
                self.__nodes[node.addr] = node
            except Trash as trash:
                nd = trash.node
                if nd is not node:
                    del self.__nodes[nd.addr]
                    self.__nodes[node.addr] = node

    def get_neighbor(self, info_hash):
        info_hash = BitArray(info_hash)
        return self.root.get_neighbor(info_hash)[0]

    def get_bucket(self, node):
        if isinstance(self.root, Bucket):
            return self.root
        else:
            return self.root.get_bucket(node)

    def clean(self):
        nodes = []
        buckets = []
        for node in self.nodes():
            if node.is_bad:
                nodes.append(node)
            if node.dubious:
                node.is_bad = True
                nodes.append(node)
            if not node.is_good():
                node.dubious = True
                nodes.append(node)
        for bucket in self.buckets():
            if time.time() - bucket.last_change > 15 * 60:
                buckets.append(bucket)
        return nodes, buckets

    def get_node(self, addr):
        return self.__nodes.get(addr)

    def __contains__(self, node):
        return bool(self.get_node(node.addr))

    def __len__(self):
        return len(self.__nodes)

    def nodes(self):
        for node in self.root.nodes():
            yield node

    def buckets(self):
        if isinstance(self.root, Bucket):
            yield self.root
        else:
            for bucket in self.root.buckets():
                yield bucket


class TreeNode(object):
    def __init__(self, bucket):
        self.depth = bucket.depth
        self.node_id = bucket.node_id

        self.left = Bucket(self.node_id, self.depth + 1)
        self.right = Bucket(self.node_id, self.depth + 1)

        try:
            self.left.me_in = bucket.me_in and not self.node_id[self.depth]
            self.right.me_in = bucket.me_in and self.node_id[self.depth]
        except IndexError as e:
            pass

        for node in bucket:
            self.insert(node)

    def insert(self, node):
        if not node.nid[self.depth]:
            self.left = self.left.insert(node)
        else:
            self.right = self.right.insert(node)
        return self

    def rm_node(self, node):
        if not node.nid[self.depth]:
            self.left.rm_node(node)
        else:
            self.right.rm_node(node)

    def get_neighbor(self, info_hash, n=k):
        if not info_hash[self.depth]:
            a = self.left
            b = self.right
        else:
            a = self.right
            b = self.left
        nodes, num = a.get_neighbor(info_hash, n)
        if num < n:
            _nodes, _n = b.get_neighbor(info_hash, n - num)
            nodes.extend(_nodes)
            num += _n
        return nodes, num

    def get_bucket(self, node):
        if not node.nid[self.depth]:
            gen = self.left
        else:
            gen = self.right
        if isinstance(gen, Bucket):
            return gen
        else:
            return gen.get_bucket(node)

    def nodes(self):
        for node in self.left.nodes():
            yield node
        for node in self.right.nodes():
            yield node

    def buckets(self):
        if isinstance(self.left, Bucket):
            yield self.left
        else:
            for bucket in self.left.buckets():
                yield bucket
        if isinstance(self.right, Bucket):
            yield self.right
        else:
            for bucket in self.right.buckets():
                yield bucket


class Bucket(object):
    def __init__(self, node_id, depth=0):
        self.node_id = node_id
        self.depth = depth
        self.__nodes = []
        self.me_in = True
        self.last_change = time.time()

    def insert(self, node):
        if len(self.__nodes) < k:
            self.__nodes.append(node)
            self.last_change = time.time()
            return self
        elif self.me_in and self.depth < 160:
            tn = TreeNode(self)
            tn.insert(node)
            return tn
        else:
            for nd in self.__nodes:
                if nd.is_bad:
                    self.rm_node(nd)
                    self.__nodes.append(node)
                    self.last_change = time.time()
                    raise Trash(nd)
            raise Trash(node)

    def rand_node(self):
        if len(self.__nodes):
            return self.__nodes[random.randint(0, len(self.__nodes) - 1)]
        else:
            return None

    def rm_node(self, node):
        if node in self.__nodes:
            self.__nodes.remove(node)

    def __iter__(self):
        for node in self.__nodes:
            yield node

    def nodes(self):
        return self

    def get_neighbor(self, info_hash, n=k):
        size = len(self.__nodes)
        n = n if size >= n else size
        return self.__nodes[:n], n

    def fresh(self):
        self.last_change = time.time()


class Trash(Exception):
    def __init__(self, node):
        self.node = node
