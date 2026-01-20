# ===================================================
# バックエンドのみ完全自動セットアップ（DuckDNS + HTTPS）
# ===================================================

Write-Host "=== Backend Setup with DuckDNS + HTTPS ===" -ForegroundColor Cyan
Write-Host ""

# 変数設定
$DUCKDNS_DOMAIN = "g4slution"
$DUCKDNS_FULL_DOMAIN = "g4slution.duckdns.org"
$DUCKDNS_TOKEN = "e64ffaf7-3d65-4122-b018-2da54c41932d"
$AWS_REGION = "us-east-1"
$CLUSTER_NAME = "wordy-tiger-lratby"
$SERVICE_NAME = "fastapi2-service-81ffemcl"
$AWS_ACCOUNT = "095622453902"
$ECR_REPOSITORY = "fastapi-web"

# Step 1: ECSタスクのパブリックIPを取得
Write-Host "Step 1: Getting ECS Task Public IP..." -ForegroundColor Green
$TASK_ARN = (aws ecs list-tasks --cluster $CLUSTER_NAME --service-name $SERVICE_NAME --query "taskArns[0]" --output text --region $AWS_REGION)
$TASK_ENI = (aws ecs describe-tasks --cluster $CLUSTER_NAME --tasks $TASK_ARN --query "tasks[0].attachments[0].details[?name=='networkInterfaceId'].value" --output text --region $AWS_REGION)
$PUBLIC_IP = (aws ec2 describe-network-interfaces --network-interface-ids $TASK_ENI --query "NetworkInterfaces[0].Association.PublicIp" --output text --region $AWS_REGION)
Write-Host "✓ Public IP: $PUBLIC_IP" -ForegroundColor Green

# Step 2: DuckDNSを更新
Write-Host "`nStep 2: Updating DuckDNS..." -ForegroundColor Green
Invoke-WebRequest -Uri "https://www.duckdns.org/update?domains=$DUCKDNS_DOMAIN&token=$DUCKDNS_TOKEN&ip=$PUBLIC_IP" -UseBasicParsing | Out-Null
Write-Host "✓ DuckDNS updated to: $PUBLIC_IP" -ForegroundColor Green

# Step 3: Cloudflare Tunnelをダウンロード
Write-Host "`nStep 3: Setting up Cloudflare Tunnel..." -ForegroundColor Green
if (-not (Test-Path "cloudflared.exe")) {
    Invoke-WebRequest -Uri "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe" -OutFile "cloudflared.exe" -UseBasicParsing
}
Write-Host "✓ Cloudflared ready" -ForegroundColor Green

# Step 4: main.pyを更新（HTTP用に設定）
Write-Host "`nStep 4: Updating main.py for HTTP..." -ForegroundColor Green
$mainPath = "main.py"
$mainContent = Get-Content $mainPath -Raw

# DuckDNSドメインをCORSに追加（HTTP）
$newCorsOrigins = @"
    allow_origins=[
        "http://localhost:3000",                    # フロントエンド（開発環境）
        "http://$PUBLIC_IP:8000",                  # バックエンド（HTTP）
        "http://$DUCKDNS_FULL_DOMAIN",            # DuckDNS（HTTP）
    ],
"@

# CORS設定を更新
$mainContent = $mainContent -replace 'allow_origins=\[[^\]]+\]', $newCorsOrigins.Trim()
Set-Content $mainPath -Value $mainContent
Write-Host "✓ main.py updated" -ForegroundColor Green

# Step 5: user.pyを更新（SameSite=lax, Secure=False）
Write-Host "`nStep 5: Updating user.py for HTTP..." -ForegroundColor Green
$userPath = "app\name\hieda\user.py"
$userContent = Get-Content $userPath -Raw

# Cookie設定を更新（HTTP環境用）
$userContent = $userContent -replace 'samesite="none"', 'samesite="lax"'
$userContent = $userContent -replace 'secure=True', 'secure=False'
Set-Content $userPath -Value $userContent
Write-Host "✓ user.py updated for HTTP" -ForegroundColor Green

# Step 6: Dockerイメージをビルド&プッシュ
Write-Host "`nStep 6: Building and pushing Docker image..." -ForegroundColor Green

# ECRにログイン
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin "${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com" 2>$null

# ビルド
docker build -t $ECR_REPOSITORY . | Out-Null
docker tag "${ECR_REPOSITORY}:latest" "${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:latest"
docker push "${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:latest" | Out-Null
Write-Host "✓ Image pushed to ECR" -ForegroundColor Green

# Step 7: ECSサービスを更新
Write-Host "`nStep 7: Updating ECS service..." -ForegroundColor Green
aws ecs update-service --cluster $CLUSTER_NAME --service $SERVICE_NAME --force-new-deployment --region $AWS_REGION | Out-Null
Write-Host "✓ ECS service updated" -ForegroundColor Green

# 待機
Write-Host "`nWaiting for new task to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 45

Write-Host "`n=== SETUP COMPLETE ===" -ForegroundColor Green -BackgroundColor Black
Write-Host ""
Write-Host "Your API is now available at:" -ForegroundColor Cyan
Write-Host "  http://$DUCKDNS_FULL_DOMAIN" -ForegroundColor White -BackgroundColor DarkBlue
Write-Host ""
Write-Host "Test endpoints:" -ForegroundColor Yellow
Write-Host "  curl http://$DUCKDNS_FULL_DOMAIN/health" -ForegroundColor White
Write-Host "  curl http://$DUCKDNS_FULL_DOMAIN/docs" -ForegroundColor White
Write-Host ""
Write-Host "Frontend configuration (localhost:3000):" -ForegroundColor Yellow
Write-Host "  const API_URL = `"http://$DUCKDNS_FULL_DOMAIN`"" -ForegroundColor White
Write-Host ""
Write-Host "Cookie settings:" -ForegroundColor Yellow
Write-Host "  SameSite=lax (same-site requests only)" -ForegroundColor White
Write-Host "  Secure=false (HTTP)" -ForegroundColor White
Write-Host ""

# ヘルスチェック
Write-Host "Testing health endpoint..." -ForegroundColor Green
try {
    $response = Invoke-WebRequest -Uri "http://$DUCKDNS_FULL_DOMAIN/health" -UseBasicParsing -TimeoutSec 10
    Write-Host "✓ Health check passed!" -ForegroundColor Green
    Write-Host "Response: $($response.Content)" -ForegroundColor White
} catch {
    Write-Host "⚠️  Health check failed (try again in a minute)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Opening Swagger UI..." -ForegroundColor Green
Start-Process "http://$DUCKDNS_FULL_DOMAIN/docs"

Write-Host ""
Write-Host "=== Next Steps ===" -ForegroundColor Cyan
Write-Host "1. Update frontend API URL to: http://$DUCKDNS_FULL_DOMAIN"
Write-Host "2. Test login from frontend (localhost:3000)"
Write-Host "3. If you want HTTPS, run setup-https.ps1"
Write-Host ""
