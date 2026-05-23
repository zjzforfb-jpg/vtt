import os
import json
import asyncio
from typing import List, Dict, Any, Optional

import httpx

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-chat"

BATCH_SIZE = 15

SYSTEM_PROMPT = """You are a professional English subtitle proofreader. Given a recognized (ASR) subtitle text and its reference original subtitle text, correct the recognized text.

Rules:
1. Use the reference original text to verify content accuracy - fix any misrecognized words.
2. Add proper capitalization (sentence start, proper nouns like Stella, Benjamin).
3. Add appropriate punctuation (. ! ?) at the end of each sentence.
4. Fix common contractions (dont→don't, its→it's, im→I'm, cant→can't, wont→won't, etc.).
5. Do NOT change names to different names - trust the recognized text's names (e.g. keep "Stella" even if reference says "Zhuang Xianhui").
6. If the reference text is empty or clearly different, just clean up the recognized text (capitalization + punctuation).
7. Output ONLY the corrected English text, nothing else."""


def build_batch_prompt(entries: List[Dict[str, str]]) -> str:
    parts = []
    for i, entry in enumerate(entries):
        rec = entry.get("recognized", "")
        ref = entry.get("reference", "")
        parts.append(f"[{i}]\nRECOGNIZED: {rec}\nREFERENCE: {ref}")
    separator = "\n\n"
    return separator.join(parts)


async def correct_batch_with_ai(entries: List[Dict[str, str]]) -> List[str]:
    if not DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY 环境变量未设置")

    prompt = build_batch_prompt(entries)

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": DEEPSEEK_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Correct each recognized text below using its reference as a guide. Output ONLY the corrected text for each item, one per line, prefixed with the item number like [0] corrected text, [1] corrected text, etc.\n\n{prompt}"},
                ],
                "temperature": 0.1,
                "max_tokens": 4000,
            },
        )

        if response.status_code != 200:
            raise Exception(f"DeepSeek API error: {response.status_code} - {response.text}")

        result = response.json()
        content = result["choices"][0]["message"]["content"]

    return parse_batch_response(content, len(entries))


def parse_batch_response(content: str, expected_count: int) -> List[str]:
    results = [""] * expected_count
    lines = content.strip().split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        import re
        match = re.match(r'\[(\d+)\]\s*(.*)', line)
        if match:
            idx = int(match.group(1))
            text = match.group(2).strip()
            if 0 <= idx < expected_count:
                results[idx] = text

    return results


async def ai_correct_entries(
    recognized_entries: List[Dict[str, Any]],
    original_entries: List[Dict[str, Any]],
    aligned_data: List[Dict[str, Any]],
) -> Dict[str, Any]:
    all_entries = []
    matched_original_indices = set()

    for i, aligned in enumerate(aligned_data):
        if aligned.get("matched_original_index"):
            matched_original_indices.add(aligned["matched_original_index"])

    for _, aligned in enumerate(aligned_data):
        rec_text = aligned.get("text", "")
        orig_text = aligned.get("original_text", "") or ""
        match_score = aligned.get("match_score", 0.0)

        all_entries.append({
            "index": aligned["index"],
            "time": f"{aligned['start_time']} --> {aligned['end_time']}",
            "recognized": rec_text,
            "reference": orig_text,
            "match_score": match_score,
            "matched_original_index": aligned.get("matched_original_index"),
            "type": "matched" if aligned.get("matched_original_index") else "extra",
        })

    batches = []
    batch_entries = []
    for i, entry in enumerate(all_entries):
        batch_entries.append({
            "recognized": entry["recognized"],
            "reference": entry["reference"],
        })
        if len(batch_entries) >= BATCH_SIZE or i == len(all_entries) - 1:
            batches.append(batch_entries)
            batch_entries = []

    all_corrected = []
    for batch in batches:
        try:
            corrected = await correct_batch_with_ai(batch)
            all_corrected.extend(corrected)
        except Exception:
            all_corrected.extend([""] * len(batch))

    timeline = []
    for i, entry in enumerate(all_entries):
        ai_text = all_corrected[i] if i < len(all_corrected) else ""
        rec_text = entry["recognized"]

        if ai_text and ai_text.strip():
            corrected_text = ai_text.strip()
        else:
            from srt_processor.text_corrector import capitalize_text
            corrected_text = capitalize_text(rec_text)

        has_changes = corrected_text.lower().strip() != rec_text.lower().strip()

        timeline.append({
            "entry_index": entry["index"],
            "time": entry["time"],
            "recognized_text": rec_text,
            "corrected_text": corrected_text,
            "original_text": entry["reference"] or "",
            "chinese": "",
            "match_score": entry["match_score"],
            "status": "modified" if has_changes else "unchanged",
            "source": "ai",
        })

    missing_entries = []
    for orig_entry in original_entries:
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
                "source": "ai",
            })

    for missing in missing_entries:
        insert_idx = 0
        missing_start = _parse_time(missing["time"].split("-->")[0].strip())
        for j, t_entry in enumerate(timeline):
            t_start = _parse_time(t_entry["time"].split("-->")[0].strip())
            if missing_start < t_start:
                break
            insert_idx = j + 1
        timeline.insert(insert_idx, missing)

    return {
        "timeline": timeline,
        "stats": {
            "total_entries": len(timeline),
            "modified_count": sum(1 for t in timeline if t["status"] == "modified"),
            "unchanged_count": sum(1 for t in timeline if t["status"] == "unchanged"),
            "missing_count": len(missing_entries),
            "extra_count": sum(1 for t in timeline if t.get("type") == "extra" and t["status"] != "missing"),
        }
    }


def _parse_time(time_str: str) -> int:
    import re
    match = re.match(r'(\d{2}):(\d{2}):(\d{2}),(\d{3})', time_str.strip())
    if not match:
        return 0
    h, m, s, ms = map(int, match.groups())
    return h * 3600000 + m * 60000 + s * 1000 + ms
