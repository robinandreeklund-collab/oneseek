# Fixa Cache-Problem - Snabbguide

## Problem
Du ser fortfarande samma fel trots att fixarna är i koden. Detta beror på **webbläsarens cache**.

## Lösning (3 steg)

### Steg 1: Hämta senaste koden
```bash
cd /path/to/oneseek
git pull origin copilot/integrera-ny-router-kodfror
```

Kontrollera att du har rätt commit:
```bash
git log --oneline -1
```
Ska visa: `de2327c Add comprehensive debugging guide...` eller senare

### Steg 2: Rensa och starta om frontend
```bash
cd web

# Stoppa dev server (Ctrl+C om den kör)

# Rensa cache
rm -rf .next
rm -rf node_modules/.cache

# Starta om
npm run dev
```

Vänta tills du ser: `✓ Compiled successfully`

### Steg 3: Hård omladdning i webbläsare

**Metod A (enklast)**:
1. Öppna F12 (DevTools)
2. Håll Ctrl och tryck F5
3. ELLER högerklicka på refresh-knappen → "Töm cache och hård omladdning"

**Metod B (säkrast)**:
1. Tryck Ctrl + Shift + Delete
2. Välj "Cachade bilder och filer"
3. Välj "Hela tiden"
4. Klicka "Rensa data"
5. Ladda om sidan (F5)

**Metod C (om inget annat funkar)**:
- Öppna nytt inkognito-fönster (Ctrl + Shift + N)
- Gå till localhost:3000
- Testa där (ingen cache finns)

### Steg 4: Verifiera
1. Öppna F12 → Console-fliken
2. Skicka test: "Använd coder för att skapa en fil test.txt"
3. Konsolen ska vara TOM (inga röda fel)
4. Coder output ska visas i chatten

## Om det fortfarande inte fungerar

### Dubbelkolla att fixarna finns
```bash
# Kontrollera fix #1
grep "reportStyle?" web/src/app/chat/components/research-block.tsx
# Ska visa: reportStyle?.toLowerCase()

# Kontrollera fix #2  
grep -A 2 "if (!message)" web/src/app/chat/components/research-activities-block.tsx
# Ska visa: if (!message) { return null; }
```

Om dessa inte visas, kör `git pull` igen.

### Aktivera "Disable cache" i DevTools
1. Öppna F12
2. Gå till Network-fliken
3. Kryssa i "Disable cache"
4. HÅLL F12 ÖPPEN medan du testar
5. Ladda om sidan

### Prova annan webbläsare
Om du använder Chrome, prova Edge/Firefox eller vice versa.

## Varför händer detta?

- Next.js kompilerar och cachar JavaScript-filer
- Webbläsaren cachar dessa filer lokalt
- När du uppdaterar kod måste både Next.js OCH webbläsaren uppdateras
- Vanlig refresh räcker inte - man måste rensa cache

## Förväntat resultat efter fix

✅ Inga fel i Console  
✅ Coder kör och skapar filen  
✅ Du ser output i chatten  
✅ Tool Results visas  
✅ Ingen "An error occurred" toast  

## Snabb checklista

- [ ] `git pull` kördes
- [ ] `rm -rf .next` kördes
- [ ] `npm run dev` startade om
- [ ] "Compiled successfully" visades
- [ ] Ctrl+Shift+R i webbläsare
- [ ] F12 Console är tom (inga fel)
- [ ] Test med coder fungerar

## Mer detaljer

Se `DEBUGGING_PERSISTENT_ERRORS.md` för fullständig guide.
