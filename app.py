from flask import Flask, request, render_template, jsonify, send_file
import psycopg2
from datetime import datetime
import os
from flask_cors import CORS
import csv
import io

app = Flask(__name__)
CORS(app)

# ✅ Database URL from environment (fallback for local testing)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://doweighs_8qxv_user:Pf4l3R6sTp7E7XtEnZYwir1HWVV5Ss3a@dpg-d33chvndiees739et920-a.singapore-postgres.render.com/doweighs_8qxv"
)

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

            # ✅ Correct table + column names
            cur.execute(
                '''SELECT "Description", "Unit weight"
                   FROM "Doweighs - ITEMS"
                   WHERE "Inventory Org" = %s AND "Item Code" = %s''',
                (div, item_code)
            )
            row = cur.fetchone()

            if row:
                description, unit_weight = row
                unit_weight = float(unit_weight)  # ✅ FIX: Convert to float
                quantity = (total_weight - pallet_weight) / unit_weight

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

@app.route('/download', methods=['GET'])
def download_logs():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM logs")
        rows = cur.fetchall()
        colnames = [desc[0] for desc in cur.description]

        cur.close()
        conn.close()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(colnames)
        writer.writerows(rows)
        output.seek(0)

        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name='logs.csv'
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/submit', methods=['POST'])
def submit_data():
    try:
        data = request.get_json()
        div = data.get('div')
        item_code = data.get('item_code')
        total_weight = float(data.get('total_weight'))
        pallet_weight = float(data.get('pallet_weight'))

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            '''SELECT "Description", "Unit weight"
               FROM "Doweighs - ITEMS"
               WHERE "Inventory Org" = %s AND "Item Code" = %s''',
            (div, item_code)
        )
        row = cur.fetchone()

        if row:
            description, unit_weight = row
            unit_weight = float(unit_weight)  # ✅ FIX: Convert to float
            net_weight = total_weight - pallet_weight
            quantity = net_weight / unit_weight

            cur.execute(
                """
                INSERT INTO logs (div, item_code, description, unit_weight, total_weight, pallet_weight, quantity, entry_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (div, item_code, description, unit_weight, total_weight, pallet_weight, quantity, datetime.now())
            )
            conn.commit()

            cur.close()
            conn.close()

            return jsonify({
                "net_weight": round(net_weight, 2),
                "quantity": int(quantity)
            }), 200
        else:
            return jsonify({"error": "Item not found in inventory"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
