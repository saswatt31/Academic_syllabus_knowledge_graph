"""
Named Entity Recognition for academic syllabi.

Two backends:
  * rule-based (default, offline): regex + gazetteers for COURSE, TOPIC,
    PREREQUISITE, OUTCOME, INSTRUCTOR, CREDITS
  * optional spaCy en_core_web_sm: adds ORG / PERSON / DATE entities on top

Output: results/entities.csv  (doc, entity, type, span_start, span_end)
"""
import csv
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
SYLLABI_DIR = os.path.join(BASE, "data", "syllabi")
OUT_DIR = os.path.join(BASE, "results")

COURSE_RE = re.compile(
    r"\b([A-Z]{2,4})\s?-?(\d{3})\s+([A-Z][^—\n.]*?)"   # CODE Title
    r"(?=\s*(?:—|-|:\s|\n|\.\s|\.$|$))")
COURSE_CODE_RE = re.compile(r"\b([A-Z]{2,4})\s?-?(\d{3})\b")

# gazetteer of topic keywords (extendable); lowercased for matching
TOPIC_GAZETTEER = [
    "linear regression", "logistic regression", "gradient descent",
    "decision trees", "random forests", "support vector machines",
    "k-means clustering", "hierarchical clustering", "principal component analysis",
    "neural networks", "backpropagation", "cross-validation",
    "bias-variance tradeoff", "classification metrics", "arrays", "linked lists",
    "stacks and queues", "binary search trees", "heaps and priority queues",
    "hash tables", "hashing", "graph representations", "bfs", "dfs",
    "shortest paths", "minimum spanning trees", "sorting algorithms",
    "dynamic programming", "greedy methods", "complexity analysis",
    "np-completeness", "entity-relationship modelling", "relational model",
    "relational algebra", "sql queries", "normalization",
    "functional dependencies", "indexing", "b-trees", "transactions",
    "acid properties", "concurrency control", "nosql", "document stores",
    "system calls", "processes and threads", "cpu scheduling",
    "process synchronization", "semaphores", "deadlocks", "memory management",
    "virtual memory", "page replacement", "file systems", "distributed systems",
    "network architecture", "layered models", "data link protocols",
    "mac protocols", "ethernet", "ip addressing", "subnetting",
    "routing algorithms", "distance vector", "link state", "udp",
    "tcp congestion control", "dns", "http", "cryptography basics", "firewalls",
    "html", "css layout", "flexbox", "grid", "javascript", "dom",
    "rest api", "react", "authentication", "sessions", "web performance",
    "caching", "subnet masks", "osi", "tcp/ip", "operating system concepts",
    "machine learning", "supervised", "unsupervised", "clustering",
]

INSTRUCTOR_RE = re.compile(
    r"\b((?:Dr|Prof|Professor)\.?\s+[A-Z]\.\s?[A-Z][a-z]+)\b")
CREDITS_RE = re.compile(r"\bCredits?:\s*(\d+)\b")
OUTCOME_RE = re.compile(r"\b(LO\d+)\b")
PREREQ_CODE_RE = re.compile(r"(?:prerequisite[s]?\s*(?:is|:|are|for this course)?|"
                            r"requires?|must have completed|should have finished|"
                            r"before enrolling|completed)\s*[:]?\s*"
                            r"([A-Z]{2,4})\s?-?(\d{3})", re.IGNORECASE)
COREQ_RE = re.compile(r"co-?requisite[s]?\s*[:]?\s*([A-Z]{2,4})\s?-?(\d{3})",
                      re.IGNORECASE)


def extract_entities(text: str, doc_name: str) -> list[dict]:
    ents = []

    for m in INSTRUCTOR_RE.finditer(text):
        ents.append(dict(doc=doc_name, entity=m.group(1), type="INSTRUCTOR",
                         span_start=m.start(), span_end=m.end()))

    for m in CREDITS_RE.finditer(text):
        ents.append(dict(doc=doc_name, entity=m.group(1), type="CREDITS",
                         span_start=m.start(), span_end=m.end()))

    # full course titles: "CS301 Machine Learning — Course Syllabus" or in prose
    for m in COURSE_RE.finditer(text):
        code = f"{m.group(1)}{m.group(2)}"
        title = (m.group(3) or "").strip().rstrip("—-: ").strip()
        label = f"{code} {title}".strip()
        ents.append(dict(doc=doc_name, entity=label, type="COURSE",
                         span_start=m.start(), span_end=m.end()))

    # topic gazetteer (case-insensitive, longest match wins at a position)
    lower = text.lower()
    taken = []
    for topic in sorted(TOPIC_GAZETTEER, key=len, reverse=True):
        for m in re.finditer(rf"\b{re.escape(topic)}\b", lower, flags=re.IGNORECASE):
            s, e = m.span()
            if any(s < t_end and e > t_start for t_start, t_end in taken):
                continue
            taken.append((s, e))
            # pretty-print the topic using the original casing
            ents.append(dict(doc=doc_name, entity=text[s:e], type="TOPIC",
                             span_start=s, span_end=e))

    for m in OUTCOME_RE.finditer(text):
        # capture the full sentence following the LO id as the outcome text
        start = m.end()
        if text[start:start + 1] == ".":
            start += 1  # skip the enumeration dot ("LO1.")
        sent_end = text.find(".", start)
        if sent_end == -1:
            sent_end = min(start + 120, len(text))
        else:
            nxt = text.find("LO", start)
            if nxt != -1 and nxt < sent_end:
                sent_end = nxt
            else:
                sent_end += 1
        outcome = re.sub(r"\s+", " ", text[m.start():sent_end]).strip()
        ents.append(dict(doc=doc_name, entity=outcome, type="OUTCOME",
                         span_start=m.start(), span_end=sent_end))

    return ents


def optional_spacy_entities(text: str, doc_name: str) -> list[dict]:
    """Extra ORG/PERSON/DATE entities via spaCy, if installed."""
    try:
        import spacy
    except ImportError:
        return []
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        print("  (spaCy installed but en_core_web_sm missing - skipping)")
        return []
    out = []
    for ent in nlp(text).ents:
        if ent.label_ in {"ORG", "PERSON", "DATE", "GPE"}:
            out.append(dict(doc=doc_name, entity=ent.text, type=ent.label_,
                            span_start=ent.start_char, span_end=ent.end_char))
    return out


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    all_ents = []
    for fname in sorted(os.listdir(SYLLABI_DIR)):
        if not fname.endswith(".txt"):
            continue
        path = os.path.join(SYLLABI_DIR, fname)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        ents = extract_entities(text, fname)
        ents += optional_spacy_entities(text, fname)
        all_ents.extend(ents)
        counts = {}
        for e in ents:
            counts[e["type"]] = counts.get(e["type"], 0) + 1
        print(f"{fname}: {len(ents)} entities {counts}")

    out_path = os.path.join(OUT_DIR, "entities.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["doc", "entity", "type",
                                          "span_start", "span_end"])
        w.writeheader()
        w.writerows(all_ents)
    print(f"\nwrote {out_path}: {len(all_ents)} entities")


if __name__ == "__main__":
    main()
