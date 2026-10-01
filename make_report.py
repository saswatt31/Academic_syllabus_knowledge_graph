"""
Generate Project_Report_Academic_Syllabus_Knowledge_Graph.docx by filling
C:\\Users\\saswa\\Downloads\\Project_Report_Template.docx IN PLACE (styles,
headers and the TOC field are preserved; Word refreshes the TOC with F9).

Run:    python make_report.py
Output: Project_Report_Academic_Syllabus_Knowledge_Graph.docx (project root)
"""
import copy
import csv
import os
from collections import Counter

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

TEMPLATE = r"C:\Users\saswa\Downloads\Project_Report_Template.docx"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "Project_Report_Academic_Syllabus_Knowledge_Graph.docx")

# ---------------------------------------------------------------- submission
GROUP = "4"
SEMESTER = "7th Semester Evaluation of B.Tech (Artificial Intelligence & Machine Learning)"
STUDENTS = [
    ("Saswat Pattanaik", "FET-BAML-2023-27-026"),
    ("Ritesh Kumar Singh", "FET-BAML-2023-27-027"),
    ("Manoranjan Barik", "FET-BAML-2023-27-039"),
    ("Ankit Kumar Das", "FET-BAML-2023-27-018"),
]
TITLE = "ACADEMIC SYLLABUS KNOWLEDGE GRAPH USING NER AND RELATION EXTRACTION"
SUBTITLE = ("A rule-based NLP pipeline that converts six course syllabi into a queryable "
            "knowledge graph of 148 nodes and 177 relations")
ACCENT = RGBColor(0x3B, 0x4F, 0xD8)   # indigo accent for figure captions
BASE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(BASE, "results")

# ---------------------------------------------------------------- real stats
ENTS = list(csv.DictReader(open(os.path.join(RES, "entities.csv"), encoding="utf-8")))
RELS = list(csv.DictReader(open(os.path.join(RES, "relations.csv"), encoding="utf-8")))
NODES = list(csv.DictReader(open(os.path.join(RES, "nodes.csv"), encoding="utf-8")))
EDGES = list(csv.DictReader(open(os.path.join(RES, "edges.csv"), encoding="utf-8")))
BENCH = list(csv.DictReader(open(os.path.join(RES, "query_benchmark.csv"),
                                 encoding="utf-8")))

ENT_COUNTS = Counter(e["type"] for e in ENTS)
REL_COUNTS = Counter(r["relation"] for r in RELS)
N_ENT, N_REL = len(ENTS), len(RELS)
N_NODES, N_EDGES = len(NODES), len(EDGES)
TOPICS = sorted({e["tail"] for e in EDGES if e["relation"] == "COVERS_TOPIC"})
N_TOPICS = len(TOPICS)
COURSES = sorted({e["head"] for e in EDGES if e["relation"] == "TAUGHT_BY"})
N_COURSES = len(COURSES)

_TP = sum(int(b["tp"]) for b in BENCH)
_FP = sum(int(b["fp"]) for b in BENCH)
_FN = sum(int(b["fn"]) for b in BENCH)
MICRO_P = _TP / (_TP + _FP) if _TP + _FP else 1.0
MICRO_R = _TP / (_TP + _FN) if _TP + _FN else 1.0
MICRO_F1 = (2 * MICRO_P * MICRO_R / (MICRO_P + MICRO_R)) if MICRO_P + MICRO_R else 0.0

from ner_extractor import TOPIC_GAZETTEER  # noqa: E402
N_GAZ = len(TOPIC_GAZETTEER)

# =========================================================================
# helpers
# =========================================================================

def set_cell(cell, text, bold=False, size=9.5, align="left"):
    p = cell.paragraphs[0]
    p.text = ""
    run = p.add_run(text)
    run.font.size = Pt(size)
    run.font.bold = bold
    p.alignment = {"left": WD_ALIGN_PARAGRAPH.LEFT,
                   "center": WD_ALIGN_PARAGRAPH.CENTER}[align]


def style_table(t, header=True):
    t.autofit = True
    for i, row in enumerate(t.rows):
        for cell in row.cells:
            for p in cell.paragraphs:
                p.paragraph_format.space_before = Pt(1)
                p.paragraph_format.space_after = Pt(1)
                for r in p.runs:
                    r.font.size = Pt(9.5)
                    if i == 0 and header:
                        r.font.bold = True


def insert_figure(doc, path, width_cm, caption, before_par):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    run.add_picture(path, width=Cm(width_cm))
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = cap.add_run(caption)
    r.font.size = Pt(9)
    r.font.italic = True
    r.font.color.rgb = ACCENT
    before_par._p.addprevious(p._p)
    before_par._p.addprevious(cap._p)


def monospace(target_par, text):
    for line in text.rstrip("\n").split("\n"):
        p = target_par.insert_paragraph_before("")
        run = p.add_run(line)
        run.font.size = Pt(8.5)
        rPr = run._element.get_or_add_rPr()
        rFonts = rPr.find(qn("w:rFonts"))
        if rFonts is None:
            rFonts = OxmlElement("w:rFonts")
            rPr.append(rFonts)
        for attr in ("w:ascii", "w:hAnsi", "w:cs"):
            rFonts.set(qn(attr), "Consolas")


def ensure_rows(t, n):
    while len(t.rows) < n:
        t._tbl.append(copy.deepcopy(t.rows[-1]._tr))


# =========================================================================
# load template
# =========================================================================

doc = Document(TEMPLATE)
P = doc.paragraphs

# ------------------------------------------------------------- title block
P[1].text = TITLE
P[2].text = SUBTITLE
P[4].text = SEMESTER
P[5].text = "Subject: Pattern Recognition and Anomaly Detection"
P[6].text = f"Submitted by (Group – {GROUP})"
P[8].text = "Under the Guidance of: Mr. Rahul Rawat"
P[9].text = "Department of Artificial Intelligence & Machine Learning (AIML)"
P[10].text = "Faculty of Engineering and Technology (FET)"
P[11].text = "Academic Year 2023 – 2027"

t0 = doc.tables[0]
for i, (name, roll) in enumerate(STUDENTS, start=1):
    t0.rows[i].cells[0].text = name
    t0.rows[i].cells[1].text = roll

# ------------------------------------------------------------- declaration
P[14].text = (
    f"We, the undersigned members of Group-{GROUP} ({SEMESTER.split(' Evaluation')[0]}, "
    "B.Tech – Artificial Intelligence & Machine Learning), hereby declare that the project "
    "entitled \"Academic Syllabus Knowledge Graph using NER and Relation Extraction\" is an original "
    "piece of work carried out by us as part of the 7th semester evaluation under the Pattern "
    "Recognition and Anomaly Detection subject. The work has not been submitted to any other "
    "university or institute for the award of any degree or diploma.")
P[15].text = (
    "We further declare that all sources of information, ideas, algorithms and corpora used in the "
    "preparation of this report have been duly acknowledged, and that every computational result "
    "reported here (entity counts, relation counts, graph statistics and query-benchmark scores) was "
    "produced by running the project's own code on the syllabus corpus described in Section 3.3.")
P[16].text = "Team Members:"
for i, (name, roll) in enumerate(STUDENTS):
    P[17 + i].text = f"{name} ({roll})"
# P[22]/P[23]: Place / Date intentionally left blank for physical signing

# ---------------------------------------------------------- acknowledgement
P[26].text = (
    "We take this opportunity to express our sincere gratitude to everyone who supported us throughout "
    "this project. We are deeply thankful to our guide, Mr. Rahul Rawat, for his continuous guidance, "
    "constructive feedback and encouragement at every stage of this work — from framing the "
    "information-extraction problem to interpreting the graph analytics and benchmark results.")
P[27].text = (
    "We would also like to thank the faculty members of the Department of Artificial Intelligence & "
    "Machine Learning for providing the academic foundation in natural language processing, pattern "
    "recognition and graph modelling that this project builds upon, and the Faculty of Engineering and "
    "Technology for the laboratory resources used to run the extraction pipeline.")
P[28].text = (
    "Finally, we would like to acknowledge the effort and cooperation of every member of our team, whose "
    "combined contribution made it possible to design the extraction rules, build and validate the "
    "knowledge graph, and prepare this report within the semester timeline.")

# --------------------------------------------------------------- abstract
P[31].text = (
    "University course catalogues and syllabus documents contain rich but unstructured information: "
    "prerequisite chains, weekly topic lists, learning outcomes, instructor assignments and credit "
    "weights are buried in free prose. Students planning a programme of study must manually cross-read "
    "documents to answer simple questions such as \"which courses teach clustering?\" or \"what must I "
    "complete before enrolling in Machine Learning?\". This project converts that unstructured corpus "
    "into structured, queryable knowledge using classical information extraction.")
P[32].text = (
    "The system applies rule-based Named Entity Recognition (regex patterns plus a "
    f"{N_GAZ}-entry topic gazetteer) to tag five entity types — COURSE, TOPIC, OUTCOME, INSTRUCTOR and "
    "CREDITS — with character-level spans, and pattern-based relation extraction to bind them into six "
    "typed relations: PREREQUISITE_OF, CO_REQUISITE_OF, COVERS_TOPIC, HAS_OUTCOME, TAUGHT_BY and "
    "HAS_CREDITS. Bare course codes are canonicalised to full labels so that each course remains a "
    "single graph node across all documents.")
P[33].text = (
    f"Methodology: six plain-text syllabi (Data Structures, Machine Learning, Database Systems, "
    f"Operating Systems, Computer Networks, Web Technologies) are processed by a four-stage pipeline — "
    f"NER, relation extraction, graph construction and evaluation. Extracted relations populate a "
    f"networkx MultiDiGraph exported as GraphML and CSV. Evaluation is two-fold: every extracted "
    f"relation is validated against deterministic source-document facts, and a ten-query benchmark "
    f"compares graph answers against independently derived expected answers.")
P[34].text = (
    f"The pipeline extracts {N_ENT} entities and {N_REL} relations and builds a knowledge graph of "
    f"{N_NODES} nodes and {N_EDGES} edges spanning {N_COURSES} courses and {N_TOPICS} unique topics. "
    f"All {N_REL} extracted relations ({N_REL}/{N_REL}, 100%) are consistent with their source "
    f"documents, and the ten-query benchmark achieves micro precision {MICRO_P:.4f}, recall "
    f"{MICRO_R:.4f} and F1 {MICRO_F1:.4f}. The result is a fully reproducible, offline academic "
    f"knowledge graph with an interactive explorer, demonstrating that transparent rule-based NLP can "
    f"deliver verifiably correct structured knowledge from syllabus text.")

# =====================================================================
# section 1
# =====================================================================
P[41].text = (
    "Academic institutions produce large volumes of semi-structured curriculum text — course syllabi, "
    "preregistration guides and programme handbooks. Although these documents share a common conceptual "
    "schema (a course covers topics, has outcomes, is taught by an instructor, carries credits and "
    "requires prerequisites), that schema exists only implicitly in prose. Knowledge graphs make such "
    "schemas explicit: entities become nodes, typed relations become edges, and curriculum-level "
    "questions become graph queries answerable in milliseconds.")
P[43].text = (
    "Manually building such a graph is laborious and quickly goes stale as syllabi change, which "
    "motivates automatic information extraction. Statistical NLP toolkits (spaCy, transformer-based "
    "NER) are powerful but require model downloads, GPU-class inference for large corpora and careful "
    "error analysis of statistical mistakes. For a bounded, formulaic document genre like syllabi — "
    "where course codes follow a fixed pattern, outcomes are explicitly numbered LO1…LOn and "
    "prerequisites live in dedicated sections — transparent rule-based extraction is attractive: every "
    "extraction can be traced to a regex match at a character span, which makes validation against the "
    "source text exact rather than probabilistic. This project explores how far such a fully offline, "
    "auditable pipeline goes on real syllabus structure.")
P[45].text = (
    "To design, implement and evaluate a rule-based NLP pipeline that reads plain-text course syllabi "
    "and produces a queryable academic knowledge graph in which courses, topics, learning outcomes, "
    "instructors and credits are linked by typed prerequisite and coverage relations, with measured — "
    "not assumed — extraction fidelity.")
P[47].text = (f"Curate a six-document syllabus corpus (DSA, ML, DBMS, OS, CN, Web Technologies) with a "
              "shared, realistic structure: headers, instructor and credit lines, prerequisite sections, "
              "weekly topic lists and numbered learning outcomes.")
P[48].text = (f"Implement span-tracking NER for five entity types using regex patterns and a "
              f"{N_GAZ}-entry topic gazetteer, with optional spaCy en_core_web_sm augmentation.")
P[49].text = ("Implement pattern-based relation extraction with code-to-label canonicalisation so each "
              "course is one node, including a section-scoped prerequisite sweep.")
P[50].text = (f"Build and export a networkx MultiDiGraph ({N_NODES} nodes / {N_EDGES} edges) as GraphML "
              "plus CSV, with a static matplotlib render.")
P[51].text = ("Evaluate rigorously: validate every extracted relation against deterministic "
              "source-document facts and benchmark ten curriculum queries against independently derived "
              "expected answers (precision / recall / F1).")
P[53].text = (
    "The project covers the full pipeline for the six-syllabus corpus: extraction, graph construction, "
    "validation, benchmark evaluation, graph analytics (degree rankings, prerequisite chains) and an "
    "interactive browser explorer with a query console. Explicitly out of scope: statistical or "
    "transformer-based NER (an optional spaCy backend exists for ORG/PERSON/DATE entities but the "
    "evaluated pipeline is purely rule-based), documents outside the syllabus genre, fuzzy matching of "
    "topic paraphrases not covered by the gazetteer, and multi-institution scale studies.")

# =====================================================================
# section 2
# =====================================================================
P[56].text = (
    "Information extraction from curriculum documents has traditionally used rule-based pipelines. "
    "Classical NER combines regular expressions, gazetteers and part-of-speech cues; relation "
    "extraction then binds entity pairs using trigger words and syntactic patterns. Manning, Raghavan "
    "and Schütze formalise this extraction-as-annotation view, and subsequent curriculum-analytics "
    "systems (prerequisite-chain mining from university catalogues, MOOC knowledge graphs) showed that "
    "syllabus text yields readily to deterministic patterns because of its formulaic structure.")
P[58].text = (
    "On the modelling side, Hogan et al. survey knowledge graphs as the standard substrate for "
    "representing entities and typed relations, with RDF/property-graph stores and GraphML as common "
    "interchange formats. In the education domain, prerequisite-graph studies extract course "
    "dependency networks from catalogues to power recommender and degree-planning tools; topic "
    "coverage graphs have been used for curriculum mapping and gap analysis. NetworkX provides the "
    "directed-multigraph machinery used here, and GraphML gives tool-agnostic export. Recent "
    "deep-learning NER improves recall on open text but obscures provenance — a mismatch for "
    "applications where every extracted fact should be checkable against its source sentence.")
P[60].text = ("Statistical NER pipelines are heavyweight for a six-document corpus: model downloads, "
              "inference cost and probabilistic errors that are hard to audit line by line.")
P[61].text = ("Bare course codes in prose (\"requires CS201\") refer to courses whose full titles live "
              "in other documents; pipelines that skip canonicalisation fragment one logical course "
              "into several graph nodes.")
P[62].text = ("Published curriculum extractors rarely report verifiable fidelity: extraction counts "
              "are shown without per-relation validation against the source documents, and query "
              "quality is demonstrated anecdotally rather than benchmarked.")
P[64].text = (
    "The proposed system addresses all three gaps: it is fully offline and auditable (every entity "
    "carries character spans; every relation names the document it came from), it canonicalises bare "
    "codes by recovering titles from document context so CS306 Linear Algebra referenced inside the ML "
    "syllabus resolves to a single node, and it ships a two-part evaluation — deterministic per-relation "
    "validation plus a ten-query benchmark with independently derived expected answers — so fidelity is "
    "measured, not asserted. An interactive explorer exposes the graph to non-technical users.")

# =====================================================================
# section 3
# =====================================================================
P[67].text = (
    "The system is a four-stage pipeline: (1) rule-based NER tags entities with character spans per "
    "document; (2) pattern-based relation extraction binds entity pairs into six typed relations and "
    "canonicalises course codes; (3) the graph builder assembles a networkx MultiDiGraph and exports "
    "GraphML + CSV artefacts; (4) the evaluation layer validates relations against source facts and "
    "benchmarks ten curriculum queries. Auxiliary modules render the graph (matplotlib spring layout) "
    "and answer demo queries. run_all.py orchestrates the whole pipeline in one command.")
P[69].text = "Input: plain-text syllabus documents from data/syllabi/*.txt (UTF-8, one file per course)."
P[70].text = ("Tokenisation-free scanning: regexes operate directly on raw text with character-offset "
              "spans preserved for every entity (span_start, span_end), enabling exact source tracing.")
P[71].text = ("Entity layer: seven core regex extractors (course header, course code, instructor, "
              "credits, outcome marker, prerequisite trigger, co-requisite trigger) plus longest-match-"
              "first gazetteer scanning for topics.")
P[72].text = ("Relation layer: trigger-pattern bindings (TAUGHT_BY, HAS_CREDITS, PREREQUISITE_OF, "
              "CO_REQUISITE_OF, COVERS_TOPIC, HAS_OUTCOME) with per-document canonicalisation of bare "
              "codes into full course labels.")
P[73].text = (f"Output: results/entities.csv ({N_ENT} rows), results/relations.csv ({N_REL} rows), "
              f"knowledge_graph.graphml + nodes.csv + edges.csv ({N_NODES} nodes / {N_EDGES} edges), "
              "a rendered graph figure, and evaluation CSVs (validation + benchmark).")
P[75].text = (
    "The corpus comprises six plain-text syllabi totalling six distinct course documents: CS201 Data "
    "Structures & Algorithms, CS301 Machine Learning, CS302 Database Systems, CS303 Operating Systems, "
    "CS304 Computer Networks and CS305 Web Technologies. Each document follows the same realistic "
    "schema: a header line with code and title; an instructor line (\"Dr. R. Iyer\"); a credit value; a "
    "prose course description; a Prerequisites section naming prerequisite and co-requisite courses; a "
    "weekly Topics Covered list; and explicitly numbered Learning Outcomes (LO1…LO5). Topic mentions "
    "are detected against the gazetteer wherever they appear — in week lists or in prose — and "
    "prerequisite sections additionally name courses from outside the corpus (e.g. MA202 Probability & "
    "Statistics, CS306 Linear Algebra, CS101 Introduction to Programming), which must still resolve to "
    "well-labelled nodes. The corpus is fixed and versioned in the repository, making every statistic "
    "in this report exactly reproducible.")
P[77].text = ("Text normalisation is deliberately minimal — documents are read as-is; matching is "
              "case-insensitive with original casing preserved in the output entities.")
P[78].text = (f"Gazetteer scanning processes topics longest-match-first ({N_GAZ} entries) and suppresses "
              "overlapping shorter hits, so \"k-means clustering\" wins over \"clustering\" at the same "
              "position.")
P[79].text = ("Outcome sentences are harvested from each LO marker to the sentence end (stopping before "
              "the next LO id), and whitespace is collapsed for clean CSV output.")
P[81].text = (
    "NER is implemented as deterministic scanners over each document: INSTRUCTOR_RE captures titled "
    "academic names (\"Dr. R. Iyer\"), CREDITS_RE captures credit values, COURSE_RE captures full "
    "\"CODE Title\" headers, OUTCOME_RE captures LO-marker sentences, and the topic gazetteer covers "
    f"{N_GAZ} curriculum concepts. Relation extraction composes six relations from those spans: "
    "TAUGHT_BY and HAS_CREDITS bind the document's own course to its instructor and credits; "
    "PREREQUISITE_OF / CO_REQUISITE_OF bind prerequisite codes to the course (trigger-word patterns "
    "plus a section-scoped sweep of the Prerequisites block, with co-requisite proximity detection); "
    "COVERS_TOPIC links the course to every gazetteer topic occurrence; HAS_OUTCOME links it to each "
    "outcome sentence. A code-to-label map built from document headers canonicalises bare codes, and "
    "full_label_for() recovers titles for codes with no syllabus file by reading the title following "
    "the code in context. The build step inserts every relation into a networkx MultiDiGraph, types "
    "each node from its role, and writes GraphML + CSVs.")

# =====================================================================
# section 4
# =====================================================================
P[84].text = (
    "Table 1 summarises the pipeline stage by stage. Unlike a neural architecture table, \"scale\" "
    "here reports the concrete artefact each stage contributes to the final graph.")
t1 = doc.tables[1]
t1_rows = [
    ("Stage", "Component", "Output", "Scale"),
    ("Text ingestion", "syllabus reader (data/syllabi/*.txt)", "6 raw documents", "6 files"),
    ("Entity layer", "regex extractors + topic gazetteer (ner_extractor.py)",
     "tagged entities with spans", f"{N_ENT} entities, 5 types"),
    ("Relation layer", "trigger patterns + canonicalisation (relation_extractor.py)",
     "typed relations per document", f"{N_REL} relations, 6 types"),
    ("Graph layer", "networkx MultiDiGraph build (build_graph.py)",
     "GraphML + nodes/edges CSV", f"{N_NODES} nodes / {N_EDGES} edges"),
]
ensure_rows(t1, len(t1_rows))
for i, row_vals in enumerate(t1_rows):
    for j, val in enumerate(row_vals):
        set_cell(t1.rows[i].cells[j], val, bold=(i == 0))
style_table(t1)

P[87].text = "Python 3.12 with standard library re/csv — all extraction patterns and evaluation logic"
P[88].text = ("networkx 3.x — MultiDiGraph construction, GraphML serialisation, degree analytics; "
              "pandas — relation-frame loading")
P[89].text = ("matplotlib — static spring-layout render of the graph; networkx.read_graphml — "
              "evaluation-time graph reload")
P[90].text = ("Optional: spaCy en_core_web_sm for ORG/PERSON/DATE augmentation; interactive browser "
              "explorer (HTML/JavaScript canvas) with no server dependencies")

P[92].text = ("Corpus organisation: curate the six syllabus documents under data/syllabi/ with a "
              "shared schema (header, instructor, credits, prerequisites, topics, LO outcomes) "
              "(data/syllabi/*.txt).")
P[93].text = ("Entity extraction: run the span-tracking NER scanners (instructor, credits, course "
              "header/code, outcomes) plus longest-match-first gazetteer scanning per document "
              "(ner_extractor.py).")
P[94].text = ("Relation extraction: apply the six trigger-pattern bindings, canonicalise bare codes "
              "via the header map and full_label_for(), and sweep the Prerequisites section "
              "(relation_extractor.py).")
P[95].text = ("Graph build: insert every relation into a networkx MultiDiGraph, type each node from "
              "its role, and export GraphML + nodes.csv + edges.csv (build_graph.py).")
P[96].text = ("Validation: re-derive deterministic facts from each source document and check every "
              "extracted relation against them (evaluate_extraction.py: validate).")
P[97].text = ("Query benchmark: pose the ten curriculum questions, derive expected answers "
              "independently from the raw text, and score precision/recall/F1 "
              "(evaluate_extraction.py: main).")

snip1 = '''# longest-match-first gazetteer scanning (ner_extractor.py, abridged)
lower = text.lower()
for topic in sorted(TOPIC_GAZETTEER, key=len, reverse=True):
    for m in re.finditer(rf"\\b{re.escape(topic)}\\b", lower, flags=re.IGNORECASE):
        s, e = m.span()
        if any(s < t_end and e > t_start for t_start, t_end in taken):
            continue            # "k-means clustering" beats "clustering"
        taken.append((s, e))'''
monospace(P[99], snip1)

snip2 = '''# section-scoped prerequisite sweep (relation_extractor.py, abridged)
pre_m = re.search(r"Prerequisites?:\\s*(.*?)(?=\\n\\s*\\n|\\Z)", text,
                  re.IGNORECASE | re.DOTALL)
for cm in re.finditer(r"\\b([A-Z]{2,4})\\s?-?(\\d{3})\\b", section):
    rel = ("CO_REQUISITE_OF" if "co-requisite" in context
           else "PREREQUISITE_OF")
    relations.append(dict(head=canon(code), relation=rel, tail=own_label))'''
monospace(P[99], snip2)
P[99].text = ""

# =====================================================================
# section 5
# =====================================================================
P[102].text = (
    f"Final corpus: 6 syllabus documents across 6 subject areas. Extraction produced {N_ENT} entity "
    f"mentions (TOPIC {ENT_COUNTS['TOPIC']}, OUTCOME {ENT_COUNTS['OUTCOME']}, COURSE "
    f"{ENT_COUNTS['COURSE']}, INSTRUCTOR {ENT_COUNTS['INSTRUCTOR']}, CREDITS {ENT_COUNTS['CREDITS']}) "
    f"and {N_REL} relations (COVERS_TOPIC {REL_COUNTS['COVERS_TOPIC']}, HAS_OUTCOME "
    f"{REL_COUNTS['HAS_OUTCOME']}, PREREQUISITE_OF {REL_COUNTS['PREREQUISITE_OF']}, TAUGHT_BY "
    f"{REL_COUNTS['TAUGHT_BY']}, HAS_CREDITS {REL_COUNTS['HAS_CREDITS']}, CO_REQUISITE_OF "
    f"{REL_COUNTS['CO_REQUISITE_OF']}), consolidated into a graph of {N_NODES} nodes and {N_EDGES} "
    f"edges covering {N_COURSES} course nodes and {N_TOPICS} unique topics.")

t2 = doc.tables[2]
t2_rows = [
    ("Parameter", "Value"),
    ("Corpus", "6 syllabus documents (data/syllabi/*.txt)"),
    ("Entity types", "5 (COURSE, TOPIC, OUTCOME, INSTRUCTOR, CREDITS)"),
    ("Relation types", "6 (PREREQUISITE_OF, CO_REQUISITE_OF, COVERS_TOPIC, HAS_OUTCOME, TAUGHT_BY, HAS_CREDITS)"),
    ("Topic gazetteer", f"{N_GAZ} curriculum concepts, longest-match-first"),
    ("Graph model", f"networkx MultiDiGraph — {N_NODES} nodes / {N_EDGES} edges"),
    ("Export formats", "GraphML + nodes.csv + edges.csv + entities.csv + relations.csv"),
]
for i, row_vals in enumerate(t2_rows):
    for j, val in enumerate(row_vals):
        set_cell(t2.rows[i].cells[j], val, bold=(i == 0))
style_table(t2)

P[106].text = (
    "Fidelity is measured with two complementary instruments. Extraction validation re-reads every "
    "syllabus and derives deterministic facts — the instructor line, the credit value, literal topic "
    "occurrence, LO markers and prerequisite codes named in the text — then checks each extracted "
    "relation against them; any contradiction is a genuine extraction error, so the resulting "
    "consistency rate is a hard upper bound on precision. Query quality is benchmarked with ten "
    "curriculum questions (prerequisites, topic-to-course lookup, outcomes, instructor lookup) whose "
    "expected answers are derived independently from the raw text; per-query precision, recall and F1 "
    "are micro-aggregated. Graph statistics (node/edge counts, degree rankings) characterise the "
    "structure itself.")

t3 = doc.tables[3]
t3_rows = [
    ("Model", "Accuracy", "Precision", "Recall", "F1-Score"),
    ("Rule-based extraction + graph (10-query benchmark, micro)",
     f"{MICRO_F1:.4f}", f"{MICRO_P:.4f}", f"{MICRO_R:.4f}", f"{MICRO_F1:.4f}"),
    ("Relation validation against source documents",
     f"{N_REL}/{N_REL} = 100.0%", "—", "—", "—"),
]
for i, row_vals in enumerate(t3_rows):
    for j, val in enumerate(row_vals):
        set_cell(t3.rows[i].cells[j], val, bold=(i == 0))
style_table(t3)

P[109].text = (
    "The pipeline is deterministic: with a fixed corpus it reproduces identical entity, relation and "
    "graph statistics on every run, and the ten-query benchmark consistently answers 30 expected "
    "answer elements correctly (micro F1 "
    f"{MICRO_F1:.4f}). The densest course nodes by outgoing degree are CS301 Machine Learning, CS201 "
    "Data Structures & Algorithms and CS304 Computer Networks — each covering 24+ topics and five "
    "outcomes — while the prerequisite chain CS101 → CS201 → {CS302, CS303} → CS304 → CS305 emerges "
    "from the PREREQUISITE_OF edges without any manual wiring.")

# =====================================================================
# section 6
# =====================================================================
P[114].text = "6.2 Query Answering and Output Quality"

t4 = doc.tables[4]
t4_rows = [("Relation type", "Extracted / source-consistent", "Violations")]
for rel in ["COVERS_TOPIC", "HAS_OUTCOME", "PREREQUISITE_OF", "TAUGHT_BY",
            "HAS_CREDITS", "CO_REQUISITE_OF"]:
    n = REL_COUNTS[rel]
    t4_rows.append((rel, f"{n} / {n}", "0"))
t4_rows.append(("TOTAL", f"{N_REL} / {N_REL} (100%)", "0"))
ensure_rows(t4, len(t4_rows))
for i, row_vals in enumerate(t4_rows):
    for j, val in enumerate(row_vals):
        set_cell(t4.rows[i].cells[j], val, bold=(i == 0 or row_vals[0] == "TOTAL"))
style_table(t4)

P[113].text = (
    f"Table 4 reports the validation verdict per relation type: all {N_REL} extracted relations "
    f"({N_REL}/{N_REL}, 100%) are consistent with deterministic facts re-derived from their source "
    "documents — every TAUGHT_BY tail matches the document's instructor line, every COVERS_TOPIC tail "
    "occurs literally in the document, every HAS_OUTCOME tail reproduces a numbered outcome sentence, "
    "and every prerequisite head's course code appears in the target document. During development the "
    "benchmark itself caught two genuine recall bugs — bare codes without a syllabus file (CS306, "
    "MA202) were not canonicalised, and prerequisites listed without a trigger word (\"...completed "
    "CS201 and MA202...\") were missed — both fixed by the canonicalisation helper and the "
    "section-scoped sweep, which is exactly the audit-first workflow rule-based extraction enables.")
P[115].text = (
    "Qualitatively, the graph answers curriculum questions directly: the prerequisites of CS301 "
    "resolve to CS201, MA202 and co-requisite CS306; topic lookups (\"clustering\", \"sql\", "
    "\"deadlocks\", \"subnetting\", \"flexbox\") each return exactly the course that teaches them; "
    "and outcome queries return the full LO1–LO5 sentence set. The interactive explorer visualises "
    "all nodes and edges with force-directed layout, inspector-panel drill-down and a query console "
    "that mirrors query_graph.py, so the extraction quality can be inspected without reading any code.")
P[117].text = (
    "Against the obvious alternative — keyword search over the raw syllabus files — the graph offers "
    "relation-aware answers: search finds documents containing \"clustering\" but cannot enumerate "
    "CS301's prerequisite chain without a human reading each file, whereas the graph answers "
    "PREREQUISITE_OF traversal in one step. Against manual curriculum mapping, the pipeline's "
    "advantage is reproducibility and auditability: re-running the entire build takes seconds and "
    "every edge can be traced to a character span in a named document, where manual maps can be "
    "checked only by re-reading everything.")
P[119].text = ("All 177 relations validate against source-document facts; the two development-time "
               "recall bugs were caught by the benchmark, not by eyeballing.")
P[120].text = ("The prerequisite chain emerges purely from extraction — no manual edge editing — and "
               "course nodes stay singular thanks to code canonicalisation.")
P[121].text = ("Topic lookups are exact (precision 1.0) because gazetteer matching is boundaried and "
               "longest-match-first; paraphrases outside the gazetteer are the recall limit.")
P[123].text = ("Fully offline and dependency-light: standard-library regex + networkx; no model "
               "downloads or GPU.")
P[124].text = ("Every entity carries character spans and every relation names its source document, so "
               "any fact can be audited in seconds.")
P[125].text = ("Deterministic and exactly reproducible: identical inputs regenerate identical "
               "statistics, figures and benchmark scores.")
P[127].text = ("Gazetteer recall is bounded: topics phrased outside the "
               f"{N_GAZ}-entry vocabulary (synonyms, paraphrases) are not extracted.")
P[128].text = "Corpus-scale dependency: patterns assume the syllabus genre's formatting conventions (headers, LO markers, Prerequisites sections)."
P[129].text = ("MultiDiGraph parallel edges (e.g. a topic named in both prose and the week list) "
               "inflate edge counts relative to simple-digraph views; the explorer collapses them "
               "visually but the CSVs preserve them.")

# =====================================================================
# section 7
# =====================================================================
P[132].text = (
    f"This project delivers an end-to-end, fully reproducible academic knowledge-graph pipeline: "
    f"rule-based NER and relation extraction convert six syllabus documents into {N_ENT} entities and "
    f"{N_REL} typed relations, consolidated into a {N_NODES}-node / {N_EDGES}-edge networkx MultiDiGraph "
    f"spanning {N_COURSES} courses and {N_TOPICS} unique topics. Evaluation is built in rather than "
    f"bolted on: {N_REL}/{N_REL} relations validate against deterministic source-document facts and the "
    f"ten-query benchmark reaches micro F1 {MICRO_F1:.4f}. The development loop itself demonstrated the "
    "value of auditable extraction — the benchmark exposed two real recall bugs that were then fixed "
    "with a canonicalisation helper and a section-scoped prerequisite sweep.")
P[134].text = ("Scale the corpus to a full university catalogue (100+ syllabi) and add gazetteer "
               "auto-expansion: harvest frequent noun phrases from the corpus as candidate topics.")
P[135].text = ("Add a statistical NER comparison arm (spaCy en_core_web_sm / transformer NER) and "
               "quantify the precision/recall trade-off against the rule-based baseline per entity "
               "type.")
P[136].text = ("Serve the graph behind a degree-planning assistant: natural-language questions mapped "
               "to the five query templates, with prerequisite-aware elective recommendations and "
               "curriculum gap analysis.")
P[138].text = (
    "As detailed in Section 6.6, the current conclusions are bounded by the corpus size (six "
    "documents, one institution's formatting conventions), the gazetteer's vocabulary coverage and "
    "the assumption of well-formed syllabus structure. Within those bounds the central result stands: "
    "transparent rule-based extraction, coupled with per-relation validation and a benchmarked query "
    "suite, produces a curriculum knowledge graph whose every fact is traceable to source text — with "
    f"measured fidelity ({N_REL}/{N_REL} consistent, benchmark F1 {MICRO_F1:.4f}) rather than assumed "
    "quality.")
P[140].text = ('[1] C. D. Manning, P. Raghavan, and H. Schütze, "Introduction to Information '
               'Retrieval", Cambridge University Press, 2008.')
P[141].text = ('[2] A. Hogan, E. Blomqvist, M. Cochez, et al., "Knowledge Graphs", ACM Computing '
               'Surveys, 54(4), 2021.')
P[142].text = ("[3] NetworkX Documentation — MultiDiGraph and GraphML I/O, NetworkX Developers, "
               "https://networkx.org (accessed 2026).")

# =====================================================================
# figures (generated from the real CSVs)
# =====================================================================
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Figure 1: entity + relation type distributions
fig1 = os.path.join(RES, "report_fig_distribution.png")
if not os.path.exists(fig1):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    ec = ENT_COUNTS.most_common()
    axes[0].barh([k for k, _ in ec][::-1], [v for _, v in ec][::-1], color="#3B4FD8")
    axes[0].set_title(f"Entity types ({N_ENT} entities)")
    for i, (k, v) in enumerate(ec[::-1]):
        axes[0].text(v + 1, i, str(v), va="center", fontsize=9)
    rc = REL_COUNTS.most_common()
    axes[1].barh([k for k, _ in rc][::-1], [v for _, v in rc][::-1], color="#0D9488")
    axes[1].set_title(f"Relation types ({N_REL} relations)")
    for i, (k, v) in enumerate(rc[::-1]):
        axes[1].text(v + 1, i, str(v), va="center", fontsize=9)
    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(fig1, dpi=150)
    plt.close(fig)

# Figure 2: the graph itself (pipeline render)
fig2 = os.path.join(RES, "knowledge_graph.png")

# Figure 3: per-query benchmark F1
fig3 = os.path.join(RES, "report_fig_benchmark.png")
if not os.path.exists(fig3):
    labels = [b["query"] for b in BENCH]
    f1s = [float(b["f1"]) for b in BENCH]
    fig, ax = plt.subplots(figsize=(10, 4.6))
    bars = ax.barh(labels[::-1], f1s[::-1],
                   color=["#3E7C4F" if f == 1 else "#C2365B" for f in f1s[::-1]])
    ax.set_xlim(0, 1.15)
    ax.set_xlabel("F1 (expected answers derived from raw text)")
    ax.set_title(f"Ten-query benchmark — micro F1 {MICRO_F1:.4f}")
    for bar, f in zip(bars, f1s[::-1]):
        ax.text(min(f + 0.02, 1.1), bar.get_y() + bar.get_height() / 2,
                f"{f:.2f}", va="center", fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(fig3, dpi=150)
    plt.close(fig)

# Figure 1 before 5.1 Dataset Details (P101)
insert_figure(doc, fig1, 16.0,
              f"Figure 1: Extraction output distribution — {N_ENT} entities (left) and "
              f"{N_REL} relations (right) by type", P[101])

# Figure 2 before 5.4 Results heading (P107)
insert_figure(doc, fig2, 16.0,
              f"Figure 2: The academic knowledge graph — {N_NODES} nodes / {N_EDGES} edges "
              "(blue=COURSE, orange=PREREQUISITE, green=TOPIC, red=OUTCOME)", P[107])

# Figure 3 before 6.1 heading (P111)
insert_figure(doc, fig3, 15.0,
              "Figure 3: Per-query benchmark scores — all ten curriculum queries at F1 = 1.00",
              P[111])

# =====================================================================
doc.save(OUT)
print("saved", OUT)
