# Convexia CRM v2 - Human-Powered Lead Generation

AI-powered biotech lead discovery with **human intelligence layer** for emails that actually get responses.

## 🎯 The Problem This Solves

**The v1 problem:** AI-generated emails sound generic and "LLM-ish" - low response rates.

**The v2 solution:** AI finds leads, humans add intelligence, together you create compelling outreach.

## ✨ What's New in v2

### 1. **Claude (Anthropic) Instead of GPT**
- Better at following instructions
- More natural, less formulaic writing
- Stronger at structured outputs

### 2. **Human Research Layer**
- Interactive research workflow
- You investigate LinkedIn, news, recent activity
- Add context AI can't find alone
- **This is what makes emails work**

### 3. **Email Review & Editing**
- Review every AI-generated email
- Edit before sending
- Quality checklist
- Track what works

### 4. **Multiple Data Sources**
- ClinicalTrials.gov (failed trials)
- Web search (company info)
- LinkedIn (decision makers)
- News (recent activity)

### 5. **Better Prompts**
- No more "I've been following your journey"
- No more "testament to your work"
- Specific, concise, human-sounding

## 🚀 Quick Start

### 1. Install

```bash
# Clone repo
git clone <your-repo-url>
cd convexia_crm_v2

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Mac/Linux
# or
.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure

```bash
# Copy example env file
cp .env.example .env

# Edit with your API keys
nano .env  # or use any text editor
```

Get your API keys:
- **Anthropic:** https://console.anthropic.com/
- **SerpAPI:** https://serpapi.com/manage-api-key (free: 100/month)

### 3. Run

```bash
# Check configuration
python main.py config-check

# Run the pipeline
python main.py run

# Or specify query directly
python main.py run -q "diabetes phase 2 failures" -n 5
```

## 📖 How It Works

### Phase 1: AI Discovery (Automated)
```
Input: "rare diseases phase 2 failures"
↓
AI searches:
- ClinicalTrials.gov for failed trials
- Web for biotech companies
- Multiple search angles
↓
Output: 10 companies with failed trials
```

### Phase 2: AI Enrichment (Automated)
```
Input: Companies from Phase 1
↓
AI finds:
- CEO, founders, C-suite
- LinkedIn profiles
- Contact info
↓
Output: 30+ decision maker contacts
```

### Phase 3: Human Research (INTERACTIVE)
```
For each lead:

1. AI shows you research questions:
   - What did they post on LinkedIn?
   - Recent company news?
   - Current priorities?
   - Pain points?

2. YOU research (10-15 mins per lead):
   - Open their LinkedIn
   - Check company news
   - Understand their situation
   - Find warm intro paths

3. YOU input findings:
   - Recent activity
   - Current focus
   - Specific pain point
   - Best angle to reach out
```

**This step is what makes emails work!**

### Phase 4: AI + Human Email Gen (INTERACTIVE)
```
For each researched lead:

1. AI generates email using YOUR research
   ↓
2. YOU review:
   ✅ Approve
   ✏️ Edit
   🔄 Regenerate
   ⏭️ Skip
   ↓
3. Quality checklist:
   - Under 75 words?
   - No generic phrases?
   - Something specific?
   ↓
4. Approve to send
```

### Phase 5: Export
```
Output: CSV with approved emails
- Company info
- Contact details
- Subject lines
- Email bodies
- Your research notes

Ready to import into your CRM!
```

## 💰 Cost

**Per search query (finding ~5 leads):**
- Claude API: ~$0.50-1.00
- SerpAPI: ~5 searches (free tier: 100/month)

**Total:** ~$1 per batch of 5 quality leads

Much cheaper than hiring a VA, much better than mass generic outreach.

## 📊 Example Output

### Before Research (Generic AI)
```
Subject: Exploring opportunities

Hi John,

I've been following your work at BioTech Co. It's 
impressive what you're doing in oncology. At Convexia, 
we help companies like yours rescue drug assets using AI.

Would love to explore opportunities together.

Best, Sanjana
```
❌ Generic, obvious AI, low response rate

### After Research (Human + AI)
```
Subject: Your Phase 2 EGFR data - alternative approach?

Hi John,

Saw your Q3 results for BTX-101. The dose-response 
curve looked promising despite missing the primary endpoint.

Quick question: have you considered alternative patient 
stratification? We've helped similar programs identify 
responder populations.

Worth a 15min call?

Sanjana
```
✅ Specific, shows research, much higher response rate

## 🎓 Tips for Success

### Research Tips
1. Spend 10-15 mins per lead (worth it!)
2. Check their last 5 LinkedIn posts
3. Google "{company} news 2024"
4. Look for trigger events (funding, trials, hires)
5. Find mutual connections

### Email Tips
**DO:**
- Reference specific trials/news
- Show understanding of their situation
- Keep under 75 words
- Ask one clear question

**DON'T:**
- Say "I hope this email finds you well"
- Say "I've been following your journey"
- Use "testament to", "excited to share"
- Make generic pitches

### Process Tips
1. Do 5 leads at a time (not 50)
2. Track response rates
3. Iterate on what works
4. Quality > quantity

## 📁 Project Structure

```
convexia_crm_v2/
├── main.py                 # CLI interface
├── agent.py                # Main orchestrator
├── human_layer.py          # Research & review workflows
├── config/
│   ├── settings.py         # Configuration
│   ├── claude_client.py    # Anthropic API client
│   └── prompts.py          # Improved prompts
├── tools/
│   ├── web_search.py       # SerpAPI integration
│   └── clinical_trials.py  # ClinicalTrials.gov API
├── data/
│   ├── output/             # Generated CSVs
│   └── cache/              # API cache
├── requirements.txt
├── .env.example
└── README.md
```

## 🔧 Advanced Usage

### Review Previously Generated Emails

```bash
python main.py review-emails data/output/diabetes_emails.csv
```

### See All Commands

```bash
python main.py --help
```

### Quick Start Guide

```bash
python main.py quick-start
```

## 🐛 Troubleshooting

**"Module not found"**
```bash
pip install -r requirements.txt
```

**"API key not found"**
- Check `.env` file exists
- Verify key names match `.env.example`
- Make sure keys are valid

**"No companies found"**
- Try broader search terms
- Check SerpAPI has searches remaining
- Verify ClinicalTrials.gov is accessible

**Emails still sound generic**
- Spend more time on research (15+ mins)
- Add very specific details from LinkedIn/news
- Edit AI drafts more heavily
- Reference exact trial data, dates, people

## 📈 Measuring Success

Track these metrics:
1. **Response rate** - How many reply?
2. **Meeting rate** - How many book calls?
3. **Time per lead** - Research + email time
4. **Quality score** - Your subjective rating 1-10

**Good benchmarks:**
- Response rate: 15-25%
- Meeting rate: 5-10%
- Time per lead: 15-20 mins
- Quality score: 7+

## 🎯 Next Steps

1. Run your first batch (5 leads)
2. Track response rates
3. Iterate on approach
4. Scale what works

## 📝 Message for Ayaan

Hey Ayaan,

I rebuilt the system from scratch based on your feedback. Key changes:

**Technical:**
- Switched to Claude (Anthropic) - better at nuanced writing
- Added interactive research layer
- Built in human review for every email
- Better prompts (no more "I've been following")

**Process:**
- AI finds leads (automated)
- Human researches (10-15 mins each)
- AI drafts email using human research
- Human edits/approves
- Export approved emails only

**The difference:**
Old approach: 100% AI → generic emails
New approach: AI + human intelligence → actually good emails

I tested this on 5 leads and the emails are night and day better. They reference specific trials, show real research, and don't sound like ChatGPT.

Want to see a demo?

- Sanjana

---

Built for Convexia Bio  
Questions? Issues? Open a GitHub issue or reach out!
