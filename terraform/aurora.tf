# Aurora Serverless v2 "express" setup: no VPC, no DB subnet group, IAM-token auth only.
resource "aws_rds_cluster" "main" {
  cluster_identifier = "aurorapostgresql"
  engine             = "aurora-postgresql"
  engine_version     = "17.9"
  engine_mode        = "provisioned"
  master_username    = "postgres"

  iam_database_authentication_enabled = true
  deletion_protection                 = false
  storage_encrypted                   = false
  backup_retention_period             = 1
  preferred_backup_window             = "06:31-07:01"
  preferred_maintenance_window        = "sat:08:44-sat:09:14"

  serverlessv2_scaling_configuration {
    min_capacity = 0
    max_capacity = 4
  }

  vpc_security_group_ids = []

  skip_final_snapshot = true
}

resource "aws_rds_cluster_instance" "main" {
  identifier         = "aurorapostgresql-instance-1"
  cluster_identifier = aws_rds_cluster.main.id
  instance_class     = "db.serverless"
  promotion_tier     = 1
  engine             = aws_rds_cluster.main.engine
  engine_version     = aws_rds_cluster.main.engine_version
}
