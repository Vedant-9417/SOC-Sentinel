@echo off
echo Starting SOC Sentinel...
if not exist .env copy .env.example .env
docker compose up --build
