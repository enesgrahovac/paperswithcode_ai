locals {
  lambda_src = "${path.module}/../lambda/hello"
}

resource "aws_iam_role" "lambda_role" {
  name               = "hello-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.assume.json
}

data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_lambda_function" "hello" {
  function_name = "hello-tf"
  filename      = data.archive_file.hello_zip.output_path
  source_code_hash = data.archive_file.hello_zip.output_base64sha256
  handler       = "handler.lambda_handler"
  runtime       = "python3.10"
  role          = aws_iam_role.lambda_role.arn
  timeout       = 10
  memory_size   = 128
}

data "archive_file" "hello_zip" {
  type        = "zip"
  source_dir  = local.lambda_src
  output_path = "${path.module}/build/hello.zip"
}