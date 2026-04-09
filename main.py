import streamlit as st
import pandas as pd
import plotly.express as px
from googleapiclient.discovery import build
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import re, io, os
from datetime import datetime
from collections import Counter

st.set_page_config(page_title="유튜브 댓글 분석기", page_icon="📺", layout="wide")

# ======================== CSS ========================
st.markdown("""
<style>
.title{font-size:2.5rem;font-weight:900;background:linear-gradient(135deg,#FF0000,#ff6b6b);
-webkit-background-clip:text;-webkit-text-fill-color:transparent;text-align:center}
.sub{text-align:center;color:#888;margin-bottom:2rem}
.card{padding:18px;border-radius:14px;color:#fff;text-align:center}
.c1{background:linear-gradient(135deg,#667eea,#764ba2)}
.c2{background:linear-gradient(135deg,#11998e,#38ef7d)}
.c3{background:linear-gradient(135deg,#f93d66,#ff6b6b)}
.c4{background:linear-gradient(135deg,#f7971e,#ffd200)}
.card .n{font-size:2rem;font-weight:900}.card .l{font-size:.85rem;opacity:.9}
.cmt{background:#fff;border:1px solid #eee;border-left:5px solid #ccc;
padding:14px 18px;margin-bottom:10px;border-radius:8px}
.cmt.pos{border-left-color:#38ef7d}
.cmt.neg{border-left-color:#f93d66}
.cmt.neu{border-left-color:#ffd200}
</style>
""", unsafe_allow_html=True)

# ======================== 상수 ========================
STOP = set("이 그 저 것 수 등 때 중 더 안 좀 잘 또 및 를 을 에 의 가 는 은 로 으로 와 과 도 에서 까지 부터 한 하는 있는 없는 하다 있다 없다 되다 이다 아니다 같다 보다 나 너 우리 그것 이것 저것 여기 거기 어디 언제 무엇 어떻게 왜 누구 뭐 진짜 정말 너무 되게 완전 약간 다 못 많이 조금 매우 아주 제일 가장 정도 거의 다시 이미 아직 바로 그냥 그래서 그러나 하지만 그런데 그리고 또한 때문에 위해 대해 통해 함께 ㅋㅋ ㅋㅋㅋ ㅋㅋㅋㅋ ㅎㅎ ㅎㅎㅎ ㅠㅠ ㅜㅜ the a an is are was were be been do does did have has had will would could should to of in for on with at by from it this that not but and or so if as no yes my your his her its our me him them what which who when where how why all".split())
POS = set("좋아 좋다 최고 대박 굿 짱 감동 행복 사랑 멋지 멋있 훌륭 완벽 감사 추천 재밌 재미있 웃기 귀여 예쁘 아름답 힐링 응원 축하 기대 신나 즐거 좋겠 최애 인정 레전드 존경 천재 love good great best amazing awesome nice beautiful wonderful perfect excellent cool funny happy thank wow legend".split())
NEG = set("싫어 싫다 별로 최악 쓰레기 짜증 화나 실망 후회 지루 지겨 노잼 구리 구려 못생 슬프 아프 힘들 어렵 무섭 그만 삭제 못하 안되 아쉽 불만 불편 역겹 hate bad worst terrible awful boring ugly stupid trash garbage suck dislike annoying disappointed waste horrible disgusting".split())

# ======================== 함수 ========================
def vid_id(url):
    for p in [r'youtube\.com\/watch\?v=([a-zA-Z0-9_-]{11})',
              r'youtu\.be\/([a-zA-Z0-9_-]{11})',
              r'youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})',
              r'youtube\.com\/embed\/([a-zA-Z0-9_-]{11})']:
        m = re.search(p, url)
        if m: return m.group(1)
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url.strip()): return url.strip()
    return None

def vid_info(yt, v):
    try:
        r = yt.videos().list(part="snippet,statistics", id=v).execute()
        if r["items"]:
            s = r["items"][0]["snippet"]; t = r["items"][0]["statistics"]
            return {"title":s.get("title",""),"channel":s.get("channelTitle",""),
                    "published":s.get("publishedAt","")[:10],
                    "views":int(t.get("viewCount",0)),"likes":int(t.get("likeCount",0)),
                    "comments":int(t.get("commentCount",0)),
                    "thumb":s.get("thumbnails",{}).get("high",{}).get("url","")}
    except Exception as e: st.error(f"영상 정보 오류: {e}")
    return None

def fetch(yt, v, mx=200, od="relevance", rp=False):
    out, npt = [], None
    try:
        while len(out) < mx:
            pt = "snippet,replies" if rp else "snippet"
            r = yt.commentThreads().list(part=pt, videoId=v,
                maxResults=min(100,mx-len(out)), order=od, pageToken=npt, textFormat="plainText").execute()
            for i in r.get("items",[]):
                sn = i["snippet"]["topLevelComment"]["snippet"]
                out.append({"작성자":sn.get("authorDisplayName",""),"댓글":sn.get("textDisplay",""),
                    "좋아요":sn.get("likeCount",0),"작성일시":sn.get("publishedAt",""),
                    "답글수":i["snippet"].get("totalReplyCount",0),"유형":"댓글"})
                if rp and "replies" in i:
                    for rr in i["replies"]["comments"]:
                        rs = rr["snippet"]
                        out.append({"작성자":rs.get("authorDisplayName",""),"댓글":rs.get("textDisplay",""),
                            "좋아요":rs.get("likeCount",0),"작성일시":rs.get("publishedAt",""),
                            "답글수":0,"유형":"답글"})
            npt = r.get("nextPageToken")
            if not npt: break
    except Exception as e:
        if "commentsDisabled" in str(e): st.error("🚫 댓글 비활성화 영상")
        else: st.error(f"수집 오류: {e}")
    return out

def sent(t):
    tl = t.lower()
    s = sum(1 for w in POS if w in tl) - sum(1 for w in NEG if w in tl)
    return ("긍정",s) if s>0 else ("부정",s) if s<0 else ("중립",0)

def kw(texts, n=30):
    ws = []
    for t in texts:
        for w in re.findall(r'[가-힣]{2,}|[a-zA-Z]{2,}', t):
            wl = w.lower()
            if wl not in STOP and len(wl)>=2: ws.append(wl)
    return Counter(ws).most_common(n)

def mkwc(freq):
    if not freq: return None
    fp = None
    for f in ["/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
              "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf"]:
        if os.path.exists(f): fp=f; break
    p = {"width":800,"height":400,"background_color":"white","colormap":"Set2","max_words":80}
    if fp: p["font_path"]=fp
    wc = WordCloud(**p).generate_from_frequencies(freq)
    fig,ax = plt.subplots(figsize=(10,5))
    ax.imshow(wc, interpolation="bilinear"); ax.axis("off"); plt.tight_layout(pad=0)
    return fig

def mkdf(raw):
    df = pd.DataFrame(raw)
    r = df["댓글"].apply(sent)
    df["감성"]=r.apply(lambda x:x[0]); df["감성점수"]=r.apply(lambda x:x[1])
    df["작성일"]=pd.to_datetime(df["작성일시"]).dt.date
    df["작성시간"]=pd.to_datetime(df["작성일시"]).dt.hour
    df["댓글길이"]=df["댓글"].str.len()
    return df

# ======================== 메인 ========================
def main():
    st.markdown('<div class="title">📺 유튜브 댓글 분석기 Pro</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub">감성분석 · 워드클라우드 · 트렌드 · 키워드추출 · CSV/Excel 다운로드</div>', unsafe_allow_html=True)

    api_key = None
    try: api_key = st.secrets["YOUTUBE_API_KEY"]
    except: pass
    if not api_key:
        st.warning("⚠️ YouTube API 키가 필요합니다.")
        api_key = st.text_input("🔑 API 키 입력:", type="password")
        if not api_key: return

    try: youtube = build("youtube","v3",developerKey=api_key)
    except Exception as e: st.error(f"API 연결 실패: {e}"); return

    with st.sidebar:
        st.header("⚙️ 설정")
        mx = st.slider("최대 댓글 수", 10, 500, 150, 10)
        od = st.radio("정렬", ["relevance","time"], format_func=lambda x:"🔥 인기순" if x=="relevance" else "🕐 최신순")
        rp = st.checkbox("💬 답글도 수집", False)

    url = st.text_input("🔗 유튜브 URL", placeholder="https://www.youtube.com/watch?v=...")
    if not url: return

    v = vid_id(url)
    if not v: st.error("❌ 올바른 URL을 입력해주세요."); return

    with st.spinner("영상 정보 로딩..."): info = vid_info(youtube, v)
    if not info: return

    ic1, ic2 = st.columns([1,2])
    with ic1:
        if info["thumb"]: st.image(info["thumb"], use_container_width=True)
    with ic2:
        st.markdown(f"### {info['title']}")
        st.write(f"📢 {info['channel']}  ·  📅 {info['published']}")
        m1,m2,m3 = st.columns(3)
        m1.metric("👀 조회수", f"{info['views']:,}")
        m2.metric("👍 좋아요", f"{info['likes']:,}")
        m3.metric("💬 댓글", f"{info['comments']:,}")

    st.markdown("---")
    if st.button("🚀 댓글 수집 & 분석", type="primary", use_container_width=True):
        with st.spinner("수집 중..."):
            raw = fetch(youtube, v, mx, od, rp)
        if raw:
            st.session_state["df"] = mkdf(raw)
            st.session_state["info"] = info
            st.success(f"✅ {len(st.session_state['df'])}개 댓글 수집 완료!")

    if "df" not in st.session_state: return
    df = st.session_state["df"]; info = st.session_state["info"]

    pc=len(df[df["감성"]=="긍정"]); nc=len(df[df["감성"]=="부정"]); uc=len(df[df["감성"]=="중립"]); tt=len(df)

    st.markdown("---")
    c1,c2,c3,c4 = st.columns(4)
    with c1: st.markdown(f'<div class="card c1"><div class="l">총 댓글</div><div class="n">{tt}</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="card c2"><div class="l">😊 긍정</div><div class="n">{pc}</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="card c3"><div class="l">😠 부정</div><div class="n">{nc}</div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="card c4"><div class="l">😐 중립</div><div class="n">{uc}</div></div>', unsafe_allow_html=True)
    st.write("")

    t1,t2,t3,t4,t5,t6,t7 = st.tabs(["📊 대시보드","🎭 감성분석","☁️ 워드클라우드","📈 트렌드","🏷️ 키워드","💬 댓글보기","📥 다운로드"])

    with t1:
        a1,a2 = st.columns(2)
        with a1:
            fig=px.pie(names=["긍정","부정","중립"],values=[pc,nc,uc],color_discrete_sequence=["#38ef7d","#f93d66","#ffd200"],title="감성 분포",hole=0.45)
            fig.update_layout(height=350); st.plotly_chart(fig, use_container_width=True)
        with a2:
            fig=px.histogram(df,x="좋아요",nbins=30,title="좋아요 분포",color_discrete_sequence=["#667eea"])
            fig.update_layout(height=350); st.plotly_chart(fig, use_container_width=True)
        b1,b2 = st.columns(2)
        with b1:
            fig=px.histogram(df,x="댓글길이",nbins=30,title="댓글 길이 분포",color_discrete_sequence=["#764ba2"])
            fig.update_layout(height=350); st.plotly_chart(fig, use_container_width=True)
        with b2:
            hd=df.groupby("작성시간").size().reset_index(name="수")
            fig=px.bar(hd,x="작성시간",y="수",title="시간대별 댓글",color_discrete_sequence=["#11998e"])
            fig.update_layout(height=350); st.plotly_chart(fig, use_container_width=True)

    with t2:
        st.subheader("🎭 감성 분석")
        if tt>0:
            st.markdown(f"- 😊 긍정: **{pc}개** ({pc/tt*100:.1f}%)")
            st.markdown(f"- 😠 부정: **{nc}개** ({nc/tt*100:.1f}%)")
            st.markdown(f"- 😐 중립: **{uc}개** ({uc/tt*100:.1f}%)")
        sl=df.groupby("감성")["좋아요"].mean().reset_index(); sl.columns=["감성","평균좋아요"]
        fig=px.bar(sl,x="감성",y="평균좋아요",color="감성",color_discrete_map={"긍정":"#38ef7d","부정":"#f93d66","중립":"#ffd200"},title="감성별 평균 좋아요")
        fig.update_layout(height=300); st.plotly_chart(fig, use_container_width=True)
        for sn in ["긍정","부정","중립"]:
            sub=df[df["감성"]==sn].nlargest(3,"좋아요")
            if len(sub)>0:
                em={"긍정":"😊","부정":"😠","중립":"😐"}[sn]
                st.markdown(f"#### {em} {sn} TOP 3")
                for _,row in sub.iterrows():
                    st.markdown(f"> **{row['작성자']}** (👍{row['좋아요']}): {row['댓글'][:200]}")

    with t3:
        st.subheader("☁️ 워드클라우드")
        kwdict=dict(kw(df["댓글"].tolist(),80))
        if kwdict:
            fig=mkwc(kwdict)
            if fig: st.pyplot(fig); plt.close(fig)
        w1,w2=st.columns(2)
        with w1:
            pt=df[df["감성"]=="긍정"]["댓글"].tolist()
            if pt:
                pk=dict(kw(pt,50))
                if pk:
                    st.markdown("#### 😊 긍정")
                    fig=mkwc(pk)
                    if fig: st.pyplot(fig); plt.close(fig)
        with w2:
            nt=df[df["감성"]=="부정"]["댓글"].tolist()
            if nt:
                nk=dict(kw(nt,50))
                if nk:
                    st.markdown("#### 😠 부정")
                    fig=mkwc(nk)
                    if fig: st.pyplot(fig); plt.close(fig)

    with t4:
        st.subheader("📈 트렌드")
        dy=df.groupby("작성일").size().reset_index(name="수"); dy["작성일"]=pd.to_datetime(dy["작성일"])
        fig=px.line(dy,x="작성일",y="수",title="일별 댓글 수",markers=True,color_discrete_sequence=["#667eea"])
        fig.update_layout(height=400); st.plotly_chart(fig, use_container_width=True)
        ds=df.groupby(["작성일","감성"]).size().reset_index(name="수"); ds["작성일"]=pd.to_datetime(ds["작성일"])
        fig=px.line(ds,x="작성일",y="수",color="감성",title="감성 트렌드",color_discrete_map={"긍정":"#38ef7d","부정":"#f93d66","중립":"#ffd200"},markers=True)
        fig.update_layout(height=400); st.plotly_chart(fig, use_container_width=True)

    with t5:
        st.subheader("🏷️ 키워드 TOP 20")
        tk=kw(df["댓글"].tolist(),20)
        if tk:
            kdf=pd.DataFrame(tk,columns=["키워드","빈도"])
            fig=px.bar(kdf,x="빈도",y="키워드",orientation="h",color="빈도",color_continuous_scale="Viridis",title="키워드 빈도")
            fig.update_layout(height=600,yaxis=dict(autorange="reversed")); st.plotly_chart(fig, use_container_width=True)

    with t6:
        st.subheader("💬 댓글 목록")
        f1,f2=st.columns([2,1])
        with f1: sq=st.text_input("🔍 검색",key="sq")
        with f2: sf=st.selectbox("감성",["전체","긍정","부정","중립"],key="sf")
        fd=df.copy()
        if sq: fd=fd[fd["댓글"].str.contains(sq,case=False,na=False)]
        if sf!="전체": fd=fd[fd["감성"]==sf]
        st.write(f"**{len(fd)}개**")
        st.dataframe(fd[["작성자","댓글","좋아요","감성","작성일","유형"]].reset_index(drop=True),use_container_width=True,height=400)
        if len(fd)>0:
            ns=st.slider("카드 수",3,min(30,len(fd)),min(10,len(fd)),key="ns")
            for _,row in fd.head(ns).iterrows():
                cls={"긍정":"pos","부정":"neg","중립":"neu"}.get(row["감성"],"neu")
                em={"긍정":"😊","부정":"😠","중립":"😐"}.get(row["감성"],"")
                st.markdown(f'<div class="cmt {cls}"><b>{row["작성자"]}</b> · {row["작성일"]} · 👍{row["좋아요"]} · {em}{row["감성"]}<br>{row["댓글"]}</div>', unsafe_allow_html=True)

    with t7:
        st.subheader("📥 다운로드")
        ts=re.sub(r'[^\w가-힣]','_',info.get("title","yt"))[:30]
        now=datetime.now().strftime("%Y%m%d_%H%M%S")
        d1,d2=st.columns(2)
        with d1:
            st.download_button("📄 CSV",df.to_csv(index=False,encoding="utf-8-sig"),f"{ts}_{now}.csv","text/csv",use_container_width=True)
        with d2:
            buf=io.BytesIO()
            with pd.ExcelWriter(buf,engine="openpyxl") as w:
                df.to_excel(w,index=False,sheet_name="댓글")
            st.download_button("📊 Excel",buf.getvalue(),f"{ts}_{now}.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True)

main()
