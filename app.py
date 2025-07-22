from flask import Flask, request, render_template
import psycopg2
from datetime import datetime
import os

app = Flask(__name__)

# Replace with your actual Render Postgres URL (external one)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://doweighs_user:LLGoSdNM6uFsOrQnO7phgzxULm1jhLxm@dpg-d1vomdumcj7s73fjji50-a.singapore-postgres.render.com/doweighs")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    error = None

    if request.method == 'POST':
        div = request.form['div']
        item_code = request.form['item_code']
        total_weight = float(request.form['total_weight'])
        pallet_weight = float(request.form['pallet_weight'])

        try:
            conn = get_db_connection()
            cur = conn.cursor()

            # Fetch unit weight
            cur.execute(
                "SELECT description, unit_weight FROM inventory WHERE inventory_org = %s AND item_code = %s",
                (div, item_code)
            )
            row = cur.fetchone()

            if row:
                description, unit_weight = row
                quantity = (total_weight - pallet_weight) / unit_weight

                # Insert into logs table
                cur.execute(
                    """
                    INSERT INTO logs (div, item_code, description, unit_weight, total_weight, pallet_weight, quantity, entry_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (div, item_code, description, unit_weight, total_weight, pallet_weight, quantity, datetime.now())
                )
                conn.commit()
                result = quantity
            else:
                error = "Item not found in inventory."

            cur.close()
            conn.close()
        except Exception as e:
            error = str(e)

    return render_template('index.html', result=result, error=error)

# ✅ This is what starts the Flask server
if __name__ == "__main__":
    app.run(debug=True)
