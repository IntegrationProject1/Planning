from flask import Flask, request
from session_producers.db_producer import DBClient
from session_producers.session_producer import SessionProducer
import os

app = Flask(__name__)

MYSQL_CONFIG = {
    'host': os.environ['MYSQL_HOST'],
    'user': os.environ['MYSQL_USER'],
    'password': os.environ['MYSQL_PASSWORD'],
    'database': os.environ['MYSQL_DATABASE']
}

queue = SessionProducer()
db = DBClient(MYSQL_CONFIG, queue)

@app.route('/api/calendar-ping', methods=['POST'])
def calendar_ping():
    data = request.get_json()
    print(f"Received calendar ping: {data}", flush=True)
    return db.process(data)
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=30015)
