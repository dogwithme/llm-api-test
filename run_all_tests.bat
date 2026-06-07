@echo off
chcp 936 >nul 2>&1
cd /d "%~dp0"

echo ==============================================
echo          Doubao API + UI Automation Test
echo ==============================================
echo.

echo [1/4] Cleaning old test reports...
if exist reports rmdir /s /q reports
mkdir reports
echo Old reports cleaned.
echo.

echo [2/4] Running all test cases (API + UI)...
echo Tips:
echo   - Only API tests: pytest -k "not test_ui_"
echo   - Only UI tests: pytest -m ui
echo   - Disable auto-retry: pytest --no-reruns
echo.
pytest
echo.
echo All tests finished.
echo.

echo [3/4] Generating and opening Allure report...
allure serve ./reports
echo.

pause