"""
Main CLI interface for Convexia CRM v2
Interactive lead generation with human-in-the-loop
"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
import questionary

from agent import ConvexiaCRMAgent
from config.settings import config

console = Console()


def show_welcome():
    """Show welcome message"""
    welcome_text = """
# Convexia CRM v2 - Human-Powered Lead Gen

This system helps you find biotech leads and craft **actually good** emails.

## How it works:

1. **🔍 AI Discovery** - Finds companies with failed trials
2. **👤 AI Enrichment** - Identifies decision makers  
3. **📝 Human Research** - YOU add the intelligence (this is the key!)
4. **✉️ AI + Human Emails** - Generate drafts, you edit/approve
5. **📤 Export** - Get CSV of approved emails ready to send

## Why the human layer matters:

Generic AI emails get ignored. **Personalized emails get responses.**

The AI finds the leads. You make them compelling.
    """
    
    console.print(Panel(
        Markdown(welcome_text),
        title="[bold cyan]Welcome[/bold cyan]",
        expand=False
    ))


@click.group()
def cli():
    """Convexia CRM - Human-powered biotech lead generation"""
    pass


@cli.command()
@click.option('--query', '-q', help='Search query (e.g., "diabetes Phase 2 failures")')
@click.option('--max-leads', '-n', default=5, help='Maximum leads to process')
@click.option('--auto-research/--manual-research', default=True, help='Auto-research leads (default) or manual')
@click.option('--batch-review/--sequential-review', default=True, help='Review all emails at once (default) or one-by-one')
@click.option('--auto-approve', is_flag=True, help='Auto-approve all emails (skip review)')
def run(query, max_leads, auto_research, batch_review, auto_approve):
    """
    Run the full pipeline interactively
    """
    show_welcome()
    
    # Show mode
    if auto_research:
        console.print("[cyan]Research Mode: AI auto-research (you can add notes optionally)[/cyan]")
    else:
        console.print("[cyan]Research Mode: Manual research required[/cyan]")
    
    if batch_review:
        console.print("[cyan]Review Mode: Batch (generate all emails, then review together)[/cyan]")
    else:
        console.print("[cyan]Review Mode: Sequential (review each email as generated)[/cyan]")
    
    # Get query if not provided
    if not query:
        query = questionary.text(
            "What therapeutic area or type of company are you looking for?",
            default="rare diseases phase 2 failures"
        ).ask()
    
    if not query:
        console.print("[yellow]No query provided. Exiting.[/yellow]")
        return
    
    # Confirm
    console.print(f"\n[cyan]Query:[/cyan] {query}")
    console.print(f"[cyan]Max leads:[/cyan] {max_leads}")
    console.print(f"[cyan]Auto-research:[/cyan] {auto_research}")
    console.print(f"[cyan]Batch review:[/cyan] {batch_review}")
    
    if not questionary.confirm("Start pipeline?", default=True).ask():
        return
    
    # Run agent with settings
    agent = ConvexiaCRMAgent(
        auto_research=auto_research,
        auto_approve=auto_approve,
        batch_review=batch_review
    )
    agent.run(query, max_leads=max_leads)


@cli.command()
def config_check():
    """
    Check configuration and API keys
    """
    console.print("\n[bold]Configuration Check[/bold]\n")
    
    # Check API keys
    checks = {
        "Anthropic API Key": bool(config.ANTHROPIC_API_KEY),
        "SerpAPI Key": bool(config.SERPAPI_KEY),
        "Output Directory": config.OUTPUT_DIR.exists(),
        "Cache Directory": config.CACHE_DIR.exists(),
    }
    
    for item, status in checks.items():
        symbol = "✅" if status else "❌"
        console.print(f"{symbol} {item}")
    
    if not all(checks.values()):
        console.print("\n[yellow]⚠️  Some checks failed. See .env.example for setup.[/yellow]")
    else:
        console.print("\n[green]✓ All checks passed![/green]")
    
    # Show config
    console.print(f"\n[bold]Settings:[/bold]")
    console.print(f"Model: {config.CLAUDE_MODEL}")
    console.print(f"From: {config.FROM_NAME} ({config.FROM_TITLE})")
    console.print(f"Max companies: {config.MAX_COMPANIES}")
    console.print(f"Human review: {'Enabled' if config.ENABLE_HUMAN_REVIEW else 'Disabled'}")


@cli.command()
@click.argument('csv_file', type=click.Path(exists=True))
def review_emails(csv_file):
    """
    Review previously generated emails from CSV
    """
    import pandas as pd
    from human_layer import EmailReviewLayer
    
    df = pd.read_csv(csv_file)
    review_layer = EmailReviewLayer()
    
    console.print(f"\n[cyan]Reviewing {len(df)} emails from {csv_file}[/cyan]\n")
    
    approved = []
    
    for idx, row in df.iterrows():
        result = review_layer.review_email(
            company_name=row.get('company_name', ''),
            contact_name=row.get('contact_name', ''),
            subject=row.get('subject', ''),
            body=row.get('body', '')
        )
        
        if result['status'] in ['approved', 'edited']:
            approved.append({
                **row.to_dict(),
                'subject': result['subject'],
                'body': result['body']
            })
    
    if approved:
        output_file = csv_file.replace('.csv', '_reviewed.csv')
        pd.DataFrame(approved).to_csv(output_file, index=False)
        console.print(f"\n[green]✓ Saved {len(approved)} approved emails to {output_file}[/green]")


@cli.command()
def quick_start():
    """
    Quick start guide and examples
    """
    guide = """
# Quick Start Guide

## First Time Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up API keys:**
   Create a `.env` file with:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   SERPAPI_KEY=...
   ```

3. **Test configuration:**
   ```bash
   python main.py config-check
   ```

## Running the Pipeline

```bash
python main.py run
```

You'll be guided through:
- Entering your search query
- Reviewing AI-found companies
- Researching each lead (LinkedIn, news, etc.)
- Editing generated emails
- Exporting approved emails

## Example Queries

- `"diabetes phase 2 failures"`
- `"rare genetic diseases terminated trials"`
- `"oncology withdrawn studies small biotech"`
- `"gene therapy suspended programs"`

## Tips for Good Emails

✅ DO:
- Reference specific trials or recent news
- Show you understand their situation
- Keep it under 75 words
- Ask one clear question

❌ DON'T:
- Use "I hope this email finds you well"
- Say "I've been following your journey"
- Make generic pitches
- Over-explain Convexia

## Output Files

All results saved to `data/output/`:
- `{query}_approved_emails.csv` - Ready to send
- `research_notes.json` - Your research findings
    """
    
    console.print(Markdown(guide))


if __name__ == "__main__":
    cli()
