#!/bin/bash
echo ""
echo " ========================================"
echo "  HR Excel Statistics Dashboard"
echo " ========================================"
echo ""

# 가상환경 활성화 (있을 경우)
if [ -f ".venv/bin/activate" ]; then
    echo " [INFO] 가상환경 활성화 중..."
    source .venv/bin/activate
fi

# 의존성 설치
echo " [INFO] 패키지 설치 중..."
pip install -r requirements.txt --quiet

echo ""
echo " [INFO] 앱을 시작합니다..."
echo " [INFO] 브라우저에서 http://localhost:8501 을 열어주세요."
echo ""

streamlit run app.py --server.port 8501
