import json, os
import boto3

rds = boto3.client("rds-data")

CLUSTER_ARN = os.environ["CLUSTER_ARN"]
SECRET_ARN  = os.environ["SECRET_ARN"]
DB_NAME     = os.environ["DB_NAME"]

def handler(event, context):
    qparams = event.get("queryStringParameters") or {}
    row_id  = qparams.get("id")

    if not row_id:
        return {"statusCode": 400, "body": json.dumps({"error": "Missing ?id="})}

    sql = "SELECT id, created_at FROM dummy WHERE id = :id LIMIT 1"
    params = [{"name": "id", "value": {"stringValue": row_id}}]

    res = rds.execute_statement(
        resourceArn = CLUSTER_ARN,
        secretArn   = SECRET_ARN,
        database    = DB_NAME,
        sql         = sql,
        parameters  = params
    )

    if not res["records"]:
        return {"statusCode": 404, "body": json.dumps({"error": "Not found"})}

    record = res["records"][0]
    return {
        "statusCode": 200,
        "body": json.dumps({
            "id":          record[0]["stringValue"],
            "created_at":  record[1]["stringValue"]
        })
    } 