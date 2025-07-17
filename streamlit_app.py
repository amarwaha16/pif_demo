import streamlit as st
import requests
import os
import pandas as pd
import openai
import re
from dotenv import load_dotenv
import uuid
from datetime import datetime

# Load API keys
load_dotenv(override=True)
openai.api_key = os.getenv("OPENAI_API_KEY")
perplexity_key = os.getenv("PERPLEXITY_API_KEY")

# Simple validation
if not perplexity_key:
    st.error("❌ Perplexity API key not found in environment variables")
    st.stop()
if not openai.api_key:
    st.error("❌ OpenAI API key not found in environment variables")
    st.stop()

# Load CSV data
@st.cache_data
def load_data():
    return pd.read_csv("investable_logistics_companies_mena.csv")

df = load_data()

# Initialize session state
if "chat_sessions" not in st.session_state:
    st.session_state.chat_sessions = {}
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "first_message_sent" not in st.session_state:
    st.session_state.first_message_sent = False

# Page config
st.set_page_config(page_title="PIF Investment Agent", layout="wide")

# Enhanced CSS Styling with PIF branding
st.markdown("""
    <style>
        /* Import PIF-style fonts */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        /* Global styles */
        .main > div {
            padding-top: 0rem;
        }
        
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }
        
        /* Top banner - PIF style */
        .top-banner {
            background: linear-gradient(135deg, #1a1a1a 0%, #2c2c2c 100%);
            padding: 1.5rem 2rem;
            display: flex;
            align-items: center;
            color: white;
            margin-bottom: 0;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .top-banner h1 {
            margin: 0;
            font-weight: 600;
            font-size: 1.8rem;
        }
        
        .pif-logo {
            width: 50px;
            height: 50px;
            background: #00B04F;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-right: 1rem;
            font-weight: 700;
            font-size: 1.2rem;
            color: white;
        }
        
        /* Sidebar styling */
        .sidebar .sidebar-content {
            background-color: #f8f9fa;
            padding: 1rem;
        }
        
        .chat-session-item {
            background: linear-gradient(135deg, #404040 0%, #2c2c2c 100%);
            border-radius: 25px;
            padding: 0.75rem 1.2rem;
            margin: 0.5rem 0;
            border: none;
            color: #00B04F;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            width: 100%;
            text-align: left;
            font-size: 0.9rem;
        }
        
        .chat-session-item:hover {
            background: linear-gradient(135deg, #4a4a4a 0%, #363636 100%);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            transform: translateY(-1px);
        }
        
        .chat-session-item.active {
            background: linear-gradient(135deg, #00B04F 0%, #00a047 100%);
            color: white;
            box-shadow: 0 4px 15px rgba(0,176,79,0.3);
        }
        
        .new-chat-btn {
            background: linear-gradient(135deg, #00B04F 0%, #00a047 100%);
            color: white;
            border-radius: 25px;
            padding: 0.8rem 1.5rem;
            border: none;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 3px 10px rgba(0,176,79,0.3);
            width: 100%;
            margin-bottom: 1rem;
        }
        
        .new-chat-btn:hover {
            background: linear-gradient(135deg, #00a047 0%, #008f3f 100%);
            box-shadow: 0 5px 15px rgba(0,176,79,0.4);
            transform: translateY(-2px);
        }
        
        /* Chat container */
        .chat-messages {
            max-height: 65vh;
            overflow-y: auto;
            padding: 0.5rem 1rem 1rem 1rem;
            background: #ffffff;
            margin-bottom: 0;
        }
        
        .chat-messages::-webkit-scrollbar {
            width: 6px;
        }
        
        .chat-messages::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 10px;
        }
        
        .chat-messages::-webkit-scrollbar-thumb {
            background: #c1c1c1;
            border-radius: 10px;
        }
        
        .chat-messages::-webkit-scrollbar-thumb:hover {
            background: #a8a8a8;
        }
        
        /* Chat messages */
        .chat-message {
            margin: 1.5rem 0;
            animation: fadeIn 0.5s ease-in;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .user-message {
            display: flex;
            justify-content: flex-end;
            margin-bottom: 1rem;
        }
        
        .user-message .message-content {
            background: linear-gradient(135deg, #f0f2f6 0%, #e8eaf0 100%);
            color: #2c2c2c;
            padding: 1rem 1.5rem;
            border-radius: 20px 20px 5px 20px;
            max-width: 70%;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            font-weight: 500;
        }
        
        .assistant-message {
            display: flex;
            justify-content: flex-start;
            margin-bottom: 1rem;
        }
        
        .assistant-message .message-content {
            background: #ffffff;
            color: #2c2c2c;
            padding: 1.5rem;
            border-radius: 20px 20px 20px 5px;
            max-width: 80%;
            border: 1px solid #e0e0e0;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            line-height: 1.6;
        }
        
        .assistant-message .message-content h2 {
            color: #00B04F;
            font-size: 1.1rem;
            margin-top: 1.5rem;
            margin-bottom: 0.8rem;
            font-weight: 600;
        }
        
        .assistant-message .message-content h2:first-child {
            margin-top: 0;
        }
        
        .assistant-message .message-content p {
            font-size: 1rem;
            line-height: 1.6;
            margin: 0.5rem 0;
        }
        
        .assistant-message .message-content ul {
            padding-left: 1.5rem;
            font-size: 1rem;
        }
        
        .assistant-message .message-content li {
            margin: 0.5rem 0;
            font-size: 1rem;
            line-height: 1.6;
        }
        
        .assistant-message .message-content a {
            color: #00B04F;
            text-decoration: none;
            font-weight: 500;
        }
        
        .assistant-message .message-content a:hover {
            text-decoration: underline;
        }
        
        /* Welcome message */
        .welcome-message {
            text-align: center;
            padding: 3rem 2rem;
            color: #666;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 20px;
            margin: 2rem;
            box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        }
        
        .welcome-message h2 {
            color: #00B04F;
            font-size: 2rem;
            margin-bottom: 1rem;
            font-weight: 600;
        }
        
        .welcome-message p {
            font-size: 1.1rem;
            line-height: 1.6;
            margin-bottom: 0.5rem;
        }
        
        /* Input styling */
        .input-container {
            position: sticky;
            bottom: 0;
            background: white;
            padding: 1rem 2rem 2rem 2rem;
            border-top: 1px solid #e0e0e0;
            box-shadow: 0 -2px 10px rgba(0,0,0,0.05);
            z-index: 100;
            margin-top: 0;
        }
        
        .input-container.centered {
            background: white;
            padding: 2rem;
            border-radius: 25px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            border: 1px solid #e0e0e0;
            width: 100%;
            max-width: 800px;
            margin: 0 auto;
        }
        
        .claude-input-container {
            background: white;
            border: 2px solid #e0e0e0;
            border-radius: 25px;
            padding: 1rem 1.5rem;
            transition: all 0.3s ease;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            position: relative;
        }
        
        .claude-input-container:focus-within {
            border-color: #00B04F;
            box-shadow: 0 0 0 3px rgba(0,176,79,0.1), 0 4px 12px rgba(0,0,0,0.1);
        }
        
        .stTextArea > div > div > textarea {
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
            background: transparent !important;
            resize: none !important;
            font-size: 1rem;
            line-height: 1.5;
            padding: 0 !important;
            min-height: 24px;
            max-height: 200px;
            font-family: 'Inter', sans-serif;
        }
        
        .stTextArea > div > div {
            border: none !important;
            background: transparent !important;
        }
        
        .stTextArea > div {
            background: transparent !important;
        }
        
        .stTextInput > div > div > input {
            border-radius: 25px;
            padding: 1rem 1.5rem;
            border: 2px solid #e0e0e0;
            font-size: 1rem;
            transition: all 0.3s ease;
        }
        
        .stTextInput > div > div > input:focus {
            border-color: #00B04F;
            box-shadow: 0 0 0 3px rgba(0,176,79,0.1);
        }
        
        .input-row {
            display: flex;
            align-items: flex-end;
            gap: 1rem;
            width: 100%;
        }
        
        .input-text-area {
            flex: 1;
        }
        
        .send-button-container {
            display: flex;
            align-items: flex-end;
            padding-bottom: 0.5rem;
        }
        
        .send-button {
            background: linear-gradient(135deg, #00B04F 0%, #00a047 100%);
            color: white;
            border-radius: 20px;
            padding: 0.75rem 1.5rem;
            border: none;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 3px 10px rgba(0,176,79,0.3);
            white-space: nowrap;
        }
        
        .send-button:hover {
            background: linear-gradient(135deg, #00a047 0%, #008f3f 100%);
            box-shadow: 0 5px 15px rgba(0,176,79,0.4);
            transform: translateY(-2px);
        }
        
        .send-button:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        
        .input-hint {
            font-size: 0.8rem;
            color: #888;
            margin-top: 0.5rem;
            text-align: center;
        }
        
        /* Loading spinner */
        .loading-spinner {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 2rem;
            color: #00B04F;
            font-weight: 500;
        }
        
        /* Responsive design */
        @media (max-width: 768px) {
            .user-message .message-content,
            .assistant-message .message-content {
                max-width: 90%;
            }
            
            .input-container.centered {
                width: 95%;
                padding: 1.5rem;
            }
        }
        
        /* Hide Streamlit elements */
        .stDeployButton {
            display: none;
        }
        
        footer {
            display: none;
        }
        
        .stMainBlockContainer {
            padding-top: 0;
        }
    </style>
""", unsafe_allow_html=True)

def create_new_chat():
    """Create a new chat session"""
    session_id = str(uuid.uuid4())
    st.session_state.chat_sessions[session_id] = {
        "title": "New Chat",
        "messages": [],
        "created_at": datetime.now()
    }
    st.session_state.current_session_id = session_id
    st.session_state.messages = []
    st.session_state.first_message_sent = False
    st.rerun()

def load_chat_session(session_id):
    """Load an existing chat session"""
    if session_id in st.session_state.chat_sessions:
        st.session_state.current_session_id = session_id
        st.session_state.messages = st.session_state.chat_sessions[session_id]["messages"]
        st.session_state.first_message_sent = len(st.session_state.messages) > 0
        st.rerun()

def save_current_session():
    """Save current messages to the session"""
    if st.session_state.current_session_id and st.session_state.current_session_id in st.session_state.chat_sessions:
        st.session_state.chat_sessions[st.session_state.current_session_id]["messages"] = st.session_state.messages
        # Update title based on first message
        if st.session_state.messages and st.session_state.chat_sessions[st.session_state.current_session_id]["title"] == "New Chat":
            first_message = st.session_state.messages[0]["content"]
            st.session_state.chat_sessions[st.session_state.current_session_id]["title"] = first_message[:40] + "..." if len(first_message) > 40 else first_message

def fetch_perplexity_articles(query):
    """Fetch articles from Perplexity API"""
    try:
        headers = {
            "Authorization": f"Bearer {perplexity_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "sonar-pro",
            "messages": [
                {
                    "role": "user",
                    "content": f"Search for 5 recent relevant articles about: {query}. For each article, provide the actual article title and working URL in this exact format: [Article Title](https://actual-working-url.com). Return only clickable links, one per line. Make sure to include 5 different articles with meaningful titles."
                }
            ],
            "search_mode": "web"
        }
        
        response = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=payload)
        
        if response.status_code == 401:
            return "• Authentication failed - please check your Perplexity API key"
        elif response.status_code != 200:
            return f"• Error fetching articles (Status {response.status_code})"
        
        response.raise_for_status()
        data = response.json()
        content = data['choices'][0]['message']['content']
        
        # More flexible parsing to capture more links
        lines = content.split('\n')
        clean_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Look for markdown links [title](url) - be more flexible with detection
            if '[' in line and '](' in line and ('http' in line or 'www' in line):
                # Skip generic article patterns like [Article 1], [Article 2], etc.
                if not re.match(r'^\[Article\s*\d*\]', line, re.IGNORECASE):
                    clean_lines.append(f"• {line}")
            
            # Look for any line that contains a URL
            elif re.search(r'https?://[^\s]+', line):
                urls = re.findall(r'https?://[^\s]+', line)
                if urls:
                    url = urls[0]
                    # Extract title from the line
                    title_part = re.sub(r'https?://[^\s]+', '', line).strip()
                    title_part = re.sub(r'[•\-\*\d\.\)]+', '', title_part).strip()
                    
                    if title_part and len(title_part) > 10:
                        clean_lines.append(f"• [{title_part}]({url})")
                    else:
                        # Extract domain as title
                        domain = re.search(r'https?://(?:www\.)?([^/]+)', url)
                        domain_name = domain.group(1) if domain else url
                        clean_lines.append(f"• [{domain_name}]({url})")
        
        # If we still don't have enough, try a different approach
        if len(clean_lines) < 3:
            # Look for any URLs in the entire content
            all_urls = re.findall(r'https?://[^\s)]+', content)
            for i, url in enumerate(all_urls[:5]):  # Get up to 5 URLs
                if not any(url in line for line in clean_lines):  # Avoid duplicates
                    domain = re.search(r'https?://(?:www\.)?([^/]+)', url)
                    domain_name = domain.group(1) if domain else f"Source {i+1}"
                    clean_lines.append(f"• [{domain_name}]({url})")
        
        return '\n'.join(clean_lines) if clean_lines else "• No relevant articles found for this query"
        
    except Exception as e:
        return f"• Error fetching articles: {str(e)}"

def get_ai_response(query, is_first_query=True):
    """Get AI response for the query"""
    if is_first_query:
        # First query: Single comprehensive call with all data
        sample_data = df.sample(10).to_dict(orient="records")
        
        try:
            # Single API call that combines everything
            comprehensive_messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a PIF private equity analyst with access to internal logistics company data. "
                        "Provide a comprehensive investment analysis in exactly 3 sections:\n"
                        "1. 📊 Summary of Findings (general market insights, up to 8 bullet points)\n"
                        "2. 🏢 Insights from PIF Logistics Company Dataset (specific company analysis)\n"
                        "3. 🔗 Relevant Articles (I will provide current articles separately)\n\n"
                        "Use bullet points for all content. Be specific and actionable."
                    )
                },
                {
                    "role": "user",
                    "content": (
                        f"Based on both general market knowledge and this PIF logistics dataset:\n{sample_data}\n\n"
                        f"User question: {query}\n\n"
                        "Provide comprehensive analysis covering general market insights and specific company data insights."
                    )
                }
            ]
            
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=comprehensive_messages,
                temperature=0.3
            )
            
            ai_analysis = response.choices[0].message.content
            
            # Get articles in parallel
            articles = fetch_perplexity_articles(query)
            
            # Combine sections
            if "3. 🔗 Relevant Articles" in ai_analysis:
                full_response = ai_analysis.replace("3. 🔗 Relevant Articles", f"3. 🔗 Relevant Articles\n{articles}")
            else:
                full_response = f"{ai_analysis}\n\n3. 🔗 Relevant Articles\n{articles}"
            
            return full_response
            
        except Exception as e:
            return f"Error: {e}"
    
    else:
        # Follow-up queries: Enhanced decision logic
        sample_data = df.sample(5).to_dict(orient="records")
        
        decision_messages = [
            {
                "role": "system",
                "content": (
                    "You are an intelligent routing assistant. Based on the user's question, determine what action to take:\n"
                    "1. If they want current articles, news, web search, or ask for 'more articles' → respond with 'SEARCH_WEB'\n"
                    "2. If they ask about companies in the dataset or previous response → respond with 'ANALYZE_DATA'\n"
                    "3. If they need to compare data with global/industry averages, benchmarks, margins, or external standards → respond with 'SEARCH_AND_ANALYZE'\n"
                    "4. If it's a general question → respond with 'GENERAL_RESPONSE'\n\n"
                    "Keywords that indicate SEARCH_AND_ANALYZE: compare, global, industry average, benchmark, market average, versus, vs, external comparison, EBITDA margin, profit margin, industry standard, typical range\n"
                    "Only respond with one of these four options: SEARCH_WEB, ANALYZE_DATA, SEARCH_AND_ANALYZE, or GENERAL_RESPONSE"
                )
            },
            {
                "role": "user",
                "content": f"User question: {query}"
            }
        ]
        
        try:
            decision_response = openai.chat.completions.create(
                model="gpt-4",
                messages=decision_messages,
                temperature=0.1
            )
            
            action = decision_response.choices[0].message.content.strip()
            
            if action == "SEARCH_WEB":
                articles = fetch_perplexity_articles(query)
                return f"Here are relevant articles about {query}:\n\n{articles}"
            
            elif action == "ANALYZE_DATA":
                analysis_messages = [
                    {
                        "role": "system",
                        "content": "You are a PIF analyst. Answer based on the company dataset provided."
                    },
                    {
                        "role": "user",
                        "content": f"Question: {query}\n\nCompany data: {sample_data}\n\nProvide specific analysis."
                    }
                ]
                
                analysis_response = openai.chat.completions.create(
                    model="gpt-4",
                    messages=analysis_messages,
                    temperature=0.3
                )
                
                return analysis_response.choices[0].message.content
            
            elif action == "SEARCH_AND_ANALYZE":
                # Enhanced search for benchmarking queries
                print(f"DEBUG: Executing SEARCH_AND_ANALYZE for query: {query}")
                
                # Create more specific search queries for benchmarking
                search_queries = [
                    f"global logistics industry EBITDA margin average benchmark 2024",
                    f"logistics companies profit margin industry standard",
                    f"transportation logistics sector financial performance metrics"
                ]
                
                # Search with multiple queries to get comprehensive data
                all_articles = []
                for search_query in search_queries:
                    articles = fetch_perplexity_articles(search_query)
                    all_articles.append(f"Search: {search_query}\n{articles}")
                
                combined_articles = "\n\n".join(all_articles)
                
                # Enhanced analysis with better context and source citation requirements
                combined_messages = [
                    {
                        "role": "system",
                        "content": (
                            "You are a PIF financial analyst. Compare the internal company data with external industry benchmarks. "
                            "IMPORTANT REQUIREMENTS:\n"
                            "1. Calculate specific metrics from the internal data and show your calculations\n"
                            "2. ALWAYS cite specific sources for external benchmark data using this format: 'According to [Source Name], global logistics EBITDA margins average X%'\n"
                            "3. If you cannot find specific benchmarks in the search results, use your knowledge but clearly state: 'Based on industry knowledge (typical ranges):'\n"
                            "4. Provide actionable investment insights based on the comparison\n"
                            "5. Include a 'Sources Referenced' section at the end listing all sources used\n"
                            "Use bullet points for all content."
                        )
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Question: {query}\n\n"
                            f"Internal PIF dataset (sample): {sample_data}\n\n"
                            f"External research results: {combined_articles}\n\n"
                            "Please provide:\n"
                            "1. Calculated average EBITDA margin from internal data (show calculation)\n"
                            "2. Global logistics industry EBITDA margin benchmarks (cite specific sources)\n"
                            "3. Detailed comparison and analysis\n"
                            "4. Investment implications and recommendations\n"
                            "5. Sources Referenced section\n\n"
                            "Remember to cite every external data point with its source."
                        )
                    }
                ]
                
                combined_response = openai.chat.completions.create(
                    model="gpt-4",
                    messages=combined_messages,
                    temperature=0.3
                )
                
                return combined_response.choices[0].message.content
            
            else:  # GENERAL_RESPONSE
                general_messages = [
                    {
                        "role": "system",
                        "content": "You are a knowledgeable financial analyst. Provide helpful insights."
                    },
                    {
                        "role": "user",
                        "content": query
                    }
                ]
                
                general_response = openai.chat.completions.create(
                    model="gpt-4",
                    messages=general_messages,
                    temperature=0.3
                )
                
                return general_response.choices[0].message.content
                
        except Exception as e:
            return f"Error: {e}"

def process_content_to_html(content):
    """Convert markdown content to HTML with proper header styling"""
    lines = content.split('\n')
    html_lines = []
    in_list = False
    
    for line in lines:
        line_stripped = line.strip()
        
        # Skip empty lines
        if not line_stripped:
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append('<br>')
            continue
        
        # Skip unwanted messages
        if ("Please provide relevant articles" in line_stripped or 
            "Please provide the relevant articles" in line_stripped or
            "I will provide current articles separately" in line_stripped or
            "these will be filled in separately" in line_stripped):
            continue
        
        # Handle main section headers (1. 📊 Summary of Findings, 2. 🏢 Insights, 3. 🔗 Relevant Articles)
        if re.match(r'^\d+\.\s+[📊🏢🔗]', line_stripped):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append(f'<h2>{line_stripped}</h2>')
            continue
        
        # Handle ## headers (like from perplexity)
        if line_stripped.startswith('## '):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            header_text = line_stripped[3:].strip()
            html_lines.append(f'<h2>{header_text}</h2>')
            continue
        
        # Handle subsection headers within sections (like "1. Investment Opportunities:")
        if re.match(r'^\d+\.\s+[A-Z]', line_stripped) and not re.match(r'^\d+\.\s+[📊🏢🔗]', line_stripped):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append(f'<h3 style="color: #2c2c2c; font-size: 1rem; font-weight: 600; margin: 1rem 0 0.5rem 0;">{line_stripped}</h3>')
            continue
        
        # Handle bullet points - everything else should be bullet points
        if line_stripped.startswith('• ') or line_stripped.startswith('- '):
            if not in_list:
                html_lines.append('<ul>')
                in_list = True
            item_text = line_stripped[2:].strip()
            # Convert markdown links within bullet points
            item_text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2" target="_blank">\1</a>', item_text)
            html_lines.append(f'<li>{item_text}</li>')
            continue
        
        # Handle markdown links [text](url) - these should be compact list items
        if '[' in line_stripped and '](' in line_stripped:
            if not in_list:
                html_lines.append('<ul>')
                in_list = True
            # Convert all markdown links in the line
            converted_line = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2" target="_blank">\1</a>', line_stripped)
            html_lines.append(f'<li>{converted_line}</li>')
            continue
        
        # Handle standalone URLs - should be bullet points
        if line_stripped.startswith('http'):
            if not in_list:
                html_lines.append('<ul>')
                in_list = True
            html_lines.append(f'<li><a href="{line_stripped}" target="_blank">{line_stripped}</a></li>')
            continue
        
        # All other text should be bullet points
        if not in_list:
            html_lines.append('<ul>')
            in_list = True
        html_lines.append(f'<li>{line_stripped}</li>')
    
    if in_list:
        html_lines.append('</ul>')
    
    return '\n'.join(html_lines)

# Sidebar for chat sessions
with st.sidebar:
    st.markdown("### 💬 Chat Sessions")
    
    # New chat button
    if st.button("➕ New Chat", key="new_chat_btn"):
        create_new_chat()
    
    st.markdown("---")
    
    # Display chat sessions
    for session_id, session_data in sorted(st.session_state.chat_sessions.items(), 
                                          key=lambda x: x[1]["created_at"], reverse=True):
        is_active = session_id == st.session_state.current_session_id
        
        if st.button(
            f"{'🟢' if is_active else '💬'} {session_data['title']}", 
            key=f"chat_{session_id}",
            help=f"Created: {session_data['created_at'].strftime('%Y-%m-%d %H:%M')}"
        ):
            load_chat_session(session_id)

# Main header
st.markdown("""
    <div class="top-banner">
        <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==" alt="PIF Logo" style="height: 50px; margin-right: 1rem; background: #00B04F; border-radius: 50%; padding: 10px;">
        <h1>Investment Agent</h1>
    </div>
""", unsafe_allow_html=True)

# Initialize first chat if none exists
if not st.session_state.chat_sessions:
    create_new_chat()

# Main content area
if not st.session_state.first_message_sent:
    # Reduced spacing to move content up
    st.markdown('<div style="height: 5vh;"></div>', unsafe_allow_html=True)
    
    # Show centered welcome message
    st.markdown("""
        <div style="text-align: center; max-width: 800px; margin: 0 auto; padding: 2rem;">
            <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); border-radius: 20px; padding: 3rem 2rem; margin-bottom: 2rem; box-shadow: 0 4px 20px rgba(0,0,0,0.05);">
                <h2 style="color: #00B04F; font-size: 2rem; margin-bottom: 1rem; font-weight: 600;">🤖 Welcome to PIF Investment Agent</h2>
                <p style="font-size: 1.1rem; line-height: 1.6; margin-bottom: 0.5rem; color: #666;">Your AI-powered investment research assistant</p>
                <p style="font-size: 1.1rem; line-height: 1.6; margin-bottom: 0.5rem; color: #666;">Ask me anything about finance, investments, or logistics companies in MENA region</p>
                <p style="margin-top: 1.5rem; font-size: 0.9rem; color: #888;">💡 Try: "Recommend investable last-mile logistics companies in Saudi Arabia"</p>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Centered input form
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        with st.form(key="chat_form_centered", clear_on_submit=True):
            user_input = st.text_area(
                "Ask a question...",
                placeholder="e.g., Recommend investable last-mile logistics companies in Saudi Arabia\n\nTip: Use Shift+Enter for new lines",
                label_visibility="collapsed",
                key="user_input_centered",
                height=100
            )
            submit_button = st.form_submit_button("Send", use_container_width=True)

else:
    # Show chat messages and bottom input when messages exist
    main_container = st.container()
    
    with main_container:
        # Chat messages area
        st.markdown('<div class="chat-messages">', unsafe_allow_html=True)
        
        if st.session_state.messages:
            for message in st.session_state.messages:
                if message["role"] == "user":
                    st.markdown(f"""
                        <div class="chat-message user-message">
                            <div class="message-content">
                                {message["content"]}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    # More thorough HTML cleaning for follow-up messages
                    content = message["content"]
                    
                    # Remove all HTML tags and artifacts
                    content = re.sub(r'<[^>]*>', '', content)
                    content = re.sub(r'&[a-zA-Z]+;', '', content)  # Remove HTML entities
                    
                    # Clean up whitespace
                    content = re.sub(r'\n\s*\n', '\n\n', content)
                    content = content.strip()
                    
                    # Convert markdown to HTML with proper header styling
                    processed_content = process_content_to_html(content)
                    
                    st.markdown(f"""
                        <div class="chat-message assistant-message">
                            <div class="message-content">
                                {processed_content}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Bottom input area
    st.markdown('<div class="input-container">', unsafe_allow_html=True)
    
    # Create Claude-style input container
    st.markdown('''
        <div class="claude-input-container">
        </div>
    ''', unsafe_allow_html=True)
    
    with st.form(key="chat_form_bottom", clear_on_submit=True):
        # Use wider layout for the input
        col1, col2 = st.columns([6, 1])
        
        with col1:
            user_input = st.text_area(
                "Ask a question...",
                placeholder="Continue the conversation...\n\nTip: Use Shift+Enter for new lines",
                label_visibility="collapsed",
                key="user_input_bottom",
                height=80
            )
        
        with col2:
            # Add some vertical spacing to align button
            st.markdown('<div style="height: 20px;"></div>', unsafe_allow_html=True)
            submit_button = st.form_submit_button("Send", use_container_width=True)
    
    # Add hint text
    st.markdown('<p class="input-hint">💡 Tip: Use Shift+Enter to add new lines, Enter to send</p>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

def validate_responsible_ai(user_input):
    """Validate user input against responsible AI guidelines"""
    user_input_lower = user_input.lower()
    
    # Define violation patterns
    violations = {
        # PII patterns
        'pii': [
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN pattern
            r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',  # Credit card pattern
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email pattern
        ],
        
        # Harmful content keywords
        'harmful': [
            'racial slur', 'discrimination', 'violence against', 'hate speech',
            'terrorist', 'terrorism', 'bomb', 'explosive', 'weapon', 'gun',
            'suicide', 'self harm', 'kill yourself', 'harm others',
            'sexual content', 'explicit', 'pornographic', 'arousal',
            'gambling', 'casino', 'betting', 'illegal drugs', 'pharmaceuticals',
            'phishing', 'scam', 'fraud', 'illegal activity', 'jailbreak',
            'threaten', 'intimidate', 'bully', 'abuse', 'harass'
        ]
    }
    
    # Check for PII patterns
    for pattern in violations['pii']:
        if re.search(pattern, user_input):
            return False
    
    # Check for harmful content keywords
    for keyword in violations['harmful']:
        if keyword in user_input_lower:
            return False
    
    return True

# Handle form submission
if submit_button and user_input:
    # Validate input against responsible AI guidelines
    if not validate_responsible_ai(user_input):
        st.error("These are not part of the Responsible AI Framework")
        st.stop()
    
    # Mark first message as sent
    st.session_state.first_message_sent = True
    
    # Add user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Determine if this is the first query
    is_first_query = len([msg for msg in st.session_state.messages if msg["role"] == "user"]) == 1
    
    # Show loading state
    with st.spinner("🤖 Analyzing investment opportunities..."):
        ai_response = get_ai_response(user_input, is_first_query)
    
    # Add AI response
    st.session_state.messages.append({"role": "assistant", "content": ai_response})
    
    # Save session
    save_current_session()
    
    # Rerun to show new messages
    st.rerun()