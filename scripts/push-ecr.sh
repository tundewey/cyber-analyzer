#!/usr/bin/env bash
# Build and push the Cybersecurity Analyzer image to Amazon ECR.
# Requires: Docker, AWS CLI v2, aws configure
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

AWS_REGION="${AWS_REGION:-us-east-1}"
ECR_REPOSITORY="${ECR_REPOSITORY:-cyber-analyzer}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

cd "$REPO_ROOT"

AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-}"
if [[ -z "$AWS_ACCOUNT_ID" ]]; then
  AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
fi

REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
REMOTE_IMAGE="${REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}"

echo "Logging in to ECR..."
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$REGISTRY"

echo "Building image..."
docker build -t cyber-analyzer .

echo "Tagging and pushing ${REMOTE_IMAGE}..."
docker tag cyber-analyzer:latest "$REMOTE_IMAGE"
docker push "$REMOTE_IMAGE"

echo "Done. Image: ${REMOTE_IMAGE}"
