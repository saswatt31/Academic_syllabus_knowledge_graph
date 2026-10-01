"""
Demo queries against the academic knowledge graph.

  1. prerequisites of a course
  2. courses that cover a topic
  3. learning outcomes of a course
  4. courses an instructor teaches
  5. top courses by topic coverage (graph analytics)
"""
import networkx as nx

BASE = "results/knowledge_graph.graphml"


def load():
    return nx.read_graphml(BASE)


def prerequisites_of(G, course_sub: str):
    out = []
    for u, v, d in G.edges(data=True):
        if d.get("relation") in {"PREREQUISITE_OF", "CO_REQUISITE_OF"} and \
                course_sub.lower() in str(v).lower():
            out.append(f"{u}  ({d['relation'].replace('_OF', '')})")
    return out or ["(none found)"]


def courses_covering(G, topic_sub: str):
    hits = set()
    for u, v, d in G.edges(data=True):
        if d.get("relation") == "COVERS_TOPIC" and \
                topic_sub.lower() in str(v).lower():
            hits.add(str(u))
    return sorted(hits) or ["(none found)"]


def outcomes_of(G, course_sub: str):
    out = [str(v) for u, v, d in G.edges(data=True)
           if d.get("relation") == "HAS_OUTCOME"
           and course_sub.lower() in str(u).lower()]
    return out or ["(none found)"]


def taught_by(G, instructor_sub: str):
    out = [str(u) for u, v, d in G.edges(data=True)
           if d.get("relation") == "TAUGHT_BY"
           and instructor_sub.lower() in str(v).lower()]
    return out or ["(none found)"]


def main():
    G = load()
    print(f"Loaded graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges\n")

    q = "CS301"
    print(f"Q1. Prerequisites of a course matching '{q}':")
    for x in prerequisites_of(G, q):
        print("   ->", x)

    t = "clustering"
    print(f"\nQ2. Courses covering '{t}':")
    for x in courses_covering(G, t):
        print("   ->", x)

    print(f"\nQ3. Learning outcomes of '{q}':")
    for x in outcomes_of(G, q)[:3]:
        print("   ->", x)

    print("\nQ4. Courses taught by 'Iyer':")
    for x in taught_by(G, "Iyer"):
        print("   ->", x)

    print("\nQ5. Top 5 courses by number of topics covered:")
    deg = sorted(G.out_degree(), key=lambda kv: kv[1], reverse=True)
    for n, k in deg[:5]:
        print(f"   {n}: {k} outgoing relations")


if __name__ == "__main__":
    main()
