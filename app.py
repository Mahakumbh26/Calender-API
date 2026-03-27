"""
app.py
Flask entry point for the Kalnirnay-like Calendar API.
Run locally : python app.py
Production  : gunicorn app:app (via Docker)
Endpoint    : GET /calendar?date=YYYY-MM-DD
"""

import os
from flask import Flask, request, jsonify
from utils.calendar_engine import get_calendar_data

app = Flask(__name__)


@app.route("/calendar", methods=["GET"])
def calendar():
    """
    GET /calendar?date=YYYY-MM-DD
    Returns Panchang + holiday + feature data for the requested date.
    """
    date_str = request.args.get("date")

    # Validate presence
    if not date_str:
        return jsonify({"error": "Missing required query parameter: date"}), 400

    # Validate format and compute data
    try:
        data = get_calendar_data(date_str)
    except ValueError:
        return jsonify({"error": "Invalid date format. Expected YYYY-MM-DD"}), 400
    except Exception as e:
        return jsonify({"error": f"Internal error: {str(e)}"}), 500

    return jsonify(data), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
