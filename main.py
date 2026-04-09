import streamlit as st
import pandas as pd
import plotly.express as px
from googleapiclient.discovery import build
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import re
import io
import os
from datetime import datetime
from collections import Counter

# ============================================================
# 페이지 설정
# ============================================================
st.set_page_config(page_title="유튜브 댓글 분석기 Pro", page_icon="📺", layout="wide")

# ============================================================
# CSS
# ============================================================
st.markdown("""
<style>
.main-title{font-size:2.5rem;font-weight:900;background:linear-gradient(135deg,#FF0000,#ff6b6b);
-webkit-background-clip:text;-webkit-text-fill-color:transparent;text-align:center;margin-bottom:0}
.sub-title{text-align:center;color:#888;font-size:1rem;margin-bottom:2rem}
.mc{padding:18px;border-radius:14px;color:#fff;text-align:center}
.mc-purple{background:linear-gradient(135deg,#667eea,#764ba2)}
.mc-green{background:linear-gradient(135deg,#11998e,#38ef7d)}
.mc-red{background:linear-gradient(135deg,#f93d66,#ff6b6b)}
.mc-orange{background:linear-gradient(135deg,#f7971e,#ffd200)}
.mc .num{font-size:2rem;font-weight:900;margin:4px 0}
.mc .lab{font-size:.85rem;opacity:.9}
.cc{background:#fff;border:1px solid #eee;border-left:5px solid #FF0000;
padding:14px 18px;margin-bottom:10px;border-radius:8px}
.cc.pos{border-left-color:#38ef7d}.cc.neg{border-left-color:#f93d66}.cc.neu{border-left-color:#ffd200}
.cc .au{font-weight:700;color:#333}.cc .mt{color:#aaa;font-size:.8rem}
.cc .bd{color:#444;margin-top:6px;line-height:1.6}
.bp{background:#d4edda;color:#155724;padding:2px 8px;border-radius:10px;font-size:.75rem}
.bn{background:#f8d7da;color:#721c24;padding:2px 8px;border-radius:10px;font-size:.75rem}
.bnu{background:#fff3cd;color:#856404;padding:2px 8px;border-radius:10px;font-size:.75rem}
</style>
""", unsafe_allow_html=True)

# ============================================================
# 상수
# ============================================================
STOPWORDS = set("이 그 저 것 수 등 때 중 더 안 좀 잘 또 및 를 을 에 의 가 는 은 로 으로 와 과 도 에서 "
"까지 부터 한 하는 있는 없는 하다 있다 없다 되다 이다 아니다 같다 보다 나 너 우리 그것 이것 저것 "
"여기 거기 저기 어디 언제 무엇 어떻게 왜 누구 뭐 진짜 정말 너무 되게 완전 약간 다 못 많이 조금 "
"매우 아주 제일 가장 정도 거의 다시 이미 아직 바로 그냥 그래서 그러나 하지만 그런데 그리고 또한 "
"때문에 위해 대해 통해 함께 ㅋㅋ ㅋㅋㅋ ㅋㅋㅋㅋ ㅎㅎ ㅎㅎㅎ ㅠㅠ ㅜㅜ ㅠ ㅜ ㄷㄷ ㅇㅇ "
"the a an is are was were be been am do does did have has had will would could should may "
"might shall can to of in for on with at by from it this that not but and or so if as no "
"yes my your his her its our me him them what which who when where how why all".split())

POS_WORDS = set("좋아 좋다 최고 대박 굿 짱 감동 행복 사랑 멋지 멋있 훌륭 완벽 감사 추천 재밌 재미있 "
"웃기 귀여 예쁘 아름답 힐링 응원 축하 기대 신나 즐거 좋겠 최애 인정 레전드 존경 천재 "
"love good great best amazing awesome nice beautiful wonderful perfect excellent fantastic "
"cool funny happy like thank wow legend brilliant incredible 👍 🔥 💯 ⭐ 🎉 👏 😂 🤣 ✨ 💪 😊".split())

NEG_WORDS = set("싫어 싫다 별로 최악 쓰레기 짜증 화나 실망 후회 지루 지겨 노잼 구리 구려 못생 슬프 "
"울다 아프 힘들 어렵 무섭 그만 삭제 나가 못하 안되 아쉽 불만 불편 역겹 "
"hate bad worst terrible awful boring ugly stupid trash garbage suck dislike annoying "
"disappointed waste horrible disgusting 😡 🤬 👎 😤 😢 😭 💔 🤮 😠".split())


# ============================================================
# 핵심 함수들
# ============================================================
def extract_video_id(url):
    for p in [r'(?:youtube\.com\/watch\?v=)([a-zA-Z0-9_-]{11})',
              r'(?:youtu\.be\/)([a-zA-Z0-9_-]{11})',
              r'(?:youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
              r'(?:youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})']:
        m = re.search(p, url)
        if m:
            return m.group(1)
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url.strip()):
        return url.strip()
    return None


def get_video_info(yt, vid):
    try:
        r = yt.videos().list(part="snippet,statistics", id=vid).execute()
        if r["items"]:
            s, t = r["items"][0]["snippet"], r["items"][0]["statistics"]
            return {"title": s.get("title",""), "channel": s.get("channelTitle",""),
                    "published": s.get("publishedAt","")[:10],
                    "views": int(t.get("viewCount",0)), "likes": int(t.get("likeCount",0)),
                    "comment_count": int(t.get("commentCount",0)),
                    "thumbnail": s.get("thumbnails",{}).get("high",{}).get("url","")}
    except Exception as e:
        st.error(f"영상 정보 오류: {e}")
    return None


def get_comments(yt, vid, max_n=200, order="relevance", replies=False):
    comments, npt = [], None
    try:
        while len(comments) < max_n:
            part = "snippet,replies" if replies else "snippet"
            r = yt.commentThreads().list(part=part, videoId=vid,
                maxResults=min(100, max_n-len(comments)), order=order,
                pageToken=npt, textFormat="plainText").execute()
            for item in r.get("items", []):
                sn = item["snippet"]["topLevelComment"]["snippet"]
                comments.append({"작성자": sn.get("authorDisplayName",""),
                    "댓글": sn.get("textDisplay",""), "좋아요": sn.get("likeCount",0),
                    "작성일시": sn.get("publishedAt",""),
                    "답글수": item["snippet"].get("totalReplyCount",0), "유형": "댓글"})
                if replies and "replies" in item:
                    for rp in item["replies"]["comments"]:
                        rs = rp["snippet"]
                        comments.append({"작성자": rs.get("authorDisplayName",""),
                            "댓글": rs.get("textDisplay",""), "좋아요": rs.get("likeCount",0),
                            "작성일시": rs.get("publishedAt",""), "답글수": 0, "유형": "답글"})
            npt = r.get("nextPageToken")
            if not npt:
                break
    except Exception as e:
        if "commentsDisabled" in str(e):
            st.error("🚫 댓글이 비활성화된 영상입니다.")
        else:
            st.error(f"댓글 수집 오류: {e}")
    return comments


def sentiment(text):
    tl = text.lower()
    s = sum(1 for w in POS_WORDS if w in tl) - sum(1 for w in NEG_WORDS if w in tl)
    if s > 0: return "긍정", s
    elif s < 0: return "부정", s
    return "중립", 0


def get_keywords(texts, n=30):
    words = []
    for t in texts:
        for w in re.findall(r'[가-힣]{2,}|[a-zA-Z]{2,}', t):
            wl = w.lower()
            if wl not in STOPWORDS and len(wl) >= 2:
                words.append(wl)
    return Counter(words).most_common(n)


def make_wordcloud(freq):
    if not freq:
        return None
    fp = None
    for f in ["/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
              "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf"]:
        if os.path.exists(f):
            fp = f
            break
    kw = {"width": 800, "height": 400, "background_color": "white",
          "colormap": "Set2", "max_words": 80, "max_font_size": 120}
    if fp:
        kw["font_path"] = fp
    wc = WordCloud(**kw).generate_from_frequencies(freq)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    plt.tight_layout(pad=0)
    return fig


def build_df(raw):
    df = pd.DataFrame(raw)
    res = df["댓글"].apply(sentiment)
    df["감성"] = res.apply(lambda x: x[0])
    df["감성점수"] = res.apply(lambda x: x[1])
    df["작성일"] = pd.to_datetime(df["작성일시"]).dt.date
    df["작성시간"] = pd.to_datetime(df["작성일시"]).dt.hour
    df["댓글길이"] = df["댓글"].str.len()
    return df


# ============================================================
# 분석 결과 표시
# ============================================================
def show_results(df, info, prefix="A"):
    pc = len(df[df["감성"]=="긍정"])
    nc = len(df[df["감성"]=="부정"])
    uc = len(df[df["감성"]=="중립"])
    total = len(df)

    c1,c2,c3,c4 = st.columns(4)
    with c1: st.markdown(f'<div class="mc mc-purple"><div class="lab">총 댓글</div><div class="num">{total}</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="mc mc-green"><div class="lab">😊 긍정</div><div class="num">{pc}</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="mc mc-red"><div class="lab">😠 부정</div><div class="num">{nc}</div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="mc mc-orange"><div class="lab">😐 중립</div><div class="num">{uc}</div></div>', unsafe_allow_html=True)
    st.write("")

    t1,t2,t3,t4,t5,t6,t7 = st.tabs(["📊 대시보드","🎭 감성분석","☁️ 워드클라우드","📈 트렌드","🏷️ 키워드","💬 댓글보기","📥 다운로드"])

    # ---- 대시보드 ----
    with t1:
        a1,a2 = st.columns(2)
        with a1:
            fig = px.pie(names=["긍정","부정","중립"], values=[pc,nc,uc],
                         color_discrete_sequence=["#38ef7d","#f93d66","#ffd200"],
                         title="감성 분포", hole=0.45)
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)
        with a2:
            fig = px.histogram(df, x="좋아요", nbins=30, title="좋아요 수 분포",
                               color_discrete_sequence=["#667eea"])
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)
        b1,b2 = st.columns(2)
        with b1:
            fig = px.histogram(df, x="댓글길이", nbins=30, title="댓글 길이 분포",
                               color_discrete_sequence=["#764ba2"])
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)
        with b2:
            hd = df.groupby("작성시간").size().reset_index(name="댓글수")
            fig = px.bar(hd, x="작성시간", y="댓글수", title="시간대별 댓글 수",
                         color_discrete_sequence=["#11998e"])
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)

    # ---- 감성분석 ----
    with t2:
        st.subheader("🎭 감성 분석 결과")
        if total > 0:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"- 😊 **긍정**: {pc}개 ({pc/total*100:.1f}%)")
                st.markdown(f"- 😠 **부정**: {nc}개 ({nc/total*100:.1f}%)")
                st.markdown(f"- 😐 **중립**: {uc}개 ({uc/total*100:.1f}%)")
            with col2:
                sl = df.groupby("감성")["좋아요"].mean().reset_index()
                sl.columns = ["감성","평균좋아요"]
                fig = px.bar(sl, x="감성", y="평균좋아요", color="감성",
                             color_discrete_map={"긍정":"#38ef7d","부정":"#f93d66","중립":"#ffd200"},
                             title="감성별 평균 좋아요")
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True)

        for s_name in ["긍정","부정","중립"]:
            sub = df[df["감성"]==s_name].nlargest(3,"좋아요")
            if len(sub) > 0:
                em = {"긍정":"😊","부정":"😠","중립":"😐"}[s_name]
                st.markdown(f"#### {em} {s_name} 대표 댓글 TOP 3")
                for _,row in sub.iterrows():
                    st.markdown(f"> **{row['작성자']}** (👍 {row['좋아요']}): {row['댓글'][:200]}")

    # ---- 워드클라우드 ----
    with t3:
        st.subheader("☁️ 전체 워드클라우드")
        kw = dict(get_keywords(df["댓글"].tolist(), 80))
        if kw:
            fig = make_wordcloud(kw)
            if fig:
                st.pyplot(fig)
                plt.close(fig)
        else:
            st.info("키워드가 부족합니다.")

        st.markdown("---")
        w1,w2 = st.columns(2)
        with w1:
            pt = df[df["감성"]=="긍정"]["댓글"].tolist()
            if pt:
                pk = dict(get_keywords(pt, 50))
                if pk:
                    st.markdown("#### 😊 긍정 워드클라우드")
                    fig = make_wordcloud(pk)
                    if fig:
                        st.pyplot(fig)
                        plt.close(fig)
        with w2:
            nt2 = df[df["감성"]=="부정"]["댓글"].tolist()
            if nt2:
                nk = dict(get_keywords(nt2, 50))
                if nk:
                    st.markdown("#### 😠 부정 워드클라우드")
                    fig = make_wordcloud(nk)
                    if fig:
                        st.pyplot(fig)
                        plt.close(fig)

    # ---- 트렌드 ----
    with t4:
        st.subheader("📈 댓글 트렌드")
        dy = df.groupby("작성일").size().reset_index(name="댓글수")
        dy["작성일"] = pd.to_datetime(dy["작성일"])
        fig = px.line(dy, x="작성일", y="댓글수", title="일별 댓글 수", markers=True,
                      color_discrete_sequence=["#667eea"])
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

        ds = df.groupby(["작성일","감성"]).size().reset_index(name="댓글수")
        ds["작성일"] = pd.to_datetime(ds["작성일"])
        fig = px.line(ds, x="작성일", y="댓글수", color="감성", title="일별 감성 트렌드",
                      color_discrete_map={"긍정":"#38ef7d","부정":"#f93d66","중립":"#ffd200"}, markers=True)
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    # ---- 키워드 ----
    with t5:
        st.subheader("🏷️ 핵심 키워드 TOP 20")
        tk = get_keywords(df["댓글"].tolist(), 20)
        if tk:
            kdf = pd.DataFrame(tk, columns=["키워드","빈도"])
            fig = px.bar(kdf, x="빈도", y="키워드", orientation="h", title="키워드 빈도",
                         color="빈도", color_continuous_scale="Viridis")
            fig.update_layout(height=600, yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(kdf, use_container_width=True)

    # ---- 댓글 보기 ----
    with t6:
        st.subheader("💬 댓글 목록")
        fc1,fc2 = st.columns([2,1])
        with fc1:
            search = st.text_input("🔍 검색", key=f"s_{prefix}")
        with fc2:
            filt = st.selectbox("감성 필터", ["전체","긍정","부정","중립"], key=f"f_{prefix}")

        fd = df.copy()
        if search:
            fd = fd[fd["댓글"].str.contains(search, case=False, na=False)]
        if filt != "전체":
            fd = fd[fd["감성"]==filt]

        st.write(f"**{len(fd)}개 댓글**")
        show_df = fd[["작성자","댓글","좋아요","감성","작성일","유형"]].reset_index(drop=True)
        show_df.index += 1
        st.dataframe(show_df, use_container_width=True, height=400)

        st.markdown("---")
        if len(fd) > 0:
            n = st.slider("카드 수", 3, min(30,len(fd)), min(10,len(fd)), key=f"sl_{prefix}")
            for _,row in fd.head(n).iterrows():
                cls = {"긍정":"pos","부정":"neg","중립":"neu"}.get(row["감성"],"neu")
                bcls = {"긍정":"bp","부정":"bn","중립":"bnu"}.get(row["감성"],"bnu")
                em = {"긍정":"😊","부정":"😠","중립":"😐"}.get(row["감성"],"")
                st.markdown(f"""<div class="cc {cls}">
                    <span class="au">{row['작성자']}</span>
                    <span class="mt"> · {row['작성일']} · 👍 {row['좋아요']}</span>
                    <span class="{bcls}">{em} {row['감성']}</span>
                    <div class="bd">{row['댓글']}</div></div>""", unsafe_allow_html=True)

    # ---- 다운로드 ----
    with t7:
        st.subheader("📥 다운로드")
        ts = re.sub(r'[^\w가-힣]','_', info.get("title","yt"))[:30]
        now = datetime.now().strftime("%Y%m%d_%H%M%S")

        d1,d2 = st.columns(2)
        with d1:
            csv = df.to_csv(index=False, encoding="utf-8-sig")
            st.download_button("📄 CSV 다운로드", csv, f"{ts}_{now}.csv", "text/csv", use_container_width=True)
        with d2:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as w:
                df.to_excel(w, index=False, sheet_name="댓글")
            st.download_button("📊 Excel 다운로드", buf.getvalue(), f"{ts}_{now}.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               use_container_width=True)


# ============================================================
# 메인 함수
# ============================================================
def main():
    st.markdown('<div class="main-title">📺 유튜브 댓글 분석기 Pro</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">감성분석 · 워드클라우드 · 트렌드 · 키워드 추출 · 영상 비교</div>', unsafe_allow_html=True)

    # API 키
    api_key = None
    try:
        api_key = st.secrets["YOUTUBE_API_KEY"]
    except Exception:
        pass

    if not api_key:
        st.warning("⚠️ YouTube API 키가 필요합니다.")
        st.info("Streamlit Cloud: **Settings → Secrets** 에 `YOUTUBE_API_KEY = \"키값\"` 입력")
        api_key = st.text_input("🔑 API 키 직접 입력:", type="password")
        if not api_key:
            return

    try:
        youtube = build("youtube", "v3", developerKey=api_key)
    except Exception as e:
        st.error(f"API 연결 실패: {e}")
        return

    # 사이드바
    with st.sidebar:
        st.header("⚙️ 설정")
        mode = st.radio("🎯 모드", ["단일 영상 분석", "영상 비교 분석"])
        st.markdown("---")
        max_n = st.slider("📝 최대 댓글 수", 10, 500, 150, 10)
        order = st.radio("정렬", ["relevance","time"],
                         format_func=lambda x: "🔥 인기순" if x=="relevance" else "🕐 최신순")
        replies = st.checkbox("💬 답글도 수집", False)
        st.markdown("---")
        st.markdown("**💡 기능:** 감성분석, 워드클라우드, 트렌드, 키워드, 비교분석, CSV/Excel 다운로드")

    # ==== 단일 영상 ====
    if mode == "단일 영상 분석":
        url = st.text_input("🔗 유튜브 URL 입력", placeholder="https://www.youtube.com/watch?v=...")

        if url:
            vid = extract_video_id(url)
            if not vid:
                st.error("❌ 올바른 URL을 입력해주세요.")
                return

            with st.spinner("영상 정보 로딩..."):
                info = get_video_info(youtube, vid)

            if info:
                ic1, ic2 = st.columns([1,2])
                with ic1:
                    if info["thumbnail"]:
                        st.image(info["thumbnail"], use_container_width=True)
                with ic2:
                    st.markdown(f"### {info['title']}")
                    st.write(f"📢 {info['channel']}  ·  📅 {info['published']}")
                    m1,m2,m3 = st.columns(3)
                    m1.metric("👀 조회수", f"{info['views']:,}")
                    m2.metric("👍 좋아요", f"{info['likes']:,}")
                    m3.metric("💬 댓글", f"{info['comment_count']:,}")

                st.markdown("---")

                if st.button("🚀 댓글 수집 & 분석 시작", type="primary", use_container_width=True):
                    with st.spinner("댓글 수집 중..."):
                        raw = get_comments(youtube, vid, max_n, order, replies)
                    if raw:
                        df = build_df(raw)
                        st.session_state["df_single"] = df
                        st.session_state["info_single"] = info
                        st.success(f"✅ {len(df)}개 댓글 수집 완료!")

            if "df_single" in st.session_state:
                st.markdown("---")
                show_results(st.session_state["df_single"], st.session_state["info_single"], "single")

    # ==== 영상 비교 ====
    elif mode == "영상 비교 분석":
        st.subheader("🔗 비교할 영상 2개 입력")
        uc1, uc2 = st.columns(2)
        with uc1:
            url_a = st.text_input("영상 A URL", placeholder="https://www.youtube.com/watch?v=...", key="url_a")
        with uc2:
            url_b = st.text_input("영상 B URL", placeholder="https://www.youtube.com/watch?v=...", key="url_b")

        if url_a and url_b:
            vid_a = extract_video_id(url_a)
            vid_b = extract_video_id(url_b)
            if not vid_a or not vid_b:
                st.error("❌ 올바른 URL을 입력해주세요.")
                return

            if st.button("🚀 비교 분석 시작", type="primary", use_container_width=True):
                # 영상 A
                with st.spinner("영상 A 수집 중..."):
                    info_a = get_video_info(youtube, vid_a)
                    raw_a = get_comments(youtube, vid_a, max_n, order, replies)
                # 영상 B
                with st.spinner("영상 B 수집 중..."):
                    info_b = get_video_info(youtube, vid_b)
                    raw_b = get_comments(youtube, vid_b, max_n, order, replies)

                if raw_a and raw_b and info_a and info_b:
                    df_a = build_df(raw_a)
                    df_b = build_df(raw_b)
                    st.session_state["cmp"] = {
                        "df_a": df_a, "df_b": df_b,
                        "info_a": info_a, "info_b": info_b
                    }
                    st.success("✅ 비교 분석 준비 완료!")

            if "cmp" in st.session_state:
                cmp = st.session_state["cmp"]
                df_a, df_b = cmp["df_a"], cmp["df_
