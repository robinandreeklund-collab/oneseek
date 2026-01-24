# Citation Handling Improvement

## Problem Report

User reported: "nu kommer det tillbaka data iaf. men svaret innehåller fortfarande inte exakt det som frågan ställde" (now data comes back at least, but the answer still doesn't contain exactly what the question asked).

The user requested: "Kan du citera 1 kap. paragraf 2 från socialtjänstlagen" (Can you quote chapter 1, paragraph 2 from the Social Services Act)

But the answer wasn't providing the exact quoted text as requested.

## Root Cause Analysis

### Issues Identified

1. **Lack of citation-specific instructions in system prompt**
   - System told agent to "provide comprehensive answer"
   - No explicit instruction to quote verbatim
   - No guidance on handling "citera" (quote) requests

2. **Generic relevance checking**
   - Standard keyword matching didn't recognize structured documents
   - No special handling for section markers (chapters, paragraphs)
   - Legal documents with "Kapitel 1, paragraf 2" patterns not prioritized

3. **Paraphrasing tendency**
   - Without explicit instructions, agent would summarize or paraphrase
   - No emphasis on finding and quoting the exact text

## Solution Implemented

### 1. Enhanced System Prompt Instructions

**Added explicit citation handling (step 9):**

```python
"9. IMPORTANT - For citation requests (when user asks to 'citera', 'quote', or requests specific paragraphs/sections):
   - Find the EXACT text in the full content from get_chunk_content
   - Quote it VERBATIM - do not paraphrase, summarize, or modify
   - Include section numbers, paragraph numbers, or headings as they appear
   - If asking for 'kapitel X, paragraf Y', search for those exact markers in the text
   - Present the quote clearly, e.g.: 'Kapitel 1, paragraf 2: [exact text]'"
```

**Key elements:**
- Detects citation requests ("citera", "quote", specific sections)
- Instructs VERBATIM quoting (no paraphrasing)
- Tells agent to search for exact markers
- Provides format example

### 2. Structured Document Pattern Matching

**Enhanced `check_chunk_relevance` tool:**

Added detection for Swedish legal/formal document patterns:
```python
structure_patterns = [
    r'kapitel\s*(\d+)',      # "kapitel 1"
    r'kap\.?\s*(\d+)',       # "kap. 1" or "kap 1"
    r'(\d+)\s*kap',          # "1 kap"
    r'paragraf\s*(\d+)',     # "paragraf 2"
    r'§\s*(\d+)',            # "§ 2"
    r'punkt\s*(\d+)',        # "punkt 3"
    r'avsnitt\s*(\d+)',      # "avsnitt 4"
    r'stycke\s*(\d+)'        # "stycke 5"
]
```

**Relevance boost logic:**
- Detects if query contains section markers
- Checks if content contains matching section numbers
- Applies +0.5 relevance boost for matches
- Result: Chunks with exact section markers get higher priority

### 3. Citation Query Detection

```python
is_citation_query = any(re.search(pattern, query_lower) for pattern in structure_patterns)

if is_citation_query:
    # Check for matching section numbers in content
    for pattern in structure_patterns:
        query_matches = re.findall(pattern, query_lower)
        content_matches = re.findall(pattern, content_lower)
        if query_matches and any(qm in content_matches for qm in query_matches):
            citation_boost = 0.5  # Strong boost
            break
```

## Expected Workflow Now

### User Query: "Kan du citera 1 kap. paragraf 2 från socialtjänstlagen [URL]"

**Step 1: browse_page**
- Returns chunk previews (large document)
- Each preview contains ~800 chars

**Step 2: check_chunk_relevance (in parallel on all chunks)**
- Query contains "1 kap" and "paragraf 2" → Detected as citation query
- Chunk 1 preview: "Introduction text..." → No section markers → Score: 0.2
- Chunk 2 preview: "Kapitel 1, paragraf 2: Denna lag..." → Has "kapitel 1" + "paragraf 2" → Score: 1.0 (with citation boost)
- Chunk 3 preview: "Kapitel 2..." → Wrong section → Score: 0.3

**Step 3: get_chunk_content**
- Fetches full content of Chunk 2 only (highest relevance)

**Step 4: Generate Answer**
- System prompt tells agent: "For citation requests, quote VERBATIM"
- Agent finds exact text: "Kapitel 1, paragraf 2: Denna lag innehåller bestämmelser om..."
- Agent returns: "Kapitel 1, paragraf 2: [exact quoted text]"

**Result:** User gets the precise paragraph text they requested ✅

## Testing

### Citation Query Test
```python
Query: "Kan du citera 1 kap. paragraf 2 från socialtjänstlagen"
Content: "Kapitel 1, paragraf 2: Denna lag innehåller..."
Result: Score 1.0, is_relevant=True ✅
```

### Non-Matching Test
```python
Query: "Kan du citera 1 kap. paragraf 2 från socialtjänstlagen"
Content: "Information om väderprognos för Stockholm..."
Result: Score 0.0, is_relevant=False ✅
```

### All Existing Tests
- test_chunk_relevance.py: ✅ All 7 tests pass
- Backward compatibility maintained

## Technical Changes

### Files Modified

**backend/agent_graph.py:**
- Added step 9 with citation handling instructions
- Emphasizes VERBATIM quoting
- Provides format example for citations
- Instructions for finding exact section markers

**backend/tools.py:**
- Added structured document pattern recognition
- Citation query detection with regex
- Section number matching logic
- Relevance boost for matching section markers
- Removed duplicate stop words ("från", "citera")

## Why This Should Work

The combination of:

1. **Explicit instructions** - Agent told exactly what to do for citations
2. **Pattern matching** - Section markers automatically detected
3. **Relevance boost** - Correct chunks prioritized
4. **Verbatim emphasis** - Multiple reminders not to paraphrase

Creates a complete solution for citation handling.

## Supported Languages/Formats

- Swedish legal documents (socialtjänstlagen, etc.)
- Chapter/paragraph structures
- Section symbols (§)
- Multiple variants ("1 kap", "kap. 1", "kapitel 1")

## Commit History

- 0c5a99a: Fixed empty response issue
- a5e3de6: Added documentation
- 45db7b9: Improved citation handling (this fix)
