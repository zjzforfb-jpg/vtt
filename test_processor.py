import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))

from srt_processor.processor import process_subtitles

with open('ep047.srt', 'r', encoding='utf-8') as f:
    original_srt = f.read()

with open('47-字幕.srt', 'r', encoding='utf-8') as f:
    recognized_srt = f.read()

print("开始处理字幕...")
result = process_subtitles(original_srt, recognized_srt)

print("\n" + "="*60)
print("统计信息:")
print("="*60)
s = result['stats']
print(f"  总条目: {s['total_entries']}")
print(f"  已修正: {s['modified_count']}")
print(f"  未变化: {s['unchanged_count']}")
print(f"  建议删除: {s['extra_count']}")
print(f"  建议新增: {s['missing_count']}")

print("\n" + "="*60)
print("时间线:")
print("="*60)
for entry in result['timeline']:
    status_emoji = {
        'modified': '✏️',
        'unchanged': '  ',
        'extra': '🔴',
        'missing': '🟡'
    }
    emoji = status_emoji.get(entry['status'], '  ')
    print(f"\n{emoji} #{entry['entry_index']} [{entry['status']}] {entry['time']}")
    if entry.get('chinese'):
        print(f"   中文: {entry['chinese'][:50]}")
    if entry.get('recognized_text'):
        print(f"   识别: {entry['recognized_text']}")
    if entry.get('corrected_text') and entry['status'] != 'unchanged':
        print(f"   校对: {entry['corrected_text']}")
    elif entry.get('corrected_text'):
        print(f"   校对: {entry['corrected_text']}")

print("\n" + "="*60)
print("校对后 SRT (前20行):")
print("="*60)
lines = result['corrected_srt'].split('\n')
for line in lines[:20]:
    print(line)
