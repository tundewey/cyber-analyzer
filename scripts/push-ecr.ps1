<#
.SYNOPSIS
  Build the Cybersecurity Analyzer Docker image and push it to Amazon ECR.

.DESCRIPTION
  Requires: Docker Desktop, AWS CLI v2, and IAM credentials (aws configure).
  Run from anywhere; script resolves the cyber repo root automatically.

.PARAMETER AwsRegion
  AWS region where the ECR repository lives (default: us-east-1).

.PARAMETER EcrRepository
  ECR repository name (default: cyber-analyzer).

.PARAMETER ImageTag
  Image tag to push (default: latest).

.PARAMETER AwsAccountId
  12-digit AWS account ID. If omitted, uses 'aws sts get-caller-identity'.
#>
param(
    [string]$AwsRegion = "us-east-1",
    [string]$EcrRepository = "cyber-analyzer",
    [string]$ImageTag = "latest",
    [string]$AwsAccountId = ""
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

if (-not $AwsAccountId) {
    $AwsAccountId = (aws sts get-caller-identity --query Account --output text).Trim()
    if (-not $AwsAccountId) { throw "Could not determine AWS account ID. Run: aws configure" }
}

$Registry = "${AwsAccountId}.dkr.ecr.${AwsRegion}.amazonaws.com"
$ImageLocal = "cyber-analyzer"
$RemoteImage = "${Registry}/${EcrRepository}:${ImageTag}"

Write-Host "Logging in to ECR..."
aws ecr get-login-password --region $AwsRegion | docker login --username AWS --password-stdin $Registry
if ($LASTEXITCODE -ne 0) { throw "ECR docker login failed (exit $LASTEXITCODE)" }

Write-Host "Building image in $RepoRoot ..."
docker build -t $ImageLocal .
if ($LASTEXITCODE -ne 0) { throw "docker build failed (exit $LASTEXITCODE). Fix the build before tagging/pushing." }

Write-Host "Tagging $ImageLocal -> $RemoteImage"
docker tag "${ImageLocal}:latest" $RemoteImage

Write-Host "Pushing $RemoteImage"
docker push $RemoteImage
if ($LASTEXITCODE -ne 0) { throw "docker push failed (exit $LASTEXITCODE). See aws/README.md if ECR times out (firewall/VPN)." }

Write-Host "Done. Use this image URI in AWS App Runner or ECS:"
Write-Host "  $RemoteImage" -ForegroundColor Green
