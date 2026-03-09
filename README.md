# LeadHunter 🎯
### Google Maps Lead Scraper — Deploy Free on Koyeb

---

## What this does
Scrapes Google Maps for any business niche in any city.
Exports clean CSV files you can sell on Fiverr/Gumroad.

---

## Deploy on Koyeb (Free)

### Step 1 — Push to GitHub
```bash
git init
git add .
git commit -m "LeadHunter v1"
git remote add origin https://github.com/YOURNAME/leadhunter.git
git push -u origin main
```

### Step 2 — Deploy on Koyeb
1. Go to https://app.koyeb.com
2. Click **Create App**
3. Choose **GitHub** → select your repo
4. Set these:
   - **Build command**: `pip install -r requirements.txt`
   - **Run command**: `uvicorn main:app --host 0.0.0.0 --port 8000`
   - **Port**: `8000`
5. Click **Deploy**

Done. Your app is live at `https://yourapp.koyeb.app`

---

## How to use

1. Open your Koyeb URL
2. Type a niche (e.g. "women boutique") and city (e.g. "Dubai")
3. Click **Hunt Leads**
4. Wait ~10 seconds
5. Click **Export CSV**
6. Sell the CSV on Fiverr

---

## How to make money

### Fiverr gig title:
> "I will provide 500 targeted local business leads in any niche"

### Pricing:
- 100 leads → $5
- 500 leads → $25
- 1000 leads → $50
- Custom niche + city → $75+

### Where to sell:
- Fiverr.com
- Gumroad.com (passive — upload CSV, people buy)
- Reddit: r/entrepreneur, r/slavelabour
- Facebook groups for marketers/agencies

---

## Upgrade ideas (when you have money)
- Add SerpApi ($50/mo) for more accurate results
- Add email finder API
- Add proxy rotation for more data
