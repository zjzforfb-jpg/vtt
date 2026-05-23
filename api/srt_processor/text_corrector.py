import re
from difflib import SequenceMatcher
from typing import Dict, Any, List, Optional

COMMON_PROPER_NOUNS = {
    'stella', 'benjamin', 'zhendong', 'zhuang', 'xianhui',
    'ross', 'huo'
}

QUESTION_STARTERS = {'what', 'who', 'where', 'when', 'why', 'how', 'do', 'does', 'did', 'is', 'are', 'was', 'were', 'will', 'would', 'can', 'could', 'should'}

EXCLAMATION_PATTERNS = {'get off', 'stay away', 'go sleep', 'take him'}

CONTRACTION_MAP = {
    'dont': "don't",
    'cant': "can't",
    'wont': "won't",
    'its': "it's",
    'im': "I'm",
    'ive': "I've",
    'id': "I'd",
    'youre': "you're",
    'theyre': "they're",
    'havent': "haven't",
    'hasnt': "hasn't",
    'hadnt': "hadn't",
    'wouldnt': "wouldn't",
    'shouldnt': "shouldn't",
    'couldnt': "couldn't",
    'isnt': "isn't",
    'arent': "aren't",
    'wasnt': "wasn't",
    'thats': "that's",
    'whats': "what's",
    'whos': "who's",
}


def clean_text(text: str) -> str:
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)
    return text


def capitalize_text(text: str) -> str:
    if not text or not text.strip():
        return text

    text = clean_text(text)

    words = text.split()
    if not words:
        return text

    text_lower = ' '.join(words).lower()

    has_punctuation = text.strip()[-1] in '.!?'

    sentence_type = 'statement'

    first_word_clean = re.sub(r'[^\w]', '', words[0].lower())
    if first_word_clean in QUESTION_STARTERS:
        sentence_type = 'question'

    if not has_punctuation:
        for pattern in EXCLAMATION_PATTERNS:
            if pattern in text_lower:
                sentence_type = 'exclamation'
                break

    capitalized_words = []
    for i, word in enumerate(words):
        word_lower = word.lower()
        clean_word = re.sub(r'[^\w]', '', word_lower)
        trailing_punct = re.sub(r'^[\w\']+', '', word)

        if clean_word in CONTRACTION_MAP:
            word = CONTRACTION_MAP[clean_word]
            if i == 0:
                word = word[0].upper() + word[1:]
        elif i == 0:
            if clean_word:
                word = clean_word[0].upper() + clean_word[1:] + trailing_punct
        elif clean_word in COMMON_PROPER_NOUNS:
            word = clean_word[0].upper() + clean_word[1:] + trailing_punct
        elif clean_word == 'i':
            word = 'I' + trailing_punct

        capitalized_words.append(word)

    result = ' '.join(capitalized_words)

    if not has_punctuation:
        if sentence_type == 'question':
            result += '?'
        elif sentence_type == 'exclamation':
            result += '!'
        else:
            result += '.'

    return result


def correct_text_with_original(recognized_text: str, original_text: str) -> Dict[str, Any]:
    if not original_text:
        corrected = capitalize_text(recognized_text)
        return {
            'corrected_text': corrected,
            'changes': []
        }

    corrections = []

    rec_words = recognized_text.lower().split()
    orig_words = original_text.lower().split()

    rec_clean = [re.sub(r'[^\w]', '', w) for w in rec_words]
    orig_clean = [re.sub(r'[^\w]', '', w) for w in orig_words]

    for i, rec_word in enumerate(rec_words):
        clean_rec_word = re.sub(r'[^\w]', '', rec_word)
        if not clean_rec_word or len(clean_rec_word) <= 3:
            continue

        best_match = None
        best_score = 0.0

        for j, orig_word in enumerate(orig_words):
            clean_orig_word = re.sub(r'[^\w]', '', orig_word)
            if not clean_orig_word or len(clean_orig_word) <= 3:
                continue

            score = similarity_score(clean_rec_word, clean_orig_word)
            if score > best_score:
                best_score = score
                best_match = orig_word

        if best_match and best_score > 0.85 and best_score < 1.0:
            clean_orig = re.sub(r'[^\w]', '', best_match)
            if clean_rec_word != clean_orig:
                corrections.append({
                    'index': i,
                    'original_word': clean_rec_word,
                    'corrected_word': best_match,
                    'confidence': best_score
                })

    corrected_words = list(rec_words)

    for correction in corrections:
        idx = correction['index']
        if idx < len(corrected_words):
            old_word = corrected_words[idx]
            trailing_punct = re.sub(r'^[\w\']+', '', old_word)
            corrected_words[idx] = correction['corrected_word'] + trailing_punct

    corrected_text = ' '.join(corrected_words)
    corrected_text = capitalize_text(corrected_text)

    return {
        'corrected_text': corrected_text,
        'changes': corrections
    }


def similarity_score(word1: str, word2: str) -> float:
    return SequenceMatcher(None, word1.lower(), word2.lower()).ratio()


def detect_sentence_type(text: str) -> str:
    text_lower = text.lower().strip()

    first_word = re.sub(r'[^\w]', '', text_lower.split()[0]) if text_lower.split() else ''
    if first_word in QUESTION_STARTERS:
        return 'question'

    for pattern in EXCLAMATION_PATTERNS:
        if pattern in text_lower:
            return 'exclamation'

    return 'statement'
