#-------------------------------------------------------------------------------
# To see in the console that terrafom deployment will pick up secret elements from the terraform.tfvars use output.
#-------------------------------------------------------------------------------

output "email" {
  value       = var.EMAIL
  description = "The email address receiving Lambda failure notifications"
  sensitive   = false
}

output "totesys_user" {
  value       = jsondecode(data.aws_secretsmanager_secret_version.totesys_db_secret_data.secret_string).TOTESYS_USER
  description = "Totesys DB user"
  sensitive   = false 
}

output "totesys_password" {
  value       = jsondecode(data.aws_secretsmanager_secret_version.totesys_db_secret_data.secret_string).TOTESYS_PASSWORD
  description = "Totesys DB password"
  sensitive   = true  # passwords better stay hidden
}

output "totesys_database" {
  value       = jsondecode(data.aws_secretsmanager_secret_version.totesys_db_secret_data.secret_string).TOTESYS_DATABASE
  description = "Totesys DB name"
  sensitive   = false
}

output "totesys_host" {
  value       = jsondecode(data.aws_secretsmanager_secret_version.totesys_db_secret_data.secret_string).TOTESYS_HOST
  description = "Totesys DB host"
  sensitive   = false
}

output "totesys_port" {
  value       = jsondecode(data.aws_secretsmanager_secret_version.totesys_db_secret_data.secret_string).TOTESYS_PORT
  description = "Totesys DB port"
  sensitive   = false
}

#-----------------------

output "warehouse_user" {
  value       = jsondecode(data.aws_secretsmanager_secret_version.warehouse_db_secret_data.secret_string).WAREHOUSE_USER
  description = "Warehouse DB user"
  sensitive   = false 
}

output "warehouse_password" {
  value       = jsondecode(data.aws_secretsmanager_secret_version.warehouse_db_secret_data.secret_string).WAREHOUSE_PASSWORD
  description = "Warehouse DB password"
  sensitive   = true  # passwords better stay hidden
}

output "warehouse_database" {
  value       = jsondecode(data.aws_secretsmanager_secret_version.warehouse_db_secret_data.secret_string).WAREHOUSE_DATABASE
  description = "Warehouse DB name"
  sensitive   = false
}

output "warehouse_host" {
  value       = jsondecode(data.aws_secretsmanager_secret_version.warehouse_db_secret_data.secret_string).WAREHOUSE_HOST
  description = "Warehouse DB host"
  sensitive   = false
}

output "warehouse_port" {
  value       = jsondecode(data.aws_secretsmanager_secret_version.warehouse_db_secret_data.secret_string).WAREHOUSE_PORT
  description = "Warehouse DB port"
  sensitive   = false
}