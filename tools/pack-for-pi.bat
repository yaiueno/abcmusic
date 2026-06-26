@echo off
chcp 65001 >nul
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$src='raspberry'; $zip='raspberry-pi.zip'; if(Test-Path $zip){Remove-Item $zip}; Compress-Archive -Path $src -DestinationPath $zip -Force; Write-Host ''; Write-Host '作成完了:' (Resolve-Path $zip); Write-Host ''; Get-ChildItem $src | ForEach-Object { Write-Host '  -' $_.Name }; Write-Host ''; Write-Host 'この zip をUSBでラズパイに渡して:' ; Write-Host '  unzip raspberry-pi.zip -d ~/' ; Write-Host '  cd ~/raspberry' ; Write-Host '  bash setup.sh'"
pause
