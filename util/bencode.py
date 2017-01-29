from collections import OrderedDict


def loads(s):
    """将传入的B编码字节数组转为相应的Python对象"""
    obj, residue = _read(s)
    return obj


def _read(s):
    if s[0] == ord('i'):
        obj, residue = _read_int(s)
    elif s[0] == ord('l'):
        obj, residue = _read_list(s)
    elif s[0] == ord('d'):
        obj, residue = _read_dict(s)
    else:
        obj, residue = _read_str(s)

    return obj, residue


def _read_str(s):
    index = s.index(ord(':'))
    length = int(s[:index])
    start = index + 1
    end = start + length

    return s[start: end], s[end:],


def _read_int(s):
    index = s.index(ord('e'))

    return int(s[1:index]), s[index + 1:]


def _read_list(s):
    obj = list()
    residue = s[1:]
    while residue[0] != ord('e'):
        o, residue = _read(residue)
        obj.append(o)

    return obj, residue[1:]


def _read_dict(s):
    obj = OrderedDict()
    residue = s[1:]
    while residue[0] != ord('e'):
        key, residue = _read(residue)
        value, residue = _read(residue)
        obj[key] = value

    return obj, residue[1:]


def dumps(obj):
    """将传入的对象转换为B编码字节数组"""
    s = _trans(obj)
    return s


def _trans(obj):
    s = str()
    if isinstance(obj, int):
        s = _trans_int(obj)
    elif isinstance(obj, bytes):
        s = _trans_str(obj)
    elif isinstance(obj, list):
        s = _trans_list(obj)
    elif isinstance(obj, dict):
        s = _trans_dict(obj)

    return s


def _trans_int(obj):
    s = ('i%de' % obj).encode()
    return s


def _trans_str(obj):
    s = (str(len(obj)) + ':').encode() + obj
    return s


def _trans_list(obj):
    s = b'l'
    for item in obj:
        s += _trans(item)
    s += b'e'

    return s


def _trans_dict(obj):
    s = b'd'
    for key, value in obj.items():
        s += _trans(key)
        s += _trans(value)
    s += b'e'

    return s
