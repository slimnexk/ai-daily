#!/usr/bin/env python3
"""
迁移脚本：将 data.json 中 dates.日期 拆分为独立 daily/YYYY-MM-DD.json 文件。
同时生成一个汇总 data.json (只保留dates元数据，用于日历标记)。
"""
import json, os, pathlib

ROOT = pathlib.Path(__file__).parent
DATA_FILE = ROOT / 'data.json'
DAILY_DIR = ROOT / 'daily'

def migrate():
    # 读取现有 data.json
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 创建 daily 目录
    DAILY_DIR.mkdir(exist_ok=True)

    # 提取每个日期的数据到独立文件
    meta_dates = {}
    for date_str, day_data in data.get('dates', {}).items():
        daily_file = DAILY_DIR / f'{date_str}.json'
        with open(daily_file, 'w', encoding='utf-8') as f:
            json.dump(day_data, f, ensure_ascii=False, indent=2)
        
        # 提取元数据（标题+desc，便于日历显示摘要）
        meta_dates[date_str] = {
            'title': day_data.get('title', ''),
            'desc': day_data.get('desc', '')
        }
        ok = 'OK'; print(f'[{ok}] 已导出: daily/{date_str}.json')

    # 更新 data.json: 只保留标题+desc+日期的元数据列表
    new_data = {
        'title': data.get('title', ''),
        'desc': data.get('desc', ''),
        'dates': meta_dates  # 只保留标题+desc，不包含完整内容
    }
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)
    
    print(f'\n[OK] 迁移完成！共导出 {len(meta_dates)} 天数据')
    print(f'   daily/目录: {len(meta_dates)} 个独立JSON文件')
    print(f'   data.json: 精简为元数据（{len(meta_dates)} 条日期记录）')
    print(f'   index.html 现在将按需加载 daily/日期.json')

if __name__ == '__main__':
    migrate()
