from pymongo import MongoClient

def subir_a_mongodb(data: dict, db_name: str, collection_name: str, uri: str = None):
    # URI corregida con la nueva contraseña (esperanza85) sin caracteres especiales
    uri = uri or "mongodb://serpy:esperanza85@serpy_mongodb:27017/?authSource=admin"
    client = MongoClient(uri)
    db = client[db_name]
    collection = db[collection_name]
    result = collection.insert_one(data)
    return result.inserted_id
