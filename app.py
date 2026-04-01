"""
app.py
Flask entry point for the Kalnirnay-like Calendar API.
Run locally : python app.py
Production  : gunicorn app:app (via Docker)
Endpoint    : GET /calendar?date=YYYY-MM-DD
"""

import os
from datetime import date, timedelta
from flask import Flask, request, jsonify
from utils.calendar_engine import get_calendar_data

app = Flask(__name__)


@app.route("/calendar", methods=["GET"])
def calendar():
    """GET /calendar?date=YYYY-MM-DD"""
    date_str = request.args.get("date")
    if not date_str:
        return jsonify({"error": "Missing required query parameter: date"}), 400
    try:
        data = get_calendar_data(date_str)
    except ValueError:
        return jsonify({"error": "Invalid date format. Expected YYYY-MM-DD"}), 400
    except Exception as e:
        return jsonify({"error": f"Internal error: {str(e)}"}), 500
    return jsonify(data), 200


@app.route("/festivals", methods=["GET"])
def festivals():
    """
    GET /festivals?year=2026
    Returns all festival dates for the given year (only days that have festivals).
    """
    year_str = request.args.get("year")
    if not year_str:
        return jsonify({"error": "Missing required query parameter: year"}), 400
    try:
        year = int(year_str)
    except ValueError:
        return jsonify({"error": "year must be an integer"}), 400

    results = []
    current = date(year, 1, 1)
    end = date(year, 12, 31)
    while current <= end:
        try:
            data = get_calendar_data(current.strftime("%Y-%m-%d"))
            if data["festivals"]:
                results.append({
                    "date": data["date"],
                    "lunar_month": data["lunar_month"],
                    "tithi": data["tithi"],
                    "nakshatra": data["nakshatra"],
                    "festivals": data["festivals"],
                })
        except Exception:
            pass
        current += timedelta(days=1)

    return jsonify({"year": year, "total": len(results), "data": results}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
