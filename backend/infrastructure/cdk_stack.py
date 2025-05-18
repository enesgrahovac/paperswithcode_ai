from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_apigatewayv2 as apigwv2,
    aws_apigatewayv2_integrations as apigwv2_integrations,
    aws_iam as iam,
    aws_secretsmanager as secretsmanager,
    aws_rds as rds,
    CfnOutput,
    Duration,
)
from constructs import Construct
import os

class PapersWithCodeStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        cluster_endpoint = os.environ["CLUSTER_ENDPOINT"]
        db_secret_name = os.environ["DB_SECRET_NAME"]

        # 1. Reference existing Aurora Serverless cluster
        cluster = rds.DatabaseCluster.from_database_cluster_attributes(
            self, "PapersDataCluster",
            cluster_identifier="papers-data",
            cluster_endpoint_address=cluster_endpoint,
            port=5432,
            security_groups=[],
            reader_endpoint_address=None
        )

        # 2. Reference existing secret (for DB credentials)
        db_secret = secretsmanager.Secret.from_secret_name_v2(
            self, "PapersDbSecret", db_secret_name
        )

        # 3. IAM Role for Lambda
        lambda_role = iam.Role(
            self, "LambdaExecRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )
        # Attach custom policy for RDS Data and SecretsManager
        lambda_role.add_to_policy(iam.PolicyStatement(
            actions=["rds-data:*"],
            resources=[cluster.cluster_arn, f"{cluster.cluster_arn}:*"]
        ))
        lambda_role.add_to_policy(iam.PolicyStatement(
            actions=["secretsmanager:GetSecretValue"],
            resources=[db_secret.secret_arn]
        ))

        # 4. Lambda functions
        lambda_configs = [
            {
                "name": "hello_world",
                "path": "../aws/lambdas/hello_world",
                "env": {}
            },
            {
                "name": "add_dummy",
                "path": "../aws/lambdas/add_dummy",
                "env": {
                    "CLUSTER_ARN": cluster.cluster_arn,
                    "SECRET_ARN": db_secret.secret_arn,
                    "DB_NAME": "postgres",
                    "DB_USER": "lambda_user"
                }
            },
            {
                "name": "get_dummy",
                "path": "../aws/lambdas/get_dummy",
                "env": {
                    "CLUSTER_ARN": cluster.cluster_arn,
                    "SECRET_ARN": db_secret.secret_arn,
                    "DB_NAME": "postgres",
                    "DB_USER": "lambda_user"
                }
            }
        ]

        lambdas = {}
        for cfg in lambda_configs:
            lambdas[cfg["name"]] = _lambda.Function(
                self, f"{cfg['name'].capitalize()}Lambda",
                runtime=_lambda.Runtime.PYTHON_3_10,
                handler="main.handler",
                code=_lambda.Code.from_asset(cfg["path"]),
                role=lambda_role,
                timeout=Duration.seconds(30),
                environment=cfg["env"]
            )

        # 5. API Gateway HTTP API
        http_api = apigwv2.HttpApi(self, "ServerlessHttpApi")

        # 6. Dynamic routes (from your variables.tf)
        api_routes = [
            {"lambda": "hello_world", "method": "GET", "path": "/hello"},
            {"lambda": "add_dummy",   "method": "POST", "path": "/dummy"},
            {"lambda": "get_dummy",   "method": "GET",  "path": "/dummy"},
        ]

        for route in api_routes:
            integration = apigwv2_integrations.HttpLambdaIntegration(
                f"{route['lambda'].capitalize()}Integration",
                handler=lambdas[route["lambda"]]
            )
            http_api.add_routes(
                path=route["path"],
                methods=[apigwv2.HttpMethod[route["method"]]],
                integration=integration
            )

        # 7. Output API URL
        CfnOutput(self, "ApiBaseUrl", value=http_api.api_endpoint)