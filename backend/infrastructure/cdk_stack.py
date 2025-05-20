from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as _lambda,
    aws_lambda_python_alpha as lambda_py,
    aws_apigatewayv2 as apigwv2,
    aws_apigatewayv2_integrations as apigwv2_integrations,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_rds as rds,
    aws_secretsmanager as secretsmanager,
    CfnOutput,
)
from constructs import Construct
import os


class PapersWithCodeStack(Stack):
    """CDK stack that deploys three Lambda functions (hello_world, add_dummy, get_dummy)
    connected to an existing Aurora PostgreSQL Serverless v2 cluster **without** a NAT gateway.
    The Lambdas sit in private‑isolated subnets and reach the RDS & Secrets Manager APIs
    through VPC interface endpoints.
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # ──────────────────────────────────────────────────────────────
        # ░█▀▀░█▀█░█░░░█░█░█▀█░█▀▄░█▀█░█▀▀
        # ░█░░░█░█░█░░░█░█░█▀█░█▀▄░█▀█░▀▀█
        # ░▀▀▀░▀▀▀░▀▀▀░▀▀▀░▀░▀░▀░▀░▀░▀░▀▀▀
        # ----------------------------------------------------------------
        # Environment variables supplied from cdk.json / shell
        # ----------------------------------------------------------------
        vpc_id                      = os.environ["VPC_ID"]
        private_subnet_ids          = os.environ["PRIVATE_SUBNET_IDS"].split(",")
        aurora_security_group_id    = os.environ["AURORA_SECURITY_GROUP"]
        cluster_endpoint            = os.environ["CLUSTER_ENDPOINT"]                # e.g. papers-data.cluster-xyz.us-east-1.rds.amazonaws.com
        cluster_resource_identifier = os.environ["CLUSTER_RESOURCE_IDENTIFIER"]      # e.g. cluster-ABCD1234567890XYZ
        db_secret_name              = os.environ.get("DB_SECRET_NAME", "")
        db_user                     = os.environ.get("DB_USER", "lambda_user")


        # ──────────────────────────────────────────────────────────────
        # ░█░█░█▀▀░█▀█░█▀▀░█▀█
        # ░█▀█░█▀▀░█░█░█░░░█░█
        # ░▀░▀░▀▀▀░▀░▀░▀▀▀░▀░▀
        # ----------------------------------------------------------------
        # Import existing VPC + Aurora SG
        # ----------------------------------------------------------------
        vpc = ec2.Vpc.from_vpc_attributes(
            self,
            "ImportedVpc",
            vpc_id=vpc_id,
            availability_zones=["us-east-1a", "us-east-1b", "us-east-1c"],
            private_subnet_ids=private_subnet_ids,
        )

        aurora_sg = ec2.SecurityGroup.from_security_group_id(
            self, "AuroraSG", aurora_security_group_id
        )

        # Security group dedicated to Lambdas
        lambda_sg = ec2.SecurityGroup(
            self, "LambdaSG", vpc=vpc, description="SG for Aurora‑access Lambdas", allow_all_outbound=True
        )
        # Permit Lambda → Aurora:5432
        aurora_sg.add_ingress_rule(lambda_sg, ec2.Port.tcp(5432), "Lambda to Aurora")

        # ──────────────────────────────────────────────────────────────
        # ░█▀█░█▀▀░█▀▄░█▀▀░█▀█░█▀█░█░█
        # ░█▀█░█▀▀░█░█░█░░░█▀█░█▀█░█░█
        # ░▀░▀░▀▀▀░▀▀░░▀▀▀░▀░▀░▀░▀░▀▀▀
        # ----------------------------------------------------------------
        # Import existing Aurora Serverless v2 cluster (PostgreSQL)
        # ----------------------------------------------------------------
        cluster = rds.DatabaseCluster.from_database_cluster_attributes(
            self,
            "AuroraCluster",
            cluster_identifier="papers-data",  # cluster identifier (DB cluster id)
            cluster_endpoint_address=cluster_endpoint,
            cluster_resource_identifier=cluster_resource_identifier,
            port=5432,
            security_groups=[aurora_sg],
        )

        # Optional: reference the secret in case you want to retrieve it elsewhere
        if db_secret_name:
            secretsmanager.Secret.from_secret_name_v2(self, "PapersDbSecret", db_secret_name)

        # ──────────────────────────────────────────────────────────────
        # ░█░█░█▀█░█░█░█░░░█▀▀
        # ░█▀█░█▀█░█░█░█░░░▀▀█
        # ░▀░▀░▀░▀░▀▀▀░▀▀▀░▀▀▀
        # ----------------------------------------------------------------
        # VPC Interface Endpoints so the Lambdas reach AWS APIs privately
        # ----------------------------------------------------------------
        for svc in [
            ec2.InterfaceVpcEndpointAwsService.RDS,
            ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
            ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS,  # CW Logs write path
        ]:
            ec2.InterfaceVpcEndpoint(
                self,
                f"{svc.short_name.title()}Endpoint",
                vpc=vpc,
                service=svc,
                subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
                security_groups=[lambda_sg],  # endpoints share the Lambda SG
            )

        # ──────────────────────────────────────────────────────────────
        # ░█░█░█▀█░█░█░█▀▀░█░░░█▀▀
        # ░█▀█░█▀█░█░█░█▀▀░█░░░▀▀█
        # ░▀░▀░▀░▀░▀▀▀░▀▀▀░▀▀▀░▀▀▀
        # ----------------------------------------------------------------
        # IAM role for all Lambdas
        # ----------------------------------------------------------------
        lambda_role = iam.Role(
            self,
            "LambdaExecRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole"),
            ],
        )

        # IAM‑DB authentication permission (rds‑db:connect)
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["rds-db:connect"],
                resources=[
                    f"arn:aws:rds-db:{self.region}:{self.account}:dbuser:{cluster.cluster_resource_identifier}/{db_user}"
                ],
            )
        )

        # (Optional) Secrets Manager access if you need it in code
        if db_secret_name:
            lambda_role.add_to_policy(
                iam.PolicyStatement(
                    actions=["secretsmanager:GetSecretValue"],
                    resources=[f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:{db_secret_name}*"],
                )
            )

        # ──────────────────────────────────────────────────────────────
        # ░█░█░█▀▀░█░█░█░░░█░█░█▀█░█▀▄
        # ░█▀█░█▀▀░█░█░█░░░█░█░█▀█░█▀▄
        # ░▀░▀░▀▀▀░▀▀▀░▀▀▀░▀▀▀░▀░▀░▀░▀
        # ----------------------------------------------------------------
        # Lambda definitions
        # ----------------------------------------------------------------
        lambda_configs = [
            {
                "name": "hello_world",
                "path": "../aws/lambdas/hello_world",
                "env": {},
            },
            {
                "name": "add_dummy",
                "path": "../aws/lambdas/add_dummy",
                "env": {
                    "CLUSTER_ENDPOINT": cluster.cluster_endpoint.hostname,
                    "DB_NAME": "postgres",
                    "DB_USER": db_user,
                },
            },
            {
                "name": "get_dummy",
                "path": "../aws/lambdas/get_dummy",
                "env": {
                    "CLUSTER_ENDPOINT": cluster.cluster_endpoint.hostname,
                    "DB_NAME": "postgres",
                    "DB_USER": db_user,
                },
            },
        ]

        lambdas: dict[str, _lambda.Function] = {}
        for cfg in lambda_configs:
            lambdas[cfg["name"]] = lambda_py.PythonFunction(
                self,
                f"{cfg['name'].capitalize()}Lambda",
                entry=cfg["path"],
                runtime=_lambda.Runtime.PYTHON_3_10,
                index="main.py",
                handler="handler",
                role=lambda_role,
                timeout=Duration.seconds(30),
                environment=cfg["env"],
                vpc=vpc,
                vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
                security_groups=[lambda_sg],
            )

        # ──────────────────────────────────────────────────────────────
        # ░█▀▀░█░█░█▀▀░█▄█░█░█░█▀▀
        # ░█▀▀░█░█░█▀▀░█░█░█░█░█▀▀
        # ░▀░░░▀▀▀░▀▀▀░▀░▀░▀▀▀░▀▀▀
        # ----------------------------------------------------------------
        http_api = apigwv2.HttpApi(self, "ServerlessHttpApi")

        api_routes = [
            {"lambda": "hello_world", "method": "GET",  "path": "/hello"},
            {"lambda": "add_dummy",   "method": "POST", "path": "/dummy"},
            {"lambda": "get_dummy",   "method": "GET",  "path": "/dummy"},
        ]

        for route in api_routes:
            integration = apigwv2_integrations.HttpLambdaIntegration(
                f"{route['lambda'].capitalize()}Integration", handler=lambdas[route["lambda"]]
            )
            http_api.add_routes(
                path=route["path"],
                methods=[apigwv2.HttpMethod[route["method"]]],
                integration=integration,
            )

        CfnOutput(self, "ApiBaseUrl", value=http_api.api_endpoint)
