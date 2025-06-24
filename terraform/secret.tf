#---------------- totesys credentials ------------------------

resource "aws_secretsmanager_secret" "totesys_db_creds" {
  name = "totesys_db_creds"
}

resource "aws_secretsmanager_secret_version" "totesys_db_creds_version" {
  secret_id     = aws_secretsmanager_secret.totesys_db_creds.id
  secret_string = jsonencode({
    TOTESYS_USER     = var.TOTESYS_USER
    TOTESYS_PASSWORD = var.TOTESYS_PASSWORD
    TOTESYS_DATABASE     = var.TOTESYS_DATABASE
    TOTESYS_HOST     = var.TOTESYS_HOST
    TOTESYS_PORT     = var.TOTESYS_PORT
  })
}

data "aws_secretsmanager_secret_version" "totesysy_db_secret_data" {
  secret_id       = aws_secretsmanager_secret.totesys_db_creds.id
  version_id      = aws_secretsmanager_secret_version.totesys_db_creds_version.version_id
  version_stage = "AWSCURRENT"
}

#---------------- warehouse credentials ------------------------

resource "aws_secretsmanager_secret" "warehouse_secrets" {
  name = "warehouse_secrets"
}

resource "aws_secretsmanager_secret_version" "warehouse_secrets_version" {
  secret_id     = aws_secretsmanager_secret.warehouse_secrets.id
  secret_string = jsonencode({
    WAREHOUSE_USER     = var.DATA_WAREHOUSE_USER
    WAREHOUSE_PASSWORD = var.DATA_WAREHOUSE_PASSWORD
    WAREHOUSE_DATABASE = var.DATA_WAREHOUSE_DATABASE
    WAREHOUSE_HOST     = var.DATA_WAREHOUSE_HOST
    WAREHOUSE_PORT     = var.DATA_WAREHOUSE_PORT
  })
}

data "aws_secretsmanager_secret_version" "warehouse_db_secret_data" {
  secret_id       = aws_secretsmanager_secret.warehouse_secrets.id
  version_id      = aws_secretsmanager_secret_version.warehouse_secrets_version.version_id
  version_stage = "AWSCURRENT"
}

#----------------------------- email -----------------------------

resource "aws_secretsmanager_secret" "email" {
  name = "notificable-email-address"
}

resource "aws_secretsmanager_secret_version" "email_version" {
  secret_id = aws_secretsmanager_secret.email.id
  secret_string = jsonencode({
    email = var.EMAIL
  })
}

