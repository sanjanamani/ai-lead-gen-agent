\# Hey Ayaan! 👋



Here's the Convexia CRM agent - rebuilt from scratch to be production-ready.



\## 🎬 Quick Demo



\[Link to your demo video here]



\## 🚀 To Run It



\### 1. Clone and setup

```bash

git clone https://github.com/YOUR\_USERNAME/convexia-crm-agent.git

cd convexia-crm-agent

python -m venv .venv

.\\.venv\\Scripts\\Activate.ps1  # Windows

pip install -r requirements.txt

pip install google-generativeai python-dotenv pydantic requests tenacity diskcache colorlog tqdm validators ratelimit

```



\### 2. Add your API keys

Create a `.env` file:

```

OPENAI\_API\_KEY=your-openai-key

SERPAPI\_KEY=your-serpapi-key

LLM\_PROVIDER=openai

SEARCH\_PROVIDER=serpapi

ENABLE\_CACHE=true

```



\### 3. Run!

```bash

python convexia\_search.py

```



Enter any therapeutic niche and watch it work!



\## ✨ What's New



\- \*\*Any therapeutic area\*\* - not just oncology anymore

\- \*\*Smarter queries\*\* - AI generates 5 targeted searches per niche

\- \*\*Better emails\*\* - truly personalized with company/role context

\- \*\*Production-ready\*\* - proper error handling, caching, logging

\- \*\*Cost optimized\*\* - caching prevents duplicate API calls



\## 📊 Output



You'll get CSVs in `data/output/`:

\- Companies ranked by fit score

\- Decision makers with LinkedIn URLs

\- Ready-to-send personalized emails



\## 💰 Cost



~$0.50-1.50 per search (5 queries × ~$0.15 each)

SerpAPI free tier: 100 searches/month



\## 🎯 Try These Searches



\- `rare genetic diseases`

\- `autoimmune disorders rheumatoid arthritis`

\- `gene therapy rare diseases`

\- `metabolic disorders obesity`

\- `CNS depression anxiety`



Let me know if you need anything else!



-Sanjana

