import threading
import queue
import socket
import logging
import multiprocessing
import sys

from util import *
from routetab import RouteTable
from node import *
from config import *


class Spider(multiprocessing.Process):
    def __init__(self, ip, port):
        super().__init__()
        self.node_id = randomid()
        self.route_table = RouteTable(self.node_id)
        self.addr = (ip, port)
        self.sender = None
        self.recver = None

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(self.addr)
        self.sender = MsgSender(sock)
        self.recver = MsgReceiver(sock)

        self.sender.start()
        self.recver.start()
        self.join_dht()
        clock = time.time()
        while True:
            try:
                try:
                    msg, addr = self.recver.recv()
                    self.msg_handler(msg, addr)
                except queue.Empty:
                    pass
                if time.time() - clock > 5 * 60:
                    self.fresh()
                    clock = time.time()
            except:
                pass

    def join_dht(self):
        for addr in start_url:
            self.find_node(addr, self.node_id)

    def fresh(self):
        nodes, buckets = self.route_table.clean()
        for node in nodes:
            self.ping(node)
        for bucket in buckets:
            node = bucket.rand_node()
            if node:
                self.find_node(node, self.node_id)

    def msg_handler(self, msg, addr):
        node = self.route_table.get_node(addr)
        if node:
            node.fresh()
            self.route_table.get_bucket(node).fresh()

        try:
            t = msg[b't']
            y = msg[b'y']
            if y == b'q':
                q = msg[b'q']
                a = msg[b'a']
                node = node if node else Node(a[b'id'], addr)
                self.req_handler(t, q, a, node)
            elif y == b'r':
                r = msg[b'r']
                node = node if node else Node(r[b'id'], addr)
                self.resp_handler(r, node)

                if node not in self.route_table:
                    self.route_table.insert(node)
        except KeyError:
            logging.debug('Unknown msg: [%s] from [%s:%d]' % (dict(msg), addr[0], addr[1]))
            # logging.warning(sys.exc_info()[:2])

    def req_handler(self, t, q, a, node):
        if node not in self.route_table:
            self.find_node(node, self.node_id)

        def ping():
            r = {b'id': self.node_id}
            logging.debug('Recv req(ping) from %s' % node)
            self.resp(node, t, r)

        def find_node():
            target = a[b'target']
            nodes = self.route_table.get_neighbor(target)
            r = {
                b'id': self.node_id,
                b'nodes': pack_nodes(nodes),
            }
            logging.debug('Recv req(find_node) from %s' % node)
            self.resp(node, t, r)

        def get_peers():
            info_hash = a[b'info_hash']
            nodes = self.route_table.get_neighbor(info_hash)
            b_str = pack_nodes(nodes)
            r = {
                b'id': self.node_id,
                b'nodes': b_str,
                b'token': randomid(8),
            }
            logging.debug('Recv req(get_peers)[%s] from %s' % (info_hash.hex(), node))
            self.resp(node, t, r)
            for nd in self.route_table.nodes():
                self.get_peers(nd, info_hash)

        def announce_peer():
            r = {b'id': self.node_id}
            self.resp(node, t, r)
            info_hash = a[b'info_hash']
            logging.info('Recv [magnet:?xt=urn:btih:%s]' % info_hash.hex())

        handlers = {
            b'ping': ping,
            b'find_node': find_node,
            b'get_peers': get_peers,
            b'announce_peer': announce_peer,
        }
        try:
            handlers[q]()
        except KeyError:
            logging.debug('Unknown request type: %s' % q)

    def resp_handler(self, r, node):
        # self.find_node(node, self.node_id)
        try:
            nodes = unpack_nodes(r[b'nodes'])
            logging.debug('Recv %d nodes from %s' % (len(nodes), node))
            for nd in nodes:
                self.route_table.insert(nd)
                self.find_node(nd, self.node_id)
            logging.debug('You already have %d nodes.' % len(self.route_table))
        except KeyError:
            pass

    def req(self, node, q, a):
        if isinstance(node, Node):
            addr = node.addr
            logging.debug('Send req(%s) to %s' % (q.decode(), node))
        else:
            addr = node
            logging.debug('Send req(%s) to %s:%d' % (q.decode(), addr[0], addr[1]))
        msg = {
            b'y': b'q',
            b'q': q,
            b'a': a,
            b't': randomid(4)
        }
        self.sender.send(msg, addr)

    def resp(self, node, t, r):
        if isinstance(node, Node):
            addr = node.addr
        else:
            addr = node
        msg = {
            b'y': b'r',
            b't': t,
            b'r': r,
        }
        self.sender.send(msg, addr)

    def ping(self, node):
        q = b'ping'
        a = {b'id': self.node_id}
        self.req(node, q, a)

    def find_node(self, node, target):
        q = b'find_node'
        a = {
            b'id': self.node_id,
            b'target': target
        }
        self.req(node, q, a)

    def get_peers(self, node, info_hash):
        q = b'get_peers'
        a = {
            b'id': self.node_id,
            b'info_hash': info_hash
        }
        self.req(node, q, a)


class MsgSender(threading.Thread):
    def __init__(self, sock):
        super().__init__()
        self.sock = sock
        self.buf = queue.Queue()
        # self.pool = threadpool.ThreadPool(5)

    def run(self):
        while True:
            data, addr = self.buf.get()
            # self.pool.add_task(self.sock.sendto, data, addr)
            try:
                self.sock.sendto(data, addr)
            except:
                pass
            self.buf.task_done()

    def send(self, msg, addr):
        self.buf.join()
        data = bencode.dumps(msg)
        self.buf.put((data, addr))


class MsgReceiver(threading.Thread):
    def __init__(self, sock):
        super().__init__()
        self.sock = sock
        self.buf = queue.Queue()

    def run(self):
        while True:
            self.buf.join()
            data, addr = self.sock.recvfrom(65535)
            self.buf.put((data, addr))

    def recv(self):
        data, addr = self.buf.get_nowait()
        self.buf.task_done()
        return bencode.loads(data), addr
