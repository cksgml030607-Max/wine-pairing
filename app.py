import os
import logging
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from google import genai
from google.genai import errors

# 환경변수 로드
load_dotenv()

# 로깅 설정 (Backend Log: 요청, 응답, 오류 출력)
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
)
logger = logging.getLogger(__name__)

# 프로젝트 기본 경로 설정 (Vercel Serverless 배포 환경 호환)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Flask 애플리케이션 초기화 (템플릿 및 정적 파일 경로 명시)
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static')
)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'default-dev-secret-key')

# Gemini API 클라이언트 초기화 (.env에서만 API Key 읽기)
api_key = os.getenv("GEMINI_API_KEY")
if not api_key or api_key == "your_gemini_api_key_here":
    logger.warning("경고: GEMINI_API_KEY가 올바르게 설정되지 않았습니다. .env 파일을 확인해 주세요.")

client = None
if api_key:
    client = genai.Client(api_key=api_key)


@app.route('/')
def index():
    """메인 화면 렌더링"""
    return render_template('index.html')


@app.route('/generate', methods=['POST'])
def generate_pairing():
    """음식 및 상황 기반 AI 주류 페어링 추천 API"""
    if not request.is_json:
        logger.error("요청 실패: 요청 데이터가 JSON 형식이 아닙니다.")
        return jsonify({
            'success': False,
            'error': '요청 형식이 잘못되었습니다. JSON 데이터를 전송해 주세요.'
        }), 400

    data = request.get_json()
    food = (data.get('food') or '').strip()
    mood = (data.get('mood') or '').strip()
    drink_type = (data.get('drink_type') or '전체').strip()
    tone = (data.get('tone') or 'casual').strip()

    # 입력값 검증 (Backend Validation)
    if not food:
        logger.warning("입력 검증 실패: 음식 이름이 누락되었습니다.")
        return jsonify({
            'success': False,
            'error': '음식 이름 또는 주요 재료를 입력해 주세요.'
        }), 400

    if tone not in ['casual', 'expert']:
        tone = 'casual'

    logger.info(f"페어링 추천 요청 수신 - 음식: '{food}', 상황: '{mood}', 선호주류: '{drink_type}', Tone: '{tone}'")

    if not client:
        logger.error("Gemini 클라이언트 미초기화: GEMINI_API_KEY 미설정")
        return jsonify({
            'success': False,
            'error': '서버에 Gemini API Key가 설정되지 않았습니다. .env 파일을 확인해 주세요.'
        }), 500

    # Prompt Engineering (Prompt A: 캐주얼/친근 vs Prompt B: 전문 소믈리에)
    if tone == 'casual':
        system_instruction = (
            "당신은 센스 있고 친근한 미식가 친구이자 유쾌한 홈술 가이드입니다. "
            "어려운 전문 용어 대신 일상에서 쉽게 공감할 수 있는 재치 있고 다정한 어조로 설명하세요. "
            "이모지를 적절히 사용하고, 누구나 마트나 편의점에서 편하게 구할 수 있는 친근한 추천을 포함하세요."
        )
    else:
        system_instruction = (
            "당신은 미슐랭 스타 레스토랑의 수석 소믈리에이자 공인 주류 전문가입니다. "
            "격조 있고 정중하며 전문적인 어조를 유지하세요. "
            "음식과 술의 마리아주(Mariage) 원리(산도, 타닌, 바디감, 잔당감, 풍미 프로필의 조화), "
            "포도 품종 및 산지 특성, 추천 서빙 온도와 최적의 글라스 선택 팁까지 깊이 있게 안내하세요."
        )

    user_prompt = f"""
다음 정보를 바탕으로 최고의 음식 & 주류 페어링 추천안을 작성해 주세요.

[요청 정보]
- 음식 또는 주요 재료: {food}
- 분위기 및 상황: {mood if mood else '자유로운 편안한 분위기'}
- 선호하는 주류 종류: {drink_type if drink_type else '모든 주류 중 최적의 페어링'}

[응답 구성 가이드라인 (Markdown 형식)]
1. 🌟 **추천 페어링 주류 요약**: 주류 명칭, 종류, 원산지 또는 특징
2. 🍷 **맛과 풍미의 조화 이유**: 음식의 맛(단맛, 짠맛, 기름기, 매운맛 등)과 주류가 왜 환상적으로 어울리는지 설명
3. 💡 **즐기는 꿀팁**: 추천 서빙 온도, 마시는 순서, 잔 선택 또는 곁들이면 좋은 사이드 팁
4. 🥂 **마무리 코멘트**: 해당 분위기/상황에 어울리는 한 줄 격려나 건배사
"""

    # 모델 호출 (안정적인 가용성을 위해 모델 순차 시도)
    candidate_models = ['gemini-3.5-flash-lite', 'gemini-3.8-flash', 'gemini-flash-latest']
    recommendation_text = None
    last_error = None

    for model_name in candidate_models:
        try:
            logger.info(f"Gemini API 호출 시도 (모델: {model_name})")
            full_prompt = f"{system_instruction}\n\n{user_prompt}"
            response = client.models.generate_content(
                model=model_name,
                contents=full_prompt
            )
            if response and response.text:
                recommendation_text = response.text
                logger.info(f"Gemini API 응답 성공 (모델: {model_name}, 응답 길이: {len(recommendation_text)}자)")
                break
        except Exception as e:
            last_error = e
            logger.warning(f"모델 {model_name} 호출 실패: {str(e)[:150]}")

    if not recommendation_text:
        logger.error(f"모든 Gemini 모델 호출 실패. 최후 오류: {str(last_error)}")
        return jsonify({
            'success': False,
            'error': f'AI 페어링 추천 생성 중 오류가 발생했습니다: {str(last_error)}'
        }), 500

    return jsonify({
        'success': True,
        'recommendation': recommendation_text
    })


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    logger.info(f"Flask 페어링 웹 서버 시작 (포트: {port})")
    app.run(host='0.0.0.0', port=port, debug=True)
