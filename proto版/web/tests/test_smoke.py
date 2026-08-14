#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""API 冒烟测试：各端点状态码 / 无 undefined/NaN / 空数据友好。

运行:
  /usr/local/bin/python3.13 web/tests/test_smoke.py
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # web/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))  # proto版/

import web.app as appmod  # noqa: E402

app = appmod.app
client = app.test_client()

QS = 'date_start=2026-08-12&date_end=2026-08-12'
QS_EMPTY = 'date_start=2099-01-01&date_end=2099-01-02'

ENDPOINTS = [
    '/health', '/api/meta', '/api/regions',
    f'/api/dashboard?{QS}',
    f'/api/overview?{QS}', f'/api/modules?{QS}', f'/api/fields?{QS}',
    f'/api/top5?{QS}', f'/api/weather-mismatch?{QS}', f'/api/cities?{QS}',
    f'/api/trend?{QS}&dim=overall', f'/api/detail?{QS}&page=1&per_page=5',
    f'/api/report/md?{QS}',
    f'/api/city/北京市?{QS}',
]


def test_endpoints():
    print('=== 正常数据端点 ===')
    fails = 0
    for path in ENDPOINTS:
        r = client.get(path)
        ok = r.status_code == 200
        body = {}
        try:
            body = json.loads(r.data)
        except Exception:
            ok = False
        s = json.dumps(body)
        if 'undefined' in s or 'NaN' in s:
            ok = False
        if ok and 'error' in body:
            ok = False
        status = '✅' if ok else '❌'
        if not ok:
            fails += 1
        print(f'  {status} {path.split("?")[0]:28s} HTTP {r.status_code}')
    return fails


def test_empty():
    print('\n=== 空数据场景（应 200 + 空数据，不报错）===')
    fails = 0
    for name in ['overview', 'modules', 'fields', 'top5', 'weather-mismatch',
                 'cities', 'trend', 'report/md']:
        r = client.get(f'/api/{name}?{QS_EMPTY}')
        body = json.loads(r.data)
        ok = r.status_code == 200 and 'error' not in body
        status = '✅' if ok else '❌'
        if not ok:
            fails += 1
        print(f'  {status} /api/{name}')
    return fails


def test_errors():
    print('\n=== 错误处理（应 4xx 友好提示，不 500/白屏）===')
    fails = 0
    cases = [
        ('/api/nonexistent', 404),
        ('/api/overview?date_start=abc', 400),
    ]
    for path, expect in cases:
        r = client.get(path)
        body = json.loads(r.data)
        ok = r.status_code == expect and ('error' in body or r.status_code == 404)
        status = '✅' if ok else '❌'
        if not ok:
            fails += 1
        print(f'  {status} {path} HTTP {r.status_code} (期望 {expect})')
    return fails


def test_report_generate():
    print('\n=== 报告生成 ===')
    r = client.post('/api/report/generate', json={'date_start': '2026-08-12', 'date_end': '2026-08-12'})
    body = json.loads(r.data)
    ok = r.status_code == 200 and 'error' not in body and body['data'].get('md')
    print(f'  {"✅" if ok else "❌"} POST /api/report/generate → md_len={len(body.get("data", {}).get("md", ""))}')
    return 0 if ok else 1


def main():
    f = 0
    f += test_endpoints()
    f += test_empty()
    f += test_errors()
    f += test_report_generate()
    print(f'\n=== 冒烟结果: {"全部通过 🎉" if f == 0 else f"{f} 项失败 ❌"} ===')
    sys.exit(1 if f else 0)


if __name__ == '__main__':
    main()
