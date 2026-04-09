import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from googleapiclient.discovery import build
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import re
import io
from datetime import datetime
from collections import Counter

# ============================================================
# 페이지 설정
# ============================================================
st.set_page_config(
    page_title="유튜브 댓글 분석기 Pro",
    page_icon="📺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# 스타일
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&display=swap');

    .main-title {
        font-family: 'Noto Sans KR', sans-serif;
        font-size: 2.8rem;
        font-weight: 900;
        background: linear-gradient(135deg, #FF0000, #ff6b6b, #FF0000);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0;
        letter-spacing: -1px;
    }
    .sub-title {
        font-family: 'Noto Sans KR', sans-serif;
        text-align: center;
        color: #888;
        font-size: 1.05rem;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .metric-card-red {
        background: linear-gradient(135deg, #f93d66 0%, #ff6b6b 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .metric-card-green {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .metric-card-orange {
        background: linear-gradient(135deg, #f7971e 0%, #ffd200 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .metric-number {
        font-size: 2rem;
        font-weight: 900;
        margin: 5px 0;
    }
    .metric-label {
        font-size: 0.85rem;
        opacity: 0.9;
    }
    .comment-card {
        background: white;
        border: 1px solid #eee;
        border-left: 5px solid #FF0000;
        padding: 15px 20px;
        margin-bottom: 12px;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        transition: transform 0.2s;
    }
    .comment-card:hover {
        transform: translateX(5px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }
    .positive { border-left-color: #38ef7d; }
    .negative { border-left-color: #f93d66; }
    .neutral  { border-left-color: #ffd200; }

    .author-name {
        font-weight: 700;
        color: #333;
        font-size: 0.95rem;
    }
    .comment-meta {
        color: #aaa;
        font-size: 0.8rem;
    }
    .comment-body {
        color: #444;
        margin-top: 8px;
        line-height: 1.6;
    }
    .sentiment-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-positive { background: #d4edda; color: #155724; }
    .badge-negative { background: #f8d7da; color: #721c24; }
    .badge-neutral  { background: #fff3cd; color: #856404; }

    .video-info-box {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        padding: 25px;
        border-radius: 15px;
        color: white;
    }
    .video-title-display {
        font-size: 1.3rem;
        font-weight: 700;
        margin-bottom: 10px;
    }
    .channel-name {
        color: #aaa;
        font-size: 0.95rem;
    }

    div[data-testid="stMetricValue"] {
        font-size: 1.5rem;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 한국어 불용어 목록
# ============================================================
STOPWORDS_KO = set([
    "이", "그", "저", "것", "수", "등", "때", "중", "더", "안",
    "좀", "잘", "또", "및", "를", "을", "에", "의", "가", "는",
    "은", "로", "으로", "와", "과", "도", "에서", "까지", "부터",
    "한", "하는", "있는", "없는", "하다", "있다", "없다", "되다",
    "이다", "아니다", "같다", "보다", "나", "너", "우리", "그것",
    "이것", "저것", "여기", "거기", "저기", "어디", "언제", "무엇",
    "어떻게", "왜", "누구", "뭐", "진짜", "정말", "너무", "되게",
    "완전", "약간", "좀", "다", "못", "안", "잘", "많이", "조금",
    "매우", "아주", "제일", "가장", "정도", "거의", "다시", "이미",
    "아직", "바로", "그냥", "그래서", "그러나", "하지만", "그런데",
    "그리고", "또한", "때문에", "위해", "대해", "통해", "함께",
    "ㅋㅋ", "ㅋㅋㅋ", "ㅋㅋㅋㅋ", "ㅎㅎ", "ㅎㅎㅎ", "ㅠㅠ",
    "ㅜㅜ", "ㅠ", "ㅜ", "ㄷㄷ", "ㅇㅇ", "ㄱㄱ",
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "am", "do", "does", "did", "have", "has", "had", "will", "would",
    "could", "should", "may", "might", "shall", "can", "to", "of",
    "in", "for", "on", "with", "at", "by", "from", "it", "this",
    "that", "not", "but", "and", "or", "so", "if", "as", "no", "yes",
    "my", "your", "his", "her", "its", "our", "me", "him", "them",
    "what", "which", "who", "when", "where", "how", "why", "all",
    "each", "every", "both", "few", "more", "most", "other", "some",
    "such", "than", "too", "very", "just", "about", "above", "after",
    "before", "into", "through", "during", "up", "down", "out",
])

# ============================================================
# 유틸리티 함수
# ============================================================

def get_api_key():
    try:
        return st.secrets["YOUTUBE_API_KEY"]
    except Exception:
        return None


def extract_video_id(url):
    patterns = [
        r'(?:youtube\.com\/watch\?v=)([a-zA-Z0-9_-]{11})',
        r'(?:youtu\.be\/)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com\/v\/)([a-zA-Z0-9_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url.strip()):
        return url.strip()
    return None


def get_video_info(youtube, video_id):
    try:
        resp = youtube.videos().list(part="snippet,statistics", id=video_id).execute()
        if resp["items"]:
            item = resp["items"][0]
            s = item["snippet"]
            st_ = item["statistics"]
            return {
                "title": s.get("title", ""),
                "channel": s.get("channelTitle", ""),
                "published": s.get("publishedAt", ""),
                "views": int(st_.get("viewCount", 0)),
                "likes": int(st_.get("likeCount", 0)),
                "comment_count": int(st_.get("commentCount", 0)),
                "thumbnail": s.get("thumbnails", {}).get("high", {}).get("url", ""),
                "description": s.get("description", "")[:300],
            }
    except Exception as e:
        st.error(f"영상 정보 오류: {e}")
    return None


def get_comments(youtube, video_id, max_comments=200, order="relevance", include_replies=False):
    comments = []
    next_page = None
    try:
        while len(comments) < max_comments:
            req = youtube.commentThreads().list(
                part="snippet,replies" if include_replies else "snippet",
                videoId=video_id,
                maxResults=min(100, max_comments - len(comments)),
                order=order,
                pageToken=next_page,
                textFormat="plainText"
            )
            resp = req.execute()
            for item in resp.get("items", []):
                snip = item["snippet"]["topLevelComment"]["snippet"]
                comments.append({
                    "작성자": snip.get("authorDisplayName", ""),
                    "댓글": snip.get("textDisplay", ""),
                    "좋아요": snip.get("likeCount", 0),
                    "작성일시": snip.get("publishedAt", ""),
                    "답글수": item["snippet"].get("totalReplyCount", 0),
                    "유형": "댓글",
                })
                # 대댓글 수집
                if include_replies and "replies" in item:
                    for reply in item["replies"]["comments"]:
                        r_snip = reply["snippet"]
                        comments.append({
                            "작성자": r_snip.get("authorDisplayName", ""),
                            "댓글": r_snip.get("textDisplay", ""),
                            "좋아요": r_snip.get("likeCount", 0),
                            "작성일시": r_snip.get("publishedAt", ""),
                            "답글수": 0,
                            "유형": "↳ 답글",
                        })
            next_page = resp.get("nextPageToken")
            if not next_page:
                break
    except Exception as e:
        err = str(e)
        if "commentsDisabled" in err:
            st.error("🚫 댓글이 비활성화된 영상입니다.")
        elif "videoNotFound" in err:
            st.error("🚫 영상을 찾을 수 없습니다.")
        else:
            st.error(f"댓글 수집 오류: {e}")
    return comments


# ============================================================
# 감성 분석 (키워드 기반 - 외부 API 불필요)
# ============================================================
POSITIVE_WORDS = set([
    "좋아", "좋다", "최고", "대박", "굿", "짱", "감동", "행복", "사랑",
    "멋지", "멋있", "훌륭", "완벽", "감사", "추천", "재밌", "재미있",
    "웃기", "귀여", "예쁘", "아름답", "힐링", "응원", "축하", "기대",
    "신나", "즐거", "좋겠", "최애", "인정", "레전드", "존경", "천재",
    "love", "good", "great", "best", "amazing", "awesome", "nice",
    "beautiful", "wonderful", "perfect", "excellent", "fantastic",
    "cool", "funny", "happy", "like", "thank", "wow", "bravo",
    "goat", "fire", "legend", "brilliant", "incredible", "outstanding",
    "❤️", "♥️", "💕", "😍", "🥰", "👍", "🔥", "💯", "⭐", "🎉",
    "👏", "😂", "🤣", "✨", "💪", "🙌", "😊", "🥺",
])

NEGATIVE_WORDS = set([
    "싫어", "싫다", "별로", "최악", "쓰레기", "짜증", "화나", "실망",
    "후회", "지루", "지겨", "노잼", "구리", "구려", "못생", "슬프",
    "울다", "아프", "힘들", "어렵", "무섭", "그만", "삭제", "나가",
    "못하", "안되", "아쉽", "불만", "불편", "소름", "역겹",
    "hate", "bad", "worst", "terrible", "awful", "boring", "ugly",
    "stupid", "dumb", "trash", "garbage", "suck", "dislike", "annoying",
    "disappointed", "waste", "horrible", "disgusting", "pathetic",
    "😡", "🤬", "👎", "😤", "😢", "😭", "💔", "🤮", "😠",
])


def analyze_sentiment(text):
    text_lower = text.lower()
    pos_count = sum(1 for w in POSITIVE_WORDS if w in text_lower)
    neg_count = sum(1 for w in NEGATIVE_WORDS if w in text_lower)
    score = pos_count - neg_count
    if score > 0:
        return "긍정", score
    elif score < 0:
        return "부정", score
    else:
        return "중립", 0


# ============================================================
# 키워드 추출
# ============================================================
def extract_keywords(texts, top_n=30):
    all_words = []
    for text in texts:
        # 한글 2글자 이상 + 영문 2글자 이상 단어 추출
        words = re.findall(r'[가-힣]{2,}|[a-zA-Z]{2,}', text)
        for w in words:
            w_lower = w.lower()
            if w_lower not in STOPWORDS_KO and len(w_lower) >= 2:
                all_words.append(w_lower)
    counter = Counter(all_words)
    return counter.most_common(top_n)


# ============================================================
# 워드클라우드 생성
# ============================================================
def generate_wordcloud(keywords_dict):
    try:
        # 한글 폰트 경로 시도
        font_paths = [
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
            "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf",
            "/usr/share/fonts/nanum/NanumGothic.ttf",
            "NanumGothic.ttf",
            None  # 시스템 기본 폰트
        ]
        font_path = None
        for fp in font_paths:
            if fp is None:
                break
            try:
                import os
                if os.path.exists(fp):
                    font_path = fp
                    break
            except:
                continue

        wc_params = {
            "width": 800,
            "height": 400,
            "background_color": "white",
            "colormap": "Set2",
            "max_words": 100,
            "max_font_size": 120,
            "min_font_size": 12,
            "prefer_horizontal": 0.7,
            "relative_scaling": 0.5,
        }
        if font_path:
            wc_params["font_path"] = font_path

        wc = WordCloud(**wc_params).generate_from_frequencies(keywords_dict)

        fig, ax = plt.subplots(figsize=(12, 6))
        ax.imshow(wc, interpolation="bilinear")
        ax.axis("off")
        plt.tight_layout(pad=0)
        return fig
    except Exception as e:
        st.warning(f"워드클라우드 생성 중 문제: {e}")
        return None


# ============================================================
# 메인 앱
# ============================================================
def main():
    st.markdown('<div class="main-title">📺 유튜브 댓글 분석기 Pro</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">감성 분석 · 워드클라우드 · 트렌드 분석 · 영상 비교까지 한 번에</div>', unsafe_allow_html=True)

    # API 키
    api_key = get_api_key()
    if not api_key or "여기에" in str(api_key):
        st.warning("⚠️ YouTube API 키가 설정되지 않았습니다.")
        st.info("""
        **설정 방법:**
        1. [Google Cloud Console](https://console.cloud.google.com/)에서 YouTube Data API v3 활성화
        2. API 키 생성
        3. Streamlit Cloud **Settings → Secrets**에 입력:
        ```
        YOUTUBE_API_KEY = "발급받은_API_키"
        ```
        """)
        api_key = st.text_input("🔑 또는 API 키 직접 입력:", type="password")
        if not api_key:
            return

    try:
        youtube = build("youtube", "v3", developerKey=api_key)
    except Exception as e:
        st.error(f"API 연결 실패: {e}")
        return

    # --------------------------------------------------------
    # 사이드바
    # --------------------------------------------------------
    with st.sidebar:
        st.markdown("## ⚙️ 분석 설정")
        st.markdown("---")

        mode = st.radio(
            "🎯 모드 선택",
            ["단일 영상 분석", "영상 비교 분석"],
            help="2개 영상의 댓글을 비교할 수 있습니다"
        )

        st.markdown("---")

        max_comments = st.slider("📝 최대 댓글 수", 10, 500, 150, 10)

        order = st.radio(
            "📊 정렬",
            ["relevance", "time"],
            format_func=lambda x: "🔥 인기순" if x == "relevance" else "🕐 최신순"
        )

        include_replies = st.checkbox("💬 대댓글(답글)도 수집", value=False)

        st.markdown("---")
        st.markdown("""
        ### 💡 이 앱의 기능
        - 🎭 감성 분석 (긍정/부정/중립)
        - ☁️ 워드클라우드
        - 📈 시간대별 트렌드
        - 🏷️ 키워드 자동 추출
        - 🔗 영상 비교 분석
        - 📥 CSV / Excel 다운로드
        """)

    # --------------------------------------------------------
    # 단일 영상 분석
    # --------------------------------------------------------
    if mode == "단일 영상 분석":
        url = st.text_input(
            "🔗 유튜브 영상 URL",
            placeholder="https://www.youtube.com/watch?v=...",
        )

        if url:
            video_id = extract_video_id(url)
            if not video_id:
                st.error("❌ 올바른 유튜브 URL을 입력해주세요.")
                return

            # 영상 정보
            with st.spinner("영상 정보 로딩 중..."):
                info = get_video_info(youtube, video_id)

            if info:
                col_t, col_i = st.columns([1, 2])
                with col_t:
                    if info["thumbnail"]:
                        st.image(info["thumbnail"], use_container_width=True)
                with col_i:
                    st.markdown(f"""
                    <div class="video-info-box">
                        <div class="video-title-display">{info['title']}</div>
                        <div class="channel-name">📢 {info['channel']}  ·  📅 {info['published'][:10]}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.write("")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("👀 조회수", f"{info['views']:,}")
                    c2.metric("👍 좋아요", f"{info['likes']:,}")
                    c3.metric("💬 댓글", f"{info['comment_count']:,}")

            st.markdown("---")

            if st.button("🚀 댓글 수집 & 분석 시작", type="primary", use_container_width=True):
                with st.spinner("댓글 수집 중..."):
                    raw = get_comments(youtube, video_id, max_comments, order, include_replies)

                if raw:
                    df = pd.DataFrame(raw)
                    # 감성 분석
                    sentiments = df["댓글"].apply(analyze_sentiment)
                    df["감성"] = sentiments.apply(lambda x: x[0])
                    df["감성점수"] = sentiments.apply(lambda x: x[1])
                    # 날짜 파싱
                    df["작성일"] = pd.to_datetime(df["작성일시"]).dt.date
                    df["작성시간"] = pd.to_datetime(df["작성일시"]).dt.hour
                    df["댓글길이"] = df["댓글"].str.len()

                    st.session_state["df"] = df
                    st.session_state["info"] = info
                    st.success(f"✅ {len(df)}개 댓글 수집 & 분석 완료!")

        # 결과 표시
        if "df" in st.session_state:
            df = st.session_state["df"]
            info = st.session_state.get("info", {})

            st.markdown("---")

            # 요약 카드
            pos_count = len(df[df["감성"] == "긍정"])
            neg_count = len(df[df["감성"] == "부정"])
            neu_count = len(df[df["감성"] == "중립"])

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">총 수집 댓글</div>
                    <div class="metric-number">{len(df)}</div>
                </div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(f"""
                <div class="metric-card-green">
                    <div class="metric-label">😊 긍정</div>
                    <div class="metric-number">{pos_count}</div>
                </div>""", unsafe_allow_html=True)
            with c3:
                st.markdown(f"""
                <div class="metric-card-red">
                    <div class="metric-label">😠 부정</div>
                    <div class="metric-number">{neg_count}</div>
                </div>""", unsafe_allow_html=True)
            with c4:
                st.markdown(f"""
                <div class="metric-card-orange">
                    <div class="metric-label">😐 중립</div>
                    <div class="metric-number">{neu_count}</div>
                </div>""", unsafe_allow_html=True)

            st.write("")

            # ---- 탭 ----
            tabs = st.tabs([
                "📊 대시보드",
                "🎭 감성 분석",
                "☁️ 워드클라우드",
                "📈 트렌드",
                "🏷️ 키워드",
                "💬 댓글 보기",
                "📥 다운로드",
            ])

            # ---- 대시보드 ----
            with tabs[0]:
                row1_c1, row1_c2 = st.columns(2)

                with row1_c1:
                    fig_pie = px.pie(
                        names=["긍정", "부정", "중립"],
                        values=[pos_count, neg_count, neu_count],
                        color_discrete_sequence=["#38ef7d", "#f93d66", "#ffd200"],
                        title="감성 분포",
                        hole=0.45,
                    )
                    fig_pie.update_layout(height=350)
                    st.plotly_chart(fig_pie, use_container_width=True)

                with row1_c2:
                    # 좋아요 분포
                    fig_likes = px.histogram(
                        df, x="좋아요", nbins=30,
                        title="좋아요 수 분포",
                        color_discrete_sequence=["#667eea"],
                    )
                    fig_likes.update_layout(height=350)
                    st.plotly_chart(fig_likes, use_container_width=True)

                row2_c1, row2_c2 = st.columns(2)

                with row2_c1:
                    fig_len = px.histogram(
                        df, x="댓글길이", nbins=30,
                        title="댓글 길이 분포",
                        color_discrete_sequence=["#764ba2"],
                    )
                    fig_len.update_layout(height=350)
                    st.plotly_chart(fig_len, use_container_width=True)

                with row2_c2:
                    hour_data = df.groupby("작성시간").size().reset_index(name="댓글수")
                    fig_hour = px.bar(
                        hour_data, x="작성시간", y="댓글수",
                        title="시간대별 댓글 수",
                        color_discrete_sequence=["#11998e"],
