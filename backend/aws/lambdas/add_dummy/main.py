import json, os, uuid
import boto3
import pg8000.dbapi
import ssl
import logging
from datetime import datetime
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
        # Get RDS client
        client = boto3.client("rds")
        
        # Required environment variables
        db_endpoint = os.environ.get("CLUSTER_ENDPOINT")
        database_name = os.environ.get("DB_NAME")
        db_username = os.environ.get("DB_USER")
        
        # SSL context with system certificates
        ssl_context = ssl.create_default_context()
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        
        # Generate IAM auth token
        password = client.generate_db_auth_token(
            DBHostname=db_endpoint, Port=5432, DBUsername=db_username
        )
        
        # Connect to the database
        conn = pg8000.dbapi.connect(
            host=db_endpoint,
            user=db_username,
            database=database_name,
            password=password,
            ssl_context=ssl_context
        )
        
        # Set autocommit mode
        conn.autocommit = True
        return conn
    except Exception as e:
        logger.error(f"Connection error: {type(e).__name__}: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def handler(event, context):
    """Lambda handler to insert a dummy record"""
    global connection
    
    # Generate UUID and timestamp
    row_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    logger.info(f"row_id: {row_id}, timestamp: {now}")
    
    try:
        # Get or create DB connection
        if connection is None:
            connection = get_connection()
        
        if connection is None:
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "Failed to connect to database"})
            }
        
        # Create a cursor and execute the insert
        cursor = connection.cursor()
        sql = "INSERT INTO dummy (id, created_at) VALUES (%s, %s)"
        cursor.execute(sql, (row_id, now))
        cursor.close()
        
        logger.info(f"Successfully inserted record with id {row_id}")
        
        return {
            "statusCode": 200,
            "body": json.dumps({"inserted_id": row_id})
        }
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        # Reset connection on error
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