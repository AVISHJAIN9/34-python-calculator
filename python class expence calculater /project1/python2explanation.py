import http.server      # The built-in library to handle HTTP requests (GET, POST).
import socketserver     # Helps create a TCP server that stays open ("listens").
import sqlite3          # The database engine. It saves data to a file on your disk.
import urllib.parse     # Tools to chop up (parse) the URL text sent by the browser.
import os               # Operating System tools (used to check if files exist).

# ==========================================
# PART 1: THE DATABASE LAYER (The Memory)
# This class handles all reading and writing to the hard drive.
# ==========================================
class ExpenseDB:
    def __init__(self, db_name='database.db'):
        self.db_name = db_name
        self._init_db()

    # HELPER: Creates a fresh connection to the database file.
    # timeout=10 waits 10 seconds if the DB is busy instead of crashing immediately.
    def _get_conn(self):
        return sqlite3.connect(self.db_name, timeout=10)

    # HELPER: creates the table if it doesn't exist yet.
    def _init_db(self):
        # The 'with' keyword is a Context Manager. 
        # It automatically closes the connection even if the code crashes.
        with self._get_conn() as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS expenses 
                            (id INTEGER PRIMARY KEY, category TEXT, amount REAL, date TEXT)''')
            conn.commit() # 'commit' saves the changes permanently.

    # FUNCTION: Saves a new expense.
    def add(self, category, amount, date):
        with self._get_conn() as conn:
            # SECURITY NOTE: We use (?, ?, ?) placeholders.
            # This prevents "SQL Injection" attacks where hackers try to run commands via input.
            # Python automatically cleans the data before putting it in the ?.
            conn.execute('INSERT INTO expenses (category, amount, date) VALUES (?, ?, ?)', 
                         (category, amount, date))
            conn.commit()

    # FUNCTION: Gets all rows for the history table.
    def get_all(self):
        with self._get_conn() as conn:
            cursor = conn.execute('SELECT * FROM expenses ORDER BY date DESC')
            return cursor.fetchall() # Returns a list of tuples: [(1, 'Food', 10.0, '2024-01-01'), ...]

    # FUNCTION: Calculates totals for the chart.
    def get_summary(self):
        with self._get_conn() as conn:
            # GROUP BY puts all "Food" rows in one pile, all "Rent" in another, then sums them.
            cursor = conn.execute('SELECT category, SUM(amount) FROM expenses GROUP BY category')
            return cursor.fetchall()

# ==========================================
# PART 2: THE SERVER LAYER (The Traffic Cop)
# This class decides what to do when the browser knocks on the door.
# ==========================================
class MyHandler(http.server.BaseHTTPRequestHandler):
    # Create one instance of our DB tool to use below
    db = ExpenseDB()

    # ------------------------------------------------
    # DO_GET: Runs when you type a URL or click a link
    # ------------------------------------------------
    def do_GET(self):
        # ROUTING: We check "self.path" to see what file the browser wants.
        
        # 1. The Home Page
        if self.path == '/':
            self.send_response(200)                 # 200 = "OK, success"
            self.send_header('Content-type', 'text/html') # Tells browser: "This is a webpage"
            self.end_headers()                      # Done sending headers, now body starts.
            
            # Generate the dynamic HTML (with charts/tables)
            html_content = self.generate_page()
            
            # Send the HTML. We must .encode('utf-8') to turn Text -> Bytes for the internet.
            self.wfile.write(html_content.encode('utf-8'))

        # 2. The CSS File (Styling)
        elif self.path == '/style.css':
            self.serve_static('style.css', 'text/css')

        # 3. The JS File (Scripts)
        elif self.path == '/script.js':
            self.serve_static('script.js', 'application/javascript')
        
        # 4. 404 Error (File not found)
        else:
            self.send_error(404, "File Not Found")

    # ------------------------------------------------
    # DO_POST: Runs when you click "Save Transaction"
    # ------------------------------------------------
    def do_POST(self):
        try:
            # STEP 1: How much data did the browser send?
            # The browser sends a header 'Content-Length' telling us the size in bytes.
            content_len = int(self.headers.get('Content-Length', 0))
            
            # STEP 2: Read the raw bytes from the stream (rfile = read file)
            post_body = self.rfile.read(content_len).decode('utf-8')
            
            # STEP 3: Parse the raw text into a dictionary.
            # Browser sends: "category=Food&amount=50&date=2024-01-01"
            # Python turns it into: {'category': ['Food'], 'amount': ['50'], ...}
            data = urllib.parse.parse_qs(post_body)
            
            # STEP 4: Extract and clean data (safely handle missing values)
            cat = data.get('category', ['Uncategorized'])[0]
            amt = float(data.get('amount', ['0'])[0]) # Convert text "50" to number 50.0
            date = data.get('date', [''])[0]

            # STEP 5: Save to Database
            self.db.add(cat, amt, date)

            # STEP 6: Redirect the user!
            # If we don't redirect, refreshing the page will resubmit the form (bad).
            # 303 = "See Other" (Go look at this other page instead).
            self.send_response(303)
            self.send_header('Location', '/')
            self.end_headers()

        except Exception as e:
            print(f"Server Error: {e}")
            self.send_error(500, "Internal Server Error")

    # HELPER: Reads a file from disk and sends it to browser
    def serve_static(self, filename, content_type):
        try:
            # 'rb' means Read Bytes (images/text alike)
            with open(filename, 'rb') as f:
                self.send_response(200)
                self.send_header('Content-type', content_type)
                self.end_headers()
                self.wfile.write(f.read())
        except FileNotFoundError:
            self.send_error(404)

    # ==========================================
    # PART 3: THE TEMPLATE ENGINE (The Builder)
    # This combines the HTML Skeleton + Database Data
    # ==========================================
    def generate_page(self):
        # 1. Open the HTML template file
        try:
            with open('index.html', 'r', encoding='utf-8') as f:
                template = f.read()
        except FileNotFoundError:
            return "<h1>Error: index.html is missing!</h1>"

        # 2. Build the Table HTML (Loop through DB rows)
        expenses = self.db.get_all()
        rows_html = ""
        for exp in expenses:
            # exp[3] is date, exp[1] is category, exp[2] is amount
            rows_html += f"<tr><td>{exp[3]}</td><td>{exp[1]}</td><td>${exp[2]:.2f}</td></tr>"

        # 3. Build the Chart HTML (Math logic)
        summary = self.db.get_summary()
        total = sum(x[1] for x in summary) if summary else 1 # Avoid divide by zero
        chart_html = ""
        colors = ["#4f46e5", "#10b981", "#f59e0b", "#ef4444"] # CSS colors
        
        for i, (cat, amt) in enumerate(summary):
            pct = (amt / total) * 100
            color = colors[i % len(colors)]
            # Simple HTML/CSS Bar Chart
            chart_html += f"""
            <div class="bar-wrapper">
                <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                    <span>{cat}</span><span>${amt:.2f}</span>
                </div>
                <div class="bar-track">
                    <div class="bar-fill" style="width:{pct}%; background-color:{color};"></div>
                </div>
            </div>
            """

        # 4. Inject the generated HTML into the placeholders {{ ... }}
        template = template.replace('{{ TABLE_ROWS }}', rows_html)
        template = template.replace('{{ CHART_DATA }}', chart_html)
        
        return template

# ==========================================
# PART 4: STARTING THE ENGINE
# ==========================================
if __name__ == '__main__':
    PORT = 8000
    
    # This line prevents "Address already in use" errors if you restart quickly.
    socketserver.TCPServer.allow_reuse_address = True
    
    print(f"🚀 SERVER RUNNING: http://localhost:{PORT}")
    print("👉 Press Ctrl+C to stop the server")

    # Create the server object listening on the specific port
    server = socketserver.TCPServer(('', PORT), MyHandler)
    
    try:
        # Keep running forever until user presses Ctrl+C
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped.")
        server.server_close()