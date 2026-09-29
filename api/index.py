import os
import sys

# 프로젝트 루트 경로를 파이썬 모듈 검색 경로에 등록
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import app

# Vercel Serverless Function 진입점
# Vercel은 파일 내의 'app' 객체를 찾아 WSGI 어플리케이션으로 실행합니다.
