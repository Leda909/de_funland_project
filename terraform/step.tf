resource "aws_sfn_state_machine" "sfn_state_machine" {
  name     = var.step_function
  role_arn = aws_iam_role.step_function_role.arn

    definition = <<EOF
    {
  "StartAt": "Extract",
  "States": {
    "Extract": {
      "Type": "Task",
      "Resource": "${aws_lambda_function.extract_lambda_handler.arn}",
      "Next": "Transform",
      "TimeoutSeconds": 900,
      "ResultPath": "$.myresult"
    },
    "Transform": {
      "Type": "Task",
      "Resource": "${aws_lambda_function.transform_lambda_handler.arn}",
      "Next": "Load",
      "TimeoutSeconds": 900,
      "ResultPath": "$.myresult"
    },
    "Load": {
      "Type": "Task",
      "Resource": "${aws_lambda_function.load_lambda_handler.arn}",
      "ResultPath": "$.myresult",
      "TimeoutSeconds": 900,
      "End": true
    }
    }
  }
    EOF
}