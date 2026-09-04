from __future__ import annotations

from dataclasses import asdict, dataclass
import json

from database.connection import Database


@dataclass(slots=True)
class GraphNode:
    id: str
    type: str
    title: str
    path: str | None = None
    importance: float = 1.0
    active: bool = False


@dataclass(slots=True)
class GraphEdge:
    source: str
    target: str
    relation: str


class KnowledgeGraph:
    def __init__(self, db: Database): self.db = db

    def rebuild(self) -> tuple[list[GraphNode], list[GraphEdge]]:
        nodes = {"naty": GraphNode("naty", "agent", "NATY", importance=3.0)}; edges: set[tuple[str,str,str]] = set()
        title_map = {}
        for row in self.db.query("SELECT * FROM obsidian_documents"):
            path = row["path"].replace("\\", "/")
            node_type = "note"
            if "/03 - Projetos/" in f"/{path}": node_type = "project_note"
            elif "/07 - Skills/" in f"/{path}": node_type = "skill"
            elif "/05 - Memórias/" in f"/{path}": node_type = "memory_note"
            node_id = f"note:{row['path']}"; nodes[node_id] = GraphNode(node_id, node_type, row["title"], row["path"]); title_map[row["title"].casefold()] = node_id
            edges.add(("naty", node_id, "knows"))
        for row in self.db.query("SELECT path,wikilinks FROM obsidian_documents"):
            source = f"note:{row['path']}"
            for title in json.loads(row["wikilinks"] or "[]"):
                target = title_map.get(title.casefold(), f"concept:{title.casefold()}")
                if target not in nodes: nodes[target] = GraphNode(target, "concept", title)
                edges.add((source, target, "wikilink"))
        for row in self.db.query("SELECT * FROM projects"):
            node_id = f"project:{row['id']}"; nodes[node_id] = GraphNode(node_id, "project", row["name"], importance=2.0); edges.add(("naty", node_id, "project"))
            for task in self.db.query("SELECT id,title FROM tasks WHERE project_id=?", (row["id"],)):
                task_id=f"task:{task['id']}"; nodes[task_id]=GraphNode(task_id,"task",task["title"]); edges.add((node_id,task_id,"contains"))
        for row in self.db.query("SELECT * FROM memories"):
            node_id=f"memory:{row['id']}"; nodes[node_id]=GraphNode(node_id,"memory",row["key"]); edges.add(("naty",node_id,"remembers"))
        with self.db.transaction() as conn:
            conn.execute("DELETE FROM knowledge_edges"); conn.execute("DELETE FROM knowledge_nodes")
            conn.executemany("INSERT INTO knowledge_nodes(id,type,title,path,importance,metadata_json) VALUES(?,?,?,?,?,?)",
                [(n.id,n.type,n.title,n.path,n.importance,"{}") for n in nodes.values()])
            conn.executemany("INSERT INTO knowledge_edges(source,target,relation) VALUES(?,?,?)", list(edges))
        return list(nodes.values()), [GraphEdge(*e) for e in edges]

    def snapshot(self, limit: int = 24) -> tuple[list[GraphNode], list[GraphEdge]]:
        rows = self.db.query("SELECT * FROM knowledge_nodes ORDER BY importance DESC,last_accessed DESC LIMIT ?", (limit,))
        nodes = [GraphNode(r["id"],r["type"],r["title"],r["path"],r["importance"]) for r in rows]; ids={n.id for n in nodes}
        edges = [GraphEdge(r["source"],r["target"],r["relation"]) for r in self.db.query("SELECT * FROM knowledge_edges") if r["source"] in ids and r["target"] in ids]
        return nodes, edges
