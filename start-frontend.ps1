$logFile = "$env:TEMP\ubuntucare-frontend.log"
$process = Start-Process -NoNewWindow -PassThru -FilePath "npm" -ArgumentList "run dev" -WorkingDirectory "D:\med ai\ambient-healthcare-agents-main\src\frontend\web" -RedirectStandardOutput $logFile -RedirectStandardError $logFile
Write-Host "Frontend dev server started (PID: $($process.Id)). Log: $logFile"
$process.Id | Out-File "$env:TEMP\ubuntucare-frontend.pid"
