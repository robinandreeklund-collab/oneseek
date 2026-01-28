# Debate Context - Justeringar för 95K Token Modell

**Datum:** 2026-01-28  
**Uppdatering:** Justerade gränser för användares 95K token context window  
**Status:** ✅ UPPDATERAD

---

## Ny Information

**Modellkapacitet:** 95,000 tokens context window (inte 32K som ursprungligen antaget)

Detta ger mycket mer utrymme för högre debattkvalitet med mindre aggressiv summarization.

---

## Uppdaterade Gränser

### FÖRE (konservativa gränser för 32K modell)

| Parameter | Värde | Motivering |
|-----------|-------|------------|
| Hard limit | 15,000 tokens | Säkerhetsmargin för 32K |
| Varning | 5,000 tokens | Tidig varning |
| Error | 10,000 tokens | Kritisk nivå |
| Summarization | 150 chars (~40 tokens) | Mycket aggressiv |
| chain_so_far | 3 senaste svar | Minimalt |
| Truncation | 300 chars | Mycket kort |
| Voting context | 300 chars/svar | Minimal info |

**Total peak context:** ~3,500 tokens (mycket konservativt)

---

### EFTER (justerade gränser för 95K modell)

| Parameter | Värde | Motivering |
|-----------|-------|------------|
| Hard limit | **60,000 tokens** | Lämnar 35K för respons |
| Varning | **30,000 tokens** | Tidig varning |
| Error | **50,000 tokens** | Kritisk nivå |
| Summarization | **300 chars (~75 tokens)** | Bättre kvalitet |
| chain_so_far | **5 senaste svar** | Mer kontext |
| Truncation | **500 chars** | Mer info behålls |
| Voting context | **500 chars/svar** | Bättre beslutsunderlag |

**Total peak context:** ~8,000-12,000 tokens (fortfarande säkert under 60K)

---

## Förbättrad Debattkvalitet

Med de nya gränserna får modellerna:

### Runda 1
```
Modell 1: 300 tokens (oförändrat)
Modell 2: 1,000 tokens (+ senaste 5 svar på 500 chars)
Modell 3: 1,500 tokens
Modell 4: 2,000 tokens
Modell 5: 2,500 tokens
```

### Runda 2
```
Modell 1: 1,500 tokens (R1 summary på 300 chars)
Modell 2: 2,000 tokens
Modell 3: 2,500 tokens
Modell 4: 3,000 tokens
Modell 5: 3,500 tokens
```

### Runda 3
```
Modell 1: 2,500 tokens (R2 summary på 300 chars)
Modell 2: 3,500 tokens
Modell 3: 4,500 tokens
Modell 4: 5,500 tokens
Modell 5: 8,000 tokens (OneSeek med fakta)
```

### Voting
```
Varje anrop: ~2,500 tokens (5 svar × 500 chars)
Totalt: 12,500 tokens (5 anrop)
```

**Peak single context:** ~8,000 tokens  
**Total processed:** ~30,000 tokens  
**Safety margin:** 65,000 tokens kvar (68% av kapacitet outnyttjad)

---

## Vad Förändrades i Koden

### 1. Summarization (mindre aggressiv)
```python
# FÖRE: 150 chars
snippet = resp['response'][:150]

# EFTER: 300 chars
snippet = resp['response'][:300]
```

**Fördel:** Behåller mer information, bättre kontext mellan rundor

---

### 2. chain_so_far (mer kontext)
```python
# FÖRE: Senaste 3 svar
recent = self.chain_so_far[-3:]

# EFTER: Senaste 5 svar
recent = self.chain_so_far[-5:]
```

**Fördel:** Modeller ser mer av debatten, bättre kontinuitet

---

### 3. Truncation (större snippets)
```python
# FÖRE: 300 chars
snippet = resp['response'][:300]

# EFTER: 500 chars
snippet = resp['response'][:500]
```

**Fördel:** Behåller mer av varje svar, färre avklippta meningar

---

### 4. Voting Context (bättre beslutsunderlag)
```python
# FÖRE: 300 chars per svar
if len(response_text) > 300:
    response_text = response_text[:300]

# EFTER: 500 chars per svar
if len(response_text) > 500:
    response_text = response_text[:500]
```

**Fördel:** Voting baseras på mer information, bättre beslut

---

### 5. Hard Limit (realistisk gräns)
```python
# FÖRE: 15,000 tokens
if token_count > 15000:
    # Skip model

# EFTER: 60,000 tokens
if token_count > 60000:
    # Skip model
```

**Fördel:** Mycket större marginal innan limit nås

---

### 6. Warnings & Errors (justerade trösklar)
```python
# FÖRE:
if token_count > 10000:  # Error
    logger.error("CRITICAL")
elif token_count > 5000:  # Warning
    logger.warning("WARNING")

# EFTER:
if token_count > 50000:  # Error
    logger.error("CRITICAL")
elif token_count > 30000:  # Warning
    logger.warning("WARNING")
```

**Fördel:** Mindre false positives, mer realistiska varningar

---

## Balans mellan Kvalitet och Säkerhet

### Kvalitetsförbättringar ✅
- **2× mer summarization info** (150 → 300 chars)
- **67% mer current round context** (3 → 5 svar)
- **67% mer truncation space** (300 → 500 chars)
- **67% mer voting info** (300 → 500 chars)

### Säkerhetsmarginaler ✅
- **Peak context:** 8,000 tokens (8% av 95K)
- **Hard limit:** 60,000 tokens (63% av 95K)
- **Utrymme för respons:** 35,000 tokens (37% av 95K)
- **Buffer till limit:** 52,000 tokens från peak till hard limit

---

## Förväntade Resultat

### Med 32K Modell (gamla gränser)
```
✓ Fungerade men mycket restriktivt
✓ Aggressiv summarization = information loss
✓ Mycket säkert men kanske överkonservativt
```

### Med 95K Modell (nya gränser)
```
✅ Mycket bättre debattkvalitet
✅ Mer kontext = bättre beslut
✅ Fortfarande säkra marginaler
✅ Utnyttjar ~8-12% av kapacitet (mycket säkert)
```

---

## Monitoring Med Nya Gränser

### Förväntade Log Messages

**Normal användning:**
```
INFO: Context for gpt-3.5-turbo round 1: 1,200 tokens
INFO: Context for oneseek-local round 2: 3,500 tokens
INFO: Context for gemini-2.5-flash round 3: 5,000 tokens
INFO: Voting context: 2,400 tokens (adjusted for 95K model)
```

**Om kontext växer ovanligt mycket:**
```
WARNING: ⚠️ Context 32,000 tokens exceeds 30K
```

**Om något går fel:**
```
ERROR: ⚠️ CRITICAL: Context 52,000 tokens exceeds 50K! Approaching limit!
```

**Hard limit (endast i extremfall):**
```
ERROR: Context too large (61,000 tokens) for oneseek-local, skipping
```

---

## Rekommendationer

### För Normal Användning
Med 95K tokens context har du gott om utrymme:

1. **Kör debatten normalt** - inga special-tricks behövs
2. **Övervaka logs** - kontrollera token counts första gången
3. **Justera vid behov** - om du vill ha ännu mer kontext, kan gränserna höjas ytterligare

### Om Du Vill Ha Ännu Mer Kontext

Du kan öka gränserna ytterligare:

```python
# I debate_flow.py

# Summarization: 300 → 500 chars
snippet = resp['response'][:500]

# chain_so_far: 5 → 7 svar
recent = self.chain_so_far[-7:]

# Voting: 500 → 800 chars
if len(response_text) > 800:
    response_text = response_text[:800]

# Hard limit: 60K → 80K
if token_count > 80000:
    # Skip
```

**OBS:** Med 95K context kan du säkert gå upp till 70-80K tokens input och fortfarande ha plats för respons.

---

## Jämförelse: Konservativ vs Balanserad Strategi

### Konservativ (gamla gränser för 32K)
```
┌─────────────────────────────────────────┐
│ [█████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] │
│  15K limit / 95K kapacitet = 16%        │
│  Peak: 3.5K tokens = 4% användning      │
└─────────────────────────────────────────┘
Resultat: Funkar men mycket restriktivt
```

### Balanserad (nya gränser för 95K)
```
┌─────────────────────────────────────────┐
│ [█████████████████████████████████░░░░] │
│  60K limit / 95K kapacitet = 63%        │
│  Peak: 8-12K tokens = 8-13% användning  │
└─────────────────────────────────────────┘
Resultat: Bättre kvalitet, fortfarande säkert
```

### Aggressiv (om du vill maxa)
```
┌─────────────────────────────────────────┐
│ [█████████████████████████████████████] │
│  80K limit / 95K kapacitet = 84%        │
│  Peak: 15-20K tokens = 16-21% användning│
└─────────────────────────────────────────┘
Resultat: Maximal kvalitet, mindre marginal
```

**Rekommendation:** Stanna på "Balanserad" - bästa tradeoff mellan kvalitet och säkerhet.

---

## Slutsats

Med 95K token context window kan vi:

✅ **Använda mindre aggressiv summarization** (300 chars istället för 150)  
✅ **Behålla mer current round kontext** (5 svar istället för 3)  
✅ **Ge bättre voting information** (500 chars istället för 300)  
✅ **Höja hard limit kraftigt** (60K istället för 15K)  
✅ **Fortfarande ha 35K tokens för respons**  
✅ **Hålla peak context på ~8-12K** (endast 8-13% av kapacitet)

**Debattkvaliteten förbättras kraftigt** medan säkerhetsmarginalen är fortfarande **mycket god**.

---

## Nästa Steg

1. ✅ Kod uppdaterad med nya gränser
2. ⏳ Testa live debatt med 5 modeller
3. ⏳ Granska logs för faktiska token counts
4. ⏳ Justera ytterligare om önskat (kan öka mer)
5. ⏳ Validera debattkvalitet är förbättrad

**Status:** Klar för testning med optimala gränser för 95K modell!
