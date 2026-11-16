terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # In production/team setups, use remote S3 backend with DynamoDB state locking
  # backend "s3" {
  #   bucket         = "uninova-terraform-state"
  #   key            = "uninova/terraform.tfstate"
  #   region         = "ap-southeast-1"
  #   dynamodb_table = "uninova-terraform-locks"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "UniNova"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}
