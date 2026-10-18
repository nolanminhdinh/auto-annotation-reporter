#!/usr/bin/env bash
# ======================================================================
# 🚀 AUTO-ANNOTATION REPORTER - ONE-CLICK QUICKSTART RUNNER (LINUX/MAC)
# ======================================================================
set -e

echo "======================================================================"
echo "🚀 AUTO-ANNOTATION REPORTER - ONE-CLICK QUICKSTART RUNNER"
echo "======================================================================"
echo ""

# 1. Kiem tra Python
echo "[1/5] Kiểm tra môi trường Python..."
if command -v python3 &>/dev/null; then
    PY_CMD="python3"
elif command -v python &>/dev/null; then
    PY_CMD="python"
else
    echo "❌ [LỖI] Không tìm thấy Python! Vui lòng cài đặt Python 3.10+."
    exit 1
fi
echo "  * Sử dụng: $($PY_CMD --version)"

# 2. Kiểm tra file cấu hình .env
echo ""
echo "[2/5] Kiểm tra file cấu hình .env..."
if [ ! -f .env ]; then
    echo "  * Đang khởi tạo file .env từ .env.example..."
    cp .env.example .env
    echo "  * Đã tạo file .env mặc định!"
else
    echo "  * File .env đã sẵn sàng."
fi

# 3. Cài đặt thư viện phụ thuộc
echo ""
echo "[3/5] Cài đặt dependencies..."
$PY_CMD -m pip install -q -r requirements.txt || $PY_CMD -m pip install -q requests python-dotenv
echo "  * Thư viện đã sẵn sàng!"

# 4. Chạy bộ Unit Tests
echo ""
echo "[4/5] Chạy kiểm thử hệ thống (Unit Tests)..."
$PY_CMD -m unittest discover tests -v

# 5. Kích hoạt Pipeline Toàn Trình
echo ""
echo "[5/5] Kích hoạt Pipeline Toàn Trình (Chế độ Offline)..."
$PY_CMD src/main.py --mode offline --llm-summary --export-powerbi --notify telegram

echo ""
echo "======================================================================"
echo "🎉 CHÚC MỪNG! HỆ THỐNG ĐÃ KHỞI TẠO VÀ CHẠY THÀNH CÔNG!"
echo "======================================================================"
echo "📁 Báo cáo Markdown: reports/MENTOR_REPORT_DRAFT.md"
echo "🗄️ Database Medallion: data/annotation_warehouse.db"
echo "📊 Power BI Datasets: powerbi/data/"
echo ""
