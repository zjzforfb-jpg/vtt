from difflib import SequenceMatcher
import re
from typing import List, Tuple, Dict


def normalize_text(text: str) -> str:
    return re.sub(r'[^\w\s]', '', text.lower()).strip()


def calculate_similarity(text1: str, text2: str) -> float:
    return SequenceMatcher(None, normalize_text(text1), normalize_text(text2)).ratio()


def find_best_match_for_entry(recognized_entry: dict, original_entries: List[dict], start_index: int) -> Tuple[int, float, str]:
    rec_text = recognized_entry.get('text', '')
    rec_normalized = normalize_text(rec_text)

    best_match_idx = -1
    best_score = 0.0
    best_combined_text = ''

    for window_size in range(1, 4):
        end_idx = min(start_index + window_size, len(original_entries))

        for i in range(max(0, start_index - 1), end_idx):
            if i + window_size > len(original_entries):
                break

            combined_texts = []
            for j in range(i, min(i + window_size, len(original_entries))):
                orig_text = original_entries[j].get('english', '') or original_entries[j].get('text', '')
                combined_texts.append(orig_text)

            combined = ' '.join(combined_texts)
            score = calculate_similarity(rec_text, combined)

            if score > best_score:
                best_score = score
                best_match_idx = i
                best_combined_text = combined

    return best_match_idx, best_score, best_combined_text


def align_subtitles(
    recognized_entries: List[dict],
    original_entries: List[dict]
) -> List[dict]:
    aligned = []
    original_idx = 0

    for rec_entry in recognized_entries:
        match_idx, score, matched_text = find_best_match_for_entry(rec_entry, original_entries, original_idx)

        if match_idx >= 0 and score > 0.5:
            rec_entry['original_text'] = matched_text
            rec_entry['match_score'] = score
            rec_entry['matched_original_index'] = match_idx + 1

            original_idx = match_idx + 1
        else:
            rec_entry['original_text'] = None
            rec_entry['match_score'] = 0.0
            rec_entry['matched_original_index'] = None

        aligned.append(rec_entry)

    return aligned
