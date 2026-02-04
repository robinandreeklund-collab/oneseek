"""
Multi-Round Debate Tools

These tools enable the debate agent to run a 3-round debate where all models
(including OneSeek) participate sequentially with strict context control.
"""

import logging
import os
from typing import Any, List, Dict
from langchain_core.tools import tool

from backend.debate_flow import get_debate_flow

logger = logging.getLogger(__name__)


@tool
async def start_debate_round(
    round_number: int,
    user_query: str,
    locale: str = "sv-SE",
    thread_id: str | None = None,
) -> str:
    """
    Start a new debate round and get the randomized order of models.
    
    Args:
        round_number: Round number (1, 2, or 3)
        user_query: The user's question
        locale: Language locale (default: sv-SE for Swedish)
        
    Returns:
        Information about the round and model order
    """
    try:
        debate_flow = get_debate_flow(thread_id=thread_id)
        debate_flow.start_new_round(round_number)
        
        order = debate_flow.get_randomized_order()
        
        language = "svenska" if locale.startswith("sv") else "engelska"
        
        return f"""### 🎯 Runda {round_number} startar

**Deltagare och ordning:**
{chr(10).join([f"{i+1}. **{debate_flow.models[m].__class__.__name__ if m in debate_flow.models else m}** (ID: `{m}`)" for i, m in enumerate(order)])}

_Språkinställning: {language}_
_Föregående runda: {len(debate_flow.full_previous_round)} svar_
"""
    except Exception as e:
        logger.error(f"Error starting debate round: {e}", exc_info=True)
        return f"Fel vid start av runda {round_number}: {str(e)}"


@tool
async def query_model_in_round(
    model_key: str,
    user_query: str,
    locale: str = "sv-SE",
    thread_id: str | None = None,
) -> str:
    """
    Query a specific model in the current debate round.
    The model will receive context based on:
    - Round 1: User query + chain_so_far
    - Round 2/3: Full previous round + chain_so_far
    
    Args:
        model_key: Model identifier (e.g., "gpt-3.5-turbo", "oneseek-local")
        user_query: The user's original question
        locale: Language locale
        
    Returns:
        The model's response in the debate
    """
    try:
        # Check if model_key contains ID in parentheses from start_debate_round output
        # e.g., "GPT-3.5 (OpenAI) (ID: gpt-3.5-turbo)" -> extract "gpt-3.5-turbo"
        import re
        id_match = re.search(r'\(ID: ([^)]+)\)', model_key)
        if id_match:
            actual_key = id_match.group(1)
            logger.info(f"Extracted model ID '{actual_key}' from '{model_key}'")
            model_key = actual_key
            
        debate_flow = get_debate_flow(thread_id=thread_id)
        
        result = await debate_flow.query_model_in_debate(model_key, user_query, locale)
        
        if result.get("error"):
            return f"❌ **{result['display_name']}:** {result['response']}"
        
        # Helper for clean context display
        context_preview = result.get('context_used', 'Ingen kontext')
        
        return f"""### 🗣️ {result['display_name']} (Pos {result['position'] + 1})

{result['response']}

<details>
<summary>Visa skickad kontext</summary>

```text
{context_preview}
```
</details>

---
"""
    except Exception as e:
        logger.error(f"Error querying model in debate: {e}", exc_info=True)
        return f"Fel vid anrop till {model_key}: {str(e)}"


@tool
async def run_internal_analysis(user_query: str, thread_id: str | None = None) -> str:
    """
    Run OneSeek's internal analysis of responses so far.
    This performs fact-checking and identifies counterarguments.
    The analysis is NOT shared with other models.
    
    Args:
        user_query: The user's original question
        
    Returns:
        Summary of internal analysis
    """
    try:
        debate_flow = get_debate_flow(thread_id=thread_id)
        
        if not debate_flow.chain_so_far:
            return "⚠️ Ingen analys att köra - inga svar ännu i denna runda."
        
        analysis = await debate_flow.run_oneseek_internal_analysis(
            user_query,
            debate_flow.chain_so_far
        )
        
        return f"""🔍 **OneSeek Intern Analys** (Runda {analysis['round']}):

Analyserade {len(analysis['insights'])} svar
Faktakontroller genomförda: {sum(len(i.get('checks', [])) for i in analysis['insights'])}

Detta används internt av OneSeek för att förbättra sitt syntetiserade svar.
"""
    except Exception as e:
        logger.error(f"Error running internal analysis: {e}", exc_info=True)
        return f"Fel vid intern analys: {str(e)}"


@tool
async def collect_debate_votes(user_query: str, thread_id: str | None = None) -> str:
    """
    Collect votes from external models on the best answer from round 3.
    Models cannot vote for themselves.
    
    Args:
        user_query: The user's original question
        
    Returns:
        Voting results with winner
    """
    try:
        debate_flow = get_debate_flow(thread_id=thread_id)
        
        if debate_flow.current_round != 3:
            return f"⚠️ Röstning kan endast ske efter runda 3. Nuvarande runda: {debate_flow.current_round}"
        
        if not debate_flow.chain_so_far:
            return "⚠️ Inga svar att rösta på i runda 3."
        
        voting_results = await debate_flow.collect_votes(user_query, debate_flow.chain_so_far)
        
        # Format results
        result_text = f"""### 🗳️ Röstningsresultat

**Totalt antal röstande:** {voting_results['total_voters']}

#### 🏆 Vinnare
**{voting_results['winner'] if voting_results['winner'] else 'Ingen vinnare'}** ({voting_results['winner_votes']} röster)

#### 📊 Detaljerade Röster
"""
        
        for detail in voting_results['vote_details']:
            result_text += f"- **{detail['voter']}** röstade på: `{detail['vote']}`\n"
            
        result_text += f"""
<details>
<summary>Visa röstningsprompt</summary>

```text
{voting_results.get('voting_prompt', 'Ingen prompt')}
```
</details>
"""
        
        return result_text
        
    except Exception as e:
        logger.error(f"Error collecting votes: {e}", exc_info=True)
        return f"Fel vid röstning: {str(e)}"


@tool
async def get_debate_summary(thread_id: str | None = None) -> str:
    """
    Get a summary of the entire debate including all rounds and voting results.
    
    Returns:
        Complete debate summary
    """
    try:
        debate_flow = get_debate_flow(thread_id=thread_id)
        
        summary = f"""📊 **Debattsammanfattning**

Total antal ronder: {len(debate_flow.debate_history)}
Nuvarande runda: {debate_flow.current_round}

"""
        
        for round_data in debate_flow.debate_history:
            summary += f"\n**Runda {round_data['round']}:**\n"
            summary += f"Antal svar: {len(round_data['responses'])}\n"
            for resp in round_data['responses']:
                if not resp.get('error'):
                    summary += f"- {resp['display_name']}: {resp['response'][:100]}...\n"
        
        if debate_flow.chain_so_far:
            summary += f"\n**Aktuell runda {debate_flow.current_round}:**\n"
            summary += f"Antal svar: {len(debate_flow.chain_so_far)}\n"
        
        if debate_flow.oneseek_analyses:
            summary += f"\nOneSeek interna analyser: {len(debate_flow.oneseek_analyses)}\n"
        
        return summary
        
    except Exception as e:
        logger.error(f"Error getting debate summary: {e}", exc_info=True)
        return f"Fel vid hämtning av sammanfattning: {str(e)}"


def get_debate_tools() -> List[Any]:
    """
    Get debate tools for external_ai_caller agent.
    
    NOTE: external_ai_caller is called ONCE PER ROUND by debate_orchestrator.
    It should ONLY orchestrate that single round, not handle voting or summary.
    
    Voting and summary are handled automatically by debate_orchestrator and reporter.
    
    Returns:
        List of debate tools for round orchestration
    """
    # Create debater_web_search tool wrapper
    @tool
    async def debater_web_search(query: str, thread_id: str | None = None) -> str:
        """
        Perform a web search to verify facts or gather information for the debate.
        The results are added to the debate context and visible to OneSeek.
        
        Args:
            query: Search query
            
        Returns:
            Search results summary
        """
        try:
            debate_flow = get_debate_flow(thread_id=thread_id)
            if not query or not str(query).strip():
                return "Sökfel: tom sökfråga."

            max_calls = int(os.getenv("DEBATE_WEB_SEARCH_MAX_CALLS", "2"))
            current_round = debate_flow.current_round or 1
            if not debate_flow.record_debater_search(current_round, max_calls):
                return (
                    f"SEARCH_LIMIT_REACHED: Max {max_calls} webbsökningar per runda. "
                    "Använd befintliga resultat och fortsätt."
                )

            logger.info(f"Debater performing cached web search: {query}")
            results = debate_flow.cached_web_search(str(query), current_round)

            max_items = debate_flow.max_search_results or 3
            formatted = debate_flow._format_search_results(results, max_items=max_items)
            if not formatted:
                return f"Inga sökresultat hittades för '{query}'."

            result_text = f"Sökresultat för '{query}':\n{formatted}"
            debate_flow.add_fact(result_text, source=f"Web Search: {query}")
            return result_text
        except Exception as e:
            logger.error(f"Error in debater web search: {e}")
            return f"Sökfel: {str(e)}"

    # REMOVED: collect_debate_votes and get_debate_summary
    # These are handled by debate_orchestrator and reporter automatically
    # external_ai_caller should ONLY orchestrate ONE ROUND at a time
    return [
        start_debate_round,
        query_model_in_round,
        run_internal_analysis,
        # Removed: collect_debate_votes - handled by debate_orchestrator
        # Removed: get_debate_summary - handled by reporter
        debater_web_search,
    ]
