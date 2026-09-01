<# :
@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-Command -ScriptBlock ([ScriptBlock]::Create((Get-Content '%~f0' -Raw)))"
#>

$ErrorActionPreference = 'Stop'
$uploadableDir = $PWD

$csvFiles = @(Get-ChildItem -Path $uploadableDir -Filter '*.csv')
if ($csvFiles.Count -eq 0) {
    Write-Host "Error: No CSV files found in uploadable_csvs folder." -ForegroundColor Red
    Start-Sleep -Seconds 3
    exit
}

# Auto-detect old date from the first file
$oldDate = $null
foreach ($file in $csvFiles) {
    # Match something like 1Sep2026 or 01Sep2026
    if ($file.Name -match '\d{1,2}[A-Za-z]{3}\d{4}') {
        $oldDate = $Matches[0]
        break
    }
}

Write-Host "========================================="
Write-Host "  Date Changer Tool for Uploadable CSVs"
Write-Host "========================================="

if (-not $oldDate) {
    Write-Host "Could not automatically detect the campaign date (e.g. 1Sep2026) from the filenames." -ForegroundColor Red
    $oldDate = Read-Host "Please enter the OLD date manually to replace"
    if ([string]::IsNullOrWhiteSpace($oldDate)) {
        Write-Host "Operation cancelled." -ForegroundColor Yellow
        Start-Sleep -Seconds 2
        exit
    }
} else {
    Write-Host "Detected campaign date: $oldDate" -ForegroundColor Cyan
}

$newDate = Read-Host "Enter the NEW campaign date (e.g. 2Sep2026)"

if ([string]::IsNullOrWhiteSpace($newDate)) {
    Write-Host "Operation cancelled." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
    exit
}

$successCount = 0
foreach ($file in $csvFiles) {
    if ($file.Name -match $oldDate) {
        $newName = $file.Name -replace $oldDate, $newDate
        $newFilePath = Join-Path $file.DirectoryName $newName
        
        Write-Host "Processing: $($file.Name) -> $newName..."
        
        # Read contents, replace, and write to new file (using UTF8)
        (Get-Content $file.FullName) -replace $oldDate, $newDate | Set-Content $newFilePath -Encoding UTF8
        
        # Delete old file permanently
        Remove-Item $file.FullName -Force
        $successCount++
    }
}

Write-Host "`nSuccessfully updated $successCount files." -ForegroundColor Green
Write-Host "Exiting tool..." -ForegroundColor DarkGray
Start-Sleep -Seconds 3