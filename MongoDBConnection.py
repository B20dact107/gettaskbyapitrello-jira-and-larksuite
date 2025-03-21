# mongodb_connection.py
from pymongo import MongoClient

class MongoDBConnection:
    def __init__(self, uri = "mongodb://mongo:27017/", db_name = "task_database"): #localhost  mongo
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
    
    def get_collection(self, collection_name):
        return self.db[collection_name]
