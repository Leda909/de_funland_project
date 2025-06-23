# Install lambda layer from lambda_packeges.txt
resource "null_resource" "install_layer_dependencies" {
  provisioner "local-exec" {
    command = "pip install -r ../lambda_packages.txt -t ../dependencies/packages/"
  }
  triggers = {
    # trigger = timestamp()
    requirements_hash = filesha256("../lambda_packages.txt") # only when change happends on it.
  }
}

# ziping the packages to lambda layer
data "archive_file" "lambda_layer" {
  type             = "zip"
  source_dir       = "${path.module}/../dependencies/packages"
  output_path      = "${path.module}/../deployment/layers/lambda_handlers_layer.zip"
  depends_on = [ null_resource.install_layer_dependencies ]
}

# uploading zipped layer to layer S3
resource "aws_s3_object" "lambda_layer_zip_file" {
  bucket = aws_s3_bucket.layer_bucket.bucket
  key    = "layers/lambda_layer.zip"
  source = data.archive_file.lambda_layer.output_path
}

# creating the lambda layer
resource "aws_lambda_layer_version" "lambda_layer" {
  layer_name          = "etl_layer"
  compatible_runtimes = [var.python_runtime]
  s3_bucket = aws_s3_object.lambda_layer_zip_file.bucket
  s3_key = aws_s3_object.lambda_layer_zip_file.key
}

# ------------ Extract Lambda ----------------

# zipping extract handler
data "archive_file" "extract_lambda" {
  type        = "zip"
  source_file = "${path.module}/../src/lambda_handler/extract.py"
  output_path = "${path.module}/../deployment/handlers/extract/lambda_handlers.zip"
}

# we are creating the extract lambda
resource "aws_lambda_function" "extract_lambda_handler" {
  filename      = "${path.module}/../deployment/handlers/extract/lambda_handlers.zip"
  function_name = var.lambda_extract
  role          = aws_iam_role.lambda_role.arn
  handler       = "extract.lambda_handler"  
  runtime       = var.python_runtime
  timeout       = 900
  memory_size   = 3000

  source_code_hash = data.archive_file.lambda.output_base64sha256
  layers = [aws_lambda_layer_version.lambda_layer.arn, "arn:aws:lambda:eu-west-2:336392948345:layer:AWSSDKPandas-Python312:17"]
  environment {
    variables = {
      S3_INGESTION_BUCKET = aws_s3_bucket.ingestion_bucket.bucket
    }
  }
}

# ------------ Transform Lambda ----------------

# zipping transform handler
data "archive_file" "transform_lambda" {
  type        = "zip"
  source_file = "${path.module}/../src/lambda_handler/transform.py"
  output_path = "${path.module}/../deployment/handlers/transform/lambda_handlers.zip"
}

resource "aws_lambda_function" "transform_lambda_handler" {
  filename      = "${path.module}/../deployment/handlers/transform/lambda_handlers.zip"
  function_name = var.lambda_transform
  role          = aws_iam_role.lambda_role.arn
  handler       = "transform.lambda_handler"  
  runtime       = var.python_runtime
  timeout       = 900
  memory_size   = 3000

  source_code_hash = data.archive_file.lambda.output_base64sha256
  layers = [aws_lambda_layer_version.lambda_layer.arn, "arn:aws:lambda:eu-west-2:336392948345:layer:AWSSDKPandas-Python312:17"]
  environment {
    variables = {
      S3_INGESTION_BUCKET = aws_s3_bucket.ingestion_bucket.bucket
      S3_PROCESSED_BUCKET = aws_s3_bucket.processed_bucket.bucket
    }
  }
}

# ------------ Load Lambda ----------------

# zipping load handler
data "archive_file" "load_lambda" {
  type        = "zip"
  source_file = "${path.module}/../src/lambda_handler/load.py"
  output_path = "${path.module}/../deployment/handlers/load/lambda_handlers.zip"
}

resource "aws_lambda_function" "load_lambda_handler" {
  filename      = "${path.module}/../deployment/handlers/load/lambda_handlers.zip"
  function_name = var.lambda_load
  role          = aws_iam_role.lambda_role.arn
  handler       = "load.lambda_handler"  
  runtime       = var.python_runtime
  timeout       = 900
  memory_size   = 3000
  
  source_code_hash = data.archive_file.lambda.output_base64sha256
  layers = [aws_lambda_layer_version.lambda_layer.arn, "arn:aws:lambda:eu-west-2:336392948345:layer:AWSSDKPandas-Python312:17"]

  environment {
    variables = {
      S3_PROCESSED_BUCKET = aws_s3_bucket.processed_bucket.bucket
    }
  }
}