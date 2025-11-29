# 🚀 START HERE

Welcome to Convexia CRM v2! This document will get you up and running in 10 minutes.

## What This Is

A biotech lead generation system that combines:
- **AI** for finding companies and decision makers
- **Human intelligence** for research and personalization
- **Result:** Emails that actually get responses

## Quick Setup (10 minutes)

### 1. Install Dependencies (2 mins)

```bash
# Make setup script executable
chmod +x setup.sh

# Run it
./setup.sh

# Or manually:
python3 -m venv .venv
source .venv/bin/activate  # Mac/Linux
# .venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 2. Get API Keys (5 mins)

You need two API keys:

**Anthropic (Claude):**
1. Go to: https://console.anthropic.com/
2. Sign up / log in
3. Go to API Keys
4. Create new key
5. Copy it

**SerpAPI (Web Search):**
1. Go to: https://serpapi.com/
2. Sign up (free tier = 100 searches/month)
3. Go to Dashboard → API Key
4. Copy it

### 3. Configure (2 mins)

```bash
# Copy example env
cp .env.example .env

# Edit with your keys
nano .env  # or use any editor
```

Add your keys:
```
ANTHROPIC_API_KEY=sk-ant-YOUR-KEY-HERE
SERPAPI_KEY=YOUR-SERPAPI-KEY-HERE
```

### 4. Test (1 min)

```bash
# Activate environment if not already
source .venv/bin/activate

# Check configuration
python main.py config-check
```

You should see all green checkmarks!

---

## Your First Run (20 mins)

Now let's find some leads:

```bash
python main.py run
```

You'll be prompted to:

1. **Enter a query:**
   ```
   Example: "diabetes phase 2 failures"
   ```

2. **Wait for AI discovery** (2 mins)
   - Finds companies with failed trials
   - Identifies decision makers
   
3. **Research each lead** (10 mins)
   - System shows you each person
   - You check their LinkedIn (what they posted)
   - You google recent news
   - You input findings
   
4. **Review emails** (5 mins)
   - AI generates draft using your research
   - You approve / edit / regenerate
   - Quality checks
   
5. **Get results!**
   - CSV file with approved emails
   - Ready to send

---

## What to Expect

### First Lead Research

When you see this:
```
🔍 Research Session
Company: MacroGenics
Contact: Scott Koenig (CEO)
LinkedIn: https://linkedin.com/in/...
```

**What to do:**
1. Open their LinkedIn in a browser
2. Read their last 5 posts
3. Google "{company name} news 2024"
4. Answer the questions the system asks

**Time:** 10-15 minutes (worth it!)

### First Email Review

When you see this:
```
📧 Generated Email

To: Scott Koenig
Company: MacroGenics

Subject: Tzield licensing - similar opportunities?

Hi Scott,

Congrats on the Sanofi/Provention deal - Tzield's...
```

**What to do:**
1. Read the email
2. Check if it references your research
3. Choose: Approve / Edit / Regenerate / Skip

**Time:** 2-3 minutes per email

---

## Tips for Success

### Good Queries
✅ "diabetes phase 2 failures"  
✅ "rare genetic diseases terminated trials"  
✅ "oncology suspended small biotech"  

❌ "biotech companies" (too broad)  
❌ "successful clinical trials" (not relevant)

### Good Research
✅ Spend 10-15 minutes per lead  
✅ Check their last 5 LinkedIn posts  
✅ Google recent news  
✅ Look for trigger events  

❌ Don't skip research (makes emails generic)  
❌ Don't rush it

### Good Emails
✅ Reference specific details  
✅ Under 75 words  
✅ One clear question  

❌ No "I've been following..."  
❌ No generic flattery

---

## Troubleshooting

**"API key not found"**
- Make sure `.env` file exists
- Check key names match `.env.example`
- No spaces around the `=` sign

**"No companies found"**
- Try broader search terms
- Check you have SerpAPI searches left
- Try a different therapeutic area

**"Emails still sound generic"**
- Spend more time on research
- Add very specific details
- Edit the AI drafts heavily
- Reference exact dates, trials, people

---

## What's Next?

1. **Run your first batch** (5 leads)
2. **Track responses** (if you send them)
3. **Iterate** on what works
4. **Read the docs:**
   - `README.md` - Full documentation
   - `COMPARISON.md` - v1 vs v2 changes
   - `MESSAGE_FOR_AYAAN.md` - Context on why v2 exists

---

## Need Help?

**Check configuration:**
```bash
python main.py config-check
```

**See all commands:**
```bash
python main.py --help
```

**Quick start guide:**
```bash
python main.py quick-start
```

---

## File Overview

```
convexia_crm_v2/
│
├── START_HERE.md          ← You are here!
├── README.md              ← Full documentation
├── MESSAGE_FOR_AYAAN.md   ← Why v2 exists
├── COMPARISON.md          ← v1 vs v2
│
├── main.py                ← Run this!
├── setup.sh               ← Setup script
├── .env.example           ← Template for API keys
│
└── data/output/           ← Your results go here
```

---

## Ready?

Let's go! Run:

```bash
python main.py run
```

And follow the prompts!

Remember: The research step is what makes this work. Don't skip it!

Good luck! 🚀
