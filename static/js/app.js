/**
 * AI Food & Wine Pairing Agent - 프론트엔드 자바스크립트
 * 폼 제출, /generate REST API 호출, 로딩 및 오류 처리, 마크다운 렌더링, 복사, 다운로드 구현
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. 주요 DOM 엘리먼트 가져오기
    const form = document.getElementById('pairingForm');
    const foodInput = document.getElementById('foodInput');
    const moodInput = document.getElementById('moodInput');
    const drinkTypeSelect = document.getElementById('drinkTypeSelect');
    const submitBtn = document.getElementById('submitBtn');

    const placeholderState = document.getElementById('placeholderState');
    const loadingState = document.getElementById('loadingState');
    const errorState = document.getElementById('errorState');
    const errorMessage = document.getElementById('errorMessage');
    const resultContent = document.getElementById('resultContent');
    const resultActions = document.getElementById('resultActions');
    const copyBtn = document.getElementById('copyBtn');
    const downloadBtn = document.getElementById('downloadBtn');

    // 생성된 원본 마크다운 텍스트를 저장할 변수
    let currentMarkdown = '';

    // 2. 폼 제출(Submit) 이벤트 리스너
    form.addEventListener('submit', async (e) => {
        e.preventDefault(); // 기본 새로고침 방지

        const food = foodInput.value.trim();
        const mood = moodInput.value.trim();
        const drinkType = drinkTypeSelect.value;
        const selectedToneRadio = document.querySelector('input[name="tone"]:checked');
        const tone = selectedToneRadio ? selectedToneRadio.value : 'casual';

        // 프론트엔드 1차 입력 검증
        if (!food) {
            showError('음식 이름 또는 식재료를 입력해 주세요.');
            foodInput.focus();
            return;
        }

        // 로딩 UI 상태로 전환
        setLoadingState(true);
        hideError();

        try {
            // 백엔드 Flask의 /generate 엔드포인트로 비동기 POST 요청 (Vercel 경로 호환)
            const apiUrl = window.location.pathname.startsWith('/flask') ? '/flask/generate' : '/generate';
            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    food: food,
                    mood: mood,
                    drink_type: drinkType,
                    tone: tone
                })
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                // 서버에서 반환한 친절한 오류 메시지 또는 기본 메시지 표시
                throw new Error(data.error || '페어링 추천을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.');
            }

            // 성공: 결과 렌더링
            currentMarkdown = data.recommendation;
            renderResult(currentMarkdown);

        } catch (err) {
            console.error('페어링 요청 오류:', err);
            showError(err.message || '네트워크 연결 상태를 확인한 후 다시 시도해 주세요.');
        } finally {
            // 로딩 종료
            setLoadingState(false);
        }
    });

    // 3. 결과 렌더링 함수
    function renderResult(markdownText) {
        // 대기 화면 숨김
        placeholderState.style.display = 'none';
        
        // marked.js를 사용하여 마크다운을 HTML로 파싱
        if (window.marked && typeof marked.parse === 'function') {
            resultContent.innerHTML = marked.parse(markdownText);
        } else {
            // marked 라이브러리를 불러오지 못했을 때의 안전 장치
            resultContent.innerText = markdownText;
        }

        resultContent.style.display = 'block';
        resultActions.style.display = 'flex';

        // 결과 화면으로 부드럽게 스크롤 (모바일 배려)
        resultContent.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    // 4. 로딩 상태 제어 함수
    function setLoadingState(isLoading) {
        if (isLoading) {
            placeholderState.style.display = 'none';
            resultContent.style.display = 'none';
            resultActions.style.display = 'none';
            loadingState.style.display = 'block';
            submitBtn.disabled = true;
            submitBtn.innerText = '⏳ AI가 페어링을 고민 중입니다...';
        } else {
            loadingState.style.display = 'none';
            submitBtn.disabled = false;
            submitBtn.innerText = '✨ 맞춤 페어링 추천받기';
        }
    }

    // 5. 오류 메시지 제어 함수
    function showError(message) {
        errorMessage.innerText = message;
        errorState.style.display = 'flex';
    }

    function hideError() {
        errorState.style.display = 'none';
        errorMessage.innerText = '';
    }

    // 6. 결과 복사 기능 (클립보드 API)
    copyBtn.addEventListener('click', async () => {
        if (!currentMarkdown) return;

        try {
            await navigator.clipboard.writeText(currentMarkdown);
            const originalText = copyBtn.innerText;
            copyBtn.innerText = '✅ 복사 완료!';
            setTimeout(() => {
                copyBtn.innerText = originalText;
            }, 2000);
        } catch (err) {
            console.error('클립보드 복사 실패:', err);
            alert('클립보드 복사에 실패했습니다.');
        }
    });

    // 7. Markdown 파일 다운로드 기능 (.md)
    downloadBtn.addEventListener('click', () => {
        if (!currentMarkdown) return;

        const foodName = foodInput.value.trim() || 'food';
        const sanitizedFoodName = foodName.replace(/[^a-zA-Z0-9가-힣_-]/g, '_');
        const filename = `${sanitizedFoodName}_pairing_recommendation.md`;

        // Blob 객체 생성 및 다운로드 링크 트리거
        const blob = new Blob([currentMarkdown], { type: 'text/markdown;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    });
});
