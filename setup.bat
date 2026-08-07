@echo off
chcp 65001 >nul
echo ============================================
echo   AI CNC Inspector - Kurulum
echo ============================================
echo.

:: Python kontrolu
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [HATA] Python bulunamadi!
    echo.
    echo Lutfen Python 3.13'u asagidaki linkten indirip kurun:
    echo https://www.python.org/downloads/release/python-31315/
    echo.
    echo ONEMLI: Kurulum sirasinda "Add Python to PATH" kutusunu isaretleyin!
    echo.
    pause
    exit /b 1
)

python --version
echo.

:: Sanal ortam kontrolu
if exist venv\Scripts\activate.bat (
    echo [OK] Sanal ortam zaten mevcut.
) else (
    echo Sanal ortam olusturuluyor...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [HATA] Sanal ortam olusturulamadi.
        pause
        exit /b 1
    )
    echo [OK] Sanal ortam olusturuldu.
)

echo.
echo Sanal ortam aktif ediliyor...
call venv\Scripts\activate.bat

echo.
echo pip guncelleniyor...
python -m pip install --upgrade pip --quiet

echo.
echo Kutuphaneler kuruluyor (bu 5-15 dakika surebilir)...
echo.

pip install "streamlit>=1.30" "opencv-python>=4.8" "numpy>=1.24" "pillow>=10.0" "ultralytics>=8.0"

echo.
echo PyTorch kuruluyor (buyuk paket, lutfen bekleyin)...
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

echo.
echo ============================================
echo   Kurulum tamamlandi!
echo ============================================
echo.
echo Uygulamayi baslatmak icin: start.bat
echo.
pause
