import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SRTEntry:
    index: int
    start_time: str
    end_time: str
    text: str
    speaker: Optional[str] = None
    chinese: Optional[str] = None
    english: Optional[str] = None


def parse_time_to_ms(time_str: str) -> int:
    time_str = time_str.strip()
    match = re.match(r'(\d{2}):(\d{2}):(\d{2}),(\d{3})', time_str)
    if not match:
        return 0
    h, m, s, ms = map(int, match.groups())
    return h * 3600000 + m * 60000 + s * 1000 + ms


def parse_srt(content: str, is_original: bool = False) -> List[SRTEntry]:
    content = content.strip()
    blocks = re.split(r'\n\s*\n', content)
    entries = []

    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue

        index = int(lines[0].strip())

        time_match = re.match(
            r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})',
            lines[1]
        )
        if not time_match:
            continue

        start_time = time_match.group(1)
        end_time = time_match.group(2)

        text_lines = lines[2:]

        if is_original:
            speaker = None
            chinese = None
            english = None

            full_text = '\n'.join(text_lines)

            speaker_match = re.match(r'\[(female|male)\](.*?):', text_lines[0])
            if speaker_match:
                speaker = speaker_match.group(2)
                text_lines = text_lines[1:]

            if len(text_lines) >= 2:
                chinese = text_lines[0]
                english = text_lines[1] if len(text_lines) > 1 else ''
            elif len(text_lines) == 1:
                chinese = text_lines[0]
                english = ''

            text = full_text
        else:
            speaker = None
            chinese = None
            english = '\n'.join(text_lines).strip()
            text = english

        entry = SRTEntry(
            index=index,
            start_time=start_time,
            end_time=end_time,
            text=text,
            speaker=speaker,
            chinese=chinese,
            english=english
        )
        entries.append(entry)

    return entries


def format_srt(entries: List[SRTEntry]) -> str:
    output = []
    for entry in entries:
        output.append(str(entry.index))
        output.append(f"{entry.start_time} --> {entry.end_time}")
        output.append(entry.text)
        output.append('')

    return '\n'.join(output)
