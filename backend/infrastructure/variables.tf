variable "api_routes" {
  description = "Each object = one <METHOD> <PATH> handled by a Lambda"
  type = list(object({
    lambda = string   # Must match a key in aws_lambda_function.all
    method = string   # GET, POST, ANY, …
    path   = string   # /hello, /users/{id}, …
  }))
  default = [
    { lambda = "hello_world", method = "GET", path = "/hello" },
    # Add more routes here ↓
    # { lambda = "other_fn",   method = "POST", path = "/submit" },
  ]
}