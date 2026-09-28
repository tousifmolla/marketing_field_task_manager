$ErrorActionPreference = 'Stop'
$backend = Join-Path $PSScriptRoot '..\backend'
Set-Location $backend
if (-not (Test-Path '.\venv\Scripts\python.exe')) { python -m venv venv; .\venv\Scripts\python.exe -m pip install -r requirements.txt }
.\venv\Scripts\python.exe app.py
