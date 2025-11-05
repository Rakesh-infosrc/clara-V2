$url = "http://clara-alb-dev-926087638.us-east-1.elb.amazonaws.com/flow/face_recognition"
try {
    $response = Invoke-WebRequest -Uri $url -Method POST -ContentType "application/json" -Body '{"test": "data"}'
    Write-Host "Status: $($response.StatusCode)"
    Write-Host "Content: $($response.Content)"
} catch {
    Write-Host "Error: $($_.Exception.Message)"
    Write-Host "Response: $($_.Exception.Response)"
}
