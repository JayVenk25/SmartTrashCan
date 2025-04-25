from flask import Flask, render_template, jsonify
from flask_cors import CORS
from SmartTrashCan import SmartTrashCan

app = Flask(__name__)
CORS(app)

# Instantiate your SmartTrashCan
trash_can = SmartTrashCan()
# Track lid state
is_open = False

@app.route('/')
def home():
    return render_template('index.html', state='open' if is_open else 'closed')

@app.route('/toggle', methods=['POST'])
def toggle():
    global is_open
    # Flip state
    is_open = not is_open
    data = {'state': 'open' if is_open else 'closed'}
    if is_open:
        # When opening, trigger image capture & analysis
        item = trash_can.process_new_item()
        data['item'] = item  # JSON-serializable dict
    return jsonify(data)

# Placeholders for future pages
@app.route('/stats')
def stats():
    # Renders the statistics dashboard
    stats = trash_can.compute_stats(period='all')  # default to all time
    return render_template('stats.html', stats=stats)

@app.route('/stats-data/<period>')
def stats_data(period):
    # Returns JSON data for specified period: 'today','week','month','year','all'
    stats = trash_can.compute_stats(period=period)
    return jsonify(stats)

@app.route('/search')
def search():
    return "Search page coming soon"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)