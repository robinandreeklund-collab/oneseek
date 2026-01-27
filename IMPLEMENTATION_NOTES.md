# Swedish Translation and Admin Panel

This document describes the changes made to translate the frontend to Swedish and add an admin panel for prompt management.

## Changes Summary

### 1. Swedish Translation (sv.json)

A complete Swedish translation file has been created at `/web/messages/sv.json` with translations for all UI text, including:

- Common UI elements (buttons, labels, etc.)
- Chat interface messages
- Settings and configuration
- Landing page content
- Error messages and notifications

The Swedish locale is now available in the language switcher alongside English and Chinese.

### 2. Brand Update: DeerFlow → Oneseek

All references to "DeerFlow" have been replaced with "Oneseek" throughout the frontend:

- Logo component (`/web/src/components/deer-flow/logo.tsx`)
- Package.json name
- HTML metadata and page titles
- Translation files (en.json, zh.json, sv.json)
- Site header

**Note**: The "deer-flow" directory structure remains unchanged to avoid breaking imports.

### 3. Admin Panel

A new admin panel has been created at `/admin` with the following features:

#### Frontend Components:

- **Layout** (`/web/src/app/admin/layout.tsx`): Main admin layout with sidebar navigation
- **Dashboard** (`/web/src/app/admin/page.tsx`): Admin home page with quick links
- **Prompts List** (`/web/src/app/admin/prompts/page.tsx`): Lists all system prompts
- **Prompt Editor** (`/web/src/app/admin/prompts/[path]/page.tsx`): Edit individual prompt files

#### Backend API Endpoints:

- `GET /api/admin/prompts`: List all available prompt files
- `GET /api/admin/prompts/[path]`: Get content of a specific prompt
- `PUT /api/admin/prompts/[path]`: Update content of a specific prompt

#### Features:

- Browse all prompt files (including subdirectories)
- View prompts with locale information (en, zh_CN, sv_SE)
- Edit prompt content in a text editor
- Save changes with validation
- Security: Path validation to prevent directory traversal

## How to Use

### Accessing the Admin Panel

1. Navigate to `/admin` in your browser
2. Use the sidebar to access different sections:
   - **Översikt** (Overview): Admin dashboard
   - **Prompts**: Prompt management

### Managing Prompts

1. Go to `/admin/prompts`
2. Click "Redigera" (Edit) on any prompt
3. Edit the content in the text editor
4. Click "Spara ändringar" (Save changes) to update the prompt

The changes are immediately saved to the prompt files in `/backend/deer_flow/prompts/`.

### Changing Language

Use the language switcher in the top navigation bar to switch between:
- 🇺🇸 English
- 🇨🇳 中文 (Chinese)
- 🇸🇪 Svenska (Swedish)

## Technical Details

### Translation System

The application uses `next-intl` for internationalization:
- Translation files: `/web/messages/{locale}.json`
- Configuration: `/web/src/i18n.ts`
- Supported locales: `en`, `zh`, `sv`

### Prompt Management

Prompts are stored as Markdown files in `/backend/deer_flow/prompts/`:
- Main prompts: `coordinator.md`, `planner.md`, `reporter.md`, etc.
- Localized prompts: `coordinator.zh_CN.md`, etc.
- Subdirectories: `podcast/`, `ppt/`, `prose/`, etc.

The admin panel recursively scans this directory and allows editing all `.md` files.

## Future Enhancements

Potential improvements for the admin panel:
- User authentication and authorization
- Prompt version history
- Preview mode for prompts
- System configuration management
- Analytics dashboard
- Backup and restore functionality

## Files Changed

### Swedish Translation:
- `web/messages/sv.json` (new)
- `web/src/i18n.ts`
- `web/src/components/deer-flow/language-switcher.tsx`

### Brand Update:
- `web/messages/en.json`
- `web/messages/zh.json`
- `web/src/components/deer-flow/logo.tsx`
- `web/src/app/layout.tsx`
- `web/src/app/chat/components/site-header.tsx`
- `web/package.json`

### Admin Panel:
- `web/src/app/admin/layout.tsx` (new)
- `web/src/app/admin/page.tsx` (new)
- `web/src/app/admin/prompts/page.tsx` (new)
- `web/src/app/admin/prompts/[path]/page.tsx` (new)
- `web/src/app/api/admin/prompts/route.ts` (new)
- `web/src/app/api/admin/prompts/[path]/route.ts` (new)
