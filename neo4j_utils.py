from neo4j import GraphDatabase

uri = "bolt://localhost:7687"
username = "neo4j"
password = "your_neo4j_password"
database = "academicworld"


driver = GraphDatabase.driver(uri, auth=(username, password))

# count institue
def count_institute():
    with driver.session(database=database) as session:
        result = session.run("MATCH (i:INSTITUTE) RETURN count(i) AS institute_count")
        return result.single()['institute_count']


def get_university_counts(university_name):
    with driver.session(database=database) as session:
        total_faculty_result = session.run("MATCH (f:FACULTY) RETURN count(f) AS total_faculty_count")
        total_faculty_count = total_faculty_result.single()['total_faculty_count']

        university_faculty_result = session.run(f"""
            MATCH (f:FACULTY)-[:AFFILIATION_WITH]->(i:INSTITUTE {{name: '{university_name}'}})
            RETURN count(f) AS university_faculty_count
        """)
        university_faculty_count = university_faculty_result.single()['university_faculty_count']
        
        return total_faculty_count, university_faculty_count

# To generate total faculty count in the database, faculty count in a school, the ratio (school faculty count/all faculty count)   
def get_university_faculty_ratio(university_name):
    total_faculty_count, university_faculty_count = get_university_counts(university_name)
    ratio = university_faculty_count / total_faculty_count if total_faculty_count != 0 else 0
    return total_faculty_count, university_faculty_count, ratio

# find the relationship between faculties    
def get_collaborations_for_faculty(faculty_name):
    query = f"""
    MATCH (f1:FACULTY {{name: '{faculty_name}'}})-[pub1:PUBLISH]->(p:PUBLICATION)<-[pub2:PUBLISH]-(f2:FACULTY)
    WHERE f1.id <> f2.id
    RETURN f1.name AS faculty1, f2.name AS faculty2, COUNT(p) AS collaborations
    """
    with driver.session(database=database) as session:
        result = session.run(query)
        collaborations = [{"source": record["faculty1"], "target": record["faculty2"], "weight": record["collaborations"]} for record in result]
    return collaborations

# Generate nodes to populate graphs
def get_faculty_nodes_for_faculty(faculty_name):
    query = f"""
    MATCH (f:FACULTY)-[pub1:PUBLISH]->(p:PUBLICATION)<-[pub2:PUBLISH]-(co:FACULTY)
    WHERE f.name = '{faculty_name}' AND f.id <> co.id
    RETURN f.name AS faculty1, f.photoUrl AS photo1, co.name AS faculty2, co.photoUrl AS photo2
    """
    with driver.session(database=database) as session:
        result = session.run(query)
        faculty_nodes = set()
        for record in result:
            faculty1 = record["faculty1"]
            photo1 = record["photo1"]
            faculty2 = record["faculty2"]
            photo2 = record["photo2"]
            faculty_nodes.add((faculty1, photo1))
            faculty_nodes.add((faculty2, photo2))
        faculty_nodes = [{"id": node[0], "label": node[0], "image":node[1]} for node in faculty_nodes]
    return faculty_nodes

if __name__ == "__main__":
    try:
        # count_faculty()
        # count_institute()
        print("Connection to Neo4j was successful!")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        driver.close()

