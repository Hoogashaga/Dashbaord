import mysql.connector

password='mysql_password'

def get_connection():
    connection = mysql.connector.connect(
        host='localhost',
        user='root',
        password=password,
        database='academicworld'
    )
    return connection

# Serach faculty by input
def search_faculty_by_name(name):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    sql_query = """
        SELECT faculty.id AS id, faculty.name AS name, faculty.position as position, 
            faculty.research_interest AS research_interest, faculty.email AS email, 
            faculty.phone AS phone , faculty.photo_url AS photo_url, 
            university.name AS university
        FROM faculty, university
        WHERE faculty.university_id = university.id
            AND faculty.name LIKE %s
    """
    cursor.execute(sql_query, ('%' + name + '%',))
    results = cursor.fetchall()
    conn.close()
    return results

# View, Database Techniques R14
# Create a view of the publication table with set year range
def search_by_year(year_min, year_max):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Drop the view if it exists to avoid errors
    cursor.execute("DROP VIEW IF EXISTS year_publication")
    
    # Create the view
    create_view = f"""
        CREATE VIEW year_publication AS
        SELECT *
        FROM publication
        WHERE publication.year >= %s AND publication.year <= %s
    """
    cursor.execute(create_view, (year_min, year_max))
    
    # Commit changes and close connection
    conn.commit()
    cursor.close()
    conn.close()

# Search Publication by title
def search_publication_by_title(title):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    sql_query = """
        SELECT id, title, venue, year, num_citations
        FROM year_publication
        WHERE title LIKE %s
    """
    cursor.execute(sql_query, (f"%{title}%",))
    results = cursor.fetchall()
    conn.close()
    return results

# Search authors by publication id
def get_author_by_publication_id(pub_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    sql_query = """
        SELECT f.name AS author FROM faculty f, faculty_publication fp
        WHERE fp.faculty_id = f.id AND fp.publication_id = %s
    """
    cursor.execute(sql_query, (pub_id,))
    results = cursor.fetchall()
    conn.close()
    return results


# Save to favorite faculty
def save_to_favorites_faculty(item_id):
    conn = get_connection()
    cursor = conn.cursor()

    # Create favorites table if it does not exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS favorite_faculty (
            id INT PRIMARY KEY,
            name VARCHAR(512),
            position VARCHAR(512),
            research_interest VARCHAR(512),
            email VARCHAR(512),
            phone VARCHAR(512),
            photo_url VARCHAR(512),
            university_id INT
        );
    """)

    # Insert item into the favorites table
    sql_query = """
        INSERT INTO favorite_faculty (id, name, position, research_interest, email, phone, photo_url, university_id)
            SELECT *
            FROM faculty
            WHERE faculty.id = %s
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                position = VALUES(position),
                research_interest = VALUES(research_interest),
                email = VALUES(email),
                phone = VALUES(phone),
                photo_url = VALUES(photo_url),
                university_id = VALUES(university_id)"""
    
    cursor.execute(sql_query, (item_id,))
    
    conn.commit()
    conn.close()

# Save to favorite publication
def save_to_favorites_publication(item_id):
    conn = get_connection()
    cursor = conn.cursor()

    # Create favorites table if it does not exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS favorite_publication (
            id INT PRIMARY KEY,
            title VARCHAR(512),
            venue VARCHAR(512),
            year VARCHAR(512),
            num_citations INT
        );
    """)

    # Insert item into the favorites table
    sql_query = """
        INSERT INTO favorite_publication (id, title, venue, year, num_citations)
            SELECT *
            FROM publication
            WHERE publication.id = %s
            ON DUPLICATE KEY UPDATE
                title = VALUES(title),
                venue = VALUES(venue),
                year = VALUES(year),
                num_citations = VALUES(num_citations)
        """
    
    cursor.execute(sql_query, (item_id,))
    
    conn.commit()
    conn.close()

# Get list of favorite faculty
def get_favorite_faculty():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Create favorites table if it does not exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS favorite_faculty (
            id INT PRIMARY KEY,
            name VARCHAR(512),
            position VARCHAR(512),
            research_interest VARCHAR(512),
            email VARCHAR(512),
            phone VARCHAR(512),
            photo_url VARCHAR(512),
            university_id INT
        );
    """)

    sql_query = """
        SELECT favorite_faculty.id AS id, favorite_faculty.name AS name, favorite_faculty.position as position, 
            favorite_faculty.research_interest AS research_interest, favorite_faculty.email AS email, 
            favorite_faculty.phone AS phone, favorite_faculty.photo_url AS photo_url, 
            university.name AS university
        FROM favorite_faculty, university
        WHERE favorite_faculty.university_id = university.id
    """

    cursor.execute(sql_query)
    results = cursor.fetchall()
    conn.close()
    return results

# Get list of favorite publication
def get_favorite_publications():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Create favorites table if it does not exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS favorite_publication (
            id INT PRIMARY KEY,
            title VARCHAR(512),
            venue VARCHAR(512),
            year VARCHAR(512),
            num_citations INT
        );
    """)

    sql_query = """
        SELECT id, title, venue, year, num_citations
        FROM favorite_publication
    """

    cursor.execute(sql_query)
    results = cursor.fetchall()
    conn.close()
    return results

# remove from favorite faculty
def remove_from_favorites_faculty(faculty_id):
    conn = get_connection()
    cursor = conn.cursor()

    sql_query = """
        DELETE FROM favorite_faculty
        WHERE id = %s
    """

    cursor.execute(sql_query, (faculty_id,))
    conn.commit()
    conn.close()

# remove from favorite publication
def remove_from_favorites_publication(publication_id):
    conn = get_connection()
    cursor = conn.cursor()

    sql_query = """
        DELETE FROM favorite_publication
        WHERE id = %s
    """

    cursor.execute(sql_query, (publication_id,))
    conn.commit()
    conn.close()


def get_top_cited_publications(faculty_id, limit=5):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    # Publication 2147483647's data is removed for quality control. It has 5000 authors
    sql_query = """
        SELECT f.name as name, p.title as title, p.num_citations as num_citations
        FROM publication p, faculty_publication fp, faculty f
        WHERE f.id = fp.faculty_id AND fp.publication_id = p.id
        AND f.id = %s AND p.id <> 2147483647
        ORDER BY num_citations DESC
        LIMIT %s
    """
    cursor.execute(sql_query, (faculty_id, limit))
    results = cursor.fetchall()
    conn.close()
    return results

# Get all the keywords and their frequencies (sum of their publication scores) of all of a faculty's publications
def get_research_interest_frequencies(faculty_id):
    conn = get_connection()
    cursor = conn.cursor()
    sql_query = """SELECT k.name as keyword, SUM(pk.score) as count
                FROM faculty f, faculty_publication fp, publication p, publication_keyword pk, keyword k
                WHERE f.id = fp.faculty_id AND fp.publication_id = p.id AND p.id = pk.publication_id
                    AND pk.keyword_id = k.id AND f.id = %s
                GROUP BY k.name
                ORDER BY count;
    """

    cursor.execute(sql_query, (faculty_id,))
    results = cursor.fetchall()
    conn.close()
    return results

# Get Faculty name from ID to use for Neo4j Search
def get_faculty_name_from_id(id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name from faculty WHERE id = %s", (id,))
    result = cursor.fetchone()
    conn.close()
    return result








    