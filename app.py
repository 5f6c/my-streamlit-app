
import os, base64, json, requests
import streamlit as st
from openai import OpenAI

# OpenAI 클라이언트 생성
client = OpenAI()

# 페이지 설정
st.set_page_config(page_title="에이블", page_icon="🤖", layout="wide")
st.title("김대리님, 안녕하세요?")
st.write("오늘은 무을 도와드릴까요?")

# 역할 지정
sys_role = """
당신은 '김 대리'의 개인 비서 '에이블'입니다.
김대리가 요청한 업무를 최선을 다해 처리합니다.

[담당 업무]
1. 회의록 분석 및 요약
   - 회의의 주요 안건과 핵심 논의 내용을 정리합니다.
   - 주요 결정 사항과 논의 결과를 요약합니다.
   - 불필요하거나 반복되는 내용은 제외하고 핵심만 전달합니다.

2. 업무 지시 사항 추출
   - 회의 내용 중 김 대리에게 배정된 업무를 찾아냅니다.
   - 담당 업무의 구체적인 내용과 수행 목적을 정리합니다.
   - 업무별 마감 기한과 우선순위를 확인합니다.
   - 담당자가 불분명하거나 마감 기한이 없는 경우 임의로 추측하지 않습니다.

3. 업무 관리 및 지원
   - 김 대리가 수행해야 할 업무를 빠짐없이 정리합니다.
   - 업무 진행에 필요한 후속 조치 사항을 제안합니다.
   - 업무 수행에 필요한 정보가 부족하면 추가 확인 사항을 안내합니다.

[응답 원칙]
1. 핵심 내용을 먼저 제시하고 구체적인 설명을 덧붙입니다.
2. 회의 내용에 없는 사실을 임의로 만들어내지 않습니다.
3. 김 대리에게 배정된 업무와 다른 참석자의 업무를 명확히 구분합니다.
4. 업무가 배정되지 않았다면 배정된 업무가 없다고 명시합니다.
5. 표와 목록을 활용하여 정보를 체계적으로 정리합니다.
"""

# 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# 지시 영역
with st.form("task_form"):
    uploaded_file = st.file_uploader("텍스트 파일 업로드", type=["txt"])
    audio_value = st.audio_input("무엇을 도와드릴까요?")
    submit = st.form_submit_button("실행")

# 버튼을 눌렀을 때만 실행
if submit:
    # 업로드 된 파일이 있으면 디코딩
    text = ""
    if uploaded_file is not None:
        text = uploaded_file.read().decode("utf-8")

    # 녹음이 없으면 녹음 요청
    if audio_value is None:
        st.warning("음성을 녹음해주세요.")
        st.stop()

    # 시스템 메세지
    system_content = sys_role
    if text:
        system_content += f"\n\n다음 내용을 참고하세요:\n{text}"
    input_messages = [{"role": "system", "content": system_content}]

    # STT: 음성 → 텍스트
    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=("audio.wav", audio_value, "audio/wav"))

    # 사용자 메시지
    input_messages.append({"role": "user", "content": transcript.text})

    # LLM 호출 및 응답 듣기
    with st.spinner("답변을 준비하고 있습니다..."):
        # LLM 호출
        response = client.responses.create(
            model="gpt-4o-mini",
            input=input_messages
        )
        answer = response.output_text

        # 응답 출력
        st.subheader("AI 답변")
        st.write(answer)
