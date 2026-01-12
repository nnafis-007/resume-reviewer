import streamlit as st
import requests
import time
import os

# Page Config
st.set_page_config(
    page_title="SeeV - Elite Career Critique",
    page_icon="🚀",
    layout="centered"
)

# Custom CSS for minimal look
st.markdown("""
<style>
    .main {
        padding-top: 2rem;
    }
    .stButton>button {
        width: 100%;
        background-color: #000000;
        color: white;
        border-radius: 5px;
        font-weight: bold;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #333333;
        border-color: #333333;
        color: #FFFFFF;
    }
    h1 {
        text-align: center;
        font-family: 'Helvetica', sans-serif;
        font-weight: 700;
    }
    .subtitle {
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
        font-size: 1.2rem;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f0fff4;
        border: 1px solid #c6f6d5;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Application Header
st.title("SeeV 🚀")
st.markdown('<p class="subtitle">Turn your resume into an interview magnet with executive-level AI analysis.</p>', unsafe_allow_html=True)

# Backend URL Configuration
# In Docker, we can address the backend service by its service name, e.g., http://backend:8000
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
API_ENDPOINT = f"{BACKEND_URL}/api/v1/review"

# File Upload Section
uploaded_file = st.file_uploader("Upload your Resume (PDF)", type="pdf", help="Upload a PDF file of your resume for analysis.")

if uploaded_file is not None:
    # Submit Button
    if st.button("Get a Professional Review"):
        
        # Loading State
        progress_text = "Analyzing document structure..."
        my_bar = st.progress(0, text=progress_text)
        
        try:
            # Simulate stages for better UX
            loading_messages = [
                "Scanning visual layout and hierarchy...",
                "Extracting key competencies and metrics...",
                "Benchmarking against industry standards...",
                "Drafting executive summary..."
            ]
            
            # Prepare the file for the request
            files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
            
            # Make request to backend (assuming default port 8000)
            # We use a session to handle potential keep-alive connection issues
            with requests.Session() as s:
                # Update progress visually while request is processing (simulated since request is blocking)
                # In a real async frontend we'd poll, but for Streamlit checking response is blocking.
                # We can just show a spinner wrapper around the request.
                
                with st.spinner("consulting our AI career coaches..."):
                    # For visual effect, let's fast iterate messages
                    for i, msg in enumerate(loading_messages):
                        my_bar.progress((i + 1) * 20, text=msg)
                        time.sleep(2)  # Simulate time taken for each stage
                    
                    response = s.post(API_ENDPOINT, files=files)
                    my_bar.progress(100, text="Analysis Complete!")
            
            if response.status_code == 200:
                result = response.json()
                review_text = result.get("review", "No review generated.")
                
                # Render the Review
                st.divider()
                st.markdown("### 🎯 Executive Analysis Result")
                st.markdown("---")
                
                # The review comes in Markdown, so we render it directly.
                st.markdown(review_text)
                
                # Success Cue
                st.toast("Review generated successfully!", icon="✅")
                
            elif response.status_code == 413:
                st.error("File is too large. Please upload a PDF smaller than 5MB.")
            else:
                st.error(f"Error: {response.status_code} - {response.text}")
                
        except requests.exceptions.ConnectionError:
            st.error(f"Could not connect to the analysis server at {BACKEND_URL}. Is the backend running?")
        except Exception as e:
            st.error(f"An unexpected error occurred: {str(e)}")

# Footer
st.markdown("---")
st.markdown(
    """<div style='text-align: center; color: #888; font-size: 0.8rem;'>
    Powered by <strong>Gemma 3 Vision</strong> & <strong>FastAPI</strong>
    </div>""", 
    unsafe_allow_html=True
)
