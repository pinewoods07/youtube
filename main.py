import streamlit as st
import pandas as pd
from googleapiclient.discovery import build
import re
from datetime import datetime

# ============================================================
# 페이지 설정
# ============================================================
st.set_page_config(
    page_title="유튜브 댓글 수집기",
    page_icon="📺",
    layout="wide"
)

# ============================================================
# 스타일
# ============================================================
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #FF0000;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .comment-box {
        background-color: #f9f9f9;
        border-left: 4px solid #FF0000;
        padding: 12px 16px;
        margin-bottom: 10px;
        border-radius: 4px;
    }
    .comment-author {
        font-weight: 700;
        color: #333;
        font-size: 0.95rem;
    }
    .comment-date {
        color: #999;
        font-size: 0.8rem;
    }
    .comment-text {
        margin-top: 6px;
        color: #444;
        font-size: 0.95rem;
        line-height: 1.5;
    }
    .comment-likes {
        color: #888;
        font-size: 0.8rem;
        margin-top: 4px;
    }
    .stat-card {
        background: linear-gradient(135deg, #FF0000, #cc0000);
        color: white;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# API 키 로드
# ============================================================
def get_api_key():
    """Streamlit secrets에서 API 키를 가져옵니다."""
    try:
        return st.secrets["YOUTUBE_API_KEY"]
    except Exception:
        return None

# ============================================================
# 유튜브 영상 ID 추출
# ============================================================
def extract_video_id(url):
    """다양한 유튜브 URL 형식에서 영상 ID를 추출합니다."""
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
    # 11자리 문자열 자체가 입력된 경우
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url.strip()):
        return url.strip()
    return None

# ============================================================
# 영상 정보 가져오기
# ============================================================
def get_video_info(youtube, video_id):
    """영상 제목, 채널명, 조회수 등 기본 정보를 가져옵니다."""
    try:
        request = youtube.videos().list(
            part="snippet,statistics",
            id=video_id
        )
        response = request.execute()
        if response["items"]:
            item = response["items"][0]
            snippet = item["snippet"]
            stats = item["statistics"]
            return {
                "title": snippet.get("title", ""),
                "channel": snippet.get("channelTitle", ""),
                "published": snippet.get("publishedAt", "")[:10],
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "comment_count": int(stats.get("commentCount", 0)),
                "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url", "")
            }
    except Exception as e:
        st.error(f"영상 정보를 가져오는 중 오류 발생: {e}")
    return None

# ============================================================
# 댓글 수집
# ============================================================
def get_comments(youtube, video_id, max_comments=100, order="relevance"):
    """
    유튜브 영상의 댓글을 수집합니다.
    order: 'relevance'(인기순) 또는 'time'(최신순)
    """
    comments = []
    next_page_token = None

    try:
        while len(comments) < max_comments:
            request = youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=min(100, max_comments - len(comments)),
                order=order,
                pageToken=next_page_token,
                textFormat="plainText"
            )
            response = request.execute()

            for item in response.get("items", []):
                snippet = item["snippet"]["topLevelComment"]["snippet"]
                comment_data = {
                    "작성자": snippet.get("authorDisplayName", ""),
                    "댓글": snippet.get("textDisplay", ""),
                    "좋아요": snippet.get("likeCount", 0),
                    "작성일": snippet.get("publishedAt", "")[:10],
                    "수정일": snippet.get("updatedAt", "")[:10] if snippet.get("updatedAt") else "",
                    "답글수": item["snippet"].get("totalReplyCount", 0)
                }
                comments.append(comment_data)

            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break

    except Exception as e:
        error_msg = str(e)
        if "commentsDisabled" in error_msg:
            st.error("🚫 이 영상은 댓글이 비활성화되어 있습니다.")
        elif "videoNotFound" in error_msg:
            st.error("🚫 영상을 찾을 수 없습니다. URL을 확인해주세요.")
        elif "forbidden" in error_msg.lower():
            st.error("🚫 API 키 권한 문제가 발생했습니다. API 키를 확인해주세요.")
        else:
            st.error(f"댓글 수집 중 오류 발생: {e}")

    return comments

# ============================================================
# 메인 앱
# ============================================================
def main():
    st.markdown('<div class="main-header">📺 유튜브 댓글 수집기</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">유튜브 영상 링크를 입력하면 댓글을 수집하여 보여줍니다</div>', unsafe_allow_html=True)

    # API 키 확인
    api_key = get_api_key()

    if not api_key or api_key == "여기에_본인의_YouTube_Data_API_v3_키를_입력하세요":
        st.warning("⚠️ YouTube API 키가 설정되지 않았습니다.")
        st.info("""
        **API 키 설정 방법:**
        1. [Google Cloud Console](https://console.cloud.google.com/)에서 프로젝트를 생성합니다.
        2. YouTube Data API v3를 활성화합니다.
        3. API 키를 생성합니다.
        4. Streamlit Cloud의 **Settings → Secrets**에 아래 내용을 입력합니다:
        ```
        YOUTUBE_API_KEY = "발급받은_API_키"
        ```
        """)

        # 직접 입력 옵션
        api_key_input = st.text_input("또는 여기에 API 키를 직접 입력하세요:", type="password")
        if api_key_input:
            api_key = api_key_input
        else:
            return

    # YouTube API 클라이언트 생성
    try:
        youtube = build("youtube", "v3", developerKey=api_key)
    except Exception as e:
        st.error(f"YouTube API 연결 실패: {e}")
        return

    # --------------------------------------------------------
    # 사이드바 설정
    # --------------------------------------------------------
    with st.sidebar:
        st.header("⚙️ 설정")

        max_comments = st.slider(
            "수집할 최대 댓글 수",
            min_value=10,
            max_value=500,
            value=100,
            step=10,
            help="API 할당량에 주의하세요"
        )

        order = st.radio(
            "정렬 기준",
            options=["relevance", "time"],
            format_func=lambda x: "🔥 인기순" if x == "relevance" else "🕐 최신순",
            index=0
        )

        st.markdown("---")
        st.markdown("""
        **💡 사용 팁**
        - 유튜브 영상 URL을 붙여넣기 하세요
        - 일반 링크, 공유 링크, 쇼츠 모두 지원
        - 수집된 댓글은 CSV로 다운로드 가능
        """)

    # --------------------------------------------------------
    # URL 입력
    # --------------------------------------------------------
    url = st.text_input(
        "🔗 유튜브 영상 URL을 입력하세요",
        placeholder="https://www.youtube.com/watch?v=...",
        help="일반 링크, youtu.be 공유 링크, 쇼츠 링크 모두 지원합니다"
    )

    # --------------------------------------------------------
    # 댓글 수집 실행
    # --------------------------------------------------------
    if url:
        video_id = extract_video_id(url)

        if not video_id:
            st.error("❌ 올바른 유튜브 URL을 입력해주세요.")
            st.info("예시: https://www.youtube.com/watch?v=dQw4w9WgXcQ")
            return

        # 영상 정보 표시
        with st.spinner("영상 정보를 불러오는 중..."):
            video_info = get_video_info(youtube, video_id)

        if video_info:
            st.markdown("---")

            col_thumb, col_info = st.columns([1, 2])

            with col_thumb:
                if video_info["thumbnail"]:
                    st.image(video_info["thumbnail"], use_container_width=True)

            with col_info:
                st.subheader(video_info["title"])
                st.write(f"📢 **채널:** {video_info['channel']}")
                st.write(f"📅 **게시일:** {video_info['published']}")

                stat_cols = st.columns(3)
                with stat_cols[0]:
                    st.metric("👀 조회수", f"{video_info['views']:,}")
                with stat_cols[1]:
                    st.metric("👍 좋아요", f"{video_info['likes']:,}")
                with stat_cols[2]:
                    st.metric("💬 댓글 수", f"{video_info['comment_count']:,}")

        # 댓글 수집 버튼
        st.markdown("---")

        if st.button("💬 댓글 수집 시작", type="primary", use_container_width=True):

            with st.spinner(f"댓글을 수집하는 중... (최대 {max_comments}개)"):
                comments = get_comments(youtube, video_id, max_comments, order)

            if comments:
                st.success(f"✅ 총 {len(comments)}개의 댓글을 수집했습니다!")

                df = pd.DataFrame(comments)

                # 세션에 저장
                st.session_state["comments_df"] = df
                st.session_state["video_title"] = video_info["title"] if video_info else "youtube_comments"
            else:
                st.warning("수집된 댓글이 없습니다.")

    # --------------------------------------------------------
    # 결과 표시 (세션에 데이터가 있을 때)
    # --------------------------------------------------------
    if "comments_df" in st.session_state:
        df = st.session_state["comments_df"]
        video_title = st.session_state.get("video_title", "youtube_comments")

        st.markdown("---")
        st.subheader("📊 수집 결과")

        # 탭 구성
        tab_table, tab_cards, tab_stats = st.tabs(["📋 표 보기", "💬 카드 보기", "📈 통계"])

        # --- 표 보기 ---
        with tab_table:
            # 검색 필터
            search = st.text_input("🔍 댓글 내 키워드 검색", placeholder="검색어를 입력하세요...")
            if search:
                filtered_df = df[df["댓글"].str.contains(search, case=False, na=False)]
                st.write(f"**'{search}'** 검색 결과: {len(filtered_df)}개")
            else:
                filtered_df = df

            st.dataframe(
                filtered_df,
                use_container_width=True,
                height=400,
                column_config={
                    "좋아요": st.column_config.NumberColumn("👍 좋아요", format="%d"),
                    "답글수": st.column_config.NumberColumn("💬 답글", format="%d"),
                }
            )

        # --- 카드 보기 ---
        with tab_cards:
            display_count = st.slider("표시할 댓글 수", 5, min(50, len(df)), 10, key="card_slider")

            for idx, row in df.head(display_count).iterrows():
                st.markdown(f"""
                <div class="comment-box">
                    <span class="comment-author">{row['작성자']}</span>
                    <span class="comment-date"> · {row['작성일']}</span>
                    <div class="comment-text">{row['댓글']}</div>
                    <div class="comment-likes">👍 {row['좋아요']}  ·  💬 답글 {row['답글수']}개</div>
                </div>
                """, unsafe_allow_html=True)

        # --- 통계 ---
        with tab_stats:
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("수집된 댓글 수", f"{len(df)}개")
            with col2:
                st.metric("평균 좋아요", f"{df['좋아요'].mean():.1f}개")
            with col3:
                st.metric("총 답글 수", f"{df['답글수'].sum()}개")

            st.markdown("#### 🏆 좋아요 TOP 10 댓글")
            top10 = df.nlargest(10, "좋아요")[["작성자", "댓글", "좋아요", "작성일"]].reset_index(drop=True)
            top10.index = top10.index + 1
            st.dataframe(top10, use_container_width=True)

            # 댓글 길이 분포
            st.markdown("#### 📏 댓글 길이 분포")
            df_temp = df.copy()
            df_temp["댓글길이"] = df_temp["댓글"].str.len()
            st.bar_chart(df_temp["댓글길이"].value_counts().sort_index().head(50))

        # --- CSV 다운로드 ---
        st.markdown("---")

        safe_title = re.sub(r'[^\w가-힣]', '_', video_title)[:30]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_title}_댓글_{timestamp}.csv"

        csv_data = df.to_csv(index=False, encoding="utf-8-sig")

        st.download_button(
            label="📥 CSV 파일 다운로드",
            data=csv_data,
            file_name=filename,
            mime="text/csv",
            use_container_width=True
        )

# ============================================================
# 실행
# ============================================================
if __name__ == "__main__":
    main()
