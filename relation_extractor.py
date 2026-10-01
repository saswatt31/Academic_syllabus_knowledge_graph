"""
Pattern-based relation extraction between entities found in syllabi.

Relations:
  PREREQUISITE_OF / CO_REQUISITE_OF : (prereq course) -> (target course)
  COVERS_TOPIC                      : course -> topic
  HAS_OUTCOME                       : course -> outcome (LOx sentence)
  TAUGHT_BY                         : course -> instructor
  HAS_CREDITS                       : course -> credits

Bare course codes (e.g. "CS201") are normalized to full labels
("CS201 Data Structures & Algorithms") so each course is ONE graph node.

Output: results/relations.csv (head, head_type, relation, tail, tail_type, doc)
"""
import csv
import os
import re

from ner_extractor import (COREQ_RE, CREDITS_RE, INSTRUCTOR_RE, OUTCOME_RE,
                           PREREQ_CODE_RE, TOPIC_GAZETTEER)

BASE = os.path.dirname(os.path.abspath(__file__))
SYLLABI_DIR = os.path.join(BASE, "data", "syllabi")
OUT_DIR = os.path.join(BASE, "results")

HEADER_RE = re.compile(r"\s*([A-Z]{2,4})\s?-?(\d{3})\s+([^—\n-]+)")
BARE_CODE_RE = re.compile(r"^[A-Z]{2,4}\d{3}$")


def build_code_title_map() -> dict:
    """Scan syllabus headers: {'CS201': 'CS201 Data Structures & Algorithms'}"""
    out = {}
    for fname in sorted(os.listdir(SYLLABI_DIR)):
        if not fname.endswith(".txt"):
            continue
        with open(os.path.join(SYLLABI_DIR, fname), encoding="utf-8") as f:
            header = f.read().split("\n", 1)[0]
        m = HEADER_RE.match(header)
        if m:
            code = f"{m.group(1)}{m.group(2)}"
            out[code] = f"{code} {m.group(3).strip()}"
    return out


_STOP = re.compile(
    r"\s*(?:\.|—|:|,| and\b| before\b| is\b| must\b| are\b| was\b|\n)")

def full_label_for(text: str, code: str) -> str:
    """Canonical label for a course code found anywhere in a document.

    Looks for '<CODE> <Title>' with the title on the same line OR wrapped to
    the next line ("MA202\nProbability & Statistics before enrolling"), and
    trims the title at the first stop pattern. Falls back to the bare code.
    """
    m = re.search(rf"\b{re.escape(code)}\s?-?\d{{3}}\s+([A-Z][^\n.]*)", text)
    if not m:  # code itself may include the digits already
        m = re.search(rf"\b{re.escape(code)}\s+([A-Z][^\n.]*)", text)
    if not m:
        return code
    title = _STOP.split(m.group(1).strip())[0].strip().rstrip("—-: .")
    return f"{code} {title}".strip() if title else code


def outcome_sentence(text: str, m: re.Match) -> str:
    """Full sentence following an 'LOx' marker (stops before the next LO)."""
    start = m.end()
    # skip the enumeration dot directly after the LO id ("LO1.")
    if text[start:start + 1] == ".":
        start += 1
    sent_end = text.find(".", start)
    if sent_end == -1:
        sent_end = min(start + 120, len(text))
    else:
        nxt = text.find("LO", start)
        if nxt != -1 and nxt < sent_end:
            sent_end = nxt
        else:
            sent_end += 1
    return re.sub(r"\s+", " ", text[m.start():sent_end]).strip()


def extract_relations(text: str, doc_name: str,
                      code2label: dict | None = None) -> list[dict]:
    code2label = code2label or {}
    relations = []

    header = text.split("\n", 1)[0]
    m = HEADER_RE.match(header)
    own_code = f"{m.group(1)}{m.group(2)}" if m else None
    own_label = code2label.get(own_code, own_code or header.strip(" —-"))

    def canon(code_or_label: str) -> str:
        if code_or_label in code2label:
            return code2label[code_or_label]
        if BARE_CODE_RE.match(code_or_label):
            # no syllabus file for this code: recover the title from the document
            return full_label_for(text, code_or_label)
        return code_or_label

    # --- TAUGHT_BY / HAS_CREDITS ------------------------------------------
    for mm in INSTRUCTOR_RE.finditer(text):
        relations.append(dict(head=own_label, head_type="COURSE",
                              relation="TAUGHT_BY", tail=mm.group(1),
                              tail_type="INSTRUCTOR", doc=doc_name))
    for mm in CREDITS_RE.finditer(text):
        relations.append(dict(head=own_label, head_type="COURSE",
                              relation="HAS_CREDITS", tail=mm.group(1),
                              tail_type="CREDITS", doc=doc_name))

    # --- PREREQUISITE_OF / CO_REQUISITE_OF --------------------------------
    for mm in PREREQ_CODE_RE.finditer(text):
        prereq = canon(f"{mm.group(1)}{mm.group(2)}")
        relations.append(dict(head=prereq, head_type="PREREQUISITE",
                              relation="PREREQUISITE_OF", tail=own_label,
                              tail_type="COURSE", doc=doc_name))
    for mm in COREQ_RE.finditer(text):
        coreq = canon(f"{mm.group(1)}{mm.group(2)}")
        relations.append(dict(head=coreq, head_type="PREREQUISITE",
                              relation="CO_REQUISITE_OF", tail=own_label,
                              tail_type="COURSE", doc=doc_name))

    # Section-scoped sweep: every course code listed in the Prerequisites
    # block becomes an edge, even when no trigger word precedes it
    # ("... must have completed CS201 and MA202 ..."). A code preceded
    # (within 40 chars) by a co-requisite mention is tagged CO_REQUISITE_OF.
    pre_m = re.search(r"Prerequisites?:\s*(.*?)(?=\n\s*\n|\Z)", text,
                      re.IGNORECASE | re.DOTALL)
    if pre_m:
        section = pre_m.group(1)
        seen_pairs = {(r["head"], r["relation"]) for r in relations
                      if r["tail"] == own_label}
        for cm in re.finditer(r"\b([A-Z]{2,4})\s?-?(\d{3})\b", section):
            code = f"{cm.group(1)}{cm.group(2)}"
            if code == own_code:
                continue
            context = section[max(0, cm.start() - 40):cm.start()].lower()
            rel = ("CO_REQUISITE_OF" if "co-requisite" in context or
                   "corequisite" in context else "PREREQUISITE_OF")
            if (canon(code), rel) in seen_pairs:
                continue
            relations.append(dict(head=canon(code), head_type="PREREQUISITE",
                                  relation=rel, tail=own_label,
                                  tail_type="COURSE", doc=doc_name))

    # "X is a prerequisite for Y" with both codes in one clause
    for mm in re.finditer(
            r"([A-Z]{2,4})\s?-?(\d{3})[^.\n]{0,80}?prerequisite for\s+"
            r"([A-Z]{2,4})\s?-?(\d{3})", text, re.IGNORECASE):
        relations.append(dict(
            head=canon(f"{mm.group(1)}{mm.group(2)}"), head_type="COURSE",
            relation="PREREQUISITE_OF",
            tail=canon(f"{mm.group(3)}{mm.group(4)}"), tail_type="COURSE",
            doc=doc_name))

    # --- COVERS_TOPIC (word-boundary gazetteer match) ----------------------
    lower = text.lower()
    taken = []
    for topic in sorted(TOPIC_GAZETTEER, key=len, reverse=True):
        for tm in re.finditer(rf"\b{re.escape(topic)}\b", lower):
            s, e = tm.span()
            if any(s < te and e > ts for ts, te in taken):
                continue
            taken.append((s, e))
            relations.append(dict(head=own_label, head_type="COURSE",
                                  relation="COVERS_TOPIC", tail=text[s:e],
                                  tail_type="TOPIC", doc=doc_name))

    # --- HAS_OUTCOME --------------------------------------------------------
    for om in OUTCOME_RE.finditer(text):
        relations.append(dict(head=own_label, head_type="COURSE",
                              relation="HAS_OUTCOME",
                              tail=outcome_sentence(text, om),
                              tail_type="OUTCOME", doc=doc_name))

    return relations


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    code2label = build_code_title_map()
    all_rels = []
    for fname in sorted(os.listdir(SYLLABI_DIR)):
        if not fname.endswith(".txt"):
            continue
        with open(os.path.join(SYLLABI_DIR, fname), encoding="utf-8") as f:
            text = f.read()
        rels = extract_relations(text, fname, code2label)
        all_rels.extend(rels)
        counts = {}
        for r in rels:
            counts[r["relation"]] = counts.get(r["relation"], 0) + 1
        print(f"{fname}: {len(rels)} relations {counts}")

    out_path = os.path.join(OUT_DIR, "relations.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["head", "head_type", "relation",
                                          "tail", "tail_type", "doc"])
        w.writeheader()
        w.writerows(all_rels)
    print(f"\nwrote {out_path}: {len(all_rels)} relations")


if __name__ == "__main__":
    main()
