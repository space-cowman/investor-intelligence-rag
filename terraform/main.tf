terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "investor-intelligence-tfstate-022444447221"
    key            = "investor-intelligence/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "investor-intelligence-tfstate-lock"
    encrypt        = true
  }
}

provider "aws" {
  region = var.region
}
