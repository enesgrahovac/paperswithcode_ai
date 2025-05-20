import json, os
import pg8000.dbapi
import ssl
import boto3
import logging
import traceback

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Global connection to be reused between invocations
connection = None

def get_connection():
    """Establish database connection using IAM authentication"""
    try:
        logger.info("Connecting to database")
        client = boto3.client("rds")
        db_endpoint = os.environ.get("CLUSTER_ENDPOINT")
        database_name = os.environ.get("DB_NAME")
        db_username = os.environ.get("DB_USER")
        ssl_context = ssl.create_default_context()
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        password = client.generate_db_auth_token(
            DBHostname=db_endpoint, Port=5432, DBUsername=db_username
        )
        conn = pg8000.dbapi.connect(
            host=db_endpoint,
            user=db_username,
            database=database_name,
            password=password,
            ssl_context=ssl_context
        )
        conn.autocommit = True
        return conn
    except Exception as e:
        logger.error(f"Connection error: {type(e).__name__}: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def handler(event, context):
    global connection
    qparams = event.get("queryStringParameters") or {}
    row_id  = qparams.get("id")

    if not row_id:
        return {"statusCode": 400, "body": json.dumps({"error": "Missing ?id="})}

    try:
        if connection is None:
            connection = get_connection()
        if connection is None:
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "Failed to connect to database"})
            }
        cursor = connection.cursor()
        sql = "SELECT id, created_at FROM dummy WHERE id = %s LIMIT 1"
        cursor.execute(sql, (row_id,))
        record = cursor.fetchone()
        cursor.close()
        if not record:
            return {"statusCode": 404, "body": json.dumps({"error": "Not found"})}
        return {
            "statusCode": 200,
            "body": json.dumps({
                "id":          str(record[0]),
                "created_at":  record[1]
            })
        }
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        try:
            if connection:
                connection.close()
        except:
            pass
        connection = None
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Database operation failed: {str(e)}"})
        } 