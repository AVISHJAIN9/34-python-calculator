import http.server
import socketserver
import sqlite3
import urllib.parse
import os
import sys

# --- DATABASE LAYER (With Auto-Closing) ---
class ExpenseDB:
    def __init__(self, db_name='database.db'):
        self.db_name = db_name
        self._init_db()

    def _get_conn(self):
        # timeout=10 helps prevent "Database is locked" errors
        return sqlite3.connect(self.db_name, timeout=10)

    def _init_db(self):
        try:
            with self._get_conn() as conn:
                conn.execute('''CREATE TABLE IF NOT EXISTS expenses 
                                (id INTEGER PRIMARY KEY, category TEXT, amount REAL, date TEXT)''')
                conn.commit()
        except Exception as e:
            print(f"🔥 DATABASE INIT ERROR: {e}")

    def add(self, category, amount, date):
        try:
            with self._get_conn() as conn:
                conn.execute('INSERT INTO expenses (category, amount, date) VALUES (?, ?, ?)', 
                             (category, amount, date))
                conn.commit()
            print(f"✅ Saved: {category} - ${amount}")
        except Exception as e:
            print(f"🔥 DATABASE WRITE ERROR: {e}")
            raise e # Re-raise to catch in the server handler

    def get_all(self):
        with self._get_conn() as conn:
            cursor = conn.execute('SELECT * FROM expenses ORDER BY date DESC')
            return cursor.fetchall()

    def get_summary(self):
        with self._get_conn() as conn:
            cursor = conn.execute('SELECT category, SUM(amount) FROM expenses GROUP BY category')
            return cursor.fetchall()

# --- WEB SERVER LAYER ---
class MyHandler(http.server.BaseHTTPRequestHandler):
    db = ExpenseDB()

    def do_GET(self):
        try:
            if self.path == '/':
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(self.generate_page().encode('utf-8'))
            
            elif self.path == '/style.css':
                self.serve_static('style.css', 'text/css')
            
            elif self.path == '/script.js':
                self.serve_static('script.js', 'application/javascript')
            
            elif self.path == '/favicon.ico':
                self.send_error(404) # Ignore favicon requests
                
            else:
                self.send_error(404, "File Not Found")
        except Exception as e:
            # Show error in browser if GET fails
            self.send_error(500, f"Server Error: {str(e)}")

    def do_POST(self):
        try:
            # 1. READ DATA
            content_len = int(self.headers.get('Content-Length', 0))
            if content_len == 0:
                raise ValueError("No data received from form")
                
            post_body = self.rfile.read(content_len).decode('utf-8')
            data = urllib.parse.parse_qs(post_body)
            
            print(f"📥 Received Raw Data: {post_body}") # Debug Print

            # 2. EXTRACT & CLEAN DATA
            # urllib returns lists like {'amount': ['50']}
            cat = data.get('category', ['Uncategorized'])[0]
            amt_str = data.get('amount', ['0'])[0]
            date = data.get('date', [''])[0]

            # 3. CONVERT TYPES
            try:
                amt = float(amt_str)
            except ValueError:
                print(f"❌ Invalid Amount Format: {amt_str}")
                amt = 0.0

            # 4. SAVE TO DB
            self.db.add(cat, amt, date)

            # 5. SUCCESS: REDIRECT
            self.send_response(303)
            self.send_header('Location', '/')
            self.end_headers()

        except Exception as e:
            # 6. FAILURE: SHOW ERROR ON SCREEN
            print(f"🔥 CRITICAL ERROR: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            error_message = f"""
            <h1>❌ Server Error</h1>
            <p>Something went wrong while saving.</p>
            <p><strong>Error Details:</strong> {str(e)}</p>
            <p>Check your terminal for more info.</p>
            <a href="/">Go Back</a>
            """
            self.wfile.write(error_message.encode('utf-8'))

    def serve_static(self, filename, content_type):
        try:
            if not os.path.exists(filename):
                self.send_error(404, f"File {filename} missing")
                return
            with open(filename, 'rb') as f:
                self.send_response(200)
                self.send_header('Content-type', content_type)
                self.end_headers()
                self.wfile.write(f.read())
        except Exception as e:
            self.send_error(500, str(e))

    def generate_page(self):
        try:
            with open('index.html', 'r', encoding='utf-8') as f:
                template = f.read()
        except FileNotFoundError:
            return "<h1>Error: index.html is missing! Please create it.</h1>"

        # Table
        expenses = self.db.get_all()
        rows_html = ""
        for exp in expenses:
            rows_html += f"<tr><td>{exp[3]}</td><td>{exp[1]}</td><td>${exp[2]:.2f}</td></tr>"
        if not rows_html:
            rows_html = "<tr><td colspan='3' style='text-align:center'>No expenses found</td></tr>"

        # Chart
        summary = self.db.get_summary()
        total = sum(x[1] for x in summary) if summary else 1
        chart_html = ""
        colors = ["#4f46e5", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"]
        
        for i, (cat, amt) in enumerate(summary):
            pct = (amt / total) * 100
            color = colors[i % len(colors)]
            chart_html += f"""
            <div class="bar-wrapper">
                <div class="bar-info"><span>{cat}</span><span>${amt:.2f} ({int(pct)}%)</span></div>
                <div class="bar-track">
                    <div class="bar-fill" style="width:{pct}%; background-color:{color};"></div>
                </div>
            </div>
            """

        return template.replace('{{ TABLE_ROWS }}', rows_html).replace('{{ CHART_DATA }}', chart_html)

if __name__ == '__main__':
    PORT = 8080
    # Allow port reuse to prevent "Address already in use" errors
    socketserver.TCPServer.allow_reuse_address = True
    
    print(f"🚀 SERVER RESTARTED: http://localhost:{PORT}")
    print("👉 Press Ctrl+C to stop")
    
    try:
        server = socketserver.TCPServer(('', PORT), MyHandler)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped.")
        server.server_close()