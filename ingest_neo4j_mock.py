from backend.services.graph_service import graph_rag
import time

def ingest_mock_data():
    if not graph_rag.driver:
        print("Neo4j is not running! Please run 'docker-compose up -d' first.")
        return
        
    print("Connecting to Neo4j to ingest enterprise topology...")
    
    try:
        with graph_rag.driver.session() as session:
            # Clear existing
            session.run("MATCH (n) DETACH DELETE n")
            
            # Create policies and owners
            session.run("""
            CREATE (p1:Policy {title: 'ISO 27001 Information Security Policy'})-[:OWNED_BY]->(o1:Owner {name: 'Alice Johnson, CISO'})
            CREATE (p2:Policy {title: 'SOC 2 Type II Cloud Compliance'})-[:OWNED_BY]->(o2:Owner {name: 'Bob Smith, Cloud VP'})
            CREATE (p3:Policy {title: '99.9% Uptime SLA Matrix'})-[:OWNED_BY]->(o3:Owner {name: 'Site Reliability Team'})
            
            CREATE (r1:Requirement {text: 'Must maintain ISO 27001 compliance'})-[:MAPPED_TO]->(p1)
            CREATE (r2:Requirement {text: 'Cloud hosting requires SOC 2'})-[:MAPPED_TO]->(p2)
            CREATE (r3:Requirement {text: 'Uptime guarantee of 99.9% availability'})-[:MAPPED_TO]->(p3)
            """)
            
            print("Successfully ingested Graph topology into Neo4j!")
            print("GraphRAG is now fully active for the BidFactory pipeline.")
            
    except Exception as e:
        print(f"Failed to ingest data: {e}")

if __name__ == "__main__":
    ingest_mock_data()
