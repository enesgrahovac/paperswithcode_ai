#!/usr/bin/env python3
import aws_cdk as cdk
import os
from cdk_stack import PapersWithCodeStack

app = cdk.App()

# Get account and region from environment variables (set by GitHub Actions)
env = cdk.Environment(
    account=os.environ.get("AWS_ACCOUNT_ID"),
    region=os.environ.get("AWS_REGION"),
)

PapersWithCodeStack(app, "PapersWithCodeStack", env=env)
app.synth()