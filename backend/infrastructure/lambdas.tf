locals {
  lambdas = fileset("${path.module}/artifacts", "*.zip")
}

resource "aws_lambda_function" "all" {
  for_each         = { for f in local.lambdas : replace(f, ".zip", "") => f }

  function_name    = each.key
  runtime          = "python3.10"
  handler          = "main.handler"

  filename         = "${path.module}/artifacts/${each.value}"
  source_code_hash = filebase64sha256("${path.module}/artifacts/${each.value}")

  role             = aws_iam_role.lambda_exec.arn

  # ⭐ Only set env-vars for the two DB functions
  dynamic "environment" {
    for_each = contains(["add_dummy", "get_dummy"], each.key) ? [1] : []
    content {
      variables = {
        CLUSTER_ARN = data.aws_rds_cluster.papers_data.arn
        DB_NAME     = "postgres"
        DB_USER     = "lambda_user"
      }
    }
  }
}