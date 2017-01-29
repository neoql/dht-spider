import random
import struct

from . import bencode


def randomid(length=20):
    return b''.join([struct.pack('B', random.randint(0, 255)) for _ in range(length)])
