# Convexia CRM Agent

AI-powered biotech lead generation that finds companies with failed clinical trials, identifies decision makers, and generates hyper-personalized outreach emails.

## 🎯 What It Does

1. **Search** - Enter any therapeutic niche (oncology, diabetes, rare diseases, etc.)
2. **Discover** - AI finds biotech companies with failed/terminated trials
3. **Enrich** - Automatically finds C-suite decision makers via LinkedIn
4. **Generate** - Creates personalized outreach emails for each contact
5. **Export** - Outputs everything to CSV for your CRM

## 🚀 Quick Start

### 1. Install Dependencies
```bash
# Create virtual environment
python -m venv .venv

# Activate it
# Windows:
.\.venv\Scripts\Activate.ps1
# Mac/Linux:
source .venv/bin/activate

# Install packages
pip install -r requirements.txt
pip install google-generativeai python-dotenv pydantic requests tenacity diskcache colorlog tqdm validators ratelimit
```

### 2. Configure API Keys
```bash
# Copy template
cp .env.example .env

# Edit with your keys
notepad .env  # Windows
nano .env     # Mac/Linux
```

Required keys:
- `OPENAI_API_KEY` - Get from: https://platform.openai.com/api-keys
- `SERPAPI_KEY` - Get from: https://serpapi.com/manage-api-key (free 100/month)

Your `.env` should look like:
```
OPENAI_API_KEY=sk-your-key-here
SERPAPI_KEY=your-serpapi-key-here
LLM_PROVIDER=openai
SEARCH_PROVIDER=serpapi
ENABLE_CACHE=true
```

### 3. Run Interactive Search
```bash
python convexia_search.py
```

Then enter any therapeutic area:
- `oncology solid tumors`
- `diabetes type 2`
- `rare genetic diseases`
- `autoimmune disorders`
- `gene therapy`
- `neurodegenerative Alzheimer's`

## 📁 Output Files

All results saved to `data/output/`:

- `{search}_companies.csv` - Companies sorted by fit score
- `{search}_decision_makers.csv` - All contacts with LinkedIn URLs
- `{search}_emails.csv` - Personalized outreach emails ready to send
- `{search}_full_results.json` - Complete data

## 💰 Cost

- **SerpAPI**: Free tier = 100 searches/month
- **OpenAI**: ~$0.10-0.30 per search query
- **ClinicalTrials.gov**: Free (unlimited)

Typical full run (5 queries): **~$0.50-1.50**

## 📊 Example Output

### Companies CSV
| company_name | fit_score | therapeutic_areas | num_decision_makers |
|-------------|-----------|-------------------|---------------------|
| Acme Biotech | 85 | oncology, immuno-oncology | 5 |
| Beta Therapeutics | 78 | oncology | 4 |

### Generated Email
```
To: Dr. Jane Smith (CEO)
Company: Acme Biotech
Subject: Exploring drug rescue opportunities for your oncology assets

Hi Dr. Smith,

I came across Acme Biotech's terminated Phase 2 trial for your EGFR inhibitor 
in NSCLC patients. The early efficacy signals were promising, and I wanted to 
reach out about potentially rescuing this asset...
```

## 🔧 Project Structure
```
convexia-crm-agent/
├── convexia_search.py      # 👈 Main interactive script
├── run_full_pipeline.py    # Batch oncology search
├── agent.py                # Core orchestrator
├── config/
│   ├── settings.py         # Configuration
│   ├── models.py           # Data models
│   ├── llm_client.py       # OpenAI/Gemini client
│   ├── prompts.py          # Prompt templates
│   └── utils.py            # Caching, logging
├── tools/
│   ├── web_search.py       # SerpAPI client
│   └── clinical_trials.py  # ClinicalTrials.gov API
├── data/
│   └── output/             # Generated CSVs
├── requirements.txt
└── .env.example
```

## 🛠️ Troubleshooting

**"Module not found"**
```bash
pip install -r requirements.txt
```

**"API key not set"**
- Make sure `.env` file exists with your keys
- Check for typos in key names

**"No companies found"**
- Try broader search terms
- Check that SerpAPI has searches remaining

## 📝 License

Built for Convexia Bio