"""
Human Research Layer - The key to non-LLM-ish emails

This module helps humans add context and intelligence that AI can't gather alone.
"""

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from typing import Dict, List
import json
import time
from pathlib import Path

from config.claude_client import claude
from config.prompts import RESEARCH_GUIDANCE_SYSTEM, RESEARCH_GUIDANCE_USER_TEMPLATE

console = Console()


class ResearchLayer:
    """
    Interactive layer for human research on leads
    """
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.research_file = output_dir / "research_notes.json"
        self.notes = self._load_notes()
    
    def _load_notes(self) -> Dict:
        """Load existing research notes"""
        if self.research_file.exists():
            with open(self.research_file) as f:
                return json.load(f)
        return {}
    
    def _save_notes(self):
        """Save research notes"""
        with open(self.research_file, 'w') as f:
            json.dump(self.notes, f, indent=2)
    
    def get_research_guidance(
        self,
        company_name: str,
        overview: str,
        why_relevant: str,
        contact_name: str,
        contact_role: str
    ) -> Dict:
        """
        Use Claude to generate research questions for this lead
        """
        user_prompt = RESEARCH_GUIDANCE_USER_TEMPLATE.format(
            company_name=company_name,
            overview=overview,
            why_relevant=why_relevant,
            contact_name=contact_name,
            contact_role=contact_role
        )
        
        return claude.chat_json(
            system_prompt=RESEARCH_GUIDANCE_SYSTEM,
            user_prompt=user_prompt
        )
    
    def conduct_research(
        self,
        company_name: str,
        contact_name: str,
        contact_linkedin: str,
        company_data: Dict,
        auto_research: bool = True
    ) -> Dict:
        """
        Research session for a specific lead - can be automatic or manual
        
        Args:
            auto_research: If True, AI does research automatically. If False, prompts user.
        """
        if auto_research:
            # Automatic research mode - AI does everything
            console.print(f"\n[cyan]📊 Auto-researching: {contact_name} at {company_name}[/cyan]")
            
            # AI generates automatic research
            research = self._auto_research(
                company_name=company_name,
                contact_name=contact_name,
                contact_linkedin=contact_linkedin,
                company_data=company_data
            )
            
            # Optional: Ask if user wants to add anything
            console.print(f"\n[dim]AI Research Summary:[/dim]")
            console.print(f"  Recent activity: {research.get('recent_activity', 'N/A')[:100]}...")
            console.print(f"  Current focus: {research.get('current_focus', 'N/A')[:100]}...")
            
            add_more = questionary.confirm(
                "Want to add your own research notes? (optional)",
                default=False
            ).ask()
            
            if add_more:
                research['manual_notes'] = questionary.text(
                    "Add any additional context:",
                    multiline=True
                ).ask() or ""
            
            return research
        
        else:
            # Manual research mode (original behavior)
            console.clear()
            
            # Show lead info
            console.print(Panel(
                f"[bold cyan]{company_name}[/bold cyan]\n"
                f"Contact: [yellow]{contact_name}[/yellow]\n"
                f"LinkedIn: {contact_linkedin}",
                title="🔍 Research Session",
                expand=False
            ))
            
            # Get AI-generated research guidance
            console.print("\n[dim]Generating research questions...[/dim]")
            guidance = self.get_research_guidance(
                company_name=company_name,
                overview=company_data.get('overview', ''),
                why_relevant=company_data.get('why_relevant_to_convexia', ''),
                contact_name=contact_name,
                contact_role=company_data.get('role', '')
            )
            
            # Display research questions
            console.print("\n[bold]Research Questions:[/bold]")
            all_questions = []
            for category, questions in guidance.items():
                console.print(f"\n[cyan]{category.replace('_', ' ').title()}:[/cyan]")
                for q in questions:
                    console.print(f"  • {q}")
                    all_questions.append(q)
            
            # Prompt to do research
            console.print("\n[yellow]⏸  Pause and research this person/company[/yellow]")
            console.print("Open their LinkedIn, check recent news, etc.\n")
            
            ready = questionary.confirm(
                "Ready to input your findings?",
                default=True
            ).ask()
            
            if not ready:
                return None
            
            # Collect research findings
            research = {}
            
            # LinkedIn activity
            research['recent_linkedin_posts'] = questionary.text(
                "What did they post about recently on LinkedIn? (or 'none')",
                multiline=True
            ).ask()
            
            research['current_focus'] = questionary.text(
                "What seems to be their current priority/focus?"
            ).ask()
            
            # Company context
            research['recent_news'] = questionary.text(
                "Any recent company news or press releases? (or 'none')",
                multiline=True
            ).ask()
            
            research['specific_pain_point'] = questionary.text(
                "What specific problem might they be facing right now?"
            ).ask()
            
            # Relationship
            research['warm_intro_path'] = questionary.text(
                "Any mutual connections or warm intro paths? (or 'none')"
            ).ask()
            
            # Hook/angle
            research['best_hook'] = questionary.text(
                "What's the best angle/hook for this outreach?"
            ).ask()
            
            # Confidence
            research['confidence'] = questionary.select(
                "How confident are you this is a good lead?",
                choices=[
                    "🔥 Excellent (9-10)",
                    "👍 Good (7-8)",
                    "😐 Okay (5-6)",
                    "👎 Weak (3-4)",
                    "❌ Skip this one"
                ]
            ).ask()
            
            if "Skip" in research['confidence']:
                console.print("\n[yellow]⏭  Skipping this lead[/yellow]")
                return None
            
            # Additional notes
            research['notes'] = questionary.text(
                "Any other observations? (optional)",
                multiline=True
            ).ask() or ""
            
            # Save research
            lead_key = f"{company_name}_{contact_name}"
            self.notes[lead_key] = research
            self._save_notes()
            
            console.print("\n[green]✓ Research saved![/green]")
            
            return research
    
    def _auto_research(
        self,
        company_name: str,
        contact_name: str,
        contact_linkedin: str,
        company_data: Dict
    ) -> Dict:
        """
        Automatically research a lead using AI and web search
        """
        from tools.web_search import enrich_with_news
        
        # Get recent news
        try:
            news_articles = enrich_with_news(company_name)
            if news_articles and isinstance(news_articles, list):
                news_summary = "\n".join([
                    f"- {article.get('title', 'News item')} ({article.get('date', 'recent')})"
                    for article in news_articles[:3]
                    if isinstance(article, dict)
                ])
            else:
                news_summary = "No recent news found"
        except Exception as e:
            console.print(f"[dim]News search error: {e}[/dim]")
            news_articles = []
            news_summary = "No recent news found"
        
        # Use Claude to analyze and synthesize
        analysis_prompt = f"""Analyze this biotech lead and provide research insights:

COMPANY: {company_name}
OVERVIEW: {company_data.get('overview', 'N/A')}
WHY RELEVANT: {company_data.get('why_relevant_to_convexia', 'N/A')}

CONTACT: {contact_name}
ROLE: {company_data.get('role', 'N/A')}

RECENT NEWS:
{news_summary}

FAILED TRIALS:
{json.dumps(company_data.get('failed_trials', []), indent=2)}

Based on this information, provide:

1. What's likely their current focus/priority?
2. What specific pain point might they have right now?
3. What recent activity or news is most relevant for outreach?
4. What's the best angle to approach them?

Return as JSON:
{{
  "recent_activity": "Summary of recent news/events",
  "current_focus": "What they're likely focused on now",
  "pain_point": "Specific problem they might be facing",
  "best_angle": "How to approach them"
}}"""
        
        try:
            from config.claude_client import claude
            insights = claude.chat_json(
                system_prompt="You are a biotech research analyst providing quick lead intelligence.",
                user_prompt=analysis_prompt
            )
            
            return {
                'recent_activity': insights.get('recent_activity', 'Recent developments in their pipeline'),
                'current_focus': insights.get('current_focus', company_data.get('why_relevant_to_convexia', 'Drug development')),
                'pain_point': insights.get('pain_point', 'Pipeline challenges or resource constraints'),
                'best_angle': insights.get('best_angle', 'Drug rescue opportunity'),
                'news_articles': news_articles,
                'auto_generated': True
            }
        except Exception as e:
            console.print(f"[yellow]Warning: Auto-research failed: {e}[/yellow]")
            # Fallback to basic research
            return {
                'recent_activity': news_summary,
                'current_focus': company_data.get('why_relevant_to_convexia', 'N/A'),
                'pain_point': 'Failed trials requiring evaluation',
                'best_angle': 'Drug rescue using AI platform',
                'auto_generated': True
            }
    
    def get_research(self, company_name: str, contact_name: str) -> Dict:
        """Retrieve saved research for a lead"""
        lead_key = f"{company_name}_{contact_name}"
        return self.notes.get(lead_key, {})
    
    def has_research(self, company_name: str, contact_name: str) -> bool:
        """Check if research exists for this lead"""
        lead_key = f"{company_name}_{contact_name}"
        return lead_key in self.notes


class EmailReviewLayer:
    """
    Interactive review and editing of generated emails
    Supports both sequential and batch review modes
    """
    
    def review_emails_batch(self, all_emails: List[Dict]) -> List[Dict]:
        """
        Review all emails at once with navigation
        
        Args:
            all_emails: List of dicts with keys: company_name, contact_name, subject, body, reasoning, company, contact, research
            
        Returns:
            List of approved emails
        """
        if not all_emails:
            return []
        
        console.print(f"\n[bold cyan]📧 Batch Email Review[/bold cyan]")
        console.print(f"Generated {len(all_emails)} emails. Let's review them all!\n")
        
        # Show all emails in summary
        console.print("[bold]All Generated Emails:[/bold]\n")
        for idx, email in enumerate(all_emails, 1):
            console.print(f"{idx}. [cyan]{email['contact_name']}[/cyan] at {email['company_name']}")
            console.print(f"   Subject: [dim]{email['subject'][:60]}...[/dim]")
        
        console.print(f"\n[yellow]Let's review each one...[/yellow]\n")
        time.sleep(1)
        
        # Track approval status
        for email in all_emails:
            email['approved'] = False
            email['edited'] = False
        
        current_idx = 0
        
        while True:
            email = all_emails[current_idx]
            console.clear()
            
            # Show position
            console.print(f"[dim]Email {current_idx + 1} of {len(all_emails)}[/dim]\n")
            
            # Display email
            status_badge = "✅ APPROVED" if email['approved'] else "⏸️  NOT APPROVED"
            console.print(Panel(
                f"[bold]To:[/bold] {email['contact_name']}\n"
                f"[bold]Company:[/bold] {email['company_name']}\n"
                f"[bold]Status:[/bold] {status_badge}\n\n"
                f"[bold cyan]Subject:[/bold cyan] {email['subject']}\n\n"
                f"{email['body']}",
                title=f"📧 Email {current_idx + 1}/{len(all_emails)}",
                expand=False
            ))
            
            if email.get('reasoning'):
                console.print(f"\n[dim]AI Reasoning: {email['reasoning']}[/dim]")
            
            # Navigation options
            choices = [
                f"{'✅ Approved' if email['approved'] else '✅ Approve this email'}",
                "✏️  Edit this email",
                f"{'❌ Remove approval' if email['approved'] else '⏭️  Skip this email'}",
            ]
            
            if current_idx > 0:
                choices.append("⬅️  Previous email")
            if current_idx < len(all_emails) - 1:
                choices.append("➡️  Next email")
            
            choices.append("🏁 Done reviewing (see summary)")
            
            action = questionary.select(
                "What would you like to do?",
                choices=choices
            ).ask()
            
            if "Approve" in action:
                email['approved'] = True
                # Auto-advance to next
                if current_idx < len(all_emails) - 1:
                    current_idx += 1
                else:
                    # Last email, show summary
                    break
            
            elif "Edit" in action:
                new_subject = questionary.text(
                    "Edit subject:",
                    default=email['subject']
                ).ask()
                
                new_body = questionary.text(
                    "Edit body:",
                    default=email['body'],
                    multiline=True
                ).ask()
                
                email['subject'] = new_subject
                email['body'] = new_body
                email['approved'] = True
                email['edited'] = True
                
                console.print("[green]✓ Email updated and approved![/green]")
                time.sleep(1)
                
                # Auto-advance
                if current_idx < len(all_emails) - 1:
                    current_idx += 1
                else:
                    break
            
            elif "Remove approval" in action or "Skip" in action:
                email['approved'] = False
                # Auto-advance to next
                if current_idx < len(all_emails) - 1:
                    current_idx += 1
                else:
                    break
            
            elif "Previous" in action:
                current_idx -= 1
            
            elif "Next" in action:
                current_idx += 1
            
            elif "Done" in action:
                break
        
        # Show final summary
        console.clear()
        console.print("\n[bold cyan]📊 Review Summary[/bold cyan]\n")
        
        approved_emails = [e for e in all_emails if e['approved']]
        skipped_emails = [e for e in all_emails if not e['approved']]
        
        console.print(f"[green]✅ Approved: {len(approved_emails)}[/green]")
        for email in approved_emails:
            edited_badge = " [dim](edited)[/dim]" if email.get('edited') else ""
            console.print(f"   • {email['contact_name']} at {email['company_name']}{edited_badge}")
        
        if skipped_emails:
            console.print(f"\n[yellow]⏭️  Skipped: {len(skipped_emails)}[/yellow]")
            for email in skipped_emails:
                console.print(f"   • {email['contact_name']} at {email['company_name']}")
        
        if not approved_emails:
            console.print("\n[yellow]No emails approved. Exiting.[/yellow]")
            return []
        
        # Final confirmation
        console.print(f"\n[bold]Export {len(approved_emails)} approved emails?[/bold]")
        if not questionary.confirm("Proceed?", default=True).ask():
            return []
        
        return approved_emails
    
    def review_email(
        self,
        company_name: str,
        contact_name: str,
        subject: str,
        body: str,
        reasoning: str = ""
    ) -> Dict:
        """
        Show generated email and let human approve/edit/skip
        """
        console.clear()
        
        # Display email
        console.print(Panel(
            f"[bold]To:[/bold] {contact_name}\n"
            f"[bold]Company:[/bold] {company_name}\n\n"
            f"[bold cyan]Subject:[/bold cyan] {subject}\n\n"
            f"{body}",
            title="📧 Generated Email",
            expand=False
        ))
        
        if reasoning:
            console.print(f"\n[dim]AI Reasoning: {reasoning}[/dim]")
        
        # Review decision
        action = questionary.select(
            "What would you like to do?",
            choices=[
                "✅ Approve (use as-is)",
                "✏️  Edit subject and body",
                "🔄 Regenerate with different angle",
                "⏭️  Skip this lead",
            ]
        ).ask()
        
        if "Approve" in action:
            return {
                "status": "approved",
                "subject": subject,
                "body": body
            }
        
        elif "Edit" in action:
            new_subject = questionary.text(
                "Edit subject:",
                default=subject
            ).ask()
            
            console.print("\n[yellow]Edit body (type or paste, press Ctrl+D when done):[/yellow]")
            new_body = questionary.text(
                "Edit body:",
                default=body,
                multiline=True
            ).ask()
            
            return {
                "status": "edited",
                "subject": new_subject,
                "body": new_body
            }
        
        elif "Regenerate" in action:
            return {
                "status": "regenerate"
            }
        
        else:  # Skip
            return {
                "status": "skipped"
            }
    
    def final_checklist(self, subject: str, body: str) -> bool:
        """
        Quality checklist before sending
        """
        console.print("\n[bold]✅ Pre-Send Checklist:[/bold]\n")
        
        checks = {
            "✓ Subject under 60 characters": len(subject) <= 60,
            "✓ Body under 100 words": len(body.split()) <= 100,
            "✓ No generic phrases": not any(phrase in body.lower() for phrase in [
                "i hope this email finds you well",
                "i've been following",
                "testament to",
                "excited to share"
            ]),
            "✓ Contains something specific": any(char.isupper() or char.isdigit() for char in body[20:]),  # Rough check
        }
        
        all_passed = True
        for check, passed in checks.items():
            symbol = "✅" if passed else "❌"
            console.print(f"{symbol} {check}")
            if not passed:
                all_passed = False
        
        if not all_passed:
            console.print("\n[yellow]⚠️  Some checks failed. Proceed anyway?[/yellow]")
            return questionary.confirm("Send email?", default=False).ask()
        
        return questionary.confirm("\nSend this email?", default=True).ask()
