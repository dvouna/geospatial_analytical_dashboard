# Streamlit Data Visualization & Gemini Query Project

An interactive Streamlit web application for visualizing tabular and geospatial data with natural language querying via Google Gemini API.

## Features

- **📊 Interactive Dashboards**: Visualize data with Plotly charts, filters, and exports
- **🗺️ Geospatial Mapping**: Interactive maps with Folium for location-based data
- **🤖 Gemini AI Integration**: Query data using natural language questions
- **📁 Multi-Dataset Support**: Load and switch between CSV files
- **🔄 Data Caching**: Optimized performance with Streamlit caching

## Project Structure

```
.
├── app.py                  # Main Streamlit application
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── .gitignore             # Git ignore rules
├── .streamlit/
│   └── config.toml        # Streamlit configuration
├── pages/
│   ├── 1_dashboard.py     # Dashboard & visualization page
│   ├── 2_maps.py          # Geospatial visualization page
│   └── 3_query.py         # Gemini query interface
├── modules/
│   ├── data_loader.py     # Data loading and caching
│   ├── visualizer.py      # Visualization utilities
│   ├── gemini_queries.py   # Gemini integration
│   └── utils.py           # Helper functions
└── data/
    └── sample_data.csv    # Sample dataset for demo
```

## Installation

1. Clone the repository:
```bash
git clone <repo-url>
cd flc26
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env and add your Gemini API key
```

5. Run the Streamlit app:
```bash
streamlit run app.py
```

The app will be available at `http://localhost:8501`

## Configuration

### Environment Variables
- `GEMINI_API_KEY`: Your Google Gemini API key (required for AI features)
- `STREAMLIT_SERVER_PORT`: Port for Streamlit server (default: 8501)
- `STREAMLIT_SERVER_ADDRESS`: Server address (default: localhost)

### Streamlit Config
Edit `.streamlit/config.toml` for additional Streamlit settings.

## Deployment

### Docker Deployment
```bash
docker build -t streamlit-app .
docker run -p 8501:8501 --env-file .env streamlit-app
```

### Production with Gunicorn
```bash
gunicorn --bind 0.0.0.0:8000 --workers 1 --worker-class sync --timeout 3600 \
  -k uvicorn.workers.UvicornWorker app:app
```

### WordPress Integration
- **Subdomain**: `app.yourdomain.com`
- **Reverse Proxy**: Configure Nginx to route `/dashboard` to Streamlit backend
- **iframe Embedding**: Use WordPress shortcode to embed Streamlit pages

## Usage

1. **Home Page**: Select and explore available datasets
2. **Dashboard**: View tabular data with charts and interactive filters
3. **Maps**: Visualize geospatial data on interactive maps
4. **Query**: Use natural language to ask questions about your data

## Security Considerations

- Never commit `.env` file with real API keys
- Use `.env.example` as a template for developers
- Restrict Gemini API key to production domain only
- Validate all user inputs before passing to Gemini
- Use HTTPS in production

## Troubleshooting

### Streamlit not starting
- Check Python version (3.8+)
- Verify all dependencies: `pip list`
- Clear cache: `streamlit cache clear`

### Gemini API errors
- Verify API key in `.env`
- Check API quota and rate limits
- Ensure internet connection

### Data loading issues
- Check CSV file format and encoding
- Verify file paths are correct
- Check data for missing values

## Contributing

1. Create a feature branch
2. Make changes and test locally
3. Submit a pull request

## License

MIT License

## Support

For issues or questions, please open an issue on GitHub.
