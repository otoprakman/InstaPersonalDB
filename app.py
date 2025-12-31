import streamlit as st
import os
from pathlib import Path

# Import our modules
# Ensure we can import from src
import sys
sys.path.append(str(Path(__file__).parent))

from src.ingest import load_shortcodes, download_post
from src.processor import process_pipeline
from src.rag_db import ingest_document, query_similar, document_exists

st.set_page_config(page_title="InstaRAG", layout="wide")

st.title("Instagram Saved Posts RAG")

# Sidebar for controls
with st.sidebar:
    st.header("Pipeline Controls")
    
    json_path = st.text_input("Path to saved_posts.json", "saved_posts.json")
    
    if st.button("Run Pipeline (Ingest -> Process -> Index)"):
        if not os.path.exists(json_path):
            st.error(f"File not found: {json_path}")
        else:
            with st.status("Running Pipeline...", expanded=True) as status:
                st.write("Parsing JSON...")
                shortcodes = load_shortcodes(json_path)
                st.write(f"Found {len(shortcodes)} posts.")
                
                progress_bar = st.progress(0)
                for i, code in enumerate(shortcodes):
                    st.write(f"Processing {code}...")
                    
                    # Optimization: Skip if already in DB (and we assume raw data is there too)
                    if document_exists(code):
                         st.info(f"Skipping {code} (Already indexed)")
                         progress_bar.progress((i + 1) / len(shortcodes))
                         continue

                    # 1. Download
                    download_post(code)
                    
                    # 2. Process
                    result = process_pipeline(code)
                    
                    # 3. Index
                    if result:
                        ingest_document(
                            result['shortcode'], 
                            result['content'], 
                            result['image_path']
                        )
                    
                    progress_bar.progress((i + 1) / len(shortcodes))
                    
                status.update(label="Pipeline Completed!", state="complete", expanded=False)

    st.header("AI Settings")
    llm_provider = st.radio("Model Provider", ["Ollama (Local)", "OpenAI (Cloud)"])
    
    openai_api_key = ""
    if llm_provider == "OpenAI (Cloud)":
        openai_api_key = st.text_input("OpenAI API Key", type="password")

# Main Search Interface
# Main Search Interface
query = st.text_input("Ask a question about your saved posts:", placeholder="Which movie should I watch today?")

if query:
    # Increase recall: Fetch more results (15) to ensure we capture all relevant content
    results = query_similar(query, n_results=15)
    
    ids = results['ids'][0]
    docs = results['documents'][0]
    metadatas = results['metadatas'][0]
    distances = results['distances'][0]
    
    # helper to check if model is available
    try:
        from langchain_community.chat_models import ChatOllama
        from langchain_openai import ChatOpenAI
        from langchain.schema import HumanMessage, SystemMessage
        
        llm = None
        if llm_provider == "Ollama (Local)":
            # We'll use a small model - assuming user has pulled it. 
            llm = ChatOllama(model="llama3.2", base_url="http://localhost:11434")
        else:
            if not openai_api_key:
                st.warning("Please enter your OpenAI API Key in the sidebar.")
                st.stop()
            llm = ChatOpenAI(model="gpt-4o-mini", api_key=openai_api_key)
        
        # Construct Context
        # Truncate likely long posts to fit more into context window
        context_text = ""
        for i, (doc, shortcode) in enumerate(zip(docs, ids)):
            # safe_doc = doc[:1000] 
            context_text += f"\n[Post {shortcode}]: {doc}\n"

        prompt = f"""
You are an intelligent assistant summarizing personal saved Instagram posts.
User Query: "{query}"

Here are the retrieved posts (may be truncated):
{context_text}

INSTRUCTIONS:
1. Analyze the provided posts to find information answering the User Query.
2. If the user asks for a LIST, clearly itemize the findings.
3. Combine details from multiple posts if they talk about the same topic.
4. If NO posts look relevant in the context, state "I couldn't find specific details in the retrieved posts" and provide a general answer.
5. Provide a helpful, concise summary. Do not output any special parsing codes.
"""
        with st.spinner("Synthesizing Summary..."):
            try:
                # Get integration
                response = llm.invoke([HumanMessage(content=prompt)])
                final_answer = response.content
                
                st.markdown("### AI Summary")
                st.write(final_answer)
                
                st.divider()
                st.subheader(f"Retrieved Posts ({len(ids)})")
                st.caption("These are the most similar posts found in your library.")
                
                for i in range(len(ids)):
                    c_id = ids[i]
                    c_doc = docs[i]
                    c_meta = metadatas[i]
                    
                    with st.container(border=True):
                        col1, col2 = st.columns([1, 3])
                        
                        with col1:
                            img_path = c_meta.get('image_path')
                            if img_path and os.path.exists(img_path):
                                st.image(img_path, width=150)
                            else:
                                st.write("No Image")
                        
                        with col2:
                            st.markdown(f"**[Link to Post](https://www.instagram.com/p/{c_id}/)**")
                            st.caption(f"Shortcode: {c_id}")
                            # Show a preview of the content derived from the doc text
                            with st.expander("Show Content Preview"):
                                st.text(c_doc) 
                     
            except Exception as e:
                st.error(f"Error communicating with AI Provider ({llm_provider}): {e}")
                if llm_provider == "Ollama (Local)":
                    st.info("Make sure Ollama is running (ollama serve) and you have the model (ollama pull llama3.2).")
                # Fallback to old view logic if LLM completely fails
                st.subheader("Raw Results (Fallback)")
                for i in range(len(ids)):
                     st.text(docs[i][:200])
                    
    except ImportError:
         st.error("LangChain community not installed?")
