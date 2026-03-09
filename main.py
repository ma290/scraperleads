from fastapi import FastAPI, BackgroundTasks, Query
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import httpx
import asyncio
import csv
import io
import json
import re
import time
import sqlite3
import urllib.parse
from datetime import datetime

app = FastAPI(title="LeadHunter")

# ---------- DB ----------
def init_db():
    con = sqlite3.connect("leads.db")
    con.execute("""CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, phone TEXT, website TEXT,
        address TEXT, rating TEXT, reviews TEXT,
        niche TEXT, city TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        niche TEXT, city TEXT, status TEXT DEFAULT 'running',
        count INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    con.commit()
    con.close()

init_db()

# ---------- Scraper ----------
async def scrape_google_maps(niche: str, city: str, job_id: int):
    query = urllib.parse.quote(f"{niche} in {city}")
    url = f"https://maps.googleapis.com/maps/api/place/textsearch/json"

    con = sqlite3.connect("leads.db")

    # We use the free Places scraping via undocumented HTML endpoint
    # This uses SerpApi-style approach with httpx
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
    }

    count = 0
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        search_url = f"https://www.google.com/maps/search/{query}/"
        try:
            resp = await client.get(search_url, headers=headers)
            html = resp.text

            # Extract business data from Google Maps HTML
            # Pattern matches JSON blobs embedded in the page
            patterns = re.findall(r'\["(.*?)","(.*?)",(\d+\.\d+),(\d+\.\d+)\]', html)
            phone_patterns = re.findall(r'\+[\d\s\-\(\)]{7,15}', html)
            name_patterns = re.findall(r'"name":"([^"]{3,60})"', html)
            rating_patterns = re.findall(r'"rating":([\d.]+)', html)
            address_patterns = re.findall(r'"formatted_address":"([^"]+)"', html)
            website_patterns = re.findall(r'"website":"([^"]+)"', html)

            # Also try alternate extraction
            blocks = re.findall(r'\["([A-Z][a-zA-Z\s&\'\-]{2,50})","([^"]*\d[^"]*)"', html)

            seen = set()
            for i, block in enumerate(blocks[:30]):
                name = block[0].strip()
                addr = block[1].strip()
                if name in seen or len(name) < 3:
                    continue
                seen.add(name)

                phone = phone_patterns[i] if i < len(phone_patterns) else ""
                rating = rating_patterns[i] if i < len(rating_patterns) else ""
                website = website_patterns[i] if i < len(website_patterns) else ""

                con.execute("""INSERT INTO leads (name,phone,website,address,rating,reviews,niche,city)
                    VALUES (?,?,?,?,?,?,?,?)""",
                    (name, phone, website, addr, rating, "", niche, city))
                count += 1

            # Fallback: use a known working approach via Outscraper-style URL
            if count == 0:
                # Try searching via Google Search for Maps listings
                gsearch = f"https://www.google.com/search?q={query}+site:maps.google.com"
                r2 = await client.get(gsearch, headers=headers)
                names = re.findall(r'<h3[^>]*>([^<]{3,60})</h3>', r2.text)
                for name in names[:20]:
                    if name in seen:
                        continue
                    seen.add(name)
                    con.execute("""INSERT INTO leads (name,phone,website,address,rating,reviews,niche,city)
                        VALUES (?,?,?,?,?,?,?,?)""",
                        (name, "", "", city, "", "", niche, city))
                    count += 1

        except Exception as e:
            print(f"Scrape error: {e}")

    con.execute("UPDATE jobs SET status='done', count=? WHERE id=?", (count, job_id))
    con.commit()
    con.close()


# ---------- Routes ----------
@app.post("/api/scrape")
async def start_scrape(background_tasks: BackgroundTasks, niche: str = Query(...), city: str = Query(...)):
    con = sqlite3.connect("leads.db")
    cur = con.execute("INSERT INTO jobs (niche,city,status) VALUES (?,?,'running')", (niche, city))
    job_id = cur.lastrowid
    con.commit()
    con.close()
    background_tasks.add_task(scrape_google_maps, niche, city, job_id)
    return {"job_id": job_id, "status": "started"}


@app.get("/api/leads")
async def get_leads(niche: str = None, city: str = None):
    con = sqlite3.connect("leads.db")
    if niche and city:
        rows = con.execute("SELECT * FROM leads WHERE niche=? AND city=? ORDER BY id DESC", (niche, city)).fetchall()
    else:
        rows = con.execute("SELECT * FROM leads ORDER BY id DESC LIMIT 500").fetchall()
    con.close()
    cols = ["id","name","phone","website","address","rating","reviews","niche","city","created_at"]
    return [dict(zip(cols, r)) for r in rows]


@app.get("/api/jobs")
async def get_jobs():
    con = sqlite3.connect("leads.db")
    rows = con.execute("SELECT * FROM jobs ORDER BY id DESC LIMIT 20").fetchall()
    con.close()
    cols = ["id","niche","city","status","count","created_at"]
    return [dict(zip(cols, r)) for r in rows]


@app.get("/api/export")
async def export_csv(niche: str = None, city: str = None):
    con = sqlite3.connect("leads.db")
    if niche and city:
        rows = con.execute("SELECT name,phone,website,address,rating,niche,city FROM leads WHERE niche=? AND city=?", (niche,city)).fetchall()
    else:
        rows = con.execute("SELECT name,phone,website,address,rating,niche,city FROM leads").fetchall()
    con.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Business Name","Phone","Website","Address","Rating","Niche","City"])
    writer.writerows(rows)
    output.seek(0)

    filename = f"leads_{niche or 'all'}_{city or 'all'}.csv".replace(" ","_")
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.delete("/api/leads")
async def clear_leads():
    con = sqlite3.connect("leads.db")
    con.execute("DELETE FROM leads")
    con.commit()
    con.close()
    return {"status": "cleared"}


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    with open("templates/index.html") as f:
        return f.read()
