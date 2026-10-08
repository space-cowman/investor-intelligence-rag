resource "aws_opensearch_domain" "main" {
  domain_name    = "investor-intel"
  engine_version = "OpenSearch_3.7"

  cluster_config {
    instance_type            = "t3.small.search"
    instance_count           = 1
    zone_awareness_enabled   = false
    dedicated_master_enabled = false
  }

  ebs_options {
    ebs_enabled = true
    volume_type = "gp3"
    volume_size = 10
    iops        = 3000
    throughput  = 125
  }

  encrypt_at_rest {
    enabled    = true
    kms_key_id = "arn:aws:kms:${var.region}:${data.aws_caller_identity.current.account_id}:key/f9ea4090-40ba-48f3-8908-b6f813f82fe7"
  }

  node_to_node_encryption {
    enabled = true
  }

  domain_endpoint_options {
    enforce_https       = true
    tls_security_policy = "Policy-Min-TLS-1-2-2019-07"
  }

  # override_main_response_version omitted: legacy option, rejected by this engine version on apply
  advanced_options = {
    "indices.fielddata.cache.size"           = "20"
    "indices.query.bool.max_clause_count"    = "1024"
    "rest.action.multi.allow_explicit_index" = "true"
  }

  off_peak_window_options {
    enabled = true
    off_peak_window {
      window_start_time {
        hours   = 0
        minutes = 0
      }
    }
  }

  access_policies = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:user/admin" }
      Action    = "es:ESHttp*"
      Resource  = "arn:aws:es:${var.region}:${data.aws_caller_identity.current.account_id}:domain/investor-intel/*"
    }]
  })
}
