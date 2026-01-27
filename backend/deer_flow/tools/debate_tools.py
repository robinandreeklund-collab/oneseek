"""
Multi-Round Debate Tools

These tools enable the debate agent to run a 3-round debate where all models
(including OneSeek) participate sequentially with strict context control.
"""

import logging
from typing import Any, List, Dict
from langchain_core.tools import tool

from backend.debate_flow import get_debate_flow

logger = logging.getLogger(__name__)


@tool
async def start_debate_round(round_number: int, user_query: str, locale: str = "sv-SE") -> str:
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
        debate_flow = get_debate_flow(max_search_results=3, resources=[])
        debate_flow.start_new_round(round_number)
        
        order = debate_flow.get_randomized_order()
        
        language = "svenska" if locale.startswith("sv") else "engelska"
        
        return f"""🎯 **Runda {round_number} startar**

Modeller kommer att svara i följande ordning:
{', '.join([f"{i+1}. {debate_flow.models[m].__class__.__name__ if m in debate_flow.models else m} (ID: {m})" for i, m in enumerate(order)])}

VIKTIGT: Använd ID:t inom parentes (t.ex. "{order[0]}") som `model_key` när du anropar `query_model_in_round`.

Språk: {language}
Föregående runda: {len(debate_flow.full_previous_round)} svar
"""
    except Exception as e:
        logger.error(f"Error starting debate round: {e}", exc_info=True)
        return f"Fel vid start av runda {round_number}: {str(e)}"


@tool
async def query_model_in_round(model_key: str, user_query: str, locale: str = "sv-SE") -> str:
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
        debate_flow = get_debate_flow()
        
        result = await debate_flow.query_model_in_debate(model_key, user_query, locale)
        
        if result.get("error"):
            return f"❌ **{result['display_name']}:** {result['response']}"
        
        return f"""✅ **{result['display_name']}** (Position {result['position'] + 1} i Runda {result['round']}):

{result['response']}

---
"""
    except Exception as e:
        logger.error(f"Error querying model in debate: {e}", exc_info=True)
        return f"Fel vid anrop till {model_key}: {str(e)}"


@tool
async def run_internal_analysis(user_query: str) -> str:
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
        debate_flow = get_debate_flow()
        
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
async def collect_debate_votes(user_query: str) -> str:
    """
    Collect votes from external models on the best answer from round 3.
    Models cannot vote for themselves.
    
    Args:
        user_query: The user's original question
        
    Returns:
        Voting results with winner
    """
    try:
        debate_flow = get_debate_flow()
        
        if debate_flow.current_round != 3:
            return f"⚠️ Röstning kan endast ske efter runda 3. Nuvarande runda: {debate_flow.current_round}"
        
        if not debate_flow.chain_so_far:
            return "⚠️ Inga svar att rösta på i runda 3."
        
        voting_results = await debate_flow.collect_votes(user_query, debate_flow.chain_so_far)
        
        # Format results
        result_text = f"""🗳️ **Röstningsresultat**

Totalt antal röstande: {voting_results['total_voters']}

**Röster per modell:**
"""
        
        for model, count in sorted(voting_results['votes'].items(), key=lambda x: x[1], reverse=True):
            result_text += f"- {model}: {count} röst{'er' if count != 1 else ''}\n"
        
        if voting_results['winner']:
            result_text += f"\n🏆 **Vinnare:** {voting_results['winner']} med {voting_results['winner_votes']} röst{'er' if voting_results['winner_votes'] != 1 else ''}!"
        
        result_text += "\n\n**Röstningsdetaljer:**\n"
        for detail in voting_results['vote_details']:
            result_text += f"- {detail['voter']} → {detail['vote']}\n"
        
        return result_text
        
    except Exception as e:
        logger.error(f"Error collecting votes: {e}", exc_info=True)
        return f"Fel vid röstning: {str(e)}"


@tool
async def get_debate_summary() -> str:
    """
    Get a summary of the entire debate including all rounds and voting results.
    
    Returns:
        Complete debate summary
    """
    try:
        debate_flow = get_debate_flow()
        
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
    Get all debate tools for the debate agent.
    
    Returns:
        List of debate tools
    """
    return [
        start_debate_round,
        query_model_in_round,
        run_internal_analysis,
        collect_debate_votes,
        get_debate_summary,
    ]
