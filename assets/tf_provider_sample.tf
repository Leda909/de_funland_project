resource "null_resource" "create_last_checked" {
  provisioner "local-exec" {
    command = <<EOT
      if aws ssm get-parameter --name "last_checked" >/dev/null 2>&1; then
        echo "Parameter 'last_checked' already exists. Skipping."
      else
        aws ssm put-parameter --name "last_checked" --type "String" --value "2018-01-01 00:00:00.000000"
        echo "Parameter 'last_checked' has been created."
      fi
    EOT
  }
}