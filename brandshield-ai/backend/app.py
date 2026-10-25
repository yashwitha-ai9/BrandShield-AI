from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3, os, re, json
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get('BRANDSHIELD_DB', os.path.join(BASE_DIR, 'brandshield.db'))
app = Flask(__name__)
CORS(app)


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db() as con:
        con.execute('''CREATE TABLE IF NOT EXISTS rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_type TEXT NOT NULL,
            rule_text TEXT NOT NULL,
            source TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )''')
        con.execute('''CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            findings TEXT NOT NULL,
            revised_content TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'Under Review',
            decision_note TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )''')
        count = con.execute('SELECT COUNT(*) FROM rules').fetchone()[0]
        if count == 0:
            now = datetime.now(timezone.utc).isoformat()
            seeds = [
                ('prohibited', 'guaranteed', 'Avoid absolute promises unless explicitly approved.'),
                ('prohibited', '100% results', 'Avoid unsupported absolute performance claims.'),
                ('required', 'BrandShield', 'Use the product name consistently in product-specific content.'),
                ('tone', 'Use clear, respectful and evidence-based language.', 'Example brand voice guideline')
            ]
            con.executemany('INSERT INTO rules(rule_type, rule_text, source, created_at) VALUES(?,?,?,?)',
                            [(t, txt, src, now) for t, txt, src in seeds])


def rowdict(row):
    return dict(row) if row else None

@app.get('/api/health')
def health():
    return jsonify({'status': 'ok', 'app': 'BrandShield AI'})

@app.get('/api/rules')
def get_rules():
    with db() as con:
        rows = con.execute('SELECT * FROM rules ORDER BY id DESC').fetchall()
    return jsonify([rowdict(r) for r in rows])

@app.post('/api/rules')
def add_rule():
    data = request.get_json(silent=True) or {}
    rule_type = str(data.get('rule_type', '')).strip().lower()
    rule_text = str(data.get('rule_text', '')).strip()
    source = str(data.get('source', '')).strip()
    if rule_type not in {'required', 'prohibited', 'fact', 'tone'} or not rule_text:
        return jsonify({'error': 'Choose a valid rule type and enter rule text.'}), 400
    now = datetime.now(timezone.utc).isoformat()
    with db() as con:
        cur = con.execute('INSERT INTO rules(rule_type, rule_text, source, created_at) VALUES(?,?,?,?)',
                          (rule_type, rule_text, source, now))
        row = con.execute('SELECT * FROM rules WHERE id=?', (cur.lastrowid,)).fetchone()
    return jsonify(rowdict(row)), 201

@app.delete('/api/rules/<int:rule_id>')
def delete_rule(rule_id):
    with db() as con:
        cur = con.execute('DELETE FROM rules WHERE id=?', (rule_id,))
    if cur.rowcount == 0:
        return jsonify({'error': 'Rule not found.'}), 404
    return jsonify({'deleted': True})

ABSOLUTE_CLAIMS = [
    (r'\bguaranteed\b', 'Absolute promise: “guaranteed”', 'High'),
    (r'\b100\s*%\b', 'Absolute percentage claim', 'High'),
    (r'\beveryone\b', 'Universal claim: “everyone”', 'Medium'),
    (r'\balways\b', 'Absolute claim: “always”', 'Medium'),
    (r'\bnever\b', 'Absolute claim: “never”', 'Medium'),
    (r'\bthe best\b', 'Comparative claim: “the best”', 'Medium'),
    (r'\bproven\b', 'Evidence-sensitive claim: “proven”', 'Medium'),
]

def analyse(content, rules):
    findings = []
    lower = content.lower()
    for rule in rules:
        text = rule['rule_text'].strip()
        if rule['rule_type'] == 'prohibited' and text and text.lower() in lower:
            findings.append({'category': 'Prohibited term', 'severity': 'High', 'matched_text': text,
                             'reason': f'This matches your configured prohibited-term rule: “{text}”.',
                             'evidence': rule.get('source') or 'Configured brand rule',
                             'suggestion': 'Remove the term or replace it with precise wording supported by approved evidence.'})
        elif rule['rule_type'] == 'required' and text and text.lower() not in lower:
            findings.append({'category': 'Required term missing', 'severity': 'Medium', 'matched_text': text,
                             'reason': f'The configured required term “{text}” was not found.',
                             'evidence': rule.get('source') or 'Configured brand rule',
                             'suggestion': f'Add “{text}” where it fits naturally, if this rule applies to the content.'})
    for pattern, label, severity in ABSOLUTE_CLAIMS:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            already = any(f['matched_text'].lower() == match.group(0).lower() for f in findings)
            if not already:
                findings.append({'category': 'Potential unsupported claim', 'severity': severity,
                                 'matched_text': match.group(0), 'reason': f'{label}. The app cannot verify this claim from wording alone.',
                                 'evidence': 'No supporting source was attached to this review; human verification is required.',
                                 'suggestion': 'Qualify the statement and attach an approved source that substantiates it.'})
    if not findings:
        findings.append({'category': 'No configured issues detected', 'severity': 'Low', 'matched_text': '',
                         'reason': 'No matches were found for the current rules and built-in claim patterns. This is not a guarantee that the content is compliant.',
                         'evidence': 'Current configured rules only', 'suggestion': 'Ask an authorised reviewer to verify the content before publication.'})
    return findings

@app.post('/api/analyse')
def analyse_content():
    data = request.get_json(silent=True) or {}
    title = str(data.get('title', 'Untitled review')).strip() or 'Untitled review'
    content = str(data.get('content', '')).strip()
    if not content:
        return jsonify({'error': 'Paste content to analyse.'}), 400
    with db() as con:
        rules = [rowdict(r) for r in con.execute('SELECT * FROM rules').fetchall()]
        findings = analyse(content, rules)
        now = datetime.now(timezone.utc).isoformat()
        cur = con.execute('INSERT INTO reviews(title, content, findings, status, created_at, updated_at) VALUES(?,?,?,?,?,?)',
                          (title, content, json.dumps(findings), 'Under Review', now, now))
        review = con.execute('SELECT * FROM reviews WHERE id=?', (cur.lastrowid,)).fetchone()
    result = rowdict(review)
    result['findings'] = json.loads(result['findings'])
    return jsonify(result), 201

@app.get('/api/reviews')
def get_reviews():
    with db() as con:
        rows = con.execute('SELECT * FROM reviews ORDER BY id DESC').fetchall()
    results = []
    for row in rows:
        item = rowdict(row)
        item['findings'] = json.loads(item['findings'])
        results.append(item)
    return jsonify(results)

@app.patch('/api/reviews/<int:review_id>')
def update_review(review_id):
    data = request.get_json(silent=True) or {}
    status = str(data.get('status', '')).strip()
    revised = str(data.get('revised_content', '')).strip()
    note = str(data.get('decision_note', '')).strip()
    if status not in {'Under Review', 'Revision Requested', 'Approved', 'Rejected'}:
        return jsonify({'error': 'Invalid review status.'}), 400
    now = datetime.now(timezone.utc).isoformat()
    with db() as con:
        cur = con.execute('UPDATE reviews SET status=?, revised_content=?, decision_note=?, updated_at=? WHERE id=?',
                          (status, revised, note, now, review_id))
        row = con.execute('SELECT * FROM reviews WHERE id=?', (review_id,)).fetchone()
    if cur.rowcount == 0:
        return jsonify({'error': 'Review not found.'}), 404
    item = rowdict(row)
    item['findings'] = json.loads(item['findings'])
    return jsonify(item)

# Serve a small status message if someone visits the backend root.
@app.get('/')
def index():
    return jsonify({'name': 'BrandShield AI API', 'health': '/api/health', 'docs': 'See README.md'} )

init_db()
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
