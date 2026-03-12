"""
SEO Audit Agent — Backend
Uses: Python + BeautifulSoup + Gemini AI + PageSpeed API
Run: pip install -r requirements.txt
     python app.py
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import os, re, time, json
from urllib.parse import urljoin, urlparse
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='static')
CORS(app)

# ── Gemini Setup ─────────────────────────────────────────────────────────────
genai.configure(api_key=os.getenv('AIzaSyC9BFnYowBjIwWZjGk373Pe4qdthnvSOXw'))
model = genai.GenerativeModel('gemini-1.5-flash')  # Free model

PAGESPEED_API = os.getenv('AIzaSyBaya6GbLWe6ZmBpDdhk9yHiYGdoWHY1nw', '')  # Optional - free from Google

# ── Helpers ───────────────────────────────────────────────────────────────────
def fetch_page(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (SEO-Audit-Agent/1.0)'}
        r = requests.get(url, headers=headers, timeout=15)
        return r.text, r.status_code, r.elapsed.total_seconds()
    except Exception as e:
        return None, 0, 0

def get_pagespeed(url):
    try:
        api_url = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={url}&strategy=mobile"
        if PAGESPEED_API:
            api_url += f"&key={PAGESPEED_API}"
        r = requests.get(api_url, timeout=30)
        data = r.json()
        cats = data.get('lighthouseResult', {}).get('categories', {})
        audits = data.get('lighthouseResult', {}).get('audits', {})
        return {
            'performance':    round((cats.get('performance',    {}).get('score', 0) or 0) * 100),
            'accessibility':  round((cats.get('accessibility',  {}).get('score', 0) or 0) * 100),
            'best_practices': round((cats.get('best-practices', {}).get('score', 0) or 0) * 100),
            'seo':            round((cats.get('seo',            {}).get('score', 0) or 0) * 100),
            'fcp': audits.get('first-contentful-paint', {}).get('displayValue', 'N/A'),
            'lcp': audits.get('largest-contentful-paint', {}).get('displayValue', 'N/A'),
            'cls': audits.get('cumulative-layout-shift', {}).get('displayValue', 'N/A'),
            'tbt': audits.get('total-blocking-time', {}).get('displayValue', 'N/A'),
        }
    except:
        return {'performance': 0, 'accessibility': 0, 'best_practices': 0, 'seo': 0,
                'fcp': 'N/A', 'lcp': 'N/A', 'cls': 'N/A', 'tbt': 'N/A'}

def crawl_links(soup, base_url):
    links = []
    broken = []
    for a in soup.find_all('a', href=True)[:50]:  # limit to 50 links
        href = a['href']
        full = urljoin(base_url, href)
        if full.startswith('http'):
            links.append(full)
    # Check first 10 links for broken
    for link in links[:10]:
        try:
            r = requests.head(link, timeout=5, allow_redirects=True)
            if r.status_code == 404:
                broken.append(link)
        except:
            broken.append(link)
    return links, broken

def check_seo(soup, url, html, response_time):
    issues   = []
    warnings = []
    passed   = []
    data     = {}

    parsed = urlparse(url)

    # ── Title Tag ──────────────────────────────────────────────────────────
    title = soup.find('title')
    title_text = title.get_text().strip() if title else ''
    data['title'] = title_text
    if not title_text:
        issues.append({'type': 'error', 'category': 'On-Page', 'item': 'Title Tag', 'detail': 'Missing title tag!', 'fix': 'Add a unique <title> tag with your main keyword (50-60 characters)'})
    elif len(title_text) < 30:
        warnings.append({'type': 'warning', 'category': 'On-Page', 'item': 'Title Tag', 'detail': f'Title too short ({len(title_text)} chars): "{title_text}"', 'fix': 'Expand title to 50-60 characters with primary keyword'})
    elif len(title_text) > 60:
        warnings.append({'type': 'warning', 'category': 'On-Page', 'item': 'Title Tag', 'detail': f'Title too long ({len(title_text)} chars) — will be truncated in Google', 'fix': 'Shorten title to under 60 characters'})
    else:
        passed.append({'category': 'On-Page', 'item': 'Title Tag', 'detail': f'Good title ({len(title_text)} chars)'})

    # ── Meta Description ───────────────────────────────────────────────────
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    desc_text = meta_desc['content'].strip() if meta_desc and meta_desc.get('content') else ''
    data['meta_description'] = desc_text
    if not desc_text:
        issues.append({'type': 'error', 'category': 'On-Page', 'item': 'Meta Description', 'detail': 'Missing meta description!', 'fix': 'Add meta description with primary keyword (150-160 characters)'})
    elif len(desc_text) < 70:
        warnings.append({'type': 'warning', 'category': 'On-Page', 'item': 'Meta Description', 'detail': f'Too short ({len(desc_text)} chars)', 'fix': 'Expand to 150-160 characters'})
    elif len(desc_text) > 160:
        warnings.append({'type': 'warning', 'category': 'On-Page', 'item': 'Meta Description', 'detail': f'Too long ({len(desc_text)} chars)', 'fix': 'Shorten to 160 characters max'})
    else:
        passed.append({'category': 'On-Page', 'item': 'Meta Description', 'detail': f'Good length ({len(desc_text)} chars)'})

    # ── H1 Tag ─────────────────────────────────────────────────────────────
    h1s = soup.find_all('h1')
    data['h1_count'] = len(h1s)
    data['h1_text']  = [h.get_text().strip() for h in h1s]
    if len(h1s) == 0:
        issues.append({'type': 'error', 'category': 'On-Page', 'item': 'H1 Tag', 'detail': 'No H1 tag found!', 'fix': 'Add one H1 tag with your primary keyword'})
    elif len(h1s) > 1:
        warnings.append({'type': 'warning', 'category': 'On-Page', 'item': 'H1 Tag', 'detail': f'Multiple H1 tags found ({len(h1s)})', 'fix': 'Keep only one H1 tag per page'})
    else:
        passed.append({'category': 'On-Page', 'item': 'H1 Tag', 'detail': f'Good: "{h1s[0].get_text().strip()[:50]}"'})

    # ── H2/H3 Structure ────────────────────────────────────────────────────
    h2s = soup.find_all('h2')
    h3s = soup.find_all('h3')
    data['h2_count'] = len(h2s)
    data['h3_count'] = len(h3s)
    if len(h2s) == 0:
        warnings.append({'type': 'warning', 'category': 'On-Page', 'item': 'Heading Structure', 'detail': 'No H2 tags — poor content structure', 'fix': 'Add H2 subheadings to structure your content'})
    else:
        passed.append({'category': 'On-Page', 'item': 'Heading Structure', 'detail': f'Good: {len(h2s)} H2s, {len(h3s)} H3s found'})

    # ── Images Alt Text ────────────────────────────────────────────────────
    images     = soup.find_all('img')
    missing_alt = [img for img in images if not img.get('alt')]
    data['total_images']   = len(images)
    data['missing_alt']    = len(missing_alt)
    if missing_alt:
        issues.append({'type': 'error', 'category': 'On-Page', 'item': 'Image Alt Text', 'detail': f'{len(missing_alt)} of {len(images)} images missing alt text', 'fix': 'Add descriptive alt text with keywords to all images'})
    elif images:
        passed.append({'category': 'On-Page', 'item': 'Image Alt Text', 'detail': f'All {len(images)} images have alt text ✅'})

    # ── SSL / HTTPS ────────────────────────────────────────────────────────
    if parsed.scheme == 'https':
        passed.append({'category': 'Technical', 'item': 'SSL Certificate', 'detail': 'HTTPS enabled ✅'})
    else:
        issues.append({'type': 'error', 'category': 'Technical', 'item': 'SSL Certificate', 'detail': 'Site not using HTTPS!', 'fix': 'Install SSL certificate — Google uses HTTPS as ranking factor'})

    # ── Page Speed ─────────────────────────────────────────────────────────
    if response_time > 3:
        issues.append({'type': 'error', 'category': 'Technical', 'item': 'Server Response Time', 'detail': f'Slow server response: {response_time:.1f}s', 'fix': 'Optimize server, use CDN, enable caching'})
    elif response_time > 1.5:
        warnings.append({'type': 'warning', 'category': 'Technical', 'item': 'Server Response Time', 'detail': f'Response time: {response_time:.1f}s (should be under 1s)', 'fix': 'Enable caching and optimize server response'})
    else:
        passed.append({'category': 'Technical', 'item': 'Server Response Time', 'detail': f'Fast response: {response_time:.1f}s ✅'})

    # ── Canonical Tag ──────────────────────────────────────────────────────
    canonical = soup.find('link', rel='canonical')
    if canonical:
        passed.append({'category': 'Technical', 'item': 'Canonical Tag', 'detail': f'Found: {canonical.get("href", "")[:50]}'})
    else:
        warnings.append({'type': 'warning', 'category': 'Technical', 'item': 'Canonical Tag', 'detail': 'Missing canonical tag', 'fix': 'Add <link rel="canonical"> to prevent duplicate content issues'})

    # ── Robots Meta ────────────────────────────────────────────────────────
    robots = soup.find('meta', attrs={'name': 'robots'})
    if robots:
        content = robots.get('content', '').lower()
        if 'noindex' in content:
            issues.append({'type': 'error', 'category': 'Technical', 'item': 'Robots Meta', 'detail': 'Page set to NOINDEX — Google will not index this page!', 'fix': 'Remove noindex if you want this page to rank'})
        else:
            passed.append({'category': 'Technical', 'item': 'Robots Meta', 'detail': 'Indexing allowed ✅'})

    # ── Open Graph Tags ────────────────────────────────────────────────────
    og_title = soup.find('meta', property='og:title')
    og_desc  = soup.find('meta', property='og:description')
    og_img   = soup.find('meta', property='og:image')
    og_count = sum([bool(og_title), bool(og_desc), bool(og_img)])
    if og_count == 3:
        passed.append({'category': 'Social', 'item': 'Open Graph Tags', 'detail': 'All OG tags present ✅'})
    elif og_count > 0:
        warnings.append({'type': 'warning', 'category': 'Social', 'item': 'Open Graph Tags', 'detail': f'Only {og_count}/3 OG tags found', 'fix': 'Add og:title, og:description, og:image for better social sharing'})
    else:
        warnings.append({'type': 'warning', 'category': 'Social', 'item': 'Open Graph Tags', 'detail': 'No Open Graph tags found', 'fix': 'Add OG tags for better Facebook/LinkedIn sharing'})

    # ── Schema Markup ──────────────────────────────────────────────────────
    schema = soup.find('script', type='application/ld+json')
    if schema:
        passed.append({'category': 'Technical', 'item': 'Schema Markup', 'detail': 'Structured data found ✅'})
    else:
        warnings.append({'type': 'warning', 'category': 'Technical', 'item': 'Schema Markup', 'detail': 'No schema markup found', 'fix': 'Add JSON-LD schema for rich snippets in Google'})

    # ── Word Count ─────────────────────────────────────────────────────────
    body_text  = soup.get_text()
    word_count = len(body_text.split())
    data['word_count'] = word_count
    if word_count < 300:
        issues.append({'type': 'error', 'category': 'Content', 'item': 'Content Length', 'detail': f'Thin content! Only {word_count} words', 'fix': 'Add more content — aim for 800+ words for blog pages, 300+ for landing pages'})
    elif word_count < 600:
        warnings.append({'type': 'warning', 'category': 'Content', 'item': 'Content Length', 'detail': f'{word_count} words — could be more', 'fix': 'Aim for 800+ words for better rankings'})
    else:
        passed.append({'category': 'Content', 'item': 'Content Length', 'detail': f'Good: {word_count} words ✅'})

    # ── Viewport Meta ──────────────────────────────────────────────────────
    viewport = soup.find('meta', attrs={'name': 'viewport'})
    if viewport:
        passed.append({'category': 'Technical', 'item': 'Mobile Viewport', 'detail': 'Viewport meta tag present ✅'})
    else:
        issues.append({'type': 'error', 'category': 'Technical', 'item': 'Mobile Viewport', 'detail': 'No viewport meta tag — site may not be mobile-friendly!', 'fix': 'Add <meta name="viewport" content="width=device-width, initial-scale=1">'})

    # ── Internal Links ─────────────────────────────────────────────────────
    internal = [a for a in soup.find_all('a', href=True) if urlparse(urljoin(url, a['href'])).netloc == parsed.netloc]
    data['internal_links'] = len(internal)
    if len(internal) < 3:
        warnings.append({'type': 'warning', 'category': 'Content', 'item': 'Internal Links', 'detail': f'Only {len(internal)} internal links found', 'fix': 'Add more internal links to improve crawlability and page authority'})
    else:
        passed.append({'category': 'Content', 'item': 'Internal Links', 'detail': f'{len(internal)} internal links found ✅'})

    return issues, warnings, passed, data

def ask_gemini(url, issues, warnings, passed, pagespeed, page_data):
    """Ask Gemini AI to analyze all findings and give expert recommendations"""
    issues_text   = '\n'.join([f"❌ {i['item']}: {i['detail']}" for i in issues])
    warnings_text = '\n'.join([f"⚠️ {w['item']}: {w['detail']}" for w in warnings])
    passed_text   = '\n'.join([f"✅ {p['item']}: {p['detail']}" for p in passed])

    prompt = f"""You are an expert SEO consultant. Analyze this SEO audit for {url} and provide actionable recommendations.

AUDIT RESULTS:
URL: {url}
Title: {page_data.get('title', 'N/A')}
Word Count: {page_data.get('word_count', 0)}
Images: {page_data.get('total_images', 0)} total, {page_data.get('missing_alt', 0)} missing alt

PAGESPEED SCORES:
- Performance: {pagespeed.get('performance')}%
- SEO Score: {pagespeed.get('seo')}%
- Accessibility: {pagespeed.get('accessibility')}%
- LCP: {pagespeed.get('lcp')}
- FCP: {pagespeed.get('fcp')}

CRITICAL ISSUES ({len(issues)}):
{issues_text if issues_text else 'None'}

WARNINGS ({len(warnings)}):
{warnings_text if warnings_text else 'None'}

PASSING ({len(passed)}):
{passed_text if passed_text else 'None'}

Provide your response in this EXACT JSON format (no markdown, pure JSON):
{{
  "overall_score": <number 0-100>,
  "grade": "<A/B/C/D/F>",
  "summary": "<2-3 sentence executive summary>",
  "top_priorities": [
    {{"priority": 1, "action": "<specific action>", "impact": "High/Medium/Low", "effort": "Easy/Medium/Hard", "timeframe": "<when to do it>"}},
    {{"priority": 2, "action": "<specific action>", "impact": "High/Medium/Low", "effort": "Easy/Medium/Hard", "timeframe": "<when to do it>"}},
    {{"priority": 3, "action": "<specific action>", "impact": "High/Medium/Low", "effort": "Easy/Medium/Hard", "timeframe": "<when to do it>"}},
    {{"priority": 4, "action": "<specific action>", "impact": "High/Medium/Low", "effort": "Easy/Medium/Hard", "timeframe": "<when to do it>"}},
    {{"priority": 5, "action": "<specific action>", "impact": "High/Medium/Low", "effort": "Easy/Medium/Hard", "timeframe": "<when to do it>"}}
  ],
  "competitor_advice": "<advice on how to outrank competitors>",
  "quick_wins": ["<win 1>", "<win 2>", "<win 3>"],
  "estimated_traffic_increase": "<realistic % increase if all fixes applied>"
}}"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        text = re.sub(r'```json\n?', '', text)
        text = re.sub(r'```\n?', '', text)
        return json.loads(text)
    except Exception as e:
        return {
            "overall_score": max(0, 100 - (len(issues) * 10) - (len(warnings) * 5)),
            "grade": "C",
            "summary": f"Found {len(issues)} critical issues and {len(warnings)} warnings. Fixing these could significantly improve your rankings.",
            "top_priorities": [{"priority": i+1, "action": iss['fix'], "impact": "High", "effort": "Medium", "timeframe": "This week"} for i, iss in enumerate(issues[:5])],
            "competitor_advice": "Focus on fixing critical issues first, then work on content quality.",
            "quick_wins": ["Fix missing meta tags", "Add alt text to images", "Improve page speed"],
            "estimated_traffic_increase": "20-40%"
        }

# ── API Routes ────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/audit', methods=['POST'])
def audit():
    data = request.json
    url  = data.get('url', '').strip()

    if not url:
        return jsonify({'error': 'Please provide a URL'}), 400

    if not url.startswith('http'):
        url = 'https://' + url

    # Step 1: Fetch page
    html, status_code, response_time = fetch_page(url)
    if not html:
        return jsonify({'error': f'Could not reach {url}. Check the URL and try again.'}), 400

    soup = BeautifulSoup(html, 'html.parser')

    # Step 2: Run SEO checks
    issues, warnings, passed, page_data = check_seo(soup, url, html, response_time)

    # Step 3: Get PageSpeed data
    pagespeed = get_pagespeed(url)

    # Step 4: Get broken links
    all_links, broken_links = crawl_links(soup, url)
    if broken_links:
        for bl in broken_links:
            issues.append({'type': 'error', 'category': 'Technical', 'item': 'Broken Link', 'detail': f'404 error: {bl}', 'fix': 'Fix or remove broken links'})
    else:
        passed.append({'category': 'Technical', 'item': 'Broken Links', 'detail': f'No broken links found in {len(all_links)} checked ✅'})

    # Step 5: Ask Gemini AI
    ai_analysis = ask_gemini(url, issues, warnings, passed, pagespeed, page_data)

    return jsonify({
        'url':         url,
        'status_code': status_code,
        'response_time': round(response_time, 2),
        'issues':      issues,
        'warnings':    warnings,
        'passed':      passed,
        'pagespeed':   pagespeed,
        'page_data':   page_data,
        'ai_analysis': ai_analysis,
        'summary': {
            'total_issues':   len(issues),
            'total_warnings': len(warnings),
            'total_passed':   len(passed),
            'score':          ai_analysis.get('overall_score', 50),
            'grade':          ai_analysis.get('grade', 'C')
        }
    })

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'message': 'SEO Audit Agent running!'})

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print(f"\n🔍 SEO Audit Agent running at http://localhost:{port}\n")
    app.run(debug=True, port=port)
