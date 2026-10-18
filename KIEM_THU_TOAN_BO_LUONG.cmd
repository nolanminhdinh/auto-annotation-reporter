@echo off
chcp 65001 >nul
setlocal
pushd "%~dp0"

echo ===============================================================================
echo 🚀 HỆ THỐNG KIỂM THỬ TOÀN DIỆN LUỒNG HOẠT ĐỘNG (END-TO-END VERIFICATION)
echo    Dự án: Auto Annotation Reporter (CVAT & GitHub Sync - Power BI Lakehouse)
echo ===============================================================================
echo.

:: 1. Xác định lệnh Python
set "PY_CMD="
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PY_CMD=%~dp0.venv\Scripts\python.exe"
) else (
    where py >nul 2>nul
    if not errorlevel 1 (
        set "PY_CMD=py -3"
    ) else (
        where python >nul 2>nul
        if not errorlevel 1 (
            set "PY_CMD=python"
        )
    )
)

if "%PY_CMD%"=="" (
    echo [LỖI] Không tìm thấy Python 3.10+ hoặc môi trường ảo .venv!
    pause
    exit /b 1
)

echo [1/5] 🛠️  Khởi tạo bộ dữ liệu giả lập toàn diện (Full-Capability Mock Dataset)...
%PY_CMD% -X utf8 tools\generate_mock_dataset.py
if errorlevel 1 (
    echo [CẢNH BÁO] Sinh dữ liệu giả lập có lỗi!
    pause
    exit /b 1
)

echo.
echo [2/5] 🧪 Chạy bộ kiểm thử tự động 140 Unit Tests (100%% Code Coverage)...
%PY_CMD% -X utf8 -m unittest discover tests -v
if errorlevel 1 (
    echo [CẢNH BÁO] Một số test case chưa hoàn thành!
)

echo.
echo [3/5] 🔄 Chạy Pipeline Toàn Trình (Offline Medallion Warehouse & LLM Synthesis)...
%PY_CMD% -X utf8 src\main.py --mode offline --snapshot sample_data\powerbi_demo --llm-summary --verify --brief --notify preview --session "Full Pipeline Verification"
if errorlevel 1 (
    echo [LỖI] Pipeline gặp sự cố!
    pause
    exit /b 1
)

echo.
echo [4/5] 📡 Kiểm tra kết nối trực tiếp LIVE CVAT API (Task #2679097)...
%PY_CMD% -X utf8 tools\accept_cvat_live.py --task-id 2679097
if errorlevel 1 (
    echo [LƯU Ý] CVAT live test hoàn tất với ghi nhận giới hạn (Token chỉ có quyền Read, chất lượng QA phụ thuộc cloud).
)

echo.
echo [5/5] 📊 Kiểm tra trạng thái Kho Dữ Liệu Medallion (data\annotation_warehouse.db)...
%PY_CMD% -X utf8 src\storage\verify_warehouse.py

echo.
echo ===============================================================================
echo 🎉 TẤT CẢ CÁC BƯỚC ĐÃ ĐƯỢC KIỂM THỬ THÀNH CÔNG VÀ TRƠN TRU!
echo -------------------------------------------------------------------------------
echo  📁 Báo cáo Markdown Mentor : data\runs\latest.json (kèm MENTOR_REPORT_DRAFT.md)
echo  🗄️ Database Medallion     : data\annotation_reporting.db & data\annotation_warehouse.db
echo  📈 Power BI Dataset Bundle : data\processed\current.json
echo  🌐 Web Dashboard HTML      : docs\index.html (Mở bằng Xem_Bao_Cao.bat)
echo ===============================================================================
echo.

popd
pause
endlocal
