"""
app.py - Kalnirnay-style Calendar API
Endpoints:
  GET /calendar?date=YYYY-MM-DD[&state=Maharashtra]
  GET /festivals?year=2026[&state=Maharashtra]
  GET /states  — list all supported states
"""

import os
from datetime import date, timedelta
from flask import Flask, request, jsonify
from utils.calendar_engine import get_calendar_data, ALL_STATES

app = Flask(__name__)


@app.route("/calendar", methods=["GET"])
def calendar():
    """GET /calendar?date=YYYY-MM-DD[&state=Maharashtra]"""
    date_str = request.args.get("date")
    state    = request.args.get("state")

    if not date_str:
        return jsonify({"error": "Missing required query parameter: date"}), 400
    try:
        data = get_calendar_data(date_str, state=state)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Internal error: {str(e)}"}), 500

    return jsonify(data), 200


@app.route("/festivals", methods=["GET"])
def festivals():
    """
    GET /festivals?year=2026[&state=Maharashtra]
    Returns all days with festivals for the given year.
    """
    year_str = request.args.get("year")
    state    = request.args.get("state")

    if not year_str:
        return jsonify({"error": "Missing required query parameter: year"}), 400
    try:
        year = int(year_str)
    except ValueError:
        return jsonify({"error": "year must be an integer"}), 400

    results = []
    current = date(year, 1, 1)
    end     = date(year, 12, 31)

    while current <= end:
        try:
            data = get_calendar_data(current.strftime("%Y-%m-%d"), state=state)
            if data["festivals_today"]:
                results.append({
                    "date":           data["date"],
                    "lunar_month":    data["lunar_month"],
                    "tithi":          data["tithi"],
                    "nakshatra":      data["nakshatra"],
                    "festivals_today": data["festivals_today"],
                    "state_festivals": data["state_festivals"],
                })
        except Exception:
            pass
        current += timedelta(days=1)

    return jsonify({"year": year, "total": len(results), "data": results}), 200


@app.route("/states", methods=["GET"])
def states():
    ""
