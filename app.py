
import os
import base64
import json
import requests
import smtplib

import streamlit as st
from email.mime.text import MIMEText
from openai import OpenAI


# OpenAI 클라이언트 생성
client = OpenAI()


# 이메일 발송 함수
def send_email(to, subject, body):

    sender = os.getenv("GMAIL_ADDRESS")
    password = os.getenv("GMAIL_APP_PASSWORD")

    if not sender or not password:
        raise ValueError("Gmail 환경변수를 확인해주세요.")

    # 메일 구성 (본문, 제목, 발신자, 수신자)
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to

    # 이메일 발송
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)

    return "이메일 발송 완료"


# 페이지 설정
st.set_page_config(
    page_title="에이블",
    page_icon="🤖",
    layout="wide"
)

st.title("김대리님, 안녕하세요?")
st.write("오늘은 무엇을 도와드릴까요?")


# 대화 초기화 버튼
if st.button("🗑️ 대화 초기화"):

    st.session_state.messages = []
    st.session_state.email_draft = None
    st.session_state.last_answer = None
    st.session_state.last_audio = None

    st.rerun()


# 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

if "email_draft" not in st.session_state:
    st.session_state.email_draft = None

if "last_answer" not in st.session_state:
    st.session_state.last_answer = None
  
if "last_audio" not in st.session_state:
    st.session_state.last_audio = None



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

4. 이메일 작성 및 발송
   - 사용자의 요청에 따라 이메일을 작성합니다.
   - 수신자, 제목, 본문을 구분하여 작성합니다.
   - 이메일 발송 요청이 있으면 send_email 함수를 호출합니다.
   - 수신자 이메일 주소가 없으면 임의로 만들어내지 않습니다.
   - 수신자, 제목, 본문 중 필요한 정보가 부족하면 추가로 질문합니다.
   - 이메일 초안은 사용자가 확인할 수 있도록 작성합니다.

[응답 원칙]

1. 핵심 내용을 먼저 제시하고 구체적인 설명을 덧붙입니다.
2. 회의 내용에 없는 사실을 임의로 만들어내지 않습니다.
3. 김 대리에게 배정된 업무와 다른 참석자의 업무를 명확히 구분합니다.
4. 업무가 배정되지 않았다면 배정된 업무가 없다고 명시합니다.
5. 표와 목록을 활용하여 정보를 체계적으로 정리합니다.
6. 이메일 발송은 사용자가 최종 확인한 후 진행합니다.
"""


# Function Calling 도구 정의
tools = [
    {
        "type": "function",
        "name": "send_email",
        "description": "사용자가 요청한 이메일의 수신자, 제목, 본문을 작성합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": "이메일 수신자 주소"
                },
                "subject": {
                    "type": "string",
                    "description": "이메일 제목"
                },
                "body": {
                    "type": "string",
                    "description": "이메일 본문"
                }
            },
            "required": ["to", "subject", "body"],
            "additionalProperties": False
        },
        "strict": True
    }
]




# 지시 영역
with st.form("task_form"):

    uploaded_file = st.file_uploader(
        "텍스트 파일 업로드",
        type=["txt"]
    )

    audio_value = st.audio_input("무엇을 도와드릴까요?")

    submit = st.form_submit_button("실행")



# 버튼을 눌렀을 때만 실행
if submit:

    # 업로드된 파일이 있으면 디코딩
    text = ""

    if uploaded_file is not None:
        text = uploaded_file.read().decode("utf-8")

    # 녹음이 없으면 녹음 요청
    if audio_value is None:
        st.warning("음성을 녹음해주세요.")
        st.stop()

    # STT: 음성 → 텍스트
    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=(
            "audio.wav",
            audio_value.getvalue(),
            "audio/wav"
        )
    )

    # 사용자 질문 저장
    user_question = transcript.text

    st.session_state.messages.append({
        "role": "user",
        "content": user_question
    })

    # 시스템 메시지 생성
    system_content = sys_role

    if text:
        system_content += f"\n\n다음 내용을 참고하세요:\n{text}"

    # 이전 대화 + 현재 질문 전달
    input_messages = [
        {
            "role": "system",
            "content": system_content
        }
    ] + st.session_state.messages

    # LLM 호출
    with st.spinner("답변을 준비하고 있습니다..."):

        response = client.responses.create(
            model="gpt-4o-mini",
            input=input_messages,
            tools=tools
        )

        # Function Calling 확인
        tool_calls = [
            item for item in response.output
            if item.type == "function_call"
        ]

        if tool_calls:

            for tool_call in tool_calls:

                if tool_call.name == "send_email":

                    email_data = json.loads(tool_call.arguments)

                    st.session_state.email_draft = email_data

            # 이메일 초안 작성 결과도 대화 기록에 저장
            answer = "요청하신 이메일 초안을 작성했습니다. 내용을 확인한 후 발송해주세요."

        else:

            # 일반 AI 답변
            answer = response.output_text

        # TTS: AI 답변 → 음성 변환
        try:
            speech_response = client.audio.speech.create(
                model="gpt-4o-mini-tts",
                voice="coral",
                input=answer,
                instructions="한국어로 자연스럽고 친절하게, 또렷한 발음으로 말해주세요."
            )

            # 음성 데이터 저장
            st.session_state.last_audio = speech_response.content

        except Exception as e:
            st.session_state.last_audio = None
            st.warning(f"음성 변환 실패: {e}")

        # AI 응답 저장
        st.session_state.messages.append({
            "role": "assistant",
            "content": answer
        })

        st.session_state.last_answer = answer

    # 화면 갱신
    st.rerun()

# AI 답변 및 음성 출력
if st.session_state.last_answer:

    st.subheader("🤖 AI 답변")
    st.write(st.session_state.last_answer)

    # 음성 자동 재생
    if st.session_state.last_audio:

        st.audio(
            st.session_state.last_audio,
            format="audio/mp3",
            autoplay=True
        )


# 이메일 발송 확인 화면
if st.session_state.email_draft is not None:

    st.divider()

    st.subheader("📧 이메일 발송 확인")

    email_data = st.session_state.email_draft

    # 이메일 정보 입력
    to = st.text_input(
        "수신자 이메일",
        value=email_data["to"],
        key="email_to"
    )

    subject = st.text_input(
        "이메일 제목",
        value=email_data["subject"],
        key="email_subject"
    )

    body = st.text_area(
        "이메일 본문",
        value=email_data["body"],
        height=250,
        key="email_body"
    )

    # 발송 버튼
    if st.button("이메일 발송"):

        if not to or not subject or not body:
            st.warning("수신자, 제목, 본문을 모두 입력해주세요.")

        else:

            try:
                result = send_email(to, subject, body)

                st.success(result)

                # 발송 완료 후 초안 초기화
                st.session_state.email_draft = None

            except Exception as e:
                st.error(f"이메일 발송 실패: {e}")

# 이전 대화 기록 출력
for message in st.session_state.messages:

    with st.chat_message(message["role"]):
        st.write(message["content"])
