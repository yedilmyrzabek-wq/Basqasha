"""Kazakh text normalization (kazakh_market R2–R4): homoglyph fix, numbers -> words,
abbreviation expansion, and the TTS-safety check (no digits / % / currency / Roman numerals)."""
from __future__ import annotations

import re

from ai.prompts import kk_abbrev

_ONES = ["", "бір", "екі", "үш", "төрт", "бес", "алты", "жеті", "сегіз", "тоғыз"]
_TENS = ["", "он", "жиырма", "отыз", "қырық", "елу", "алпыс", "жетпіс", "сексен", "тоқсан"]
_ORD = {"нөл": "нөлінші", "бір": "бірінші", "екі": "екінші", "үш": "үшінші", "төрт": "төртінші",
        "бес": "бесінші", "алты": "алтыншы", "жеті": "жетінші", "сегіз": "сегізінші",
        "тоғыз": "тоғызыншы", "он": "оныншы", "жиырма": "жиырмасыншы", "отыз": "отызыншы",
        "қырық": "қырқыншы", "елу": "елуінші", "алпыс": "алпысыншы", "жетпіс": "жетпісінші",
        "сексен": "сексенінші", "тоқсан": "тоқсаныншы", "жүз": "жүзінші", "мың": "мыңыншы",
        "миллион": "миллионыншы", "миллиард": "миллиардыншы"}
_SCALES = [(10**9, "миллиард"), (10**6, "миллион"), (1000, "мың")]
NUMBER_WORDS = {w for w in _ONES + _TENS if w} | {"нөл", "жүз", "мың", "миллион", "миллиард"}

_LAT2CYR = str.maketrans("aeopcxykihAEOPCXYKHBMTI", "аеорсхукіһАЕОРСХУКНВМТІ")
_CYR = re.compile(r"[Ѐ-ӿ]")
_LAT = re.compile(r"[A-Za-z]")
_WORD = re.compile(r"[\wЀ-ӿ'-]+")
_ROMAN_VAL = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
_ROMAN = re.compile(r"\b[IVXLC]+\b")
_UNSAFE = re.compile(r"[0-9%$€₸№§]")


# ------------------------------------------------------------------ numbers
def _under_1000(n: int) -> list[str]:
    out: list[str] = []
    h, rest = divmod(n, 100)
    if h:
        out += ([] if h == 1 else [_ONES[h]]) + ["жүз"]
    t, o = divmod(rest, 10)
    if t:
        out.append(_TENS[t])
    if o:
        out.append(_ONES[o])
    return out


def num_words(n: int) -> str:
    """Cardinal: 1880 -> 'мың сегіз жүз сексен'."""
    if n == 0:
        return "нөл"
    if n < 0:
        return "минус " + num_words(-n)
    words: list[str] = []
    for value, name in _SCALES:
        q, n = divmod(n, value)
        if q:
            words += ([] if (q == 1 and value == 1000) else _under_1000(q)) + [name]
    words += _under_1000(n)
    return " ".join(words)


def ordinal_words(n: int) -> str:
    """Ordinal: 1880 -> 'мың сегіз жүз сексенінші'."""
    parts = num_words(n).split()
    parts[-1] = _ORD.get(parts[-1], parts[-1] + "інші")
    return " ".join(parts)


def _decimal_words(s: str) -> str:
    whole, frac = re.split(r"[.,]", s, maxsplit=1)
    denom = {1: "оннан", 2: "жүзден", 3: "мыңнан"}.get(len(frac), "мыңнан")
    return f"{num_words(int(whole))} бүтін {denom} {num_words(int(frac[:3]))}"


def _roman_to_int(s: str) -> int:
    total = 0
    for a, b in zip(s, s[1:] + " "):
        v = _ROMAN_VAL[a]
        total += -v if b != " " and _ROMAN_VAL.get(b, 0) > v else v
    return total


# ------------------------------------------------------------------ public
def fix_homoglyphs(text: str) -> str:
    """ə/Ə -> ә/Ә everywhere; Latin look-alikes -> Cyrillic inside Cyrillic words."""
    text = text.replace("ə", "ә").replace("Ə", "Ә")
    return _WORD.sub(lambda m: m.group(0).translate(_LAT2CYR)
                     if _CYR.search(m.group(0)) and _LAT.search(m.group(0)) else m.group(0), text)


def mixed_script_tokens(text: str) -> list[str]:
    return [w for w in _WORD.findall(text) if _CYR.search(w) and _LAT.search(w)]


def numbers_to_words(text: str) -> str:
    t = re.sub(r"(?<=\d)[   ](?=\d{3}\b)", "", text)                      # 10 000 -> 10000
    t = re.sub(r"\b([IVXLC]+)(?:[\s-]+)(ғасыр\w*)", lambda m: f"{ordinal_words(_roman_to_int(m.group(1)))} {m.group(2)}", t)
    t = re.sub(r"(\d+)\s*[–—-]\s*(\d+)(\s*-?\s*(?:жыл|ғасыр)\w*)",                     # ranges of years
               lambda m: f"{ordinal_words(int(m.group(1)))}-{ordinal_words(int(m.group(2)))} {m.group(3).strip(' -')}", t)
    t = re.sub(r"(\d+)\s*-?\s*(жыл\w*|ғасыр\w*)", lambda m: f"{ordinal_words(int(m.group(1)))} {m.group(2)}", t)
    t = re.sub(r"(\d+)\s*-\s*(?:ші|шы|інші|ыншы|нші|ншы)\b", lambda m: ordinal_words(int(m.group(1))), t)
    t = re.sub(r"(\d+)-([а-яәғқңөұүһі]+)", lambda m: num_words(int(m.group(1))) + m.group(2), t)  # 600-ден
    t = re.sub(r"(\d+)\s*[–—]\s*(\d+)", lambda m: f"{num_words(int(m.group(1)))}-{num_words(int(m.group(2)))}", t)
    t = re.sub(r"[$]\s*(\d+)", lambda m: f"{num_words(int(m.group(1)))} доллар", t)
    t = re.sub(r"(\d+[.,]\d+)", lambda m: _decimal_words(m.group(1)), t)
    t = re.sub(r"(?:(?<=\s)|^)[-−–](\d+)", lambda m: "минус " + num_words(int(m.group(1))), t)
    t = re.sub(r"\d+", lambda m: num_words(int(m.group(0))), t)
    return t


def expand_abbreviations(text: str) -> str:
    for key, full in sorted(kk_abbrev().items(), key=lambda kv: -len(kv[0])):
        if key[0].isalpha():
            text = re.sub(rf"(?<![\wЀ-ӿ]){re.escape(key)}(?![\wЀ-ӿ])", full, text)
        else:
            text = re.sub(rf"\s*{re.escape(key)}", " " + full, text)
    return text


def normalize_kk(text: str) -> str:
    """Normalize narration for display + TTS (idempotent for already-clean text)."""
    t = fix_homoglyphs(text)
    t = expand_abbreviations(numbers_to_words(t))
    t = _ROMAN.sub(lambda m: num_words(_roman_to_int(m.group(0))), t)
    return re.sub(r"[ \t]{2,}", " ", t).strip()


def tts_issues(text: str) -> list[str]:
    """Empty list = safe for ElevenLabs (kazakh_market R2–R4)."""
    issues = [f"unsafe char {c!r}" for c in sorted(set(_UNSAFE.findall(text)))]
    issues += [f"roman numeral {r!r}" for r in _ROMAN.findall(text)]
    issues += [f"mixed script {w!r}" for w in mixed_script_tokens(text)]
    issues += [f"dot inside token {w!r}" for w in re.findall(r"\b\w+\.\w+\b", text)]
    return issues
