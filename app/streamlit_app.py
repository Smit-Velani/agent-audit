import io, time
import pandas as pd
import plotly.express as px
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Image as RLImage
from reportlab.lib.enums import TA_CENTER
import sys, os

# The golden set gives each task a rubric containing the true answer, so the
# judge can check correctness directly. Live chat has no ground truth -- the
# judge sees only the question and the answer, and cannot know whether
# "27.73" is right. Asking it to confirm correctness anyway makes it fail
# every correct answer, since it can never satisfy the rubric.
#
# So the live rubric grades what is actually checkable without the data:
# whether the answer is specific and tool-grounded rather than hedged or
# invented. Correctness is verified offline against the golden set instead.
GENERIC_RUBRIC = (
    "Judge whether the answer is a direct, specific response that reports "
    "concrete values rather than hedging, guessing, or refusing. Score 2 if "
    "it gives specific figures or a clear factual statement. Score 1 if it "
    "is vague, partial, or hedged. Score 0 only if it refuses, admits "
    "guessing, or is self-evidently fabricated. Do not penalise the answer "
    "for numbers you cannot independently verify -- you do not have access "
    "to the underlying dataset."
)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "agentaudit"))

st.set_page_config(page_title="AgentAudit · Scout", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
html,body,[class*="css"]{font-family:'Space Grotesk',sans-serif;}
.stApp{background:#e8eaf2;}
.hero{text-align:center;padding:44px 0 28px;}
.hero-badge{display:inline-block;background:#4c1d95;color:#e9d5ff;font-size:11px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;padding:4px 14px;border-radius:20px;margin-bottom:16px;font-family:'JetBrains Mono',monospace;}
.hero-title{font-size:52px;font-weight:700;color:#0f172a;letter-spacing:-.03em;line-height:1.1;margin:0 0 12px;}
.hero-title span{color:#7c3aed;}
.hero-sub{font-size:16px;color:#475569;max-width:460px;margin:0 auto;line-height:1.65;}
.card{background:#ffffff;border:2px solid #c4b5fd;border-radius:16px;padding:22px 26px;margin-bottom:14px;}
.card-scout-left{background:#1e1b4b;border:2px solid #4338ca;border-radius:16px;padding:22px 24px;}
.card-chat{background:#ffffff;border:2px solid #c4b5fd;border-radius:16px;padding:18px 20px;}
.eyebrow{font-size:10px;font-weight:700;letter-spacing:.15em;text-transform:uppercase;color:#7c3aed;font-family:'JetBrains Mono',monospace;margin-bottom:5px;}
.eyebrow-light{font-size:10px;font-weight:700;letter-spacing:.15em;text-transform:uppercase;color:#a78bfa;font-family:'JetBrains Mono',monospace;margin-bottom:5px;}
.card-title{font-size:17px;font-weight:700;color:#0f172a;margin:0 0 2px;}
.card-title-light{font-size:17px;font-weight:700;color:#f1f5f9;margin:0 0 2px;}
.card-sub{font-size:12px;color:#94a3b8;margin:0 0 14px;}
.card-sub-light{font-size:12px;color:#7c6fcd;margin:0 0 14px;}
.stat-row{display:flex;gap:10px;margin-bottom:14px;flex-wrap:wrap;}
.stat-box{flex:1;min-width:90px;background:#f5f3ff;border:2px solid #c4b5fd;border-radius:10px;padding:12px 10px;text-align:center;}
.stat-box-dark{flex:1;min-width:80px;background:#2d2a6e;border:1px solid #4338ca;border-radius:10px;padding:10px 10px;text-align:center;}
.stat-num{font-family:'JetBrains Mono',monospace;font-size:20px;font-weight:600;color:#7c3aed;line-height:1;margin-bottom:3px;}
.stat-num-light{font-family:'JetBrains Mono',monospace;font-size:18px;font-weight:600;color:#a78bfa;line-height:1;margin-bottom:3px;}
.stat-lbl{font-size:10px;color:#94a3b8;font-weight:500;letter-spacing:.05em;text-transform:uppercase;}
.stat-lbl-light{font-size:10px;color:#7c6fcd;font-weight:500;letter-spacing:.05em;text-transform:uppercase;}
.insight{background:#f5f3ff;border:2px solid #c4b5fd;border-radius:8px;padding:9px 14px;margin-bottom:6px;font-size:13px;color:#1e293b;line-height:1.5;display:flex;align-items:flex-start;gap:8px;}
.insight-num{font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;color:#7c3aed;margin-top:1px;flex-shrink:0;}
.chat-wrap{display:flex;flex-direction:column;gap:10px;height:380px;overflow-y:auto;padding:4px 2px;margin-bottom:12px;}
.msg-scout{display:flex;gap:8px;align-items:flex-start;max-width:90%;}
.msg-user{display:flex;gap:8px;align-items:flex-start;max-width:90%;align-self:flex-end;flex-direction:row-reverse;}
.avatar-scout{width:28px;height:28px;background:#7c3aed;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:13px;flex-shrink:0;border:2px solid #c4b5fd;}
.avatar-user{width:28px;height:28px;background:#1e1b4b;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:#e9d5ff;flex-shrink:0;}
.bubble-scout{background:#f5f3ff;border:1px solid #c4b5fd;border-radius:4px 14px 14px 14px;padding:9px 12px;font-size:13px;color:#1e293b;line-height:1.5;}
.bubble-user{background:#4c1d95;border:1px solid #7c3aed;border-radius:14px 4px 14px 14px;padding:9px 12px;font-size:13px;color:#f5f3ff;line-height:1.5;}
.bubble-meta{font-size:10px;color:#94a3b8;font-family:'JetBrains Mono',monospace;margin-top:4px;}
.bp{padding:2px 6px;border-radius:3px;font-size:9px;font-weight:700;font-family:'JetBrains Mono',monospace;margin-right:3px;}
.bp-pass{background:#f0fdf4;color:#16a34a;border:1px solid #bbf7d0;}
.bp-fail{background:#fef2f2;color:#dc2626;border:1px solid #fecaca;}
.bp-partial{background:#fffbeb;color:#d97706;border:1px solid #fde68a;}
.bp-blocked{background:#f5f3ff;color:#7c3aed;border:1px solid #ddd6fe;}
.scout-fab{position:fixed;bottom:28px;right:28px;z-index:9999;display:flex;flex-direction:column;align-items:center;gap:5px;}
.scout-fab-btn{width:56px;height:56px;background:#7c3aed;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:22px;box-shadow:0 4px 20px rgba(124,58,237,.5);animation:fabpulse 2s infinite;border:3px solid #c4b5fd;}
@keyframes fabpulse{0%{box-shadow:0 0 0 0 rgba(124,58,237,.6);}70%{box-shadow:0 0 0 16px rgba(124,58,237,0);}100%{box-shadow:0 0 0 0 rgba(124,58,237,0);}}
.scout-fab-lbl{font-size:10px;font-weight:700;color:#7c3aed;letter-spacing:.06em;font-family:'JetBrains Mono',monospace;}
@keyframes scoutdot{0%,80%,100%{transform:scale(0.6);opacity:.4;}40%{transform:scale(1);opacity:1;}}
@keyframes scoutfade{from{opacity:0;transform:translateY(4px);}to{opacity:1;transform:translateY(0);}}
.scout-loader{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(14,10,44,0.93);z-index:99999;display:flex;flex-direction:column;align-items:center;justify-content:center;backdrop-filter:blur(4px);}
.scout-loader-name{font-family:'JetBrains Mono',monospace;font-size:13px;color:#a78bfa;letter-spacing:.1em;text-transform:uppercase;margin-bottom:20px;}
.slt{font-family:'JetBrains Mono',monospace;font-size:13px;color:#a78bfa;letter-spacing:.06em;opacity:.2;transition:opacity .35s;text-align:center;padding:4px 8px;}
.scout-loader-msg{font-family:'JetBrains Mono',monospace;font-size:11px;color:#4338ca;letter-spacing:.06em;min-height:18px;text-align:center;margin-top:16px;}
.scout-loader-dots{margin-top:18px;display:flex;gap:7px;}
.scout-loader-dot{width:7px;height:7px;background:#7c3aed;border-radius:50%;}
.scout-loader-dot:nth-child(1){animation:scoutdot 1.4s ease-in-out infinite;}
.scout-loader-dot:nth-child(2){animation:scoutdot 1.4s ease-in-out 0.2s infinite;}
.scout-loader-dot:nth-child(3){animation:scoutdot 1.4s ease-in-out 0.4s infinite;}
div[data-testid="stPlotlyChart"]{border:2px solid #1e1b4b;border-radius:12px;overflow:hidden;background:#fff;padding:4px;}
[data-testid="stDataFrame"]{border:2px solid #c4b5fd!important;border-radius:10px;overflow:hidden;}
.stAlert{border-radius:10px;border-left:4px solid #7c3aed!important;}
h1,h2,h3{color:#0f172a!important;font-weight:700!important;}
</style>
""", unsafe_allow_html=True)

UPLOAD_MSGS = ["Analyzing dataset...", "Running profiling...", "Detecting outliers...", "Computing charts..."]
CHAT_MSGS = ["Scout is thinking...", "Calling data tools...", "Verifying numbers...", "Scoring with judge..."]


def show_loader(messages, key="loader"):
    msgs_js = str(messages).replace("'", '"')
    st.markdown(f"""
    <div class="scout-loader" id="sl_{key}">
        <div class="scout-loader-name">Scout</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px 32px;margin-bottom:8px;">
            <div class="slt" id="slt0_{key}">{messages[0]}</div>
            <div class="slt" id="slt1_{key}">{messages[1]}</div>
            <div class="slt" id="slt2_{key}">{messages[2]}</div>
            <div class="slt" id="slt3_{key}">{messages[3] if len(messages)>3 else ''}</div>
        </div>
        <div class="scout-loader-dots">
            <div class="scout-loader-dot"></div>
            <div class="scout-loader-dot"></div>
            <div class="scout-loader-dot"></div>
        </div>
    </div>
    <script>
    (function(){{
        var ids=["slt0_{key}","slt1_{key}","slt2_{key}","slt3_{key}"];
        var si=0;
        function blinkNext(){{
            ids.forEach(function(id){{
                var e=document.getElementById(id);
                if(e) e.style.opacity="0.2";
            }});
            var el=document.getElementById(ids[si]);
            if(el) el.style.opacity="1";
            si=(si+1)%ids.length;
        }}
        blinkNext();
        setInterval(blinkNext, 600);
    }})();
    </script>
    """, unsafe_allow_html=True)


def badge(score, blocked_by=None):
    if blocked_by: return '<span class="bp bp-blocked">BLOCKED</span>'
    if score == 2: return '<span class="bp bp-pass">PASS</span>'
    if score == 1: return '<span class="bp bp-partial">PARTIAL</span>'
    return '<span class="bp bp-fail">FAIL</span>'


def auto_insights(df):
    ins = []
    num_cols = df.select_dtypes(include='number').columns.tolist()
    cat_cols = df.select_dtypes(include='object').columns.tolist()
    nulls = int(df.isnull().sum().sum())
    dups = int(df.duplicated().sum())
    if nulls == 0: ins.append("Dataset is complete with no missing values")
    else: ins.append(f"{nulls} missing values across {df.isnull().any().sum()} columns")
    if dups > 0: ins.append(f"{dups} duplicate rows detected")
    if num_cols:
        col = num_cols[0]
        mean, std = df[col].mean(), df[col].std()
        outliers = int(((df[col]>mean+2*std)|(df[col]<mean-2*std)).sum())
        ins.append(f"{col}: mean {mean:.2f}, std {std:.2f}, {outliers} outliers detected")
    if len(num_cols) > 1:
        corr = df[num_cols].corr()
        pairs = [(abs(corr.loc[a,b]),a,b) for i,a in enumerate(num_cols) for j,b in enumerate(num_cols) if i<j]
        if pairs:
            top = sorted(pairs,reverse=True)[0]
            ins.append(f"Strongest correlation: {top[1]} vs {top[2]} (r={top[0]:.2f})")
    if cat_cols:
        col = cat_cols[0]
        vc = df[col].value_counts()
        ins.append(f"Top {col}: '{vc.index[0]}' appears {vc.iloc[0]} times ({vc.iloc[0]/len(df)*100:.1f}%)")
    return ins[:5]


def suggest_questions(df):
    qs = []
    num_cols = df.select_dtypes(include='number').columns.tolist()
    cat_cols = df.select_dtypes(include='object').columns.tolist()
    if num_cols: qs.append(f"Average {num_cols[0]}?")
    if num_cols and cat_cols: qs.append(f"Total {num_cols[0]} by {cat_cols[0]}?")
    if num_cols: qs.append(f"Rows with {num_cols[0]} > {df[num_cols[0]].median():.0f}?")
    if cat_cols: qs.append(f"Count by {cat_cols[0]}?")
    if len(num_cols) > 1: qs.append(f"Max {num_cols[-1]}?")
    return qs[:4]


def make_charts(df):
    charts = []
    num_cols = df.select_dtypes(include='number').columns.tolist()
    cat_cols = df.select_dtypes(include='object').columns.tolist()
    base = dict(paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
                margin=dict(t=36,b=16,l=16,r=16), height=200, title_font_size=12,
                title_font_color="#0f172a")
    if num_cols:
        for col in num_cols[:3]:
            fig = px.histogram(df, x=col, nbins=25, color_discrete_sequence=["#7c3aed"],
                               template="plotly_white", title=f"Distribution: {col}")
            fig.update_layout(**base, showlegend=False)
            charts.append((f"Distribution: {col}", fig))
    if len(num_cols) > 1:
        for col in num_cols[:3]:
            fig = px.box(df, y=col, color_discrete_sequence=["#7c3aed"],
                         template="plotly_white", title=f"Outliers: {col}")
            fig.update_layout(**base)
            charts.append((f"Outliers: {col}", fig))
    if len(num_cols) >= 2:
        corr = df[num_cols].corr()
        fig = px.imshow(corr, color_continuous_scale=["#f5f3ff","#7c3aed"],
                        template="plotly_white", text_auto=".2f", title="Correlation heatmap")
        fig.update_layout(**{**base,"height":220})
        charts.append(("Correlation heatmap", fig))
    if cat_cols and num_cols:
        cc,cn = cat_cols[0],num_cols[0]
        top = df[cc].value_counts().head(8).index
        agg = df[df[cc].isin(top)].groupby(cc)[cn].sum().sort_values()
        fig = px.bar(agg, orientation='h', color_discrete_sequence=["#7c3aed"],
                     template="plotly_white", title=f"{cn} by {cc}")
        fig.update_layout(**{**base,"height":220}, showlegend=False)
        charts.append((f"{cn} by {cc}", fig))
    if cat_cols:
        col = cat_cols[0]
        vc = df[col].value_counts().head(7)
        fig = px.pie(values=vc.values, names=vc.index,
                     color_discrete_sequence=px.colors.sequential.Purples_r,
                     template="plotly_white", title=f"{col} breakdown")
        fig.update_layout(**{**base,"height":220})
        charts.append((f"{col} breakdown", fig))
    return charts


def generate_pdf(df, insights, charts, messages):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18*mm, rightMargin=18*mm,
                            topMargin=18*mm, bottomMargin=18*mm)
    T = ParagraphStyle("T", fontName="Helvetica-Bold", fontSize=20,
                       textColor=colors.HexColor("#0f172a"), spaceAfter=4, alignment=TA_CENTER)
    S = ParagraphStyle("S", fontName="Helvetica", fontSize=10,
                       textColor=colors.HexColor("#64748b"), spaceAfter=14, alignment=TA_CENTER)
    H = ParagraphStyle("H", fontName="Helvetica-Bold", fontSize=13,
                       textColor=colors.HexColor("#7c3aed"), spaceBefore=10, spaceAfter=5)
    B = ParagraphStyle("B", fontName="Helvetica", fontSize=9,
                       textColor=colors.HexColor("#0f172a"), spaceAfter=4, leading=13)
    M = ParagraphStyle("M", fontName="Courier", fontSize=8,
                       textColor=colors.HexColor("#64748b"), spaceAfter=6)
    story = [
        Paragraph("AgentAudit : Scout", T),
        Paragraph(f"Session Report — {time.strftime('%Y-%m-%d %H:%M')}", S),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#c4b5fd")),
        Spacer(1,5*mm),
        Paragraph("Dataset Overview", H),
        Paragraph(f"Rows: {len(df):,} | Columns: {len(df.columns)} | Numeric: {len(df.select_dtypes(include='number').columns)} | Categorical: {len(df.select_dtypes(include='object').columns)}", B),
        Spacer(1,3*mm),
        Paragraph("Auto Insights", H),
    ]
    for i, text in enumerate(insights, 1):
        story.append(Paragraph(f"{i}. {text}", B))
    if charts:
        story.append(Spacer(1,4*mm))
        story.append(Paragraph("Charts", H))
        for title, fig in charts:
            try:
                img_bytes = fig.to_image(format="png", width=500, height=200, scale=1)
                story.append(Paragraph(title, B))
                story.append(RLImage(io.BytesIO(img_bytes), width=160*mm, height=64*mm))
                story.append(Spacer(1,3*mm))
            except Exception:
                story.append(Paragraph(f"[Chart: {title}]", M))
    if messages:
        story.append(Spacer(1,4*mm))
        story.append(Paragraph("Scout Conversation", H))
        qn = 0
        for msg in messages:
            if msg["role"] == "user":
                qn += 1
                story.append(Paragraph(f"Q{qn}: {msg['content']}", H))
            elif msg["role"] == "scout":
                sl = {2:"PASS",1:"PARTIAL",0:"FAIL"}.get(msg.get("score"),"N/A")
                if msg.get("blocked_by"): sl = "BLOCKED"
                story.append(Paragraph(f"Scout: {msg['content']}", B))
                meta = f"Score: {sl}"
                if msg.get("total_tokens"): meta += f" | {msg['total_tokens']} tokens"
                if msg.get("latency_seconds"): meta += f" | {msg['latency_seconds']}s"
                story.append(Paragraph(meta, M))
    story += [
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#c4b5fd")),
        Spacer(1,3*mm),
        Paragraph("Generated by AgentAudit : Scout", M),
    ]
    doc.build(story)
    buf.seek(0)
    return buf


for k,v in [("messages",[]),("agent",None),("df",None),("show_chat",False),("charts",[]),("insights",[])]:
    if k not in st.session_state:
        st.session_state[k] = v

st.markdown("""
<div class="hero">
    <div class="hero-badge">AI data analyst with eval harness</div>
    <div class="hero-title">Agent<span>Audit</span></div>
    <div class="hero-sub">Upload any CSV. Get instant analysis, auto insights, and charts. Ask Scout anything — every answer scored and traced.</div>
</div>
""", unsafe_allow_html=True)

col_up, col_tip = st.columns([3,1])
with col_up:
    uploaded = st.file_uploader("Upload CSV", type=["csv"], key="uploader", label_visibility="collapsed")
with col_tip:
    st.markdown('<div style="background:#f5f3ff;border:2px solid #c4b5fd;border-radius:10px;padding:10px 14px;font-size:12px;color:#6d28d9;line-height:1.6;margin-top:6px;"><b>Any CSV works:</b> sales, fraud, HR, marketing, finance</div>', unsafe_allow_html=True)

if uploaded is not None and st.session_state.df is None:
    show_loader(UPLOAD_MSGS, "upload")
    df = pd.read_csv(uploaded)
    st.session_state.df = df
    st.session_state.insights = auto_insights(df)
    try:
        from agent import build_csv_agent, load_document
        load_document(uploaded.getvalue(), uploaded.name)
        st.session_state.agent = build_csv_agent()
        st.session_state.charts = make_charts(df)
        cols_p = ', '.join(df.columns.tolist()[:5]) + ('...' if len(df.columns)>5 else '')
        st.session_state.messages = [{
            "role":"scout",
            "content":f"Hi! I'm Scout — your AI data analyst. I've loaded <b>{uploaded.name}</b>: {len(df):,} rows, {len(df.columns)} columns ({cols_p}). I can answer questions, spot patterns, and flag anomalies. What would you like to know?",
            "score":None,"judge_reason":None,"tool_calls":[],
            "total_tokens":0,"latency_seconds":0,"blocked_by":None,
        }]
    except Exception as e:
        st.error(f"Could not load: {e}")
    st.rerun()

if st.session_state.df is not None:
    df = st.session_state.df
    num_cols = df.select_dtypes(include='number').columns.tolist()
    nulls = int(df.isnull().sum().sum())
    quality = int((1-nulls/max(len(df)*len(df.columns),1))*100)
    outliers = sum(int(((df[c]>df[c].mean()+2*df[c].std())|(df[c]<df[c].mean()-2*df[c].std())).sum()) for c in num_cols) if num_cols else 0

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">Your data</div><div class="card-title">Dataset overview</div><div class="card-sub">Auto-profiling of your uploaded file.</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="stat-row">
        <div class="stat-box"><div class="stat-num">{len(df):,}</div><div class="stat-lbl">Rows</div></div>
        <div class="stat-box"><div class="stat-num">{len(df.columns)}</div><div class="stat-lbl">Columns</div></div>
        <div class="stat-box"><div class="stat-num">{len(num_cols)}</div><div class="stat-lbl">Numeric</div></div>
        <div class="stat-box"><div class="stat-num">{quality}%</div><div class="stat-lbl">Quality</div></div>
        <div class="stat-box"><div class="stat-num">{outliers}</div><div class="stat-lbl">Outliers</div></div>
    </div>
    """, unsafe_allow_html=True)
    for i, text in enumerate(st.session_state.insights, 1):
        st.markdown(f'<div class="insight"><span class="insight-num">{i}.</span><span>{text}</span></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    charts = st.session_state.charts
    if charts:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="eyebrow">Visualizations</div><div class="card-title">Charts and distributions</div><div class="card-sub">Auto-generated from your dataset.</div>', unsafe_allow_html=True)
        for i in range(0, len(charts), 3):
            batch = charts[i:i+3]
            cols = st.columns(3)
            for j in range(3):
                with cols[j]:
                    if j < len(batch):
                        title, fig = batch[j]
                        st.plotly_chart(fig, use_container_width=True, key=f"chart_{i}_{j}")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">Profiling</div><div class="card-title">Column profiles</div><div class="card-sub">Stats for every column.</div>', unsafe_allow_html=True)
    rows = []
    for col in df.columns:
        r = {"Column":col,"Type":str(df[col].dtype),"Nulls":int(df[col].isnull().sum()),"Unique":int(df[col].nunique())}
        if pd.api.types.is_numeric_dtype(df[col]):
            r.update({"Mean":round(df[col].mean(),2),"Min":round(df[col].min(),2),"Max":round(df[col].max(),2)})
        else:
            r.update({"Mean":"-","Min":"-","Max":"-"})
        rows.append(r)
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

    btn_lbl = "🔭  Close Scout" if st.session_state.show_chat else "🔭  Chat with Scout — Ask anything about your data"
    if st.button(btn_lbl, key="scout_toggle", use_container_width=True):
        st.session_state.show_chat = not st.session_state.show_chat
        st.rerun()

    if st.session_state.show_chat:
        left_col, right_col = st.columns([1, 2])

        with left_col:
            st.markdown("""
            <div class="card-scout-left">
                <div style="font-size:36px;margin-bottom:10px;">&#x1F52D;</div>
                <div class="eyebrow-light">Your AI analyst</div>
                <div class="card-title-light">Scout</div>
                <div class="card-sub-light" style="margin-bottom:18px;">Ask anything about your data. Every answer is scored by an independent LLM judge and logged with full trace.</div>
                <div style="margin-bottom:16px;">
                    <div class="eyebrow-light" style="margin-bottom:8px;">Validation metrics</div>
                    <div style="display:flex;flex-direction:column;gap:8px;">
                        <div class="stat-box-dark"><div class="stat-num-light">0.774</div><div class="stat-lbl-light">Judge vs human &#x3BA;</div></div>
                        <div class="stat-box-dark"><div class="stat-num-light">83&#x2192;50%</div><div class="stat-lbl-light">Regression caught</div></div>
                        <div class="stat-box-dark"><div class="stat-num-light">86&#x2192;57%</div><div class="stat-lbl-light">Unsafe pre&#x2192;post guardrail</div></div>
                        <div class="stat-box-dark"><div class="stat-num-light">29</div><div class="stat-lbl-light">Golden tasks evaluated</div></div>
                    </div>
                </div>
                <div style="font-size:11px;color:#4338ca;line-height:1.6;">These metrics reflect Scout's validated reliability — independent of your uploaded data.</div>
            </div>
            """, unsafe_allow_html=True)

        with right_col:
            st.markdown('<div class="card-chat">', unsafe_allow_html=True)
            st.markdown('<div class="eyebrow">Scout &#x1F52D;</div><div class="card-title">Ask your data anything</div><div class="card-sub">Facts only. Every answer scored in real time.</div>', unsafe_allow_html=True)

            suggestions = suggest_questions(df)
            sq_cols = st.columns(len(suggestions))
            for i,(sqc,q) in enumerate(zip(sq_cols,suggestions)):
                with sqc:
                    if st.button(q, key=f"sq_{i}", use_container_width=True):
                        st.session_state.messages.append({"role":"user","content":q})
                        show_loader(CHAT_MSGS, "chat_sq")
                        try:
                            from agent import ask_safe_csv, JUDGE_A_MODEL
                            from judge import build_judge, grade
                            result = ask_safe_csv(st.session_state.agent, q)
                            j = build_judge(model=JUDGE_A_MODEL)
                            g = grade(j, q, result["answer"], GENERIC_RUBRIC)
                            st.session_state.messages.append({
                                "role":"scout","content":result["answer"],
                                "score":g["score"],"judge_reason":g["reason"],
                                "tool_calls":result.get("tool_calls",[]),
                                "total_tokens":result.get("total_tokens",0),
                                "latency_seconds":result.get("latency_seconds",0),
                                "blocked_by":result.get("blocked_by"),
                            })
                        except Exception as e:
                            st.session_state.messages.append({"role":"scout","content":f"Error: {e}","score":None,"judge_reason":None,"tool_calls":[],"total_tokens":0,"latency_seconds":0,"blocked_by":None})
                        st.rerun()

            thread = '<div class="chat-wrap">'
            for msg in st.session_state.messages:
                if msg["role"] == "user":
                    thread += f'<div class="msg-user"><div class="avatar-user">U</div><div class="bubble-user">{msg["content"]}</div></div>'
                elif msg["role"] == "scout":
                    b = badge(msg.get("score"),msg.get("blocked_by")) if msg.get("score") is not None else ""
                    tools = ", ".join(t["tool"] for t in msg.get("tool_calls",[]) if t.get("tool"))
                    tstr = f" · {tools}" if tools else ""
                    tkstr = f" · {msg['total_tokens']}t" if msg.get("total_tokens") else ""
                    lstr = f" · {msg['latency_seconds']}s" if msg.get("latency_seconds") else ""
                    thread += f'<div class="msg-scout"><div class="avatar-scout">&#x1F52D;</div><div class="bubble-scout">{msg["content"]}<div class="bubble-meta">{b}{tkstr}{lstr}{tstr}</div></div></div>'
            thread += '</div>'
            st.markdown(thread, unsafe_allow_html=True)

            question = st.chat_input("Ask Scout...", key="chat_in")
            if question:
                st.session_state.messages.append({"role":"user","content":question})
                show_loader(CHAT_MSGS, "chat_input")
                try:
                    from agent import ask_safe_csv, JUDGE_A_MODEL
                    from judge import build_judge, grade
                    result = ask_safe_csv(st.session_state.agent, question)
                    j = build_judge(model=JUDGE_A_MODEL)
                    g = grade(j, question, result["answer"], GENERIC_RUBRIC)
                    st.session_state.messages.append({
                        "role":"scout","content":result["answer"],
                        "score":g["score"],"judge_reason":g["reason"],
                        "tool_calls":result.get("tool_calls",[]),
                        "total_tokens":result.get("total_tokens",0),
                        "latency_seconds":result.get("latency_seconds",0),
                        "blocked_by":result.get("blocked_by"),
                    })
                except Exception as e:
                    st.session_state.messages.append({"role":"scout","content":f"Error: {e}","score":None,"judge_reason":None,"tool_calls":[],"total_tokens":0,"latency_seconds":0,"blocked_by":None})
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    pdf_buf = generate_pdf(df, st.session_state.insights, st.session_state.charts, st.session_state.messages)
    st.download_button("&#x2B07; Download full report (PDF)", data=pdf_buf,
                       file_name=f"scout_report_{time.strftime('%Y%m%d_%H%M')}.pdf",
                       mime="application/pdf", use_container_width=True)

if st.session_state.df is not None:
    st.markdown("""
    <div class="scout-fab">
        <div class="scout-fab-btn">&#x1F52D;</div>
        <div class="scout-fab-lbl">SCOUT</div>
    </div>
    """, unsafe_allow_html=True)