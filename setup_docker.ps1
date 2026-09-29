# PowerShell script to (re)install Docker Desktop, build and run the SIH Project stack
# -----------------------------------------------------------------------------
# 1. Ensure Docker Desktop is installed via winget (or chocolatey if you prefer)
# -----------------------------------------------------------------------------
# If Docker is already on PATH this block will be skipped.
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Docker CLI not found – attempting to install Docker Desktop via winget..."
    # winget may require admin rights; if unavailable, instruct the user.
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        winget install --id Docker.DockerDesktop --source winget --accept-source-agreements --accept-package-agreements
        Write-Host "Docker Desktop installation initiated. Please restart PowerShell after installation to use Docker CLI."
    } else {
        Write-Error "winget not available. Please install Docker Desktop manually from https://www.docker.com/products/docker-desktop"
        exit 1
    }
}

# -----------------------------------------------------------------------------
# 2. Start Docker Desktop (if not already running)
# -----------------------------------------------------------------------------
# Docker Desktop creates a Windows service named "com.docker.service".
# We'll start it and then wait until the Docker daemon is reachable.
$serviceName = "com.docker.service"
if ((Get-Service -Name $serviceName -ErrorAction SilentlyContinue).Status -ne "Running") {
    Write-Host "Starting Docker service..."
    Start-Service -Name $serviceName -ErrorAction SilentlyContinue
}

# Wait for the Docker daemon to be ready (max 90 seconds)
$maxWait = 90
$elapsed = 0
while ($elapsed -lt $maxWait) {
    try {
        docker version -Quiet | Out-Null
        Write-Host "Docker daemon is up after $elapsed seconds."
        break
    } catch {
        Start-Sleep -Seconds 3
        $elapsed += 3
    }
}
if ($elapsed -ge $maxWait) {
    Write-Error "Docker daemon did not become ready within $maxWait seconds. Please start Docker Desktop manually and retry."
    exit 1
}

# -----------------------------------------------------------------------------
# 3. Build the compose stack (no cache to force fresh images)
# -----------------------------------------------------------------------------
Write-Host 'Building Docker images (no cache)...'
# Ensure we are in the project root directory
Set-Location "c:/Users/jebas/OneDrive/Desktop/Organization/Desktop/Organized/Projects/Project_Files/React/SIH Project"

docker compose build --no-cache
if ($LASTEXITCODE -ne 0) {
    Write-Error "docker compose build failed. Check the logs above for details."
    exit 1
}

# -----------------------------------------------------------------------------
# 4. Bring the stack up in detached mode
# -----------------------------------------------------------------------------
Write-Host "Starting the Docker Compose stack..."

docker compose up -d
if ($LASTEXITCODE -ne 0) {
    Write-Error "docker compose up failed."
    exit 1
}

# -----------------------------------------------------------------------------
# 5. Verify containers are running
# -----------------------------------------------------------------------------
Write-Host "Checking container status..."

docker ps --format "{{.Names}} {{.Status}}"

# -----------------------------------------------------------------------------
# 6. Test the FastAPI health endpoint
# -----------------------------------------------------------------------------
Write-Host "Testing FastAPI health endpoint..."
try {
    $resp = Invoke-RestMethod -Uri http://localhost:8000/health -Method GET -TimeoutSec 15
    Write-Host "Health response: $($resp | ConvertTo-Json -Depth 5)"
} catch {
    Write-Warning "Health endpoint not reachable."
}

# -----------------------------------------------------------------------------
# 7. Open the frontend in the default browser (optional)
# -----------------------------------------------------------------------------
Start-Process "http://localhost:3000"

Write-Host "Setup complete. Your SIH Project stack is running locally."
