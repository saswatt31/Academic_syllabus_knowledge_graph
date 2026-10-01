"""
Evaluation for the Academic Syllabus Knowledge Graph.

Two complementary, fully reproducible checks:

1. Extraction validation — every extracted relation is checked against
   deterministic document facts (the "Instructor:"/"Credits:" lines, the
   prerequisites section text, literal topic occurrence, LO markers).
   Any violation is a real extraction error.

2. Query benchmark — ten questions are asked against the built graph;
   expected answers are derived independently from the syllabus text and
   compared with the graph's answers (precision/recall per query).

Run:    python evaluate_extraction.py
Output: results/extraction_validation.csv, results/query_benchmark.csv
        + console summary
"""
import csv
import os
import re
import sys

import networkx as nx

BASE = os.path.dirname(os.path.abspath(__file__))
SYLLABI = os.path.join(BASE, "data", "syllabi")
OUT = os.path.join(BASE, "results")

# ---------------------------------------------------------------- load facts
def load_docs():
    docs = {}
    for fname in sorted(os.listdir(SYLLABI)):
        if fname.endswith(".txt"):
            with open(os.path.join(SYLLABI, fname), encoding="utf-8") as f:
                docs[fname] = f.read()
    return docs

HEADER_RE = re.compile(r"\s*([A-Z]{2,4})\s?-?(\d{3})\s+([^—\n-]+)")
INSTRUCTOR_RE = re.compile(r"\b((?:Dr|Prof|Professor)\.?\s+[A-Z]\.\s?[A-Z][a-z]+)\b")
CREDITS_RE = re.compile(r"\bCredits?:\s*(\d+)\b")

def doc_facts(text):
    """Deterministic facts every correct relation must respect."""
    header = text.split("\n", 1)[0]
    m = HEADER_RE.match(header)
    code = f"{m.group(1)}{m.group(2)}" if m else None
    instr = [mm.group(1) for mm in INSTRUCTOR_RE.finditer(text)]
    creds = [mm.group(1) for mm in CREDITS_RE.finditer(text)]
    return {"code": code, "instructors": instr, "credits": creds, "text": text}

def validate(docs, relations):
    """Return (checked, violations) over all relations."""
    checked = 0
    violations = []
    for r in relations:
        doc = docs.get(r["doc"])
        if doc is None:
            violations.append((r, "doc not found"))
            continue
        f = doc_facts(doc)
        rel, head, tail = r["relation"], r["head"], r["tail"]
        ok = True
        if rel == "TAUGHT_BY":
            ok = (r["head_type"] == "COURSE" and r["tail_type"] == "INSTRUCTOR"
                  and f["code"] and head.startswith(f["code"])
                  and tail in f["instructors"])
        elif rel == "HAS_CREDITS":
            ok = (f["code"] and head.startswith(f["code"]) and tail in f["credits"])
        elif rel == "COVERS_TOPIC":
            ok = (f["code"] and head.startswith(f["code"])
                  and tail.lower() in doc.lower())
        elif rel == "HAS_OUTCOME":
            ok = (f["code"] and head.startswith(f["code"])
                  and re.match(r"LO\d+", tail) and tail.split(".")[0] in doc)
        elif rel in {"PREREQUISITE_OF", "CO_REQUISITE_OF"}:
            # prereq course code must literally appear in the target document
            m = re.match(r"([A-Z]{2,4}\d{3})", head)
            ok = bool(m) and m.group(1) in doc
        else:
            ok = False
        checked += 1
        if not ok:
            violations.append((r, "relation contradicts source text"))
    return checked, violations

# ---------------------------------------------------------------- queries
def prerequisites_of(G, course_sub):
    out = []
    for u, v, d in G.edges(data=True):
        if d.get("relation") in {"PREREQUISITE_OF", "CO_REQUISITE_OF"} and \
                course_sub.lower() in str(v).lower():
            out.append(str(u))
    return set(out)

def courses_covering(G, topic_sub):
    return {str(u) for u, v, d in G.edges(data=True)
            if d.get("relation") == "COVERS_TOPIC"
            and topic_sub.lower() in str(v).lower()}

def outcomes_of(G, course_sub):
    return {str(v) for u, v, d in G.edges(data=True)
            if d.get("relation") == "HAS_OUTCOME"
            and course_sub.lower() in str(u).lower()}

def taught_by(G, instructor_sub):
    return {str(u) for u, v, d in G.edges(data=True)
            if d.get("relation") == "TAUGHT_BY"
            and instructor_sub.lower() in str(v).lower()}

def build_query_suite():
    """10 queries with independently-derived expected answer sets."""
    Q = []
    # Q1 prerequisites of CS301 (text: CS201 + MA202 prereq, CS306 co-req)
    Q.append(("Prerequisites of CS301", prerequisites_of, "CS301",
              {"CS201 Data Structures & Algorithms", "MA202 Probability & Statistics",
               "CS306 Linear Algebra"}))
    # Q2 courses covering 'clustering' (CS301 topic list; CS201/CS302/... none mention it)
    Q.append(("Courses covering 'clustering'", courses_covering, "clustering",
              {"CS301 Machine Learning"}))
    # Q3 courses covering 'sql' (CS302 topics; CS305 mentions SQL? -> derive from text)
    #    filled after docs are loaded (see expected_from_text below)
    # Q4 outcomes of CS301 (5 LOs)
    #    filled from text
    # Q5 courses taught by 'Iyer'
    #    filled from text
    return Q

def expected_from_text(docs):
    """Derive expected answer sets straight from the raw syllabi text."""
    exp = {}
    sql_courses = set()
    for fname, text in docs.items():
        m = HEADER_RE.match(text.split("\n", 1)[0])
        code = f"{m.group(1)}{m.group(2)}" if m else fname
        if re.search(r"\bsql\b", text, re.IGNORECASE):
            sql_courses.add(code2label(text, code))
    exp["sql"] = sql_courses
    iyer = set()
    for fname, text in docs.items():
        m = HEADER_RE.match(text.split("\n", 1)[0])
        code = f"{m.group(1)}{m.group(2)}" if m else fname
        if INSTRUCTOR_RE.search(text) and "Iyer" in text:
            iyer.add(code2label(text, code))
    exp["iyer"] = iyer
    return exp

def code2label(text, code):
    m = HEADER_RE.match(text.split("\n", 1)[0])
    title = m.group(3).strip() if m else ""
    return f"{code} {title}".strip()

def main():
    sys.stdout.reconfigure(encoding="utf-8")
    os.makedirs(OUT, exist_ok=True)
    docs = load_docs()

    # reload relations exactly as the pipeline produced them
    rels = []
    with open(os.path.join(OUT, "relations.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rels.append(r)
    print(f"validating {len(rels)} extracted relations against source text ...")
    checked, violations = validate(docs, rels)
    print(f"  checked: {checked}")
    print(f"  violations: {len(violations)}")
    for r, why in violations[:10]:
        print(f"    !! {r['doc']}: {r['relation']} {r['head']} -> {r['tail'][:50]} ({why})")

    with open(os.path.join(OUT, "extraction_validation.csv"), "w",
              newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["relation", "head", "tail", "doc", "status"])
        for r in rels:
            status = "violation" if any(v[0] is r for v in violations) else "ok"
            w.writerow([r["relation"], r["head"], r["tail"], r["doc"], status])
    print(f"  wrote {OUT}/extraction_validation.csv")

    G = nx.read_graphml(os.path.join(OUT, "knowledge_graph.graphml"))

    # build the 10-query benchmark (expected sets derived from raw text)
    exp = expected_from_text(docs)
    outcomes_301 = set()
    text301 = docs["CS301_machine_learning.txt"]
    for mm in re.finditer(r"LO\d+\.[^\n]*", text301):
        outcomes_301.add(mm.group(0).strip())
    queries = [
        ("Prerequisites of CS301",
         sorted(prerequisites_of(G, "CS301")),
         ["CS201 Data Structures & Algorithms", "MA202 Probability & Statistics",
          "CS306 Linear Algebra"]),
        ("Courses covering 'clustering'",
         sorted(courses_covering(G, "clustering")),
         ["CS301 Machine Learning"]),
        ("Courses covering 'sql'",
         sorted(courses_covering(G, "sql")),
         sorted(exp["sql"])),
        ("Learning outcomes of CS301",
         sorted(outcomes_of(G, "CS301")),
         sorted(outcomes_301)),
        ("Courses taught by Dr. Iyer",
         sorted(taught_by(G, "Iyer")),
         sorted(exp["iyer"])),
        ("Prerequisites of CS302",
         sorted(prerequisites_of(G, "CS302")),
         ["CS101 Introduction to Programming"]),
        ("Courses covering 'normalization'",
         sorted(courses_covering(G, "normalization")),
         ["CS302 Database Systems"]),
        ("Courses covering 'deadlocks'",
         sorted(courses_covering(G, "deadlocks")),
         ["CS303 Operating Systems"]),
        ("Courses covering 'subnetting'",
         sorted(courses_covering(G, "subnetting")),
         ["CS304 Computer Networks"]),
        ("Courses covering 'flexbox'",
         sorted(courses_covering(G, "flexbox")),
         ["CS305 Web Technologies"]),
    ]

    rows, tp_total, fp_total, fn_total = [], 0, 0, 0
    for q, got, want in queries:
        got_set, want_set = set(got), set(want)
        tp, fp, fn = len(got_set & want_set), len(got_set - want_set), len(want_set - got_set)
        p = tp / (tp + fp) if tp + fp else 1.0
        r = tp / (tp + fn) if tp + fn else 1.0
        f1 = 2 * p * r / (p + r) if p + r else 0.0
        tp_total += tp; fp_total += fp; fn_total += fn
        rows.append(dict(query=q, found=len(got_set), expected=len(want_set),
                         tp=tp, fp=fp, fn=fn, precision=round(p, 4),
                         recall=round(r, 4), f1=round(f1, 4)))
    micro_p = tp_total / (tp_total + fp_total) if tp_total + fp_total else 1.0
    micro_r = tp_total / (tp_total + fn_total) if tp_total + fn_total else 1.0
    micro_f1 = 2 * micro_p * micro_r / (micro_p + micro_r) if micro_p + micro_r else 0.0

    with open(os.path.join(OUT, "query_benchmark.csv"), "w",
              newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    print(f"\nquery benchmark (10 queries):")
    for row in rows:
        print(f"  {row['query'][:38]:40s} found {row['found']:3d} expected "
              f"{row['expected']:3d}  P={row['precision']:.2f} R={row['recall']:.2f} "
              f"F1={row['f1']:.2f}")
    print(f"\n  micro precision {micro_p:.4f} | recall {micro_r:.4f} | F1 {micro_f1:.4f}")
    print(f"  wrote {OUT}/query_benchmark.csv")

    print(f"\nSUMMARY: validation {checked - len(violations)}/{checked} relations consistent "
          f"with source text ({100*(checked-len(violations))/checked:.1f}%); "
          f"query F1 {micro_f1:.4f}")

if __name__ == "__main__":
    main()
