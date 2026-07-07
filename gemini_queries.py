"""
Gemini Query Engine Module
Handles natural language queries via Google Gemini API
"""

import streamlit as st
import pandas as pd
from typing import Optional, Dict, Any
from config import Config

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class GeminiQueryEngine:
    """Interface for querying data using Gemini API"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini API
        
        Args:
            api_key: Google Gemini API key (from config if not provided)
        """
        self.api_key = api_key or Config.GEMINI_API_KEY
        self.model = None
        self.model_name = Config.GEMINI_MODEL
        self.max_tokens = Config.GEMINI_MAX_TOKENS
        self.temperature = Config.GEMINI_TEMPERATURE
        
        if GEMINI_AVAILABLE and self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(self.model_name)
            except Exception as e:
                st.error(f"Failed to initialize Gemini: {str(e)}")
    
    def is_available(self) -> bool:
        """Check if Gemini API is properly configured"""
        return self.model is not None
    
    def analyze_dataset(self, df: pd.DataFrame, query: str) -> Optional[Dict[str, Any]]:
        """
        Analyze dataset using natural language query
        
        Args:
            df: pandas DataFrame
            query: Natural language question
            
        Returns:
            Dictionary with analysis results or None if API unavailable
        """
        if not self.is_available():
            return None
        
        try:
            # Prepare dataset summary for Gemini
            dataset_info = self._prepare_dataset_info(df)
            
            # Create prompt for Gemini
            prompt = self._create_analysis_prompt(dataset_info, query)
            
            # Get response from Gemini
            response = self.model.generate_content(prompt)
            
            return {
                'query': query,
                'response': response.text,
                'status': 'success'
            }
        except Exception as e:
            return {
                'query': query,
                'response': f"Error: {str(e)}",
                'status': 'error'
            }
    
    def generate_insights(self, df: pd.DataFrame) -> Optional[str]:
        """
        Generate automatic insights from dataset
        
        Args:
            df: pandas DataFrame
            
        Returns:
            String with insights or None if API unavailable
        """
        if not self.is_available():
            return None
        
        try:
            dataset_info = self._prepare_dataset_info(df)
            prompt = f"""
Given this dataset summary:
{dataset_info}

Please provide 3-5 key insights about this data. Be concise and specific.
Focus on:
1. Data structure and quality
2. Interesting patterns or trends
3. Potential analysis opportunities
"""
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error generating insights: {str(e)}"
    
    def suggest_visualizations(self, df: pd.DataFrame) -> Optional[str]:
        """
        Suggest visualizations based on dataset
        
        Args:
            df: pandas DataFrame
            
        Returns:
            String with visualization suggestions
        """
        if not self.is_available():
            return None
        
        try:
            dataset_info = self._prepare_dataset_info(df)
            prompt = f"""
Given this dataset:
{dataset_info}

What are the best visualizations to create? Suggest 3-4 charts that would provide the most insights.
For each suggestion, mention:
- Chart type
- Which columns to use
- Why this chart is appropriate
"""
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error generating suggestions: {str(e)}"
    
    @staticmethod
    def _prepare_dataset_info(df: pd.DataFrame) -> str:
        """
        Prepare dataset summary for Gemini analysis
        
        Args:
            df: pandas DataFrame
            
        Returns:
            Formatted string with dataset information
        """
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
        
        info = f"""
Dataset Summary:
- Shape: {df.shape[0]} rows × {df.shape[1]} columns
- Numeric columns ({len(numeric_cols)}): {', '.join(numeric_cols[:5])}
- Categorical columns ({len(categorical_cols)}): {', '.join(categorical_cols[:5])}
- Missing values: {df.isnull().sum().sum()}
- Date range: {df.dtypes}

First few rows:
{df.head(3).to_string()}

Basic statistics:
{df.describe().to_string()}
"""
        return info
    
    @staticmethod
    def _create_analysis_prompt(dataset_info: str, query: str) -> str:
        """
        Create a prompt for Gemini analysis
        
        Args:
            dataset_info: Dataset summary
            query: User query
            
        Returns:
            Formatted prompt
        """
        return f"""
You are a data analyst assistant. A user has asked a question about their dataset.

Dataset Information:
{dataset_info}

User Question: {query}

Please provide:
1. A direct answer to their question
2. Any relevant insights from the data
3. Suggested next steps or follow-up analysis

Be concise but informative. If you cannot answer from the data, explain why.
"""


def query_data_with_gemini(df: pd.DataFrame, query: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to query data with Gemini
    
    Args:
        df: pandas DataFrame
        query: Natural language question
        api_key: Gemini API key (optional)
        
    Returns:
        Dictionary with query results
    """
    engine = GeminiQueryEngine(api_key)
    
    if not engine.is_available():
        return {
            'query': query,
            'response': "Gemini API is not configured. Please set GEMINI_API_KEY environment variable.",
            'status': 'unavailable'
        }
    
    return engine.analyze_dataset(df, query)
