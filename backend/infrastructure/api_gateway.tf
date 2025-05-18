# 1️⃣  Create one HTTP API
resource "aws_apigatewayv2_api" "http_api" {
  name          = "serverless-http-api"
  protocol_type = "HTTP"
}

# 2️⃣  Auto-deploy changes
resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http_api.id
  name        = "$default"
  auto_deploy = true
}

# 3️⃣  Lambda ↔ API Gateway integrations (one per route)
resource "aws_apigatewayv2_integration" "lambda" {
  for_each = {
    for r in var.api_routes :
    "${r.method} ${r.path}" => r
  }

  api_id                 = aws_apigatewayv2_api.http_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.all[each.value.lambda].invoke_arn
  payload_format_version = "2.0"
}

# 4️⃣  Expose the route & method
resource "aws_apigatewayv2_route" "lambda" {
  for_each  = aws_apigatewayv2_integration.lambda

  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = each.key        
  target    = "integrations/${each.value.id}"
}

# 5️⃣  Allow API Gateway to call the function
resource "aws_lambda_permission" "apigw" {
  for_each = {
    for r in var.api_routes :
    "${r.method} ${r.path}" => r
  }

  statement_id  = "AllowAPIGWInvoke-${each.value.lambda}-${each.value.method}-${replace(each.value.path, "/", "-")}"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.all[each.value.lambda].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
}

# 6️⃣  Optional: output the base URL
output "api_base_url" {
  value = aws_apigatewayv2_api.http_api.api_endpoint
}