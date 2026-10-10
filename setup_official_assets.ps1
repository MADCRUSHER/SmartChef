$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host "Downloading official SmartChef frontend..."
New-Item -ItemType Directory -Force -Path "$root\templates" | Out-Null
Invoke-WebRequest `
  -Uri "https://raw.githubusercontent.com/saksham483/Smart-chef/main/templates/index.html" `
  -OutFile "$root\templates\index.html"

Write-Host "Downloading official SmartChef YOLO model archive..."
Invoke-WebRequest `
  -Uri "https://raw.githubusercontent.com/saksham483/Smart-chef/main/yolov8s-world.zip" `
  -OutFile "$root\yolov8s-world.zip"

Write-Host "Extracting model..."
Expand-Archive "$root\yolov8s-world.zip" -DestinationPath "$root\model_extract" -Force

$model = Get-ChildItem "$root\model_extract" -Recurse -Filter "yolov8s-world.pt" | Select-Object -First 1
if (-not $model) {
    throw "Could not find yolov8s-world.pt in the downloaded archive."
}
Copy-Item $model.FullName "$root\yolov8s-world.pt" -Force

Remove-Item "$root\model_extract" -Recurse -Force
Remove-Item "$root\yolov8s-world.zip" -Force

Write-Host ""
Write-Host "Assets ready."
Write-Host "Next:"
Write-Host '  py -m venv .venv'
Write-Host '  .\.venv\Scripts\Activate.ps1'
Write-Host '  pip install -r requirements.txt'
Write-Host '  $env:SPOONACULAR_API_KEY="YOUR_KEY"'
Write-Host '  python app.py'
