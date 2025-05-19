import json, os, uuid
from datetime import datetime

import boto3

rds = boto3.client("rds-data")

CLUSTER_ARN = os.environ["CLUSTER_ARN"]
SECRET_ARN  = os.environ["SECRET_ARN"]
DB_NAME     = os.environ["DB_NAME"]

def handler(event, context):
    row_id = str(uuid.uuid4())
    print(f"row_id: {row_id}")
    now    = datetime.utcnow().isoformat()
    print(f"Now: {now}")

    sql = "INSERT INTO dummy (id, created_at) VALUES(:id, :ts)"
    params = [
        {"name": "id", "value": {"stringValue": row_id}},
        {"name": "ts", "value": {"stringValue": now}}
    ]

    rds.execute_statement(
        resourceArn = CLUSTER_ARN,
        secretArn   = SECRET_ARN,
        database    = DB_NAME,
        sql         = sql,
        parameters  = params
    )

    return {
        "statusCode": 200,
        "body": json.dumps({"inserted_id": row_id})
    } 