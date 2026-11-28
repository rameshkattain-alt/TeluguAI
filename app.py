import streamlit as st
from googleapiclient.discovery import build
from google import genai
import requests
import json
import pandas as pd
import altair as alt
import re
from datetime import datetime

st.set_page_config(page_title="360° తెలుగు పొలిటికల్ వార్-రూమ్ AI", page_icon="🛡️", layout="wide")

# మీ API Keys
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
YOUTUBE_API_KEY = st.secrets["YOUTUBE_API_KEY"]
APIFY_API_TOKEN = st.secrets["APIFY_API_TOKEN"]



client = genai.Client(api_key=GEMINI_API_KEY)
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

def extract_video_id(url):
    match = re.search(r'(?:youtu\.be\/|v=|shorts\/|embed\/)([0-9A-Za-z_-]{11})', url)
    return match.group(1) if match else None

def fetch_youtube_comments(video_id, target_count):
    comments = []
    next_page_token = None
    while len(comments) < target_count:
        batch_size = min(100, target_count - len(comments))
        req = youtube.commentThreads().list(
            part="snippet", videoId=video_id, maxResults=batch_size,
            pageToken=next_page_token, textFormat="plainText"
        )
        res = req.execute()
        for item in res.get("items", []):
            comments.append(item['snippet']['topLevelComment']['snippet']['textDisplay'])
        next_page_token = res.get("nextPageToken")
        if not next_page_token:
            break
    return comments

def fetch_apify_comments(actor_name, payload, token):
    host = "https://apify.com"
    path = f"/v2/acts/{actor_name}/run-sync-get-dataset-items"
    full_url = f"{host}{path}?token={token}"
    res = requests.post(full_url, json=payload, timeout=90)
    res.raise_for_status()
    items = res.json()
    extracted = []
    for item in items:
        txt = item.get("text") or item.get("comment") or item.get("full_text") or item.get("message")
        if txt:
            extracted.append(str(txt))
    return extracted

if "report_data" not in st.session_state:
    st.session_state.report_data = None
if "all_comments" not in st.session_state:
    st.session_state.all_comments = []
if "selected_filter" not in st.session_state:
    st.session_state.selected_filter = "నెగెటివ్" # డిఫాల్ట్‌గా నెగెటివ్ కామెంట్లు కనిపిస్తాయి

st.title("🛡️ 360° పొలిటికల్ ఇంటెలిజెన్స్ & ఆటో-రిప్లై వార్-రూమ్")
st.caption("YouTube + Instagram + Facebook + X (Twitter) | ఆటోమేటిక్ కామెంట్ విశ్లేషణ & స్మార్ట్ రిప్లై")

with st.sidebar:
    st.header("⚙️ నాయకుడి ప్రొఫైల్")
    leader_name = st.text_input("నాయకుడు / పార్టీ పేరు:", value="రేవంత్ రెడ్డి / KTR / చంద్రబాబు / జగన్")
    constituency = st.text_input("నియోజకవర్గం / ప్రాంతం:", value="తెలంగాణ / ఆంధ్రప్రదేశ్")
    reply_tone = st.selectbox("రిప్లై టోన్ (శైలి):", ["హుందాగా & ఆత్మీయంగా (Respectful)", "అధికారికంగా (Official)", "స్ట్రాంగ్ కౌంటర్ (Aggressive)"])
    num_comments = st.slider("కామెంట్ల సంఖ్య (ఒక్కో ప్లాట్‌ఫామ్ నుండి):", 20, 500, 50, 10)

st.subheader("📥 సోషల్ మీడియా లింక్ వేయి (1-Click Auto Fetch)")
t_yt, t_ig, t_fb, t_x = st.tabs(["▶️ YouTube (Auto)", "📸 Instagram (Auto Link)", "📘 Facebook (Auto Link)", "𝕏 X / Twitter (Auto Link)"])

with t_yt:
    yt_url = st.text_input("YouTube వీడియో లింక్:")
with t_ig:
    ig_url = st.text_input("Instagram రీల్ / పోస్ట్ లింక్:")
with t_fb:
    fb_url = st.text_input("Facebook పోస్ట్ లింక్:")
with t_x:
    x_url = st.text_input("X (Twitter) పోస్ట్ లింక్:")
if st.button("🚀 360° ఆటోమేటిక్ విశ్లేషణ ప్రారంభించు", type="primary"):
    combined_comments = []
ig_url = st.text_input("Enter URL")
if ig_url:
        with st.spinner("Instagram రీల్/పోస్ట్ కామెంట్లు తెస్తున్నాము (20-30 సెకన్లు పట్టవచ్చు)..."):
            try:
                clean_ig = ig_url.split("?")[0]
                ig_list = fetch_apify_comments(
                    "apify~instagram-comment-scraper",
                    {"directUrls": [clean_ig], "resultsLimit": num_comments},
                    APIFY_API_TOKEN
                )
                combined_comments.extend([f"[Instagram] {c}" for c in ig_list])
            except Exception as e:
                st.error(f"Instagram సమస్య: {e}")
if fb_url:
        with st.spinner("Facebook పోస్ట్ కామెంట్లు తెస్తున్నాము (20-30 సెకన్లు పట్టవచ్చు)..."):
            try:
                fb_list = fetch_apify_comments(
                    "apify~facebook-comments-scraper",
                    {"startUrls": [{"url": fb_url}], "resultsLimit": num_comments},
                    APIFY_API_TOKEN
                )
                combined_comments.extend([f"[Facebook] {c}" for c in fb_list])
            except Exception as e:
                st.error(f"Facebook సమస్య: {e}")

    if x_url:
        with st.spinner("X (Twitter) రిప్లైలు తెస్తున్నాము (20-30 సెకన్లు పట్టవచ్చు)..."):
            try:
                x_list = fetch_apify_comments(
                    "kaitoeasyapi~twitter-x-data-tweet-scraper-pay-per-result-cheapest",
                    {"startUrls": [x_url], "maxItems": num_comments},
                    APIFY_API_TOKEN
                )
                combined_comments.extend([f"[X/Twitter] {c}" for c in x_list])
            except Exception as e:
                st.error(f"X/Twitter సమస్య: {e}")

    if fb_url:
        with st.spinner("Facebook పోస్ట్ కామెంట్లు తెస్తున్నాము (20-30 సెకన్లు పట్టవచ్చు)..."):
            try:
                fb_list = fetch_apify_comments(
                    "apify~facebook-comments-scraper",
                    {"startUrls": [{"url": fb_url}], "resultsLimit": num_comments},
                    APIFY_API_TOKEN
                )
                combined_comments.extend([f"[Facebook] {c}" for c in fb_list])
            except Exception as e:
                st.error(f"Facebook సమస్య: {e}")

    if x_url:
        with st.spinner("X (Twitter) రిప్లైలు తెస్తున్నాము (20-30 సెకన్లు పట్టవచ్చు)..."):
            try:
                x_list = fetch_apify_comments(
                    "apidojo~tweet-scraper",
                    {"startUrls": [x_url], "maxItems": num_comments},
                    APIFY_API_TOKEN
                )
                combined_comments.extend([f"[X/Twitter] {c}" for c in x_list])
            except Exception as e:
                st.error(f"X/Twitter సమస్య: {e}")

    if combined_comments:
        st.session_state.all_comments = combined_comments
        st.success(f"✅ మొత్తం {len(combined_comments)} నిజమైన కామెంట్లు సేకరించబడ్డాయి!")
        with st.spinner("AI కామెంట్లను వర్గీకరించి నాయకుడి కోసం రిపోర్ట్ తయారు చేస్తోంది..."):
            prompt = f"""
            నువ్వు {leader_name} ({constituency}) కి చీఫ్ పొలిటికల్ స్ట్రాటజిస్ట్. రిప్లై శైలి: {reply_tone}.
            కింది తెలుగు మరియు తంగ్లీష్ (Tanglish) సోషల్ మీడియా కామెంట్లను నిశితంగా విశ్లేషించి, కేవలం ఖచ్చితమైన JSON ఫార్మాట్‌లో మాత్రమే సమాధానం ఇవ్వు:
            {{
                "positive_pct": 0,
                "negative_pct": 0,
                "sarcasm_neutral_pct": 0,
                "bot_pct": 0,
                "viral_risk_level": "Low / Medium / High (ఎందుకు అనేది ఒక్క వాక్యంలో)",
                "platform_summary": "ప్రజల స్పందనపై 2 లైన్ల సమగ్ర నివేదిక",
                "categorized_comments": {{
                    "పాజిటివ్": ["ముఖ్యమైన పాజిటివ్ కామెంట్ 1", "కామెంట్ 2", "కామెంట్ 3", "కామెంట్ 4", "కామెంట్ 5"],
                    "నెగెటివ్": ["ముఖ్యమైన నెగెటివ్ కామెంట్ 1", "కామెంట్ 2", "కామెంట్ 3", "కామెంట్ 4", "కామెంట్ 5"],
                    "వ్యంగ్యం": ["వ్యంగ్యపు (Sarcasm) కామెంట్ 1", "కామెంట్ 2", "కామెంట్ 3"],
                    "బాట్స్": ["ఫేక్/కాపీ-పేస్ట్ ఐటీ సెల్ కామెంట్ 1", "కామెంట్ 2", "కామెంట్ 3"]
                }},
                "actionable_replies": [
                    {{
                        "platform": "YouTube/Insta/FB/X",
                        "category": "నెగెటివ్ / సమస్య / పాజిటివ్",
                        "user_comment": "ముఖ్యమైన నిజమైన కామెంట్",
                        "suggested_reply": "{leader_name} తరఫున ప్రజలకు ఇచ్చే పర్ఫెక్ట్ తెలుగు/తంగ్లీష్ రిప్లై"
                    }}
                ],
                "issues": {{"రోడ్లు/మౌలిక వసతులు": 0, "నీళ్లు/కరెంటు": 0, "ప్రభుత్వ పథకాలు": 0, "నిరుద్యోగం/ధరలు": 0, "వ్యక్తిగత విమర్శలు": 0}},
                "issue_comments": {{
                    "రోడ్లు/మౌలిక వసతులు": ["సంబంధిత కామెంట్ 1", "కామెంట్ 2"],
                    "నీళ్లు/కరెంటు": ["సంబంధిత కామెంట్ 1", "కామెంట్ 2"],
                    "ప్రభుత్వ పథకాలు": ["సంబంధిత కామెంట్ 1", "కామెంట్ 2"],
                    "నిరుద్యోగం/ధరలు": ["సంబంధిత కామెంట్ 1", "కామెంట్ 2"],
                    "వ్యక్తిగత విమర్శలు": ["సంబంధిత కామెంట్ 1", "కామెంట్ 2"]
                }},
                "counter_strategy": ["ప్రతిపక్ష విమర్శలకు స్ట్రాంగ్ కౌంటర్ పాయింట్ 1", "కౌంటర్ పాయింట్ 2", "కౌంటర్ పాయింట్ 3"]
            }}
            కామెంట్లు: {combined_comments[:300]}
            """
            for m in ['gemini-3.8-flash', 'gemini-3.5-flash']:
                try:
                    ai_res = client.models.generate_content(
                        model=m, 
                        contents=prompt, 
                        config={"response_mime_type": "application/json"}
                    )
                    st.session_state.report_data = json.loads(ai_res.text)
                    break
                except Exception as e:
                    st.error(f"AI విశ్లేషణ సమస్య ({m}): {e}")
                    continue
    else:
        st.warning("కనీసం ఒక్క లింక్ (YouTube, Instagram, Facebook, లేదా X) పేస్ట్ చెయ్ బాస్!")

data = st.session_state.report_data
if data:
    st.divider()
    
    # 1. వైరల్ అలర్ట్ & సారాంశం
    risk = data.get('viral_risk_level', 'Low')
    if "High" in risk:
        st.error(f"🚨 **వైరల్ క్రైసిస్ అలర్ట్:** {risk}")
    else:
        st.success(f"🛡️ **పరిస్థితి సమీక్ష:** {risk}")
        
    st.info(f"📋 **సమగ్ర నివేదిక:** {data.get('platform_summary', '')}")
    
    # 2. క్లిక్ చేయగానే కామెంట్లు చూపించే ఇంటరాక్టివ్ మెట్రిక్స్
    st.subheader("👆 ఏ కేటగిరీ కామెంట్లు చదవాలో ఆ బటన్ మీద క్లిక్ చేయండి:")
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        if st.button(f"👍 పాజిటివ్: {data.get('positive_pct', 0)}%", use_container_width=True):
            st.session_state.selected_filter = "పాజిటివ్"
    with c2:
        if st.button(f"👎 నెగెటివ్: {data.get('negative_pct', 0)}%", use_container_width=True):
            st.session_state.selected_filter = "నెగెటివ్"
    with c3:
        if st.button(f"😏 వ్యంగ్యం: {data.get('sarcasm_neutral_pct', 0)}%", use_container_width=True):
            st.session_state.selected_filter = "వ్యంగ్యం"
    with c4:
        if st.button(f"🤖 బాట్స్: {data.get('bot_pct', 0)}%", use_container_width=True):
            st.session_state.selected_filter = "బాట్స్"
                # ఎంచుకున్న బటన్ తాలూకు కామెంట్లు ఇక్కడ వెంటనే ఓపెన్ అవుతాయి
    cat_comments = data.get("categorized_comments", {})
    active_cat = st.session_state.selected_filter
    if cat_comments and active_cat in cat_comments:
        with st.container(border=True):
            st.markdown(f"### 💬 '{active_cat}' విభాగంలోని ముఖ్య కామెంట్లు:")
            comments_to_show = cat_comments.get(active_cat, [])
            if comments_to_show:
                for idx, cm in enumerate(comments_to_show, 1):
                    st.write(f"**{idx}.** {cm}")
            else:
                st.write("ఈ విభాగంలో ముఖ్యమైన కామెంట్లు లేవు.")

    # 3. స్థానిక సమస్యల గ్రాఫ్ + సమస్యల వారీగా కామెంట్లు & వార్-రూమ్ వ్యూహం
    st.divider()
    col_chart, col_counter = st.columns([1.2, 1])
    
    with col_chart:
        st.subheader("📊 నియోజకవర్గ సమస్యల తీవ్రత (Ground Issues)")
        issues_dict = data.get("issues", {})
        if issues_dict:
            df_issues = pd.DataFrame({
                "సమస్య": list(issues_dict.keys()),
                "కామెంట్ల సంఖ్య": list(issues_dict.values())
            })
            chart = alt.Chart(df_issues).mark_bar(color="#FF4B4B").encode(
                x=alt.X("కామెంట్ల సంఖ్య:Q", title="ప్రస్తావించిన సంఖ్య"),
                y=alt.Y("సమస్య:N", sort="-x", title=""),
                tooltip=["సమస్య", "కామెంట్ల సంఖ్య"]
            ).properties(height=230)
            st.altair_chart(chart, use_container_width=True)
            
            # సమస్యను ఎంచుకుని ఆ కామెంట్లు చదివే ఆప్షన్
            selected_issue = st.selectbox("🔍 ఏ సమస్యపై ప్రజలు ఏమన్నారో చూడండి:", list(issues_dict.keys()))
            issue_cm_list = data.get("issue_comments", {}).get(selected_issue, [])
            if issue_cm_list:
                for ic in issue_cm_list:
                    st.caption(f"🗣️ {ic}")

    with col_counter:
        st.subheader("⚔️ వార్-రూమ్ కౌంటర్ స్ట్రాటజీ")
        for idx, point in enumerate(data.get("counter_strategy", []), 1):
            st.warning(f"**వ్యూహం {idx}:** {point}")

    # 4. 1-Click స్మార్ట్ ఆటో-రిప్లై సెంటర్
    st.divider()
    st.subheader("✍️ 1-Click స్మార్ట్ ఆటో-రిప్లై సెంటర్")
    for item in data.get("actionable_replies", []):
        with st.container(border=True):
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"**[{item.get('platform', 'Social')}] ({item.get('category', '')}) ప్రజల కామెంట్:**")
                st.write(f"💬 *{item.get('user_comment', '')}*")
            with col_b:
                st.markdown("**✅ నాయకుడి రెడీమేడ్ రిప్లై (Copy చెయ్):**")
                st.code(item.get('suggested_reply', ''), language=None)

    # 5. మార్నింగ్ బ్రీఫింగ్ రిపోర్ట్ డౌన్‌లోడ్
    st.divider()
    st.subheader("📥 డైలీ మార్నింగ్ బ్రీఫింగ్ (WhatsApp షేరింగ్ కోసం)")
    report_text = f"""🛡️ 360° పొలిటికల్ వార్-రూమ్ రిపోర్ట్
నాయకుడు: {leader_name} | ప్రాంతం: {constituency}
తేదీ: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}
-----------------------------------------
📊 ప్రజల స్పందన:
- పాజిటివ్: {data.get('positive_pct', 0)}%
- నెగెటివ్: {data.get('negative_pct', 0)}%
- వ్యంగ్యం: {data.get('sarcasm_neutral_pct', 0)}%
- బాట్స్ (Fake): {data.get('bot_pct', 0)}%

📋 సారాంశం: {data.get('platform_summary', '')}

⚔️ కౌంటర్ వ్యూహాలు:
""" + "\n".join([f"- {p}" for p in data.get("counter_strategy", [])])

    st.download_button(
        label="📄 వాట్సాప్ రిపోర్ట్ డౌన్‌లోడ్ చేయి (Text File)",
        data=report_text,
        file_name=f"WarRoom_Report_{datetime.now().strftime('%Y%m%d')}.txt",
        mime="text/plain"
    )
         # 6. NEXT LEVEL: Apify లైవ్ ఫేక్ & పేరడీ అకౌంట్ల రాడార్ (Instagram & X Table)
st.divider()
st.subheader("🕵️‍♂️ లైవ్ ఫేక్ & పేరడీ అకౌంట్ల రాడార్ (Instagram & X)")
st.caption("Apify ద్వారా సోషల్ మీడియాలో నాయకుడి పేరుతో ఉన్న అసలు ప్రొఫైల్ లింకులను వెతికి, ఫేక్ అకౌంట్లను టేబుల్‌లో చూపిస్తుంది:")

search_leader = st.text_input("ఏ నాయకుడి పేరుతో లైవ్ ప్రొఫైల్స్ వెతకాలి? (English లో టైప్ చేస్తే ఎక్కువ ఫలితాలు వస్తాయి):", value="Revanth Reddy")

def fetch_live_profiles(query, token):
    profiles = []
    
    # 1. YouTube Live Channels & Fake Channels Search (100% Free & Instant)
    try:
        yt_search = youtube.search().list(
            part="snippet", q=query, type="channel", maxResults=8
        ).execute()
        for item in yt_search.get("items", []):
            ch_id = item["snippet"]["channelId"]
            ch_title = item["snippet"]["title"]
            ch_desc = item["snippet"]["description"]
            profiles.append({
                "platform": "YouTube Channel",
                "name": ch_title,
                "handle": ch_id[:12] + "...",
                "followers": "Check Link",
                "verified": "No",
                "bio": str(ch_desc)[:100],
                "link": f"https://youtube.com{ch_id}"
            })
    except Exception as e:
        st.caption(f"YouTube Search Note: {e}")

    # 2. Instagram Live Profile Search (Apify)
    try:
        ig_url = "https://apify.com" + token
        ig_res = requests.post(ig_url, json={"search": query, "searchType": "user", "resultsLimit": 8}, timeout=60)
        if ig_res.status_code == 200 or ig_res.status_code == 201:
            for u in ig_res.json():
                uname = u.get("username", "")
                if uname:
                    profiles.append({
                        "platform": "Instagram",
                        "name": u.get("fullName", uname),
                        "handle": f"@{uname}",
                        "followers": str(u.get("followersCount", 0)),
                        "verified": "Yes" if u.get("verified") else "No",
                        "bio": str(u.get("biography", ""))[:100],
                        "link": f"https://instagram.com{uname}/"
                    })
    except Exception:
        pass

    # 3. X (Twitter) Live Accounts Search (Apify)
    try:
        x_url = "https://apify.com" + token
        x_res = requests.post(x_url, json={"searchTerms": [query], "maxItems": 10, "sort": "Top"}, timeout=60)
        if x_res.status_code == 200 or x_res.status_code == 201:
            seen_x = set()
            for item in x_res.json():
                author = item.get("author", {})
                uname = author.get("userName", "")
                if uname and uname not in seen_x:
                    seen_x.add(uname)
                    profiles.append({
                        "platform": "X (Twitter)",
                        "name": author.get("name", uname),
                        "handle": f"@{uname}",
                        "followers": str(author.get("followers", 0)),
                        "verified": "Yes" if author.get("isBlueVerified") else "No",
                        "bio": str(author.get("description", ""))[:100],
                        "link": f"https://x.com{uname}"
                    })
    except Exception:
        pass

    return profiles

if st.button("🔍 లైవ్ ప్రొఫైల్స్ & ఫేక్ అకౌంట్లను స్కాన్ చేయి", type="primary"):
    with st.spinner(f"Instagram మరియు X (Twitter) లో '{search_leader}' ప్రొఫైల్స్ వెతుకుతున్నాము (20-30 సెకన్లు పట్టవచ్చు)..."):
        raw_profiles = fetch_live_profiles(search_leader, APIFY_API_TOKEN)
        
        if raw_profiles:
            st.success(f"✅ మొత్తం {len(raw_profiles)} లైవ్ ప్రొఫైల్స్ దొరికాయి! AI వీటిని తనిఖీ చేస్తోంది...")
            
            classify_prompt = f"""
            నువ్వు పొలిటికల్ సైబర్ సెక్యూరిటీ అనలిస్ట్. కింద '{search_leader}' పేరుతో దొరికిన సోషల్ మీడియా ప్రొఫైల్స్ లిస్ట్ ఉంది.
            ప్రతి ప్రొఫైల్ యొక్క 'verified' స్టేటస్, 'followers', మరియు 'bio' ఆధారంగా వాటిని వర్గీకరించి JSON లిస్ట్ ఇవ్వు:
            [
                {{
                    "handle": "@username",
                    "status": "✅ Official / 🧡 Fan Page / 🚨 Fake or Parody Risk",
                    "reason": "తెలుగులో ఒక్క చిన్న కారణం (ఉదా: బ్లూ టిక్ లేదు, ఫేక్ పేరు)"
                }}
            ]
            ప్రొఫైల్స్: {json.dumps(raw_profiles, ensure_ascii=False)}
            """
            try:
                ai_prof_res = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=classify_prompt,
                    config={"response_mime_type": "application/json"}
                )
                ai_tags = {item["handle"]: item for item in json.loads(ai_prof_res.text)}
            except Exception:
                ai_tags = {}

            table_rows = []
            for p in raw_profiles:
                tag_info = ai_tags.get(p["handle"], {})
                table_rows.append({
                    "ప్లాట్‌ఫామ్": p["platform"],
                    "అకౌంట్ పేరు": p["name"],
                    "హ్యాండిల్": p["handle"],
                    "ఫాలోవర్లు": p["followers"],
                    "AI నిర్ధారణ (Status)": tag_info.get("status", "🔍 తనిఖీ చేయాలి"),
                    "కారణం": tag_info.get("reason", p["bio"]),
                    "ప్రొఫైల్ లింక్ (Click)": p["link"]
                })

            df_profiles = pd.DataFrame(table_rows)
            
            st.dataframe(
                df_profiles,
                column_config={
                    "ప్రొఫైల్ లింక్ (Click)": st.column_config.LinkColumn("ప్రొఫైల్ లింక్ (Open)")
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.warning("ప్రస్తుతం లైవ్ ప్రొఫైల్స్ దొరకలేదు. నాయకుడి పేరును ఇంగ్లీష్‌లో (ఉదా: KTR, Chandrababu, Jagan) ఇచ్చి మళ్ళీ ప్రయత్నించండి.")
