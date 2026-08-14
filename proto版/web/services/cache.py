#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""进程内 LRU + TTL 缓存。

数据只增不改，缓存安全。key 由 FilterSpec.cache_key() 生成。
"""
import os
import sys
import time
from collections import OrderedDict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import config  # noqa: E402

_store = OrderedDict()  # key -> (expire_ts, value)


def get(key):
    item = _store.get(key)
    if item is None:
        return None
    expire_ts, value = item
    if time.time() > expire_ts:
        _store.pop(key, None)
        return None
    _store.move_to_end(key)
    return value


def set(key, value, ttl=None):
    ttl = ttl or config.CACHE_TTL
    _store[key] = (time.time() + ttl, value)
    _store.move_to_end(key)
    # 超上限淘汰最旧
    while len(_store) > config.CACHE_MAXSIZE:
        _store.popitem(last=False)


def clear():
    _store.clear()
