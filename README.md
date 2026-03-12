# 🔍 SEO Audit Agent
**Built by Saddam Adil — AI-Augmented SEO Specialist**

Automatically audits any website for 20+ SEO factors and generates
AI-powered fix recommendations using Google Gemini (FREE).

## What It Checks
- ✅ Title tag, Meta description, H1/H2/H3 structure
- ✅ Image alt texts, Internal links, Word count
- ✅ SSL, Mobile viewport, Canonical tags
- ✅ Schema markup, Open Graph tags, Robots meta
- ✅ Core Web Vitals (FCP, LCP, CLS, TBT)
- ✅ Broken links, Server response time
- ✅ PageSpeed scores (Performance, SEO, Accessibility)
- ✅ AI recommendations via Gemini

## Setup (5 minutes)

### Step 1 — Get Free Gemini API Key
1. Go to https://aistudio.google.com/apikey
2. Click "Create API Key"
3. Copy the key

### Step 2 — Install & Run
```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# Run the server
python app.py
```

### Step 3 — Open Dashboard
Go to: http://localhost:5000

## Deploy to Web (Free)
### Railway.app
1. Push to GitHub
2. Connect Railway → deploy
3. Add GEMINI_API_KEY in Variables

### Render.com
1. Push to GitHub  
2. New Web Service → connect repo
3. Build: `pip install -r requirements.txt`
4. Start: `python app.py`
5. Add GEMINI_API_KEY in Environment

## Add to Your Portfolio
This agent demonstrates:
- Python backend development
- AI API integration (Gemini)
- SEO technical knowledge
- Web scraping (BeautifulSoup)
- Full-stack development (Flask + HTML/CSS/JS)
