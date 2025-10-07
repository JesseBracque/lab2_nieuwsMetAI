"""
Simple tag generator for Dutch/Flemish news articles.
Returns up to 3 tags based on topic keywords and salient words in the title.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import List, Optional


STOPWORDS = set(
    """
    de het een en of maar want dus toch al niet wel is zijn was waren ben bent
    aan op in uit van voor met zonder door naar bij om over tegen tot vanaf tot
    deze dit die dat daar hier waar welk welke wie wat waarom hoe wanneer
    je jij u hij zij ze wij we jullie hun hen ik mij me mijn jouw jouw uw zijn
    haar ons onze jullie hun hunne ze'n d'r 'n 't
    ook nog meer meest minst heel zeer veel weinig soms vaak nooit altijd
    er dan nu straks vandaag morgen gisteren reeds reeds
    bijv bv etc enz enzovoort
    het's 's
    
    ook omdat zodat zodat terwijl hoewel indien tenzij zodra zodra zoals
    
    a an the to from for of as at on by into about over under above below
    
    rt via
    """.split()
)


TOPIC_KEYWORDS = [
    ("Politiek", [
        "politiek","reger","parlement","partij","minister","verkiez","coalitie","vlaams","kamer","premier","kabinet"
    ]),
    ("Economie", [
        "economie","inflatie","rente","werkloos","banen","ondernem","bank","beurs","aandeel","crypto","bitcoin","euro","energieprijs"
    ]),
    ("Sport", [
        "sport","voetbal","wieler","tennis","olymp","ek","wk","wedstrijd","goal","club","anderlecht","ajax","psv","feyenoord","genk"
    ]),
    ("Tech", [
        "tech","technologie","ai","kunstmatige","startup","software","app","google","apple","microsoft","meta","chip","semiconductor","smartphone","laptop","nvidia","tweakers"
    ]),
    ("Wetenschap", [
        "wetenschap","onderzoek","universiteit","ruimte","nasa","esa","astronom","natuurkund","biolog","geneesk"
    ]),
    ("Internationaal", [
        "eu","europ","navo","nato","rusland","oekrai","vs","china","frankrijk","duitsland","verenigde staten","midden-oosten","israel","palestin"
    ]),
    ("België", [
        "belgië","belgie","vlaanderen","antwerpen","gent","brussel","vlaming","waals"
    ]),
    ("Nederland", [
        "nederland","amsterdam","rotterdam","den haag","utrecht","eindhoven","rutte","randstad","nl"
    ]),
    ("Cultuur", [
        "cultuur","film","muziek","festival","boek","kunst","theater","serie"
    ]),
    ("Weer", [
        "weer","storm","hitte","koude","temperatuur","regen","code geel","code oranje","onweer"
    ]),
    ("Verkeer", [
        "verkeer","spoor","trein","ns","thales","file","bus","tram","metro","wegwerkzaam"
    ]),
]


def _tokenize(s: str) -> list[str]:
    # Fallback: use simple a-z0-9 if regex module isn't present
    try:
        import regex as reg
        return [t.lower() for t in reg.findall(r"[\p{L}\p{N}'\-]+", s)]
    except Exception:
        return [t.lower() for t in re.findall(r"[a-z0-9'\-]+", s.lower())]


def _top_words(title: str, text: str, k: int) -> list[str]:
    tokens = _tokenize((title or "") + " " + (text or ""))
    tokens = [w for w in tokens if len(w) >= 3 and w not in STOPWORDS]
    cnt = Counter(tokens)
    # Prefer title words
    title_tokens = set(_tokenize(title or ""))
    scored = []
    for w, c in cnt.items():
        bonus = 2 if w in title_tokens else 0
        scored.append((c + bonus, len(w), w))
    scored.sort(key=lambda x: (-x[0], -x[1], x[2]))
    out = []
    for _, __, w in scored:
        if w not in out:
            out.append(w)
        if len(out) >= k:
            break
    return [w.capitalize() for w in out]


def generate_tags(text: str, title: str = "", source_name: Optional[str] = None, max_tags: int = 1) -> List[str]:
    """
    Choose up to `max_tags` tags, prioritizing the single most relevant topic label.
    Relevance is scored by number of keyword hits (title gets a bonus).
    If no topic matches: use source hint, else fall back to a salient word.
    """
    title_l = (title or "").lower()
    body_l = (text or "").lower()
    hay = f"{title_l} {body_l}"

    # Score topic labels
    best_label: Optional[str] = None
    best_score = 0
    for label, keys in TOPIC_KEYWORDS:
        score = 0
        for k in keys:
            if not k:
                continue
            if k in hay:
                # count occurrences roughly
                score += hay.count(k)
                if k in title_l:
                    score += 2  # bonus if appears in title
        if score > best_score:
            best_score = score
            best_label = label

    tags: list[str] = []
    if best_label and best_score > 0:
        tags.append(best_label)
        return tags[:max_tags]

    # Use source name as weak signal only if no topic match
    if source_name and len(tags) < max_tags:
        sn = source_name.lower()
        if "tweakers" in sn:
            tags.append("Tech")
        elif ("nos" in sn or "nu.nl" in sn):
            tags.append("Nederland")
        elif ("hln" in sn):
            tags.append("België")
        if len(tags) >= max_tags:
            return tags[:max_tags]

    # Fallback: most salient word from title/text
    filler = _top_words(title, text, max_tags)
    for w in filler:
        if w not in tags:
            tags.append(w)
        if len(tags) >= max_tags:
            break
    return tags[:max_tags]
