from neo4j import GraphDatabase
driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "testing123"))
with driver.session(database="neo4j") as session:
    print(session.run("RETURN 1").single())