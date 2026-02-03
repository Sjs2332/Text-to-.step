# Start Docker Desktop (Windows) and launch the application

# Check if Docker is running
try {
    docker ps | Out-Null
    Write-Host "Docker is running"
} catch {
    Write-Host "Starting Docker Desktop..."
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe" -ErrorAction SilentlyContinue
    
    # Wait for Docker to be ready
    Write-Host "Waiting for Docker to start..."
    $maxAttempts = 30
    $attempt = 0
    while ($attempt -lt $maxAttempts) {
        try {
            docker ps | Out-Null
            Write-Host "Docker is ready!"
            break
        } catch {
            $attempt++
            Start-Sleep -Seconds 1
        }
    }
}

# Run setup and start
npm run setup
if ($LASTEXITCODE -eq 0) {
    npm run dev:all
}
