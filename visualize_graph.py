"""
Visualize the academic knowledge graph.

  results/knowledge_graph.png   - matplotlib spring layout (always produced)
  results/knowledge_graph.html  - interactive pyvis version (if pyvis installed)
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE, "results")

TYPE_COLORS = {
    "COURSE": "#4e79a7",
    "PREREQUISITE": "#f28e2b",
    "TOPIC": "#59a14f",
    "OUTCOME": "#e15759",
    "INSTRUCTOR": "#b07aa1",
    "CREDITS": "#9c755f",
    "ORG": "#76b7b2", "PERSON": "#76b7b2", "DATE": "#bab0ac", "GPE": "#bab0ac",
}


def main():
    G = nx.read_graphml(os.path.join(OUT_DIR, "knowledge_graph.graphml"))

    # collapse parallel edges for the static drawing
    S = nx.DiGraph()
    for u, v, d in G.edges(data=True):
        S.add_edge(u, v, relation=d.get("relation", ""))
    for n in G.nodes:
        S.nodes[n]["type"] = G.nodes[n].get("type", "TOPIC")

    pos = nx.spring_layout(S, k=0.55, seed=7, iterations=120)
    node_types = [S.nodes[n].get("type", "TOPIC") for n in S.nodes]
    colors = [TYPE_COLORS.get(t, "#888888") for t in node_types]
    sizes = [1400 if S.nodes[n].get("type") == "COURSE" else
             500 if S.nodes[n].get("type") == "PREREQUISITE" else 180
             for n in S.nodes]

    plt.figure(figsize=(18, 13))
    nx.draw_networkx_edges(S, pos, alpha=0.25, arrowsize=8)
    nx.draw_networkx_nodes(S, pos, node_color=colors, node_size=sizes, alpha=0.9)
    big = [n for n in S.nodes if S.nodes[n].get("type") in {"COURSE", "PREREQUISITE"}]
    nx.draw_networkx_labels(S, pos, labels={n: n for n in big}, font_size=7)
    rel_to_color = {"PREREQUISITE_OF": "#d62728", "CO_REQUISITE_OF": "#ff7f0e"}
    for u, v, d in S.edges(data=True):
        if d["relation"] in rel_to_color:
            nx.draw_networkx_edges(S, pos, edgelist=[(u, v)],
                                   edge_color=rel_to_color[d["relation"]],
                                   arrowsize=10)
    plt.title("Academic Syllabus Knowledge Graph\n"
              "(blue=COURSE orange=PREREQUISITE green=TOPIC red=OUTCOME)", fontsize=13)
    plt.axis("off")
    plt.tight_layout()
    os.makedirs(OUT_DIR, exist_ok=True)
    out_png = os.path.join(OUT_DIR, "knowledge_graph.png")
    plt.savefig(out_png, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"saved {out_png}")

    # optional interactive version
    try:
        from pyvis.network import Network
        net = Network(height="800px", width="100%", directed=True,
                      notebook=False, cdn_resources="remote")
        for n, d in G.nodes(data=True):
            t = d.get("type", "TOPIC")
            net.add_node(n, label=n, title=f"{n} ({t})",
                         color=TYPE_COLORS.get(t, "#888888"),
                         size=18 if t in {"COURSE", "PREREQUISITE"} else 8)
        for u, v, d in G.edges(data=True):
            net.add_edge(u, v, title=d.get("relation", ""))
        out_html = os.path.join(OUT_DIR, "knowledge_graph.html")
        net.write_html(out_html)
        print(f"saved {out_html} (interactive)")
    except ImportError:
        print("pyvis not installed - skipping interactive HTML "
              "(pip install pyvis)")


if __name__ == "__main__":
    main()
