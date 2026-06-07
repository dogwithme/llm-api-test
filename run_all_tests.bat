@echo off
chcp 65001 >nul
echo ==============================================
echo          豆包大模型API+UI自动化测试
echo ==============================================
echo.

echo [1/4] 正在清理旧的测试报告...
if exist reports rmdir /s /q reports
mkdir reports
echo 旧报告清理完成
echo.

echo [2/4] 正在运行所有测试用例（API+UI）...
echo 提示：
echo   - 只运行API测试：pytest -k "not test_ui_"
echo   - 只运行UI测试：pytest -m ui
echo   - 关闭自动重试：pytest --no-reruns
echo.
pytest
echo.
echo 所有测试运行完成
echo.

echo [3/4] 正在生成并打开Allure报告...
allure serve ./reports
echo.

pause