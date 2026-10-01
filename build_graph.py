"""
Build an academic knowledge graph (networkx MultiDiGraph) from the extracted
entities and relations.

Outputs:
  results/knowledge_graph.graphml
  results/nodes.csv
  results/edges.csv
"""
import csv
import os

import networkx as nx
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE, "results")


def main():
    rel_path = os.path.join(OUT_DIR, "relations.csv")
    rels = pd.read_csv(rel_path)

    G = nx.MultiDiGraph()
    type_map = {}

    for _, r in rels.iterrows():
        h, t = str(r["head"]).strip(), str(r["tail"]).strip()
        type_map.setdefault(h, r["head_type"])
        type_map.setdefault(t, r["tail_type"])
        # normalize bare prerequisite codes to their course label if known
        G.add_edge(h, t, relation=r["relation"], doc=r["doc"])

    for node in G.nodes:
        G.nodes[node]["type"] = type_map.get(node, "TOPIC")

    os.makedirs(OUT_DIR, exist_ok=True)
    nx.write_graphml(G, os.path.join(OUT_DIR, "knowledge_graph.graphml"))

    with open(os.path.join(OUT_DIR, "nodes.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["node", "type"])
        for n, d in G.nodes(data=True):
            w.writerow([n, d.get("type", "")])

    with open(os.path.join(OUT_DIR, "edges.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["head", "relation", "tail", "doc"])
        for u, v, d in G.edges(data=True):
            w.writerow([u, d["relation"], v, d.get("doc", "")])

    type_counts = {}
    for _, t in type_map.items():
        type_counts[t] = type_counts.get(t, 0) + 1
    rel_counts = {}
    for _, _, d in G.edges(data=True):
        rel_counts[d["relation"]] = rel_counts.get(d["relation"], 0) + 1

    print(f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    print("Node types:", type_counts)
    print("Edge types:", rel_counts)
    print(f"saved {OUT_DIR}/knowledge_graph.graphml, nodes.csv, edges.csv")
    return G


if __name__ == "__main__":
    main()
