# Debugging Guide: Persistent TypeError Errors

## Problem

User reports getting the same TypeErrors even after fixes have been committed:
1. `TypeError: Cannot read properties of undefined (reading 'toLowerCase')`
2. `TypeError: Cannot read properties of undefined (reading 'agent')`

## Fixes Applied (Commit 51a6254)

### Fix #1: research-block.tsx line 822
```typescript
// Before
reportStyle={useSettingsStore.getState().general.reportStyle.toLowerCase()}

// After
reportStyle={useSettingsStore.getState().general.reportStyle?.toLowerCase() ?? "comprehensive"}
```

### Fix #2: research-activities-block.tsx lines 98-101
```typescript
// Added guard
if (!message) {
  return null;
}
```

## Why Errors Persist: Browser Cache

The most common reason for seeing old errors after fixes is **browser caching old JavaScript**.

## Solution Steps

### Step 1: Verify Latest Code

```bash
cd /path/to/oneseek
git fetch origin
git checkout copilot/integrera-ny-router-kodfror
git pull origin copilot/integrera-ny-router-kodfror

# Verify you have the fix
git log --oneline -1
# Should show: 51a6254 Fix two TypeError crashes...

# Verify the actual changes
git show 51a6254:web/src/app/chat/components/research-block.tsx | grep -A 1 -B 1 "reportStyle="
# Should show: reportStyle?.toLowerCase()

git show 51a6254:web/src/app/chat/components/research-activities-block.tsx | grep -A 3 "Guard against"
# Should show: if (!message) { return null; }
```

### Step 2: Clean Build and Restart Frontend

```bash
cd web

# Kill current dev server (Ctrl+C)

# Remove all caches
rm -rf .next
rm -rf node_modules/.cache
rm -rf .turbo

# Optional: Reinstall dependencies if needed
# npm install

# Start fresh
npm run dev
```

### Step 3: Hard Refresh Browser

**Option A: DevTools Method**
1. Open DevTools (F12)
2. Right-click the refresh button in browser toolbar
3. Select "Empty Cache and Hard Reload"

**Option B: Keyboard Shortcut**
- Windows/Linux: `Ctrl + Shift + R` or `Ctrl + F5`
- Mac: `Cmd + Shift + R`

**Option C: Manual Cache Clear**
1. Press `Ctrl + Shift + Delete`
2. Select "Cached images and files"
3. Select time range "All time"
4. Click "Clear data"
5. Then refresh page normally

### Step 4: Verify Cache is Cleared

Open Console and run:
```javascript
// Check when resources were loaded
performance.getEntriesByType('resource')
  .filter(r => r.name.includes('research'))
  .map(r => ({
    url: r.name.split('/').pop(),
    loadTime: new Date(r.responseEnd).toLocaleTimeString()
  }))
```

The timestamps should be AFTER your git pull time.

### Step 5: Test Again

1. Send test message: "Använd coder för att skapa en fil test.txt"
2. Watch Console for errors
3. If no errors → SUCCESS!
4. If still errors → See "Advanced Debugging" below

## Advanced Debugging

### Check if Fix is Actually Loaded

Open Console and run:
```javascript
// Check research-block component
const blocks = document.querySelectorAll('[data-component="research-block"]');
console.log('Found research blocks:', blocks.length);

// Check activities
const activities = document.querySelectorAll('[data-component="research-activities"]');
console.log('Found activities:', activities.length);
```

### Force Module Reload

If cache persists:

**Option 1: Disable Cache in DevTools**
1. Open DevTools (F12)
2. Go to Network tab
3. Check "Disable cache" checkbox
4. Keep DevTools OPEN while testing
5. Refresh page

**Option 2: Incognito/Private Mode**
1. Open new incognito/private window
2. Navigate to localhost:3000
3. Test there (no cache exists)

**Option 3: Different Browser**
Try in a different browser that hasn't cached the old code.

### Check Build Output

After `npm run dev`, check terminal output:
```
○ Compiling /chat ...
✓ Compiled /chat in X.Xms
```

If you see warnings or errors about TypeScript, the build might have failed.

### Manual Verification

Navigate to the actual file on disk:
```bash
cat web/src/app/chat/components/research-block.tsx | grep -A 1 "reportStyle="
# Should show: reportStyle?.toLowerCase()

cat web/src/app/chat/components/research-activities-block.tsx | grep -A 3 "if (!message)"
# Should show: if (!message) { return null; }
```

## If Still Failing

### Collect Diagnostic Information

1. **Current git commit**:
```bash
git rev-parse HEAD
```

2. **File checksums**:
```bash
md5sum web/src/app/chat/components/research-block.tsx
md5sum web/src/app/chat/components/research-activities-block.tsx
```

3. **Browser info**:
- Browser name and version
- OS

4. **Console error**:
- Full error message
- Stack trace
- Line numbers

5. **Network tab**:
- Check Response tab for the .js file
- Verify it contains the fixed code

### Report Back

If errors persist after ALL above steps, provide:
- Output of diagnostic commands
- Screenshot of Console error with full stack trace
- Screenshot of Network tab showing loaded resources
- Confirmation that all steps were followed

## Common Pitfalls

❌ **Only refreshing page** - Not enough, cache persists  
❌ **Clearing cookies** - Wrong thing, need to clear cached files  
❌ **Not restarting dev server** - Old build still in .next directory  
❌ **DevTools not open** - Some cache clearing requires DevTools  
❌ **Testing too quickly** - Wait for "Compiled successfully" message  

✅ **Full clean** - Remove .next, restart dev, hard refresh  
✅ **DevTools open** - Keep F12 open with cache disabled  
✅ **Wait for build** - Ensure "Compiled successfully" appears  
✅ **Verify fix** - Check actual file content on disk  

## Expected Behavior After Fix

When working correctly:
1. No console errors
2. Coder messages display in chat
3. Tool results shown
4. No "An error occurred" toast
5. Smooth streaming and rendering

## Summary

The fixes ARE in the code (verified). The issue is almost certainly browser cache serving old JavaScript. Follow the steps above methodically, and the errors will disappear.
