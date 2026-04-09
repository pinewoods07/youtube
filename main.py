import streamlit as st
import pandas as pd
import plotly.express as px
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
# CSS 스타일
# ============================================================
st.markdown("""
<style>
    .main-title {
        font-size: 2.8rem;
        font-weight: 900;
        background: linear-gradient(135deg, #FF0000, #ff6b6b);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0;
    }
    .sub-title {
        text-align: center;
        color: #888;
        font-size: 1.05rem;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea, #764ba2);
        padding: 20px; border-radius: 15px;
        color: white; text-align: center;
    }
    .metric-card-green {
        background: linear-gradient(135deg, #11998e, #38ef7d);
        padding: 20px; border-radius: 15px;
        color: white; text-align: center;
    }
    .metric-card-red {
        background: linear-gradient(135deg, #f93d66, #ff6b6b);
        padding: 20px; border-radius: 15px;
        color: white; text-align: center;
    }
    .metric-card-orange {
        background: linear-gradient(135deg, #f7971e, #ffd200);
        padding: 20px; border-radius: 15px;
        color: white; text-align: center;
    }
    .metric-number { font-size: 2rem; font-weight: 900; margin: 5px 0; }
    .metric-label { font-size: 0.85rem; opacity: 0.9; }
    .comment-card {
        background: white; border: 1px solid #eee;
        border-left: 5px solid #FF0000;
        padding: 15px 20px; margin-bottom: 12px; border-radius: 8px;
    }
    .comment-card.positive { border-left-color: #38ef7d; }
    .comment-card.negative { border-left-color: #f93d66; }
    .comment-card.neutral { border-left-color: #ffd200; }
    .author-name { font-weight: 700; color: #333; }
    .comment-meta { color: #aaa; font-size: 0.8rem; }
    .comment-body { color: #444; margin-top: 8px; line-height: 1.6; }
    .badge-positive { background: #d4edda; color: #155724; padding: 2px 10px; border-radius: 12px; font-size: 0.75rem; }
    .badge-negative { background: #f8d7da; color: #721c24; padding: 2px 10px; border-radius: 12px; font-size: 0.75rem; }
    .badge-neutral { background: #fff3cd; color: #856404; padding: 2px 10px; border-radius: 12px; font-size: 0.75rem; }
    .video-info-box {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        padding: 25px; border-radius: 15px; color: white;
    }
    .video-title-display { font-size: 1.3rem; font-weight: 700; margin-bottom: 10px; }
    .channel-name { color: #aaa; font-size: 0.95rem; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 불용어
# ============================================================
STOPWORDS_KO = set([
    "이", "그", "저", "것", "수", "등", "때", "중", "더", "안",
    "좀", "잘", "또", "및", "를", "을", "에", "의", "가", "는",
    "은", "로", "으로", "와", "과", "도", "에서", "까지", "부터",
    "한", "하는", "있는", "없는", "하다", "있다", "없다", "되다",
    "이다", "아니다", "같다", "보다", "나", "너", "우리", "그것",
    "이것", "저것", "여기", "거기", "저기", "어디", "언제", "무엇",
    "어떻게", "왜", "누구", "뭐", "진짜", "정말", "너무", "되게",
    "완전", "약간", "다", "못", "많이", "조금", "매우", "아주",
    "제일", "가장", "정도", "거의", "다시", "이미", "아직", "바로",
    "그냥", "그래서", "그러나", "하지만", "그런데", "그리고", "또한",
    "때문에", "위해", "대해", "통해", "함께",
    "ㅋㅋ", "ㅋㅋㅋ", "ㅋㅋㅋㅋ", "ㅎㅎ", "ㅎㅎㅎ", "ㅠㅠ",
    "ㅜㅜ", "ㅠ", "ㅜ", "ㄷㄷ", "ㅇㅇ", "ㄱㄱ",
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "am", "do", "does", "did", "have", "has", "had", "will", "would",
    "could", "should", "may", "might", "shall", "can", "to", "of",
    "in", "for", "on", "with", "at", "by", "from", "it", "this",
    "that", "not", "but", "and", "or", "so", "if", "as", "no", "yes",
    "my", "your", "his", "her", "its", "our", "me", "him", "them",
    "what", "which", "who", "when", "where", "how", "why", "all",
])

# ============================================================
# 감성 분석 단어
# ============================================================
POSITIVE_WORDS = set([
    "좋아", "좋다", "최고", "대박", "굿", "짱", "감동", "행복", "사랑",
    "멋지", "멋있", "훌륭", "완벽", "감사", "추천", "재밌", "재미있",
    "웃기", "귀여", "예쁘", "아름답", "힐링", "응원", "축하", "기대",
    "신나", "즐거", "좋겠", "최애", "인정", "레전드", "존경", "천재",
    "love", "good", "great", "best", "amazing", "awesome", "nice",
    "beautiful", "wonderful", "perfect", "excellent", "fantastic",
    "cool", "funny", "happy", "like", "thank", "wow", "bravo",
    "legend", "brilliant", "incredible",
    "❤️", "💕", "😍", "🥰", "👍", "🔥", "💯", "⭐", "🎉",
    "👏", "😂", "🤣", "✨", "💪", "🙌", "😊",
])

NEGATIVE_WORDS = set([
    "싫어", "싫다", "별로", "최악", "쓰레기", "짜증", "화나", "실망",
    "후회", "지루", "지겨", "노잼", "구리", "구려", "못생", "슬프",
    "울다", "아프", "힘들", "어렵", "무섭", "그만", "삭제", "나가",
    "못하", "안되", "아쉽", "불만", "불편", "역겹",
    "hate", "bad", "worst", "terrible", "awful", "boring", "ugly",
    "stupid", "trash", "garbage", "suck", "dislike", "annoying",
    "disappointed", "waste", "horrible", "disgusting",
    "😡", "🤬", "👎", "😤", "😢", "😭", "💔", "🤮", "😠",
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
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url.strip()):
        return url.strip()
    return None


def get_video_info(youtube, video_id):
    try:
        resp = youtube.videos().list(part="snippet,statistics", id=video_id).execute()
        if resp["items"]:
            s = resp["items"][0]["snippet"]
            t = resp["items"][0]["statistics"]
            return {
                "title": s.get("title", ""),
                "channel": s.get("channelTitle", ""),
                "published": s.get("publishedAt", "")[:10],
                "views": int(t.get("viewCount", 0)),
                "likes": int(t.get("likeCount", 0)),
                "comment_count": int(t.get("commentCount", 0)),
                "thumbnail": s.get("thumbnails", {}).get("high", {}).get("url", ""),
            }
    except Exception as e:
        st.error(f"영상 정보 오류: {e}")
    return None


def get_comments(youtube, video_id, max_comments=200, order="relevance", include_replies=False):
    comments = []
    next_page = None
    try:
        while len(comments) < max_comments:
            part_str = "snippet,replies" if include_replies else "snippet"
            req = youtube.commentThreads().list(
                part=part_str,
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
                if include_replies and "replies" in item:
                    for reply in item["replies"]["comments"]:
                        r_snip = reply["snippet"]
                        comments.append({
                            "작성자": r_snip.get("authorDisplayName", ""),
                            "댓글": r_snip.get("textDisplay", ""),
                            "좋아요": r_snip.get("likeCount", 0),
                            "작성일시": r_snip.get("publishedAt", ""),
                            "답글수": 0,
                            "유형": "답글",
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


def analyze_sentiment(text):
    text_lower = text.lower()
    pos = sum(1 for w in POSITIVE_WORDS if w in text_lower)
    neg = sum(1 for w in NEGATIVE_WORDS if w in text_lower)
    score = pos - neg
    if score > 0:
        return "긍정", score
    elif score < 0:
        return "부정", score
    else:
        return "중립", 0


def extract_keywords(texts, top_n=30):
    all_words = []
    for text in texts:
        words = re.findall(r'[가-힣]{2,}|[a-zA-Z]{2,}', text)
        for w in words:
            wl = w.lower()
            if wl not in STOPWORDS_KO and len(wl) >= 2:
                all_words.append(wl)
    return Counter(all_words).most_common(top_n)


def generate_wordcloud(keywords_dict):
    if not keywords_dict:
        return None
    try:
        import os
        font_path = None
        for fp in ["/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
                    "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf"]:
            if os.path.exists(fp):
                font_path = fp
                break
        params = {
            "width": 800, "height": 400,
            "background_color": "white", "colormap": "Set2",
            "max_words": 80, "max_font_size": 120,
        }
        if font_path:
            params["font_path"] = font_path
        wc = WordCloud(**params).generate_from_frequencies(keywords_dict)
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.imshow(wc, interpolation="bilinear")
        ax.axis("off")
        plt.tight_layout(pad=0)
        return fig
    except Exception as e:
        st.warning(f"워드클라우드 오류: {e}")
        return None


def process_dataframe(raw_comments):
    df = pd.DataFrame(raw_comments)
    sentiments = df["댓글"].apply(analyze_sentiment)
    df["감성"] = sentiments.apply(lambda x: x[0])
    df["감성점수"] = sentiments.apply(lambda x: x[1])
    df["작성일"] = pd.to_datetime(df["작성일시"]).dt.date
    df["작성시간"] = pd.to_datetime(df["작성일시"]).dt.hour
    df["댓글길이"] = df["댓글"].str.len()
    return df


# ============================================================
# 분석 결과 표시 함수
# ============================================================
def show_analysis(df, info, key_prefix="single"):
    pos_count = len(df[df["감성"] == "긍정"])
    neg_count = len(df[df["감성"] == "부정"])
    neu_count = len(df[df["감성"] == "중립"])
    total = len(df)

    # 요약 카드 4개
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="metric-card"><div class="metric-label">총 댓글</div>'
                     f'<div class="metric-number">{total}</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-card-green"><div class="metric-label">😊 긍정</div>'
                     f'<div class="metric-number">{pos_count}</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="metric-card-red"><div class="metric-label">😠 부정</div>'
                     f'<div class="metric-number">{neg_count}</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="metric-card-orange"><div class="metric-label">😐 중립</div>'
                     f'<div class="metric-number">{neu_count}</div></div>', unsafe_allow_html=True)
    st.write("")

    # ==== 탭 구성 ====
    tab_dash, tab_sent, tab_wc, tab_trend, tab_kw, tab_comments, tab_dl = st.tabs([
        "📊 대시보드", "🎭 감성분석", "☁️ 워드클라우드",
        "📈 트렌드", "🏷️ 키워드", "💬 댓글보기", "📥 다운로드"
    ])

    # ---- 대시보드 ----
    with tab_dash:
        r1c1, r1c2 = st.columns(2)
        with r1c1:
            fig_pie = px.pie(
                names=["긍정", "부정", "중립"],
                values=[pos_count, neg_count, neu_count],
                color_discrete_sequence=["#38ef7d", "#f93d66", "#ffd200"],
                title="감성 분포", hole=0.45
            )
            fig_pie.update_layout(height=350)
            st.plotly_chart(fig_pie, use_container_width=True)
        with r1c2:
            fig_likes = px.histogram(
                df, x="좋아요", nbins=30,
                title="좋아요 수 분포",
                color_discrete_sequence=["#667eea"]
            )
            fig_likes.update_layout(height=350)
            st.plotly_chart(fig_likes, use_container_width=True)

        r2c1, r2c2 = st.columns(2)
        with r2c1:
            fig_len = px.histogram(
                df, x="댓글길이", nbins=30,
                title="댓글 길이 분포",
                color_discrete_sequence=["#764ba2"]
            )
            fig_len.update_layout(height=350)
            st.plotly_chart(fig_len, use_container_width=True)
        with r2c2:
            hour_data = df.groupby("작성시간").size().reset_index(name="댓글수")
            fig_hour = px.bar(
                hour_data, x="작성시간", y="댓글수",
                title="시간대별 댓글 수",
                color_discrete_sequence=["#11998e"]
            )
            fig_hour.update_layout(height=350)
            st.plotly_chart(fig_hour, use_container_width=True)

    # ---- 감성분석 ----
    with tab_sent:
        st.subheader("🎭 감성 분석 결과")
        if total > 0:
            st.markdown(f"""
| 구분 | 개수 | 비율 |
|------|------|------|
| 😊 긍정 | {pos_count}개 | {pos_count/total*100:.1f}% |
| 😠 부정 | {neg_count}개 | {neg_count/total*100:.1f}% |
| 😐 중립 | {neu_count}개 | {neu_count/total*100:.1f}% |
            """)

        sent_likes = df.groupby("감성")["좋아요"].mean().reset_index()
        sent_likes.columns = ["감성", "평균좋아요"]
        fig_bar = px.bar(
            sent_likes, x="감성", y="평균좋아요", color="감성",
            color_discrete_map={"긍정": "#38ef7d", "부정": "#f93d66", "중립": "#ffd200"},
            title="감성별 평균 좋아요 수"
        )
        fig_bar.update_layout(height=350)
        st.plotly_chart(fig_bar, use_container_width=True)

        for sentiment in ["긍정", "부정", "중립"]:
            subset = df[df["감성"] == sentiment].nlargest(3, "좋아요")
            if len(subset) > 0:
                emoji = {"긍정": "😊", "부정": "😠", "중립": "😐"}[sentiment]
                st.markdown(f"#### {emoji} {sentiment} 대표 댓글 (좋아요 TOP 3)")
                for _, row in subset.iterrows():
                    st.markdown(f"> **{row['작성자']}** (👍 {row['좋아요']})\n> {row['댓글'][:200]}")

    # ---- 워드클라우드 ----
    with tab_wc:
        st.subheader("☁️ 워드클라우드")
        keywords = extract_keywords(df["댓글"].tolist(), top_n=80)
        kw_dict = dict(keywords)
        if kw_dict:
            fig_wc = generate_wordcloud(kw_dict)
            if fig_wc:
                st.pyplot(fig_wc)
                plt.close(fig_wc)
        else:
            st.info("추출할 키워드가 부족합니다.")

        st.markdown("---")
        st.subheader("감성별 워드클라우드")
        wc1, wc2 = st.columns(2)
        with wc1:
            pos_texts = df[df["감성"] == "긍정"]["댓글"].tolist()
            if pos_texts:
                pos_kw = dict(extract_keywords(pos_texts, 50))
                if pos_kw:
                    st.markdown("#### 😊 긍정 댓글")
                    fig_p = generate_wordcloud(pos_kw)
                    if fig_p:
                        st.pyplot(fig_p)
                        plt.close(fig_p)
        with wc2:
            neg_texts = df[df["감성"] == "부정"]["댓글"].tolist()
            if neg_texts:
                neg_kw = dict(extract_keywords(neg_texts, 50))
                if neg_kw:
                    st.markdown("#### 😠 부정 댓글")
                    fig_n = generate_wordcloud(neg_kw)
                    if fig_n:
                        st.pyplot(fig_n)
                        plt.close(fig_n)

    # ---- 트렌드 ----
    with tab_trend:
        st.subheader("📈 시간 트렌드 분석")
        daily = df.groupby("작성일").size().reset_index(name="댓글수")
        daily["작성일"] = pd.to_datetime(daily["작성일"])
        fig_daily = px.line(
            daily, x="작성일", y="댓글수",
            title="일별 댓글 수 추이", markers=True,
            color_discrete_sequence=["#667eea"]
        )
        fig_daily.update_layout(height=400)
        st.plotly_chart(fig_daily, use_container_width=True)

        daily_sent = df.groupby(["작성일", "감성"]).size().reset_index(name="댓글수")
        daily_sent["작성일"] = pd.to_datetime(daily_sent["작성일"])
        fig_st = px.line(
            daily_sent, x="작성일", y="댓글수", color="감성",
            title="일별 감성 트렌드",
            color_discrete_map={"긍정": "#38ef7d", "부정": "#f93d66", "중립": "#ffd200"},
            markers=True
        )
        fig_st.update_layout(height=400)
        st.plotly_chart(fig_st, use_container_width=True)

    # ---- 키워드 ----
    with tab_kw:
        st.subheader("🏷️ 핵심 키워드 TOP 20")
        top_kw = extract_keywords(df["댓글"].tolist(), top_n=20)
        if top_kw:
            kw_df = pd.DataFrame(top_kw, columns=["키워드", "빈도"])
            fig_kw = px.bar(
                kw_df, x="빈도", y="키워드", orientation="h",
                title="키워드 빈도 TOP 20",
                color="빈도", color_continuous_scale="Viridis"
            )
            fig_kw.update_layout(height=600, yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig_kw, use_container_width=True)
            st.dataframe(kw_df, use_container_width=True)

    # ---- 댓글 보기 ----
    with tab_comments:
        st.subheader("💬 댓글 목록")
        fc1, fc2 = st.columns([2, 1])
        with fc1:
            search = st.text_input("🔍 키워드 검색", placeholder="검색어 입력...", key=f"search_{key_prefix}")
        with fc2:
            filter_sent = st.selectbox("감성 필터", ["전체", "긍정", "부정", "중립"], key=f"filter_{key_prefix}")

        filtered = df.copy()
        if search:
            filtered = filtered[filtered["댓글"].str.contains(search, case=False, na=False)]
        if filter_sent != "전체":
            filtered = filtered[filtered["감성"] == filter_sent]

        st.write(f"**{len(filtered)}개 댓글 표시 중**")
        display_df = filtered[["작성자", "댓글", "좋아요", "감성", "작성일", "유형"]].reset_index(drop=True)
        display_df.index = display_df.index + 1
        st.dataframe(display_df, use_container_width=True, height=400)

        st.markdown("---")
        card_count = min(30, len(filtered))
        if card_count > 0:
            show_n = st.slider("카드로 볼 댓글 수", 5, card_count, min(10, card_count), key=f"slider_{key_prefix}")
            for _, row in filtered.head(show_n).iterrows():
                s_class = {"긍정": "positive", "부정": "negative", "중립": "neutral"}.get(row["감성"], "neutral")
                b_class = f"badge-{s_class}"
                emoji = {"긍정": "😊", "부정": "😠", "중립": "😐"}.get(row["감성"], "")
                st.markdown(f"""
                <div class="comment-card {s_class}">
                    <span class="author-name">{row['작성자']}</span>
                    <span class="comment-meta"> · {row['작성일']} · 👍 {row['좋아요']}</span>
                    <span class="{b_class}">{emoji} {row['감성']}</span>
                    <div class="comment-body">{row['댓글']}</div>
                </div>
                """, unsafe_allow_html=True)

    # ---- 다운로드 ----
    with tab_dl:
        st.subheader("📥 데이터 다운로드")
        title_safe = re.sub(r'[^\w가-힣]', '_', info.get("title", "youtube"))[:30]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        dl1, dl2 = st.columns(2)
        with dl1:
            csv_data = df.to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                label="📄 CSV 다운로드",
                data=csv_data,
                file_name=f"{title_safe}_{timestamp}.csv",
                mime="text/csv",
                use_container_width=True
            )
        with dl2:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="댓글데이터")
            excel_data = buffer.getvalue()
            st.download_button(
                label="📊 Excel 다운로드",
                data=excel_data,
                file_name=f"{title_safe}_{timestamp}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )


# ============================================================
# 메인 앱
# ============================================================
def main():
    st.markdown('<div class="main-title">📺 유튜브 댓글 분석기 Pro</div>', unsafe_allow_html=True)
    st.markdown
