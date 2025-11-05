#!/usr/bin/env pwsh
<#
.SYNOPSIS
Deploy Clara updates to AWS ECS with company information fixes

.DESCRIPTION
This script builds and deploys the updated Clara agent with company information functionality
to the existing AWS ECS infrastructure.
#>

param(
    [string]$Region = "us-east-1",
    [string]$ECRRepo = "339713066436.dkr.ecr.us-east-1.amazonaws.com/clara-agent-worker",
    [string]$ClusterName = "clara-app-ClaraECSCluster-STKkt4VTjreQ",
    [string]$ServiceName = "clara-agent-svc-dev",
    [string]$ImageTag = "company-info-fix-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
)

Write-Host "🚀 Starting Clara Company Information Update Deployment" -ForegroundColor Green
Write-Host "=" * 60

# Step 1: Build the Docker image
Write-Host "📦 Building Docker image..." -ForegroundColor Yellow
Set-Location backend

try {
    # Build the image with agent configuration
    docker build -t clara-agent:$ImageTag --build-arg RUN_AGENT=true .
    if ($LASTEXITCODE -ne 0) {
        throw "Docker build failed"
    }
    Write-Host "✅ Docker image built successfully" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to build Docker image: $_" -ForegroundColor Red
    exit 1
}

# Step 2: Tag for ECR
Write-Host "🏷️  Tagging image for ECR..." -ForegroundColor Yellow
docker tag clara-agent:$ImageTag ${ECRRepo}:$ImageTag
docker tag clara-agent:$ImageTag ${ECRRepo}:latest

# Step 3: Login to ECR
Write-Host "🔐 Logging into ECR..." -ForegroundColor Yellow
try {
    aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin $ECRRepo.Split('/')[0]
    if ($LASTEXITCODE -ne 0) {
        throw "ECR login failed"
    }
    Write-Host "✅ ECR login successful" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to login to ECR: $_" -ForegroundColor Red
    exit 1
}

# Step 4: Push to ECR
Write-Host "📤 Pushing image to ECR..." -ForegroundColor Yellow
try {
    docker push ${ECRRepo}:$ImageTag
    docker push ${ECRRepo}:latest
    if ($LASTEXITCODE -ne 0) {
        throw "Docker push failed"
    }
    Write-Host "✅ Image pushed to ECR successfully" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to push image to ECR: $_" -ForegroundColor Red
    exit 1
}

# Step 5: Update ECS service
Write-Host "🔄 Updating ECS service..." -ForegroundColor Yellow
Set-Location ..

try {
    # Force new deployment with the latest image
    aws ecs update-service --cluster $ClusterName --service $ServiceName --force-new-deployment --region $Region
    if ($LASTEXITCODE -ne 0) {
        throw "ECS service update failed"
    }
    Write-Host "✅ ECS service update initiated" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to update ECS service: $_" -ForegroundColor Red
    exit 1
}

# Step 6: Wait for deployment to complete
Write-Host "⏳ Waiting for deployment to complete..." -ForegroundColor Yellow
try {
    aws ecs wait services-stable --cluster $ClusterName --services $ServiceName --region $Region
    if ($LASTEXITCODE -ne 0) {
        throw "Deployment wait failed"
    }
    Write-Host "✅ Deployment completed successfully!" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Deployment may still be in progress. Check AWS Console for status." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🎉 Clara Company Information Update Deployment Complete!" -ForegroundColor Green
Write-Host "=" * 60
Write-Host "📋 Summary:" -ForegroundColor Cyan
Write-Host "   • Image Tag: $ImageTag" -ForegroundColor White
Write-Host "   • ECR Repository: $ECRRepo" -ForegroundColor White
Write-Host "   • Cluster: $ClusterName" -ForegroundColor White
Write-Host "   • Service: $ServiceName" -ForegroundColor White
Write-Host ""
Write-Host "🔍 To verify deployment:" -ForegroundColor Cyan
Write-Host "   aws ecs describe-services --cluster $ClusterName --services $ServiceName --region $Region" -ForegroundColor White
Write-Host ""
Write-Host "✨ Clara now has enhanced company information capabilities!" -ForegroundColor Green
Write-Host "   • Fetches data from company_info.pdf in S3" -ForegroundColor White
Write-Host "   • Falls back to web search if PDF unavailable" -ForegroundColor White
Write-Host "   • Provides intelligent responses to company questions" -ForegroundColor White
