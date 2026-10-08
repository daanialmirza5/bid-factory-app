import os
from neo4j import GraphDatabase

class GraphRAGService:
    def __init__(self):
        # We wrap this in a safe try/except so it NEVER crashes the main pipeline
        # if the Docker container is not running during a demo.
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "")
        self.driver = None
        self._connect()

    def _connect(self):
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        except Exception as e:
            print(f"GraphRAG Service Offline: Docker container not running. Error: {e}")

    def close(self):
        if self.driver:
            self.driver.close()

    def safely_extract_graph_knowledge(self, requirement_text: str):
        """
        This safely queries Neo4j. If Neo4j is offline, it gracefully returns empty metadata 
        so the main pipeline NEVER breaks.
        """
        if not self.driver:
            return {"graph_entities": [], "status": "Neo4j Offline - Bypassed"}

        try:
            with self.driver.session() as session:
                # Example GraphRAG traversal: match a requirement category to a compliance policy
                result = session.run(
                    "MATCH (r:Requirement)-[:MAPPED_TO]->(p:Policy)-[:OWNED_BY]->(o:Owner) "
                    "WHERE r.text CONTAINS $req "
                    "RETURN p.title AS policy, o.name AS owner LIMIT 1",
                    req=requirement_text.split()[0] # Rough mock matching
                )
                nodes = [record.data() for record in result]
                return {"graph_entities": nodes, "status": "GraphRAG Active"}
        except Exception as e:
            print(f"GraphTraverse Warning: {e}")
            return {"graph_entities": [], "status": "Neo4j Offline - Bypassed"}

# Singleton instance
graph_rag = GraphRAGService()
