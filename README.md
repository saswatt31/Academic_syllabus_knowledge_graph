# Academic Syllabus Knowledge Graph (NER + Relation Extraction)

Builds a **knowledge graph** from raw academic syllabus text using classic NLP:
**Named Entity Recognition** (regex/rule-based + optional spaCy) and lightweight
**relation extraction** (dependency / co-occurrence patterns).

Entities: `COURSE`, `TOPIC`, `PREREQUISITE`, `OUTCOME`, `INSTRUCTOR`, `CREDITS`.
Relations: `PREREQUISITE_OF`, `COVERS_TOPIC`, `HAS_OUTCOME`, `TAUGHT_BY`,
`HAS_CREDITS`, `CO_REQUISITE_OF`.

## Files
| File | Purpose |
|---|---|
| `data/syllabi/*.txt` | 6 sample syllabi (DSA, DBMS, ML, OS, CN, Web Tech) with prerequisites, topics, outcomes |
| `ner_extractor.py` | Rule-based NER (regex + keyword gazetteers) with optional spaCy `en_core_web_sm` backend |
| `relation_extractor.py` | Pattern-based relation extraction between entity pairs |
| `build_graph.py` | Builds a `networkx.MultiDiGraph`, exports `results/knowledge_graph.graphml`, `nodes.csv`, `edges.csv` |
| `visualize_graph.py` | Spring-layout matplotlib render + interactive `pyvis` HTML (if installed) |
| `query_graph.py` | Demo queries: prerequisites of a course, courses covering a topic, learning outcomes |
| `run_all.py` | Runs the whole pipeline |

## How to run
```bash
python run_all.py
```
or step by step:
```bash
python ner_extractor.py            # -> results/entities.csv
python relation_extractor.py       # -> results/relations.csv
python build_graph.py              # -> results/knowledge_graph.graphml + CSVs
python visualize_graph.py          # -> results/knowledge_graph.png (+ .html if pyvis installed)
python query_graph.py              # demo answers from the graph
```

## Optional: spaCy backend
The default extractor needs no downloads. For statistical NER on top of the
rules: `pip install spacy && python -m spacy download en_core_web_sm`
(used for extra ORG/PERSON entities like universities and instructors).

## Sample output (verified run)
```
Entities extracted: 182  (TOPIC 131, COURSE 14, OUTCOME 25, INSTRUCTOR 6, ...)
Relations extracted: 176 (COVERS_TOPIC 131, HAS_OUTCOME 25, PREREQUISITE_OF 6,
                          TAUGHT_BY 6, HAS_CREDITS 6, CO_REQUISITE_OF 2)
Graph: 147 nodes, 176 edges  ->  results/knowledge_graph.graphml
Q1. Prerequisites of a course matching 'CS301':
   -> CS201 Data Structures & Algorithms  (PREREQUISITE)
   -> CS306  (CO_REQUISITE)
Q3. Learning outcomes of 'CS301':
   -> LO1. Formulate a prediction problem as regression or classification.
```

## Deliverables (submission-ready)

| Artefact | File |
|---|---|
| Project report (official template) | `Project_Report_Academic_Syllabus_Knowledge_Graph.docx` |
| Presentation (10 slides, light theme) | `Presentation_Academic_Syllabus_Knowledge_Graph.pptx` |
| Interactive frontend ("Syllabus Atlas") | `frontend/index.html` (serve with `python -m http.server 8000 --directory frontend`) |

Build / verify commands:
```bash
python run_all.py                    # full pipeline incl. evaluate_extraction.py
python frontend/build_demo_data.py   # assemble frontend data bundle
python make_report.py                # fill the official template -> report DOCX
python check_report_template.py      # compliance check (PASS)
python make_slides.py                # 10-slide deck
python check_slides_layout.py        # layout audit (PASS)
python render_slides_preview.py      # PNG previews -> slides_preview/index.html
```
