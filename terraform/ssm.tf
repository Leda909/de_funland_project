# -------------------------------------------------------
# For the aim to only fetch new or updated data from the "totesys" database, rather than re-extracting the entire database every time, 
# we implemented a parameter, called: "last_checked" as a checkpoint for managing the incremental data extraction process. 
# It is stored in AWS Systems Manager (SSM). It stores the timestamp of the last successful data extraction run, 
# which is a date in the format "YYYY-MM-DD HH:MM:SS:ffffff". 
# This date should be some date before 2019, to ensure that all the data gets extracted from the database initially.
# This tf file helps to automaticaly create a resource "last_checked" parameter in AWS Systems Manager (SSM).
# -------------------------------------------------------

resource "aws_ssm_parameter" "last_checked_parameter" {
  name        = "last_checked"
  type        = "String"
  value       = "2018-01-01 00:00:00.000000"
}
