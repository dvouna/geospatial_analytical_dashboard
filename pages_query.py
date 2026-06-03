"""
Gemini Query Page
Natural language data querying with Google Gemini API
"""

import streamlit as st
import pandas as pd
from data_loader import load_sample_dataset
from gemini_queries import GeminiQueryEngine
from visualizer import get_numeric_columns, get_categorical_columns


def render_research_assistant_page():
    st.title("🤖 Research Assistant")
    st.write("Use natural language to ask questions about your dataset.")

    st.sidebar.header("📁 Data Source")
    data_source = st.sidebar.radio("Select data source:", ["Sample Data", "Upload CSV"], key="query_source")

    if data_source == "Sample Data":
        sample_options = ["Sample Sales Data", "Sample Locations Data"]
        selected_sample = st.sidebar.selectbox("Choose a sample dataset:", sample_options)

        if selected_sample == "Sample Sales Data":
            df = load_sample_dataset('sample_sales')
        else:
            df = load_sample_dataset('sample_locations')
    else:
        uploaded_file = st.sidebar.file_uploader("Choose a CSV file", type="csv", key="query_upload")
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
            st.sidebar.success("✅ File uploaded successfully")
        else:
            df = None

    if df is not None:
        engine = GeminiQueryEngine()

        if not engine.is_available():
            st.warning(
                "⚠️ **Gemini API is not configured.**\n\n"
                "To enable AI-powered queries:\n"
                "1. Get your Gemini API key from Google AI Studio\n"
                "2. Add it to your `.env` file: `GEMINI_API_KEY=your_key_here`\n"
                "3. Restart the Streamlit app"
            )
            st.info("In the meantime, you can still explore your data.")

        st.sidebar.subheader("💡 Example Queries")
        example_queries = [
            "What is the average value in this dataset?",
            "Show me the top 5 items by sales",
            "What patterns do you see in the data?",
            "Calculate the total and percentage by region",
            "Are there any outliers in the data?",
        ]

        for example in example_queries:
            st.sidebar.caption(f"• {example}")

        st.subheader("❓ Ask a Question")
        col1, col2 = st.columns([4, 1])
        with col1:
            user_query = st.text_input(
                "Enter your question about the data:",
                placeholder="e.g., What is the average sales by region?",
                label_visibility="collapsed"
            )
        with col2:
            submit_button = st.button("🔍 Query", type="primary", use_container_width=True)

        if submit_button and user_query:
            if engine.is_available():
                with st.spinner("🤔 Analyzing your data..."):
                    result = engine.analyze_dataset(df, user_query)

                if result:
                    if result.get('status') == 'success':
                        st.success("✅ Analysis Complete")
                        st.markdown(result.get('response', ''))
                    else:
                        st.error(f"❌ {result.get('response', 'An error occurred')}")
            else:
                st.warning("Please configure the Gemini API key first.")

        st.divider()
        st.subheader("📊 Automatic Insights")

        if st.button("Generate Insights", key="generate_insights"):
            if engine.is_available():
                with st.spinner("🤔 Generating insights..."):
                    insights = engine.generate_insights(df)
                if insights:
                    st.markdown(insights)
            else:
                st.warning("Please configure the Gemini API key first.")

        st.divider()
        st.subheader("📈 Visualization Suggestions")

        if st.button("Suggest Visualizations", key="suggest_viz"):
            if engine.is_available():
                with st.spinner("🤔 Suggesting visualizations..."):
                    suggestions = engine.suggest_visualizations(df)
                if suggestions:
                    st.markdown(suggestions)
            else:
                st.warning("Please configure the Gemini API key first.")

        st.divider()
        st.subheader("🔍 Data Overview")
        tab1, tab2, tab3 = st.tabs(["Preview", "Statistics", "Columns"])

        with tab1:
            st.dataframe(df.head(10), use_container_width=True)

        with tab2:
            st.write("**Numeric Columns Summary:**")
            numeric_cols = get_numeric_columns(df)
            if numeric_cols:
                st.dataframe(df[numeric_cols].describe(), use_container_width=True)
            else:
                st.info("No numeric columns found")

        with tab3:
            st.write(f"**Total Columns: {len(df.columns)}**")
            col_info = pd.DataFrame({
                'Column': df.columns,
                'Type': df.dtypes.values,
                'Non-Null Count': df.count().values,
                'Null Count': df.isnull().sum().values
            })
            st.dataframe(col_info, use_container_width=True)
    else:
        st.info("👆 Please select a data source to get started")


if __name__ == "__main__":
    render_research_assistant_page()
