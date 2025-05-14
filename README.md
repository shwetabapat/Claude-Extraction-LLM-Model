# Trade Document Analyzer

This application analyzes trade documents using AI to identify insights and discrepancies. It uses Claude 3.7 Sonnet for document analysis and provides a modern web interface for document upload and analysis.

## Features

- Upload multiple trade documents (minimum 2)
- AI-powered analysis using Claude 3.7 Sonnet
- Modern, responsive web interface
- Real-time document analysis
- Detailed insights and discrepancy reporting

## Prerequisites

- Python 3.8+
- Node.js 14+
- Anthropic API key

## Setup

### Backend Setup

1. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Update the Anthropic API key in `backend/main.py`:
```python
client = Anthropic(api_key="your-api-key-here")
```

4. Run the backend server:
```bash
cd backend
uvicorn main:app --reload
```

### Frontend Setup

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Start the development server:
```bash
npm start
```

## Usage

1. Open your browser and navigate to `http://localhost:3000`
2. Upload at least 2 trade documents (PDF or images)
3. Click "Analyze Documents" to start the analysis
4. View the insights and discrepancies in the results section

## API Endpoints

- POST `/api/analyze-documents`: Upload and analyze documents
  - Accepts multiple files
  - Returns insights and discrepancies

## Technologies Used

- Backend: Python, FastAPI
- Frontend: React, TypeScript, Material-UI
- AI: Claude 3.7 Sonnet
- File Handling: react-dropzone 