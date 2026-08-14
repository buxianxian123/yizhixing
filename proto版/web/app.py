#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""墨迹天气 国内/国际 数据一致性比对平台 — Flask 入口。

直接连 weather_data.db，提供：
  - 在线交互式分析（筛选 / 图表 / 表格 / 钻取）
  - 批次灵活比对（单批次 / 多批次趋势 / A/B 组比较）
  - 生成 Markdown 报告（复用现有 gen_md_report.py，口径与旧 CLI 完全一致）

启动:
  /usr/local/bin/python3.13 web/app.py
  浏览器打开 http://localhost:5000
"""
import os
import sys
import time
import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))  # web/
PROTO_DIR = os.path.dirname(SCRIPT_DIR)                   # proto版/
for p in (SCRIPT_DIR, PROTO_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from flask import Flask, jsonify, render_template, request, send_from_directory  # noqa: E402

import config  # noqa: E402
import reformat_threshold as rt  # noqa: E402

from repository import connection as repo_conn  # noqa: E402
from repository import meta as repo_meta  # noqa: E402
from repository import points as repo_points  # noqa: E402
from services import filters as svc_filters  # noqa: E402
from services import compare as svc_compare  # noqa: E402
from services import aggregation as svc_agg  # noqa: E402
from services import report as svc_report  # noqa: E402
from services import cache as svc_cache  # noqa: E402


def create_app():
    app = Flask(__name__)
    app.config['JSON_AS_ASCII'] = False
    app.config['JSON_SORT_KEYS'] = False

    # 启动时初始化比对规则常量（load_cities 会设置全局 CITY_RANK）
    try:
        rt.load_cities()
    except Exception as e:
        print(f"[WARN] load_cities 失败: {e}")

    # ============ 错误处理 ============
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': '接口不存在'}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({'error': f'服务异常: {e}'}), 500

    # ============ 页面 ============
    @app.route('/')
    def index():
        return render_template('index.html')

    # ============ 健康检查 ============
    @app.route('/health')
    def health():
        h = repo_conn.check_healthy()
        return jsonify({'ok': h['db_exists'] and all(v is not None for v in h['tables'].values()),
                        **h})

    # ============ 元数据 ============
    @app.route('/api/meta')
    def api_meta():
        try:
            return _ok(repo_meta.get_meta())
        except Exception as e:
            return _err(e)

    @app.route('/api/regions')
    def api_regions():
        try:
            return _ok(repo_meta.get_region_tree())
        except Exception as e:
            return _err(e)

    # ============ 分析端点 ============
    @app.route('/api/dashboard')
    def api_dashboard():
        """组合端点：一次 DB 读取 + 比对，返回全部聚合数据。
        替代前端并行请求 7 个独立端点（各自重复 read_points + compare_points）。
        """
        t0 = time.time()
        try:
            fs = svc_filters.parse_args(request.args)
        except ValueError as e:
            return jsonify({'error': str(e)}), 400

        cache_key = f'dashboard:{fs.cache_key()}'
        cached = svc_cache.get(cache_key)
        if cached is not None:
            data, meta = cached
            meta['cached'] = True
            meta['elapsed_ms'] = int((time.time() - t0) * 1000)
            return jsonify({'data': data, 'meta': meta})

        try:
            conn = repo_conn.get_conn()
            try:
                pts, pulls = repo_points.read_points(conn, fs)
            finally:
                conn.close()
        except Exception as e:
            return jsonify({'error': f'数据库查询失败: {e}'}), 500

        try:
            results = svc_compare.compare_points(pts)
        except Exception as e:
            return jsonify({'error': f'比对失败: {e}'}), 500

        try:
            data = {
                'overview': svc_agg.overview(results, fs),
                'modules': svc_agg.module_rows(results),
                'fields': svc_agg.summary_rows(results),
                'top5': svc_agg.top5_rows(results),
                'weather_mismatch': svc_agg.weather_mismatch(results),
                'cities': svc_agg.city_rows(results, fs),
                'trend': svc_agg.trend_rows(results, fs),
            }
        except Exception as e:
            return jsonify({'error': f'分析失败: {e}'}), 500

        meta = {
            'filter_snapshot': fs.snapshot(),
            'pulls': len(pulls),
            'points': len(results),
            'elapsed_ms': int((time.time() - t0) * 1000),
        }
        svc_cache.set(cache_key, (data, meta), ttl=config.CACHE_TTL)
        return jsonify({'data': data, 'meta': meta})

    @app.route('/api/overview')
    def api_overview():
        return _with_points('overview', svc_agg.overview)

    @app.route('/api/modules')
    def api_modules():
        return _with_points('modules', svc_agg.module_rows)

    @app.route('/api/fields')
    def api_fields():
        return _with_points('fields', svc_agg.summary_rows)

    @app.route('/api/trend')
    def api_trend():
        return _with_points('trend', svc_agg.trend_rows)

    @app.route('/api/cities')
    def api_cities():
        return _with_points('cities', svc_agg.city_rows)

    @app.route('/api/top5')
    def api_top5():
        return _with_points('top5', svc_agg.top5_rows)

    @app.route('/api/weather-mismatch')
    def api_weather_mismatch():
        return _with_points('weather-mismatch', svc_agg.weather_mismatch)

    @app.route('/api/detail')
    def api_detail():
        return _with_points('detail', svc_agg.detail_rows)

    @app.route('/api/city/<name>')
    def api_city(name):
        return _with_points('city-detail', lambda r, fs: svc_agg.city_detail(r, fs, name))

    # ============ 批次比较 ============
    @app.route('/api/compare')
    def api_compare():
        return _with_points('compare', svc_agg.compare_rows)

    # ============ 报告 ============
    @app.route('/api/report/md')
    def api_report_md():
        try:
            fs = svc_filters.parse_args(request.args)
            md, tables, meta = svc_report.build_report_view(fs)
            return _ok({'md': md, 'tables': tables, 'meta': meta})
        except Exception as e:
            return _err(e)

    @app.route('/api/report/generate', methods=['POST'])
    def api_report_generate():
        try:
            payload = request.get_json(silent=True) or {}
            fs = svc_filters.parse_payload(payload)
            res = svc_report.generate_report(fs)
            return _ok(res)
        except Exception as e:
            return _err(e)

    @app.route('/report/<path:filename>')
    def report_file(filename):
        return send_from_directory(config.REPORT_DIR, filename)

    return app


# ============ 统一响应 / 错误 ============
def _ok(data, extra_meta=None):
    resp = {'data': data, 'meta': {'elapsed_ms': 0}}
    if extra_meta:
        resp['meta'].update(extra_meta)
    return jsonify(resp)


def _err(e, code=400):
    return jsonify({'error': str(e)}), code


def _with_points(endpoint, fn):
    """通用包装：解析筛选 → 读比对点 → 比对 → 聚合 → 缓存 → 返回。
    fn(results, filter_spec) -> JSON 数据。
    """
    t0 = time.time()
    try:
        fs = svc_filters.parse_args(request.args)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    cache_key = f'{endpoint}:{fs.cache_key()}'
    cached = svc_cache.get(cache_key)
    if cached is not None:
        data, meta = cached
        meta['cached'] = True
        meta['elapsed_ms'] = int((time.time() - t0) * 1000)
        return jsonify({'data': data, 'meta': meta})

    try:
        conn = repo_conn.get_conn()
        try:
            pts, pulls = repo_points.read_points(conn, fs)
        finally:
            conn.close()
    except Exception as e:
        return jsonify({'error': f'数据库查询失败: {e}'}), 500

    try:
        results = svc_compare.compare_points(pts)
    except Exception as e:
        return jsonify({'error': f'比对失败: {e}'}), 500

    try:
        import inspect
        if len(inspect.signature(fn).parameters) >= 2:
            data = fn(results, fs)
        else:
            data = fn(results)
    except Exception as e:
        return jsonify({'error': f'分析失败: {e}'}), 500
    meta = {
        'filter_snapshot': fs.snapshot(),
        'pulls': len(pulls),
        'points': len(results),
        'elapsed_ms': int((time.time() - t0) * 1000),
    }
    svc_cache.set(cache_key, (data, meta), ttl=config.CACHE_TTL)
    return jsonify({'data': data, 'meta': meta})


app = create_app()

if __name__ == '__main__':
    print(f"数据源: {config.DB_PATH}")
    print("启动平台: http://localhost:5000")
    app.run(host='127.0.0.1', port=5000, debug=False, threaded=True)
