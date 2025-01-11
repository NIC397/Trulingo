import streamlit as st
import pandas as pd
from source_retrieval import SourceRetriever
from googletrans import Translator

class SourceRetrieverUI:
    def __init__(self):
        self.retriever = None  # Initialize later with API key if provided
        self.translator = Translator()

    def translate_text(self, text, dest_lang):
        """Translate text to the destination language."""
        detected_lang = self.translator.detect(text).lang
        if dest_lang == detected_lang:
            return text
        else:
            return self.translator.translate(text, dest=dest_lang).text

    def render_article_info(self, idx: int, row: pd.Series, lang: str):
        """Render article information in the Streamlit UI."""
        def escape_markdown(text):
            """Escape markdown special characters."""
            if not isinstance(text, str):
                return text
            
            # Characters to escape: * _ ` [ ] ( ) # + - . ! { } > |
            special_chars = ['$', '*', '_', '`', '[', ']', '(', ')', '#', '+', '-', '.', '!', '{', '}', '>', '|']
            for char in special_chars:
                text = text.replace(char, '\\' + char)
            return text

        title = escape_markdown(str(row['title']) if row['title'] else row['url'][:100])
        with st.expander(f"{self.translate_text('Source', lang)} {idx + 1}: {title}..."):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**{self.translate_text('Source Website', lang)}:**")
                st.write(escape_markdown(str(row['source'])))
                st.write(f"**{self.translate_text('URL', lang)}:**")
                st.markdown(row['url'])  # Don't escape URLs
                
            with col2:
                st.write(f"**{self.translate_text('Publication Date', lang)}:**")
                st.write(row['date'].strftime('%Y-%m-%d') if pd.notnull(row['date']) else self.translate_text('Date not available', lang))
                if row['authors']:
                    st.write(f"**{self.translate_text('Authors', lang)}:**")
                    st.write(escape_markdown(", ".join(row['authors'])))
            
            st.write(f"**{self.translate_text('Content', lang)}:**")
            st.write(escape_markdown(str(row['content'])))

    def render_search_results(self, results_df: pd.DataFrame, lang: str):
        """Render search results in the Streamlit UI."""
        st.subheader(self.translate_text("Search Results", lang))
        if not results_df.empty:
            tab1, tab2 = st.tabs([self.translate_text("English Sources", lang), self.translate_text("Chinese Sources", lang)])

            with tab1:
                for idx, row in results_df[results_df['language'] == 'en'].iterrows():
                    self.render_article_info(idx, row, lang)

            with tab2:
                for idx, row in results_df[results_df['language'] == 'zh'].iterrows():
                    self.render_article_info(idx, row, lang)

            # Add download button for CSV
            st.download_button(
                label=self.translate_text("Download results as CSV", lang),
                data=results_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig'),
                file_name='search_results.csv',
                mime='text/csv',
            )
        else:
            st.warning(self.translate_text("No results found. Please ensure your API Keys are correct and try again.", lang))

    def render_verification_result(self, verification_result, lang: str, raw_response=None):
        """Render verification results in the Streamlit UI."""
        st.subheader(self.translate_text("LLM Verification Results", lang))
        
        # Show raw response in expander if available
        if raw_response:
            with st.expander(self.translate_text("Show Raw Gemini Response", lang)):
                st.text(raw_response)
        
        if verification_result:
            st.write(f"**{self.translate_text('Your Query', lang)}:** {verification_result['claim']}")
            
            st.subheader(self.translate_text("English Context Summary", lang))
            st.write(self.translate_text(verification_result['english_summary'], lang))
            
            st.subheader(self.translate_text("Chinese Context Summary", lang))
            st.write(self.translate_text(verification_result['chinese_summary'], lang))
            
            st.subheader(self.translate_text("Comparison", lang))
            st.write(self.translate_text(verification_result['comparison'], lang))
            
            st.subheader(self.translate_text("Conclusion", lang))
            st.write(self.translate_text(verification_result['conclusion'], lang))
        else:
            st.error(self.translate_text("Could not parse Gemini response into the expected format", lang))

    def main(self):
        """Main UI rendering function."""

        # Language selection
        if 'lang' not in st.session_state:
            st.session_state.lang = 'en'
        lang = st.session_state.lang

        # Title
        title = "图灵搜 🌍" if lang == 'zh-cn' else "Trulingo 🌍"
        st.title(title)
        
        # Language toggle button
        st.sidebar.header(f"{self.translate_text('Language', lang)} 🌐")
        toggle_button_label = "Switch to English" if st.session_state.lang == 'zh-cn' else "切换为中文"

        with st.sidebar.expander(toggle_button_label):
            warning_text = "The page will refresh and all previous results will be lost. Continue?" if st.session_state.lang == 'zh-cn' else "页面将会刷新，已有的结果将会丢失。继续吗？"
            st.warning(warning_text)
            if st.button("OK", key='lang_toggle'):
                st.session_state.lang = 'en' if st.session_state.lang == 'zh-cn' else 'zh-cn'
                st.rerun()  # Force a rerun to immediately reflect the language change

        lang = st.session_state.lang

        # API Key input in sidebar
        with st.sidebar:
            st.sidebar.header(f"{self.translate_text('Options', lang)} ⚙️")
            google_api_key = st.text_input(f"{self.translate_text('Enter Google Custom Search JSON API Key:', lang)} *", type="password")
            cse_id = st.text_input(f"{self.translate_text('Enter Google CSE ID:', lang)} *", type="password")
            api_key = None
            verify_enabled = st.session_state.get('verify_enabled', False)
            
            if verify_enabled:
                st.caption(self.translate_text("LLM Analysis is enabled.", lang))
                with st.expander(self.translate_text("Disable LLM Analysis", lang)):
                    st.warning(self.translate_text("Disabling this option will refresh the page and all previous results will be lost.", lang))
                    if st.button("OK", key='disable_llm'):
                        st.session_state.verify_enabled = False
                        st.rerun()  # Force a rerun to immediately reflect the change
                api_key = st.text_input(self.translate_text("Enter Gemini API Key *:", lang), type="password")
            else:
                st.caption(self.translate_text("LLM Analysis is disabled.", lang))
                with st.expander(self.translate_text("Enable LLM Analysis", lang)):
                    st.warning(self.translate_text("Enabling this option will refresh the page and all previous results will be lost.", lang))
                    if st.button("OK", key='enable_llm'):
                        st.session_state.verify_enabled = True
                        st.rerun()  # Force a rerun to immediately reflect the change

        # Initialize retriever with API keys if provided
        self.retriever = SourceRetriever(gemini_api_key=api_key if verify_enabled else None, google_api_key=google_api_key, cse_id=cse_id)
        
        # Input section
        st.subheader(self.translate_text("Multilingual News Aggregator", lang))
        claim = st.text_area(self.translate_text("Verify News Here:", lang), height=100)
        
        # Checkbox selection for news sources
        st.subheader(self.translate_text("Select News Sources", lang))
        sources_en = st.checkbox(self.translate_text("English Sources", lang), value=True)
        sources_zh = st.checkbox(self.translate_text("Chinese Sources", lang), value=True)
        
        # Number of articles to retrieve per source
        num_results = st.slider(self.translate_text("Number of articles to retrieve per source:", lang), 
                              min_value=1, max_value=5, value=1)
        
        # Search button
        if st.button(self.translate_text("Search!", lang)):
            if not google_api_key or not cse_id or (verify_enabled and not api_key):
                st.warning(self.translate_text("Please enter all required API Keys.", lang))
            elif not claim:
                st.warning(self.translate_text("Please enter a piece of news to verify.", lang))
            elif claim:
                with st.spinner(self.translate_text('Searching and analyzing...', lang)):
                    try:
                        selected_sources = {
                            'en': sources_en,
                            'zh-cn': sources_zh
                        }
                        results_df = self.retriever.search_and_process_articles(
                            claim, selected_sources, num_results=num_results, verify=verify_enabled
                        )
                        self.render_search_results(results_df, lang)
                        
                        # Display verification results if available
                        if verify_enabled:
                            raw_response = results_df.attrs.get('raw_gemini_response')
                            verification_result = results_df.attrs.get('verification')
                            self.render_verification_result(verification_result, lang, raw_response)
                    except Exception as e:
                        st.error(self.translate_text(f"An error occurred: {str(e)}", lang))

if __name__ == "__main__":
    app = SourceRetrieverUI()
    app.main()