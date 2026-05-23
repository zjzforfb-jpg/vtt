from typing import List, Dict, Any, Optional
from srt_processor.srt_parser import parse_srt, format_srt, SRTEntry
from srt_processor.text_matcher import align_subtitles
from srt_processor.text_corrector import capitalize_text, correct_text_with_original


def _parse_time_ms(time_str: str) -> int:
    import re
    m = re.match(r'(\d{2}):(\d{2}):(\d{2}),(\d{3})', time_str.strip())
    if not m:
        return 0
    h, mi, s, ms = map(int, m.groups())
    return h * 3600000 + mi * 60000 + s * 1000 + ms


def _build_timeline(aligned_entries, original_data, matched_original_indices, source="rule") -> Dict[str, Any]:
    timeline = []

    for aligned in aligned_entries:
        rec_text = aligned.get("text", "")
        orig_text = aligned.get("original_text", "") or ""
        match_score = aligned.get("match_score", 0.0)
        has_match = aligned.get("matched_original_index") is not None

        if has_match and orig_text:
            correction = correct_text_with_original(rec_text, orig_text)
            corrected_text = correction["corrected_text"]
        else:
            corrected_text = capitalize_text(rec_text)

        has_changes = corrected_text.lower().strip() != rec_text.lower().strip()
        is_extra = not has_match or match_score <= 0.4

        chinese = ""
        if has_match:
            match_idx = aligned["matched_original_index"] - 1
            if 0 <= match_idx < len(original_data):
                chinese = original_data[match_idx].get("chinese", "") or ""

        status = "unchanged"
        if has_changes and not is_extra:
            status = "modified"
        elif is_extra:
            status = "extra"

        timeline.append({
            "entry_index": aligned["index"],
            "time": f"{aligned['start_time']} --> {aligned['end_time']}",
            "recognized_text": rec_text,
            "corrected_text": corrected_text,
            "original_text": orig_text,
            "chinese": chinese,
            "match_score": match_score,
            "status": status,
            "source": source,
        })

    missing_entries = []
    for orig_entry in original_data:
        if orig_entry["index"] not in matched_original_indices:
            missing_entries.append({
                "entry_index": orig_entry["index"],
                "time": f"{orig_entry['start_time']} --> {orig_entry['end_time']}",
                "recognized_text": "",
                "corrected_text": orig_entry.get("english", "") or "",
                "original_text": orig_entry.get("english", "") or "",
                "chinese": orig_entry.get("chinese", "") or "",
                "match_score": 0,
                "status": "missing",
                "source": source,
            })

    for missing in missing_entries:
        insert_idx = len(timeline)
        missing_start = _parse_time_ms(missing["time"].split("-->")[0].strip())
        for j, t_entry in enumerate(timeline):
            t_start = _parse_time_ms(t_entry["time"].split("-->")[0].strip())
            if missing_start < t_start:
                insert_idx = j
                break
        timeline.insert(insert_idx, missing)

    stats = {
        "total_entries": len(timeline),
        "modified_count": sum(1 for t in timeline if t["status"] == "modified"),
        "unchanged_count": sum(1 for t in timeline if t["status"] == "unchanged"),
        "missing_count": sum(1 for t in timeline if t["status"] == "missing"),
        "extra_count": sum(1 for t in timeline if t["status"] == "extra"),
    }

    return {"timeline": timeline, "stats": stats}


def process_subtitles(original_srt: str, recognized_srt: str) -> Dict[str, Any]:
    original_entries = parse_srt(original_srt, is_original=True)
    recognized_entries = parse_srt(recognized_srt, is_original=False)

    recognized_data = []
    for entry in recognized_entries:
        recognized_data.append({
            'index': entry.index,
            'start_time': entry.start_time,
            'end_time': entry.end_time,
            'text': entry.english or entry.text
        })

    original_data = []
    for entry in original_entries:
        original_data.append({
            'index': entry.index,
            'start_time': entry.start_time,
            'end_time': entry.end_time,
            'text': entry.text,
            'english': entry.english,
            'chinese': entry.chinese
        })

    aligned_entries = align_subtitles(recognized_data, original_data)

    corrected_entries = []
    matched_original_indices = set()

    for entry in aligned_entries:
        rec_text = entry.get('text', '')
        orig_text = entry.get('original_text', '')
        match_score = entry.get('match_score', 0.0)

        if orig_text and match_score > 0.4:
            correction_result = correct_text_with_original(rec_text, orig_text)
            corrected_text = correction_result['corrected_text']
            if entry.get('matched_original_index'):
                matched_original_indices.add(entry['matched_original_index'])
        else:
            corrected_text = capitalize_text(rec_text)

        corrected_entry = SRTEntry(
            index=entry['index'],
            start_time=entry['start_time'],
            end_time=entry['end_time'],
            text=corrected_text,
            speaker=None,
            chinese=None,
            english=corrected_text
        )
        corrected_entries.append(corrected_entry)

    corrected_srt = format_srt(corrected_entries)

    timeline_result = _build_timeline(aligned_entries, original_data, matched_original_indices, source="rule")

    corrections_log = []
    for t in timeline_result["timeline"]:
        if t["status"] == "modified":
            corrections_log.append({
                "entry_index": t["entry_index"],
                "original_recognized": t["recognized_text"],
                "corrected": t["corrected_text"],
                "matched_original": t["original_text"],
                "match_score": t["match_score"],
                "changes": []
            })

    return {
        'corrected_srt': corrected_srt,
        'timeline': timeline_result["timeline"],
        'stats': timeline_result["stats"],
        'corrections': corrections_log,
    }
