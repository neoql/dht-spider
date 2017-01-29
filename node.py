import time
import socket
import struct

from bitstring import BitArray


class Node(object):
    def __init__(self, node_id, addr):
        self.nid = BitArray(bytes=node_id)
        self.addr = addr
        self.dubious = False
        self.is_bad = False
        self.last_fresh = time.time()

    def is_good(self):
        return time.time() - self.last_fresh < 5 * 60

    def fresh(self):
        self.dubious = False
        self.is_bad = False
        self.last_fresh = time.time()

    def __repr__(self):
        return 'Node(%s, %s)' % (self.nid.bytes.hex(), self.addr)

    def pack(self):
        node_id = self.nid.bytes
        ip, port = self.addr
        ip = socket.inet_aton(ip)
        port = struct.pack('!H', port)
        return node_id + ip + port


def unpack_nodes(b_str):
    nodes = []
    for i in range(len(b_str) // 26):
        info = b_str[i * 26: i * 26 + 26]
        node_id = info[:20]
        ip = socket.inet_ntoa(info[20:24])
        port = struct.unpack('!H', info[24:])[0]
        nodes.append(Node(node_id, (ip, port)))
    return nodes


def pack_nodes(nodes):
    b_str = b''
    for node in nodes:
        b_str += node.pack()
    return b_str
