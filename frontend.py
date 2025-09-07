import streamlit as st
import requests
from newspaper import Article
import os
import concurrent.futures
import io
from fpdf import FPDF
import markdown2
st.set_page_config(layout="wide", page_title="AI Research Agent", page_icon="🌐")

# --- Custom CSS for background, fonts, buttons, containers ---
st.markdown(
    """
    <style>
    /* Background image */
    .stApp {
        background-image: url("https://images.unsplash.com/photo-1655841439659-0afc60676b70?q=80&w=1170&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }
    stMarkdown{
        background-color: rgb(10 10 10 / 70%);
    }
    /* Transparent containers */
    .css-1d391kg {
        background-color: rgba(0,0,0,0.6);
        padding: 20px;
        border-radius: 15px;
    }
    .st-emotion-cache-gquqoo {
        background-color: transparent;
    }
    /* Buttons */
    .stButton>button {
        background-color: #000000;
        color: white;
        border-radius: 8px;
        padding: 10px 24px;
        font-size: 16px;
    }

    /* Input boxes */
    .stTextInput>div>div>input {
        border-radius: 8px;
        padding: 10px;
        font-size: 16px;
    }

    /* Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');
    html, body, [class*="css"]  {
        font-family: 'Roboto', sans-serif;
        color: #ffffff;
    }
    .st-emotion-cache-18tdrd9 {
        font-family: 'Roboto', sans-serif;
    }
    .st-emotion-cache-1krtkoa {
        border: 1px solid rgb(87 237 188);
    }
    .st-emotion-cache-1krtkoa:hover, .st-emotion-cache-1krtkoa:focus-visible {
        border: 1px solid rgb(88 88 88);
        background-color: rgb(88 88 88);
    }
    .st-b7 {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 0px;
        box-shadow: 20px 4px 30px rgba(0, 0, 0, 0.1);
        backdrop-filter: blur(-1px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgb(74 255 198 / 30%);

    }
    .st-bv {
        font-weight: 700;
    }
    
    /* Alerts */
    div.stAlert {
        border-radius: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True
)
# --- Streamlit Page Setup ---
st.set_page_config(layout="wide")
st.title("AI Research Agent")
st.write("Enter a research topic and get a structured report with sources and metadata.")

# --- User Input ---
research_topic = st.text_input("Enter your research topic:", "", placeholder="Write your research idea here")

st.markdown("---")
st.subheader("Search Filters (Optional)")
col1, col2, col3 = st.columns(3)
with col1:
    tone = st.selectbox("Select Report Tone:", ["Formal", "Casual", "Technical"])
with col2:
    language = st.selectbox("Select Language:", ["English", "Spanish", "German","Hindi"])
with col3:
    time_filter = st.selectbox("Time Filter:", ["All time", "Past year", "Past month"])

st.markdown("---")
search_button = st.button("Generate Research Report", type="primary")

if search_button:
    if not research_topic.strip():
        st.error("Please enter a research topic.")
        st.stop()

    st.info("Searching the web... Please wait.")

    # --- SerpAPI Setup ---
    serpapi_api_key = os.getenv("SERPAPI_API_KEY")
    if not serpapi_api_key:
        st.error("SerpAPI key not found. Please set SERPAPI_API_KEY in your environment variables.")
        st.stop()

    language_map = {"English": "en", "Spanish": "es", "German": "de","Hindi":"hi"}
    time_map = {"All time": None, "Past year": "y", "Past month": "m"}

    params = {
        "engine": "google",
        "q": research_topic,
        "api_key": serpapi_api_key,
        "hl": language_map[language]
    }
    if time_map[time_filter]:
        params["tbs"] = f"qdr:{time_map[time_filter]}"

    search_results = requests.get("https://serpapi.com/search.json", params=params).json()

    if "error" in search_results:
        st.error(f"Search API Error: {search_results['error']}")
        st.stop()
    if "organic_results" not in search_results or len(search_results["organic_results"]) == 0:
        st.warning("No search results found for this topic.")
        st.stop()

    # --- Function to fetch article with fallback to snippet ---
    def fetch_article(result):
        url = result.get("link", "")
        title = result.get("title", "")
        snippet = result.get("snippet", "")
        if not url:
            return None
        try:
            article = Article(url)
            article.download()
            article.parse()
            author = ", ".join(article.authors) if article.authors else "Unknown"
            publish_date = article.publish_date.strftime("%Y-%m-%d") if article.publish_date else "Unknown"
            domain = article.source_url if article.source_url else url.split("/")[2]
            # Limit content for speed; fallback to snippet if article text is empty
            content = "\n".join(article.text.split("\n")[:5]) if article.text else snippet
            return {
                "title": title,
                "author": author,
                "date": publish_date,
                "domain": domain,
                "url": url,
                "content": content
            }
        except:
            # If newspaper fails, use snippet only
            if snippet:
                return {
                    "title": title,
                    "author": "Unknown",
                    "date": "Unknown",
                    "domain": url.split("/")[2],
                    "url": url,
                    "content": snippet
                }
            return None

    # --- Fetch articles in parallel ---
    sources_info = []
    consolidated_text = ""
    results_to_fetch = search_results.get("organic_results", [])[:3]  # Limit to 3 articles
    with concurrent.futures.ThreadPoolExecutor() as executor:
        fetched_articles = list(executor.map(fetch_article, results_to_fetch))

    for art in fetched_articles:
        if art:
            sources_info.append(art)
            consolidated_text += f"Title: {art['title']}\nAuthor: {art['author']}\nDate: {art['date']}\nDomain: {art['domain']}\nContent:\n{art['content']}\n\n"

    if not consolidated_text:
        st.warning("Unable to extract content from top results. Using snippets only.")
        for result in results_to_fetch:
            if result.get("snippet"):
                consolidated_text += f"Title: {result.get('title')}\nContent:\n{result.get('snippet')}\n\n"

    # --- Gemini API Summarization ---
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        st.error("Gemini API key not found. Please set GEMINI_API_KEY in your environment variables.")
        st.stop()

    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={gemini_api_key}"

    system_instruction = f"""
        You are an AI research agent. Analyze the following articles and generate a detailed research report.
        The report should:
        - Be written in {language.lower()}.
        - Include a title reflecting the user's query.
        - Provide a 1-2 paragraph introduction.
        - Include headings/subheadings for main topics.
        - Summarize content under each heading in a {tone.lower()} tone.
        - Include relevant facts, trends, or differences in viewpoints.
        - Do NOT include sources; display them separately below the report.
        """


    payload = {
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "contents": [{"parts": [{"text": consolidated_text}]}]
    }

    try:
        response = requests.post(api_url, json=payload)
        response.raise_for_status()
        data = response.json()
        report_text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "Error generating report.")

        st.success("Report generated successfully!")
        st.markdown(report_text)

        # --- Display Sources ---
        # st.markdown("### Sources")
        # st.markdown("---")
        # for src in sources_info:
        #     st.markdown(f"- **{src['title']}**, {src['author']}, {src['date']}, [{src['domain']}]({src['url']})")

        # --- PDF / Markdown Download ---
        def generate_pdf(report_text):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.set_font("Arial", size=12)
            for line in report_text.split("\n"):
                pdf.multi_cell(0, 8, line.encode('latin-1', errors='replace').decode('latin-1'))
            
            # Save to a temporary file and read into BytesIO
            temp_file = "temp_report.pdf"
            pdf.output(temp_file)  # output expects a string filename
            pdf_buffer = io.BytesIO()
            with open(temp_file, "rb") as f:
                pdf_buffer.write(f.read())
            pdf_buffer.seek(0)
            return pdf_buffer

        def generate_markdown(report_text):
            md = markdown2.markdown(report_text)
            md_buffer = io.BytesIO(md.encode('utf-8'))
            return md_buffer

        pdf_file = generate_pdf(report_text)
        st.download_button("Download Report as PDF", data=pdf_file,
                           file_name=f"{research_topic.replace(' ','_')}.pdf", mime="application/pdf")
        md_file = generate_markdown(report_text)
        st.download_button("Download Report as Markdown", data=md_file,
                           file_name=f"{research_topic.replace(' ','_')}.md", mime="text/markdown")

    except Exception as e:
        st.error(f"An error occurred while summarizing: {e}")
