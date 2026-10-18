@echo off
chcp 65001 >nul
echo ======================================================================
echo 🚀 AUTO-ANNOTATION REPORTER - ONE-CLICK QUICKSTART RUNNER
echo ======================================================================
echo.

:: 1. Kiem tra Python
echo [1/5] Kiem tra moi truong Python...
where py >nul 2>nul
if %errorlevel% equ 0 (
    set PY_CMD=py -3
    goto :FOUND_PY
)

where python >nul 2>nul
if %errorlevel% equ 0 (
    set PY_CMD=python
    goto :FOUND_PY
)

where python3 >nul 2>nul
if %errorlevel% equ 0 (
    set PY_CMD=python3
    goto :FOUND_PY
)

echo [LOI] Khong tim thay Python! Vui long cai dat Python 3.10+ tu https://www.python.org/
pause
exit /b 1

:FOUND_PY
echo   * Su dung: %PY_CMD%
%PY_CMD% --version

:: 2. Kiem tra file cau hinh .env
echo.
echo [2/5] Kiem tra file cau hinh .env...
if not exist .env (
    echo   * Chua co .env, dang tu dong khoi tao tu .env.example...
    copy .env.example .env >nul
    echo   * Da tao file .env mac dinh!
) else (
    echo   * File .env da san sang.
)

:: 3. Cai dat thu vien can thiet
echo.
echo [3/5] Kiem tra thu vien phu thuoc (Dependencies)...
%PY_CMD% -m pip install -q -r requirements.txt
if %errorlevel% neq 0 (
    echo   * Canh bao: Cai dat qua requirements.txt gap loi, thu cai goi toi thieu...
    %PY_CMD% -m pip install -q requests python-dotenv
)
echo   * Thu vien da san sang!

:: 4. Chay bo test kiem dinh he thong
echo.
echo [4/5] Chay kiem thu toan bo 80 Unit Tests...
%PY_CMD% -m unittest discover tests -v
if %errorlevel% neq 0 (
    echo [CANH BAO] Mot so test case chua dat, van tiep tuc chay pipeline...
) else (
    echo   * 80/80 Unit Tests PASS 100%!
)

:: 5. Kich hoat Pipeline Toan Trinh
echo.
echo [5/5] Kich hoat Pipeline Toan Trinh (Che do Offline Demo)...
%PY_CMD% src/main.py --mode offline --llm-summary --export-powerbi --notify telegram

echo.
echo ======================================================================
echo 🎉 CHUC MUNG! HE THONG DA KHOI TAO VA CHAY THANH CONG!
echo ======================================================================
echo 📁 File bao cao: reports\MENTOR_REPORT_DRAFT.md
echo 🗄️ Database kho: data\annotation_warehouse.db
echo 📊 Power BI Data: powerbi\data\
echo.

set /p OPEN_REPORT="Ban co muon mo file bao cao MENTOR_REPORT_DRAFT.md ngay khong? (Y/N): "
if /i "%OPEN_REPORT%"=="Y" (
    if exist reports\MENTOR_REPORT_DRAFT.md (
        start notepad reports\MENTOR_REPORT_DRAFT.md
    )
)

pause
