@echo off
setlocal
REM Capture honest, timestamped cluster outputs. Does NOT fabricate GitHub screenshots.
cd /d "%~dp0.."
if not exist "docs\evidence" mkdir "docs\evidence"
echo Capturing RAHBAR runtime evidence into docs\evidence\
minikube kubectl -- get pods -n rahbar -o wide > "docs\evidence\pods.txt" 2>&1
minikube kubectl -- get endpoints -n rahbar > "docs\evidence\endpoints.txt" 2>&1
minikube kubectl -- get hpa api -n rahbar > "docs\evidence\hpa.txt" 2>&1
minikube kubectl -- top pods -n rahbar > "docs\evidence\resource-usage.txt" 2>&1
minikube kubectl -- get jobs,cronjobs -n rahbar > "docs\evidence\indexing-jobs.txt" 2>&1
minikube kubectl -- get deployment api -n rahbar -o wide > "docs\evidence\api-deployment.txt" 2>&1
minikube kubectl -- get pvc -n rahbar > "docs\evidence\pvc.txt" 2>&1
curl.exe --max-time 20 http://127.0.0.1:8000/readyz > "docs\evidence\api-readyz.json" 2>&1
curl.exe --max-time 20 http://127.0.0.1:8000/healthz > "docs\evidence\api-healthz.json" 2>&1
echo Done. Open each file and verify it contains real results, not connection errors.
echo GitHub branch-protection, blocked merge, PR approval and CD run screenshots
 echo must be captured manually from the real GitHub interface.
endlocal
