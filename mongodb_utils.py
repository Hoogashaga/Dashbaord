from pymongo import MongoClient

def get_database():
    client = MongoClient("mongodb://localhost:27017/")
    db = client['academicworld']
    return db

#Indexing, Database Techniques R13
def create_indexes():
    db = get_database()
    db.faculty.create_index([("affiliation.name", 1)])
    db.faculty.create_index([("publications", 1)])
    db.publications.create_index([("id", 1)])
    db.publications.create_index([("keywords.name", 1)])

# will connect to searching bar
def search_collection(collection_name, query):
    db = get_database()
    collection = db[collection_name]
    return list(collection.find(query))

# shoe faculty info
def get_faculty(limit=5):
    db = get_database()
    collection = db['faculty']
    return list(collection.find().limit(limit))

# Get faculty count
def get_faculty_cnt():
    db = get_database()
    collection = db['faculty']
    return collection.count_documents({})

# Get affilication count
def get_affiliation_count():
    db = get_database()
    collection = db['faculty']
    pipeline = [
        { "$group": { "_id": "$affiliation.id" } },
        { "$count": "count" }
    ]
    result = list(collection.aggregate(pipeline))
    if result:
        return result[0]['count']
    else:
        return 0
    
# Get all affilications  
def get_all_affiliations():
    db = get_database()
    collection = db['faculty']
    pipeline = [
        { "$group": { "_id": "$affiliation.id", "name": { "$first": "$affiliation.name" } } },
        { "$project": { "_id": 0, "name": 1 } }
    ]
    result = list(collection.aggregate(pipeline))
    return result

# Calculate KRC of a professor
def calculate_krc(affiliation_name, keyword):
    db = get_database()
    pipeline = [
        { "$match": { "affiliation.name": affiliation_name } },
        { "$lookup": { 
            "from": "publications",
            "localField": "publications",
            "foreignField": "id",
            "as": "pub_data" } },
        { "$unwind": "$pub_data" },
        { "$unwind": "$pub_data.keywords" },
        { "$match": { "pub_data.keywords.name": keyword } },
        { "$group": { "_id": "$name", "KRC": { "$sum": { "$multiply": ["$pub_data.keywords.score", "$pub_data.numCitations"] } } } },
        { "$sort": { "KRC": -1 } },
        { "$limit": 10 },
        { "$project": { "_id": 1, "KRC": 1} }
    ]
    result = list(db.faculty.aggregate(pipeline))
    return result

# Get top keywords in a school
def top_keywords_by_school(school_name):
    db = get_database()
    pipeline = [
        { "$match": { "affiliation.name": school_name } },
        { "$lookup": { 
            "from": "publications",
            "localField": "publications",
            "foreignField": "id",
            "as": "pub_data" } },
        { "$unwind": "$pub_data" },
        { "$unwind": "$pub_data.keywords" },  
        { "$group": { 
            "_id": "$pub_data.keywords.name",
            "count": { "$sum": 1 }
        }},
        { "$sort": { "count": -1 } },
        { "$limit": 20 }
    ]
    result = list(db.faculty.aggregate(pipeline))
    return result