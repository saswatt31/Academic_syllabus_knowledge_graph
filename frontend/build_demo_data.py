"""
Assemble the frontend data bundle from real pipeline artifacts:
  results/nodes.csv, results/edges.csv  -> frontend/data/graph.json
  results/query_benchmark.csv           -> benchmark rows in the same file
  results/entities.csv                  -> entity type counts

Run:    python frontend/build_demo_data.py
"""
import csv
import json
import os
import re
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(BASE, "results")
FRONT = os.path.join(BASE, "frontend")
DATA = os.path.join(FRONT, "data")

CODE_LABEL = {}
COURSE_COLORS = {}
PALETTE = ["#2563EB", "#7C3AED", "#0D9488", "#D97706",
           "#DC2626", "#4F46E5", "#059669"]

def course_label_of(text_head):
    return text_head

def main():
    os.makedirs(DATA, exist_ok=True)

    nodes = list(csv.DictReader(open(os.path.join(RES, "nodes.csv"),
                                     encoding="utf-8")))
    edges = list(csv.DictReader(open(os.path.join(RES, "edges.csv"),
                                     encoding="utf-8")))
    ents = list(csv.DictReader(open(os.path.join(RES, "entities.csv"),
                                    encoding="utf-8")))
    # node types live in nodes.csv; rebuild head/tail type lookups from it
    node_types = {n["node"]: n["type"] for n in nodes}

    # canonical labels for bare codes appearing as heads
    code2label = {}
    for e in edges:
        m = re.match(r"^([A-Z]{2,4}\d{3})\s+(.+)$", e["head"])
        if m:
            code2label[m.group(1)] = e["head"]

    def label(node):
        if node in code2label:
            return code2label[node]
        m = re.match(r"^([A-Z]{2,4}\d{3})$", node)
        if m:
            return code2label.get(node, node)
        return node

    courses = sorted({label(e["head"]) for e in edges
                      if node_types.get(e["head"]) in {"COURSE", "PREREQUISITE"}}
                     | {label(e["tail"]) for e in edges
                        if node_types.get(e["tail"]) == "COURSE"})
    for i, c in enumerate(courses):
        COURSE_COLORS[c] = PALETTE[i % len(PALETTE)]

    # ------- node list with degrees
    out_deg = Counter(e["head"] for e in edges)
    in_deg = Counter(e["tail"] for e in edges)
    node_list = []
    for n in nodes:
        node = n["node"]
        code = re.match(r"^([A-Z]{2,4}\d{3})", node)
        node_list.append({
            "id": node,
            "label": label(node),
            "type": n["type"],
            "code": code.group(1) if code else None,
            "out": out_deg.get(node, 0),
            "in": in_deg.get(node, 0),
        })

    # ------- topic -> courses index + outcomes per course
    topic_courses = defaultdict(set)
    course_topics = defaultdict(list)
    course_outcomes = defaultdict(list)
    course_meta = {}
    for e in edges:
        h, t, rel = label(e["head"]), e["tail"], e["relation"]
        if rel == "COVERS_TOPIC":
            topic_courses[t.lower()].add(h)
            course_topics[h].append(t)
        elif rel == "HAS_OUTCOME":
            course_outcomes[h].append(t)

    # course meta from syllabus text (instructor, credits)
    syl_dir = os.path.join(BASE, "data", "syllabi")
    for fname in sorted(os.listdir(syl_dir)):
        if not fname.endswith(".txt"):
            continue
        text = open(os.path.join(syl_dir, fname), encoding="utf-8").read()
        header = text.split("\n", 1)[0]
        m = re.match(r"\s*([A-Z]{2,4})\s?-?(\d{3})\s+([^—\n-]+)", header)
        if not m:
            continue
        code = f"{m.group(1)}{m.group(2)}"
        lbl = f"{code} {m.group(3).strip()}"
        ins = re.search(r"((?:Dr|Prof|Professor)\.?\s+[A-Z]\.\s?[A-Z][a-z]+)", text)
        cr = re.search(r"Credits?:\s*(\d+)", text)
        # dedupe case variants ("HTTP"/"http") while keeping first-seen casing
        seen, topics_dedup = set(), []
        for t in course_topics.get(lbl, []):
            if t.lower() not in seen:
                seen.add(t.lower())
                topics_dedup.append(t)
        course_meta[lbl] = {
            "code": code,
            "instructor": ins.group(1) if ins else None,
            "credits": int(cr.group(1)) if cr else None,
            "topics": topics_dedup,
            "outcomes": course_outcomes.get(lbl, []),
        }

    topic_index = [
        {"topic": t, "courses": sorted(cs)} for t, cs in
        sorted(topic_courses.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    ]

    bench = list(csv.DictReader(open(os.path.join(RES, "query_benchmark.csv"),
                                     encoding="utf-8")))

    entity_counts = Counter(e["type"] for e in ents)
    relation_counts = Counter(e["relation"] for e in edges)

    bundle = {
        "meta": {
            "nodes": len(node_list),
            "edges": len(edges),
            "entities": len(ents),
            "relations": len(edges),
            "courses": len(courses),
            "docs": 6,
        },
        "courses": courses,
        "courseColors": COURSE_COLORS,
        "courseMeta": course_meta,
        "nodes": node_list,
        "edges": edges,
        "topicIndex": topic_index,
        "benchmark": bench,
        "entityCounts": dict(entity_counts),
        "relationCounts": dict(relation_counts),
    }
    out = os.path.join(DATA, "graph.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(bundle, f, indent=1)

    out_js = os.path.join(DATA, "graph_data.js")
    with open(out_js, "w", encoding="utf-8") as f:
        f.write("window.GRAPH_DATA = " + json.dumps(bundle, indent=1) + ";\n")

    print(f"wrote {out} and {out_js}: {len(node_list)} nodes, {len(edges)} edges, "
          f"{len(topic_index)} topics, {len(bench)} benchmark queries")

if __name__ == "__main__":
    main()
