"""Busi Find - web interface."""

import io
import threading
from flask import Flask, render_template, request, jsonify, Response

from sources import google_maps
from website_checker import check_websites
from processor import merge_and_deduplicate, filter_no_website

app = Flask(__name__)

jobs = {}
job_counter = 0
lock = threading.Lock()


def _run_search(job_id, location, category, limit):
    job = jobs[job_id]

    def on_progress(step, detail):
        job["step"] = step
        job["detail"] = detail
        # append to log so frontend can show a live feed
        job["log"].append({"step": step, "detail": detail})

    try:
        results = google_maps.search(location, category, limit, on_progress=on_progress)

        if not results:
            job["step"] = "done"
            job["detail"] = "No businesses found"
            job["results"] = {"no_website": [], "has_website": [], "total": 0}
            job["status"] = "done"
            return

        on_progress("verify", "Processing results...")
        results = merge_and_deduplicate(results)

        # Trust Google Maps: if a website URL was scraped, the business has a website.
        # No need for slow/unreliable HTTP verification.
        no_site = [b for b in results if not b.website]
        with_site = [b for b in results if b.website]

        job["results"] = {
            "no_website": [b.to_dict() for b in no_site],
            "has_website": [b.to_dict() for b in with_site],
            "total": len(results),
        }
        job["status"] = "done"
        job["step"] = "done"
        job["detail"] = f"Found {len(results)} businesses"
    except Exception as e:
        job["status"] = "done"
        job["step"] = "error"
        job["detail"] = str(e)
        job["results"] = {"no_website": [], "has_website": [], "total": 0, "error": str(e)}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search", methods=["POST"])
def search():
    global job_counter
    data = request.json
    location = data.get("location", "").strip()
    category = data.get("category", "").strip()
    limit = min(int(data.get("limit", 20)), 50)

    if not location or not category:
        return jsonify({"error": "Location and category are required"}), 400

    with lock:
        job_counter += 1
        job_id = job_counter

    jobs[job_id] = {
        "status": "running",
        "step": "starting",
        "detail": "",
        "log": [],
        "results": None,
    }
    thread = threading.Thread(target=_run_search, args=(job_id, location, category, limit), daemon=True)
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/status/<int:job_id>")
def status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Not found"}), 404

    # only send new log entries since last poll
    since = request.args.get("since", 0, type=int)
    return jsonify({
        "status": job["status"],
        "step": job["step"],
        "detail": job["detail"],
        "log": job["log"][since:],
        "log_total": len(job["log"]),
        "results": job["results"],
    })


@app.route("/download/<int:job_id>")
def download(job_id):
    job = jobs.get(job_id)
    if not job or not job.get("results"):
        return jsonify({"error": "Not found"}), 404

    fmt = request.args.get("format", "csv")
    tab = request.args.get("tab", "no")  # "no", "yes", or "all"

    results = job["results"]
    if tab == "no":
        items = results["no_website"]
    elif tab == "yes":
        items = results["has_website"]
    else:
        items = results["no_website"] + results["has_website"]

    if not items:
        return jsonify({"error": "No data to export"}), 400

    import pandas as pd
    df = pd.DataFrame(items)
    # Clean up columns for export
    export_cols = ["name", "address", "phone", "category", "rating", "website"]
    df = df[[c for c in export_cols if c in df.columns]]
    df["website"] = df["website"].apply(lambda x: x if x else "No website")

    if fmt == "excel":
        buf = io.BytesIO()
        df.to_excel(buf, index=False, engine="openpyxl")
        buf.seek(0)
        return Response(
            buf.getvalue(),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=busifind_results.xlsx"},
        )
    else:
        csv_data = df.to_csv(index=False, encoding="utf-8-sig")
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=busifind_results.csv"},
        )


if __name__ == "__main__":
    app.run(debug=False, port=5000)
