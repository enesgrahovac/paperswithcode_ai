#!/usr/bin/env python3
import aws_cdk as cdk
from cdk_stack import PapersWithCodeStack

app = cdk.App()
PapersWithCodeStack(app, "PapersWithCodeStack")
app.synth()