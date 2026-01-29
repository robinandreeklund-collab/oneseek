#!/usr/bin/env python3
"""
Test script for debate mode enhancements.
Tests the new internal analysis functionality.
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.debate_flow import DebateFlow


def test_extract_claims():
    """Test claim extraction from responses."""
    debate_flow = DebateFlow()
    
    # Test Swedish text
    response_sv = """
    Klimatförändringarna är en av vår tids största utmaningar. 
    Forskning visar att temperaturen har stigit med 1.1 grader sedan 1900-talet.
    Studier indikerar att detta beror på mänsklig aktivitet.
    Det finns många åsikter om detta ämne.
    Väldigt kort mening.
    Data pekar på att vi måste agera nu för att rädda planeten.
    """
    
    claims = debate_flow._extract_claims(response_sv)
    
    print("Test 1: Extract claims from Swedish text")
    print(f"Found {len(claims)} claims:")
    for i, claim in enumerate(claims, 1):
        print(f"  {i}. {claim}")
    
    assert len(claims) > 0, "Should extract at least one claim"
    assert len(claims) <= 5, "Should limit to maximum 5 claims"
    assert any('forskning' in c.lower() or 'studier' in c.lower() or 'data' in c.lower() 
               for c in claims), "Should find claims with factual indicators"
    print("✓ Test 1 passed\n")


def test_summarize_search_results():
    """Test search results summarization."""
    debate_flow = DebateFlow()
    
    # Test with list of results
    search_results = [
        {"content": "Climate change is real and happening now. Scientists agree that...", "url": "http://example.com"},
        {"content": "Another study shows...", "url": "http://example2.com"}
    ]
    
    summary = debate_flow._summarize_search_results(search_results)
    
    print("Test 2: Summarize search results")
    print(f"Summary: {summary}")
    
    assert len(summary) > 0, "Should generate a summary"
    assert "Verifierat" in summary or "Hittade" in summary, "Should contain Swedish verification text"
    print("✓ Test 2 passed\n")


def test_find_contradictions():
    """Test contradiction detection."""
    debate_flow = DebateFlow()
    
    responses = [
        {
            "display_name": "Model A",
            "model": "model-a",
            "response": "Ja, detta är definitivt sant och korrekt."
        },
        {
            "display_name": "Model B", 
            "model": "model-b",
            "response": "Nej, detta är falskt och inkorrekt."
        },
        {
            "display_name": "Model C",
            "model": "model-c",
            "response": "Jag håller med om att det är bra."
        }
    ]
    
    contradictions = debate_flow._find_contradictions(responses)
    
    print("Test 3: Find contradictions")
    print(f"Found {len(contradictions)} contradictions:")
    for i, contradiction in enumerate(contradictions, 1):
        print(f"  {i}. {contradiction}")
    
    assert len(contradictions) > 0, "Should find contradictions between opposing statements"
    print("✓ Test 3 passed\n")


def test_create_synthesis_points():
    """Test synthesis point creation."""
    debate_flow = DebateFlow()
    
    responses = [
        {"display_name": "Model A", "model": "model-a", "response": "Test response 1"},
        {"display_name": "Model B", "model": "model-b", "response": "Test response 2"},
    ]
    
    verified_facts = [
        {"model": "Model A", "claim": "Claim 1", "verification": "Verified"},
        {"model": "Model B", "claim": "Claim 2", "verification": "Verified"},
    ]
    
    synthesis = debate_flow._create_synthesis_points(responses, verified_facts)
    
    print("Test 4: Create synthesis points")
    print(f"Created {len(synthesis)} synthesis points:")
    for i, point in enumerate(synthesis, 1):
        print(f"  {i}. {point}")
    
    assert len(synthesis) > 0, "Should create synthesis points"
    assert any("perspektiv" in p.lower() for p in synthesis), "Should mention perspectives"
    print("✓ Test 4 passed\n")


def test_analyze_response_evolution():
    """Test response evolution analysis."""
    debate_flow = DebateFlow()
    
    # Set up previous round
    debate_flow.debate_history = [{
        "round": 1,
        "responses": [
            {"model": "model-a", "display_name": "Model A", "response": "Short response"},
            {"model": "model-b", "display_name": "Model B", "response": "Another short response"},
        ]
    }]
    
    # Current round with longer responses
    current_responses = [
        {"model": "model-a", "display_name": "Model A", "response": "This is a much longer response " * 20},
        {"model": "model-b", "display_name": "Model B", "response": "Still short"},
    ]
    
    evolution = debate_flow._analyze_response_evolution(current_responses)
    
    print("Test 5: Analyze response evolution")
    print(f"Found {len(evolution)} evolution notes:")
    for i, note in enumerate(evolution, 1):
        print(f"  {i}. {note}")
    
    # Should detect that Model A changed significantly
    assert len(evolution) > 0, "Should detect response evolution"
    print("✓ Test 5 passed\n")


def main():
    """Run all tests."""
    print("=" * 70)
    print("Testing Debate Mode Enhancements")
    print("=" * 70)
    print()
    
    try:
        test_extract_claims()
        test_summarize_search_results()
        test_find_contradictions()
        test_create_synthesis_points()
        test_analyze_response_evolution()
        
        print("=" * 70)
        print("✓ All tests passed!")
        print("=" * 70)
        return 0
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
