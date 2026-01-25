# Implementation Structure

## Frontend Structure

```
web/
├── messages/
│   ├── en.json          [Updated: DeerFlow → Oneseek]
│   ├── zh.json          [Updated: DeerFlow → Oneseek]
│   └── sv.json          [NEW: 286+ Swedish translations]
│
├── src/
│   ├── app/
│   │   ├── admin/                    [NEW: Admin Panel]
│   │   │   ├── layout.tsx           [Sidebar navigation]
│   │   │   ├── page.tsx             [Dashboard]
│   │   │   └── prompts/
│   │   │       ├── page.tsx         [Prompt list]
│   │   │       └── [path]/
│   │   │           └── page.tsx     [Prompt editor]
│   │   │
│   │   ├── api/
│   │   │   └── admin/
│   │   │       └── prompts/
│   │   │           ├── route.ts     [GET: List prompts]
│   │   │           └── [path]/
│   │   │               └── route.ts [GET/PUT: Read/Update prompt]
│   │   │
│   │   ├── chat/
│   │   │   └── components/
│   │   │       └── site-header.tsx  [Updated: Logo]
│   │   └── layout.tsx               [Updated: Title]
│   │
│   ├── components/
│   │   └── deer-flow/
│   │       ├── logo.tsx             [Updated: Oneseek]
│   │       └── language-switcher.tsx [Updated: Added Swedish]
│   │
│   └── i18n.ts                      [Updated: Swedish locale]
│
└── package.json                     [Updated: oneseek-web]
```

## Backend Integration

```
backend/
└── deer_flow/
    └── prompts/                     [Managed by Admin Panel]
        ├── coordinator.md
        ├── coordinator.zh_CN.md
        ├── planner.md
        ├── planner.zh_CN.md
        ├── reporter.md
        ├── reporter.zh_CN.md
        ├── researcher.md
        ├── researcher.zh_CN.md
        ├── analyst.md
        ├── analyst.zh_CN.md
        ├── coder.md
        ├── coder.zh_CN.md
        ├── podcast/
        │   ├── podcast_composer.md
        │   └── podcast_composer.zh_CN.md
        ├── ppt/
        │   ├── ppt_composer.md
        │   └── ppt_composer.zh_CN.md
        ├── prose/
        │   ├── prose_*.md files
        │   └── prose_*.zh_CN.md files
        └── prompt_enhancer/
            └── prompt_enhancer.md
```

## User Flow

### 1. Language Selection
```
User → Language Switcher → 🇸🇪 Svenska → Reload → Swedish UI
```

### 2. Admin Panel Access
```
User → Navigate to /admin → Dashboard
     ↓
     → Click "Prompts" → List of all prompts
     ↓
     → Click "Redigera" on any prompt → Edit page
     ↓
     → Edit content → Click "Spara ändringar" → Save to file
```

### 3. API Flow
```
Frontend                   Backend API                 File System
   │                           │                           │
   ├─GET /api/admin/prompts───→│                           │
   │                           ├─Scan directory────────────→│
   │                           │←─Return file list─────────┤
   │←──────────────────────────┤                           │
   │                           │                           │
   ├─GET /api/admin/prompts/   │                           │
   │  coordinator.md───────────→│                           │
   │                           ├─Read file─────────────────→│
   │                           │←─Return content───────────┤
   │←──────────────────────────┤                           │
   │                           │                           │
   ├─PUT /api/admin/prompts/   │                           │
   │  coordinator.md───────────→│                           │
   │  (new content)             ├─Validate path            │
   │                           ├─Write file────────────────→│
   │                           │←─Confirm write────────────┤
   │←─Success───────────────────┤                           │
```

## Features Summary

### Swedish Translation ✅
- All UI text translated
- Consistent terminology
- Natural Swedish phrasing
- Context-appropriate translations

### Brand Update ✅
- Logo: "Oneseek" (no deer emoji)
- All text references updated
- Consistent across all languages
- Maintained internal structure

### Admin Panel ✅
- Clean, intuitive interface
- Real-time editing
- Security validations
- Error handling
- Responsive design
- Swedish language

## Security Features

1. **Path Validation**: Prevents directory traversal attacks
2. **Type Checking**: Validates input data types
3. **Error Handling**: Graceful failure with user feedback
4. **File Restrictions**: Only .md files in prompts directory

## Extensibility

The admin panel is designed to be easily extended:
- Add new sections to sidebar
- Create new management pages
- Add more API endpoints
- Implement authentication
- Add version control
