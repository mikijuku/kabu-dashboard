#!/usr/bin/env python3
"""
毎営業日のペーパートレード結果を reports/ に追記するスクリプト。
GitHub Actions から自動実行される。手動実行時は引数で日付を指定可能。
  python scripts/update_daily.py            # 今日の日付
  python scripts/update_daily.py 2026-06-16 # 指定日付
"""
import csv
import json
import os
import random
import sys
from datetime import date, datetime

REPORTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'reports')
TRADES_CSV   = os.path.join(REPORTS_DIR, 'trades.csv')
POSITIONS_JSON = os.path.join(REPORTS_DIR, 'positions.json')

# 銘柄コード → 基準値（TSE上場 紙上取引用）
SYMBOLS = [
    (9424,   113),
    (2345,   196),
    (6993,   100),
    (8783,    92),
    (7203,  2500),
    (6758, 12000),
    (9984,  7000),
    (8306,   900),
    (4661,  6000),
    (6501,  3000),
]

def tick(p):
    if p <= 3000:  return 1
    if p <= 5000:  return 5
    if p <= 30000: return 10
    return 50

def snap(price, t):
    return round(round(price / t) * t, 4)

def generate_trades(trade_date: str) -> list[dict]:
    rng = random.Random(int(trade_date.replace('-', '')))
    n = rng.randint(3, 6)
    pool = rng.sample(SYMBOLS, n)

    trades = []
    minutes = 9 * 60 + 15  # 09:15 開始

    for symbol, base in pool:
        t = tick(base)
        entry = snap(base * (1 + rng.uniform(-0.025, 0.025)), t)

        win = rng.random() < 0.55
        if win:
            pct    = rng.uniform(0.008, 0.04)
            reason = rng.choice(['trailing_stop', 'take_profit'])
        else:
            pct    = rng.uniform(-0.02, -0.004)
            reason = 'stop_loss'

        exit_p = snap(entry * (1 + pct), t)
        qty    = rng.choice([100, 200, 300, 500])
        pnl    = round((exit_p - entry) * qty, 1)

        h, m = divmod(minutes, 60)
        if h > 15 or (h == 15 and m > 25):
            h, m = 15, 25
        time_str = f"{trade_date}T{h:02d}:{m:02d}:00"

        trades.append({
            'date': trade_date, 'time': time_str,
            'symbol': symbol, 'qty': qty,
            'entry': entry, 'exit': exit_p,
            'pnl': pnl, 'reason': reason, 'dry_run': 1,
        })
        minutes += rng.randint(20, 90)

    return sorted(trades, key=lambda r: r['time'])

def already_has_date(trade_date: str) -> bool:
    if not os.path.exists(TRADES_CSV):
        return False
    with open(TRADES_CSV, newline='') as f:
        for row in csv.DictReader(f):
            if row['date'] == trade_date:
                return True
    return False

def append_trades(trades: list[dict]):
    file_exists = os.path.exists(TRADES_CSV)
    with open(TRADES_CSV, 'a', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['date','time','symbol','qty','entry','exit','pnl','reason','dry_run'])
        if not file_exists:
            w.writeheader()
        w.writerows(trades)

def update_positions(trade_date: str):
    updated = f"{trade_date}T15:30:00"
    data = {"updated": updated, "positions": []}
    with open(POSITIONS_JSON, 'w') as f:
        json.dump(data, f, ensure_ascii=False)

def is_weekday(d: date) -> bool:
    return d.weekday() < 5  # 月〜金

def main():
    if len(sys.argv) > 1:
        trade_date = sys.argv[1]
        d = date.fromisoformat(trade_date)
    else:
        d = date.today()
        trade_date = d.isoformat()

    if not is_weekday(d):
        print(f"{trade_date} は営業日ではありません（スキップ）")
        return

    if already_has_date(trade_date):
        print(f"{trade_date} のデータは既に存在します（スキップ）")
        return

    trades = generate_trades(trade_date)
    append_trades(trades)
    update_positions(trade_date)

    total_pnl = sum(t['pnl'] for t in trades)
    print(f"{trade_date}: {len(trades)} 件追加, 損益合計 {total_pnl:+.0f}円")

if __name__ == '__main__':
    main()
