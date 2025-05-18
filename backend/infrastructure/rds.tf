# resource "aws_rds_cluster" "papers_data" {
#   cluster_identifier   = "papers-data"
#   engine               = "aurora-postgresql"
#   engine_mode          = "provisioned"     
#   engine_version       = "16.2"           
#   db_subnet_group_name = aws_db_subnet_group.papers.name
#   vpc_security_group_ids = [aws_security_group.db.id]
#   enable_http_endpoint = true               

#   # NEW – Serverless v2 capacity range
#   serverlessv2_scaling_configuration {
#     min_capacity             = 0         
#     max_capacity             = 4          
#     seconds_until_auto_pause = 300          
#   }
# }
