#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""常驻循环：每 interval 秒跑一轮 pull_latest_round.py（实时拉取并写入数据库）。

对比 cron 的好处：Mac 睡眠时进程挂起、醒来自动续跑，不会像 cron 那样错过的轮次直接漏掉。
用法:  cd proto版
      nohup /usr/local/bin/python3 run_pull_loop.py >> ../data/比对结果/pull_loop.log 2>&1 &
停止:  pkill -f run_pull_loop.py
间隔:  SC_INTERVAL 环境变量覆盖, 默认 3600s(1小时)
"""
import os, sys, time, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pull_latest_round

INTERVAL = int(os.environ.get('SC_INTERVAL', 3600))


def now():
    return datetime.datetime.now().strftime('%F %T')


def main():
    round_no = 0
    print(f"[{now()}] 常驻循环启动 (数据库模式), 每 {INTERVAL}s 拉一轮 (Ctrl-C 优雅停止)", flush=True)
    try:
        while True:
            round_no += 1
            print(f"\n===== [{now()}] 第 {round_no} 轮 =====", flush=True)
            pull_latest_round.main()
            print(f"[{now()}] 第 {round_no} 轮完成, 休眠 {INTERVAL}s", flush=True)
            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        print(f"\n[{now()}] 收到 Ctrl-C, 优雅停止 (已完成 {round_no - 1} 轮)", flush=True)


if __name__ == '__main__':
    main()
