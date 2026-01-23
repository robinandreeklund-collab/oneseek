# Design Proposals for Model Action Transparency

This directory contains 20 unique design proposals for showcasing complete transparency and insights into the actions performed by AI models. Each design aligns with the existing OneSeek frontend design language while exploring diverse approaches to visualizing model actions.

## Overview

These designs demonstrate different ways to display:
- Web searches and API calls
- Data aggregation and retrieval
- Processing steps and workflows
- Real-time updates and streaming
- Retrieved documents and sources

All designs maintain consistency with the OneSeek design system:
- **Color Scheme**: HSL-based with light/dark mode support
- **Components**: shadcn/ui (Radix UI primitives)
- **Icons**: Lucide React
- **Framework**: Tailwind CSS utilities

## Design Proposals

### 1. Linear Timeline View
**File**: `proposal-01-linear-timeline.html`

**Key Features**:
- Chronological display of all model actions
- Each action shown as a card on a vertical timeline
- Real-time updates append to the bottom
- Color-coded by action type (search, API call, retrieval)
- Expandable details for each step

**Use Case**: Best for users who want to see the exact sequence of events

---

### 2. Expandable Cards Pipeline
**File**: `proposal-02-expandable-cards.html`

**Key Features**:
- Compact card view with expand/collapse functionality
- Shows action summary in collapsed state
- Detailed information when expanded
- Visual connecting lines between cards
- Progress indicators on each card

**Use Case**: Balances information density with accessibility

---

### 3. Vertical Flow Diagram
**File**: `proposal-03-flow-diagram.html`

**Key Features**:
- Visual flowchart-style representation
- Arrows showing data flow between steps
- Parallel actions shown side-by-side
- Error/success states clearly marked
- Interactive hover states for details

**Use Case**: Ideal for complex multi-step processes

---

### 4. Tabbed Interface
**File**: `proposal-04-tabbed-interface.html`

**Key Features**:
- Separate tabs for different action types
- "All", "Searches", "API Calls", "Retrieval" tabs
- Badge counts on each tab
- Filtered view within each tab
- Unified timeline when "All" is selected

**Use Case**: Best when users want to focus on specific action types

---

### 5. Sidebar Panel
**File**: `proposal-05-sidebar-panel.html`

**Key Features**:
- Persistent sidebar showing live activity
- Doesn't interfere with main chat interface
- Toggle to show/hide panel
- Scrollable with most recent at top
- Compact representation of actions

**Use Case**: Always-visible transparency without cluttering main view

---

### 6. Modal Overlay
**File**: `proposal-06-modal-overlay.html`

**Key Features**:
- Full-screen overlay when activated
- Detailed breakdown of all actions
- Close button to return to chat
- Search/filter capabilities within modal
- Export/copy functionality

**Use Case**: Deep dive analysis when needed

---

### 7. Progress Bar with Steps
**File**: `proposal-07-progress-steps.html`

**Key Features**:
- Linear progress bar showing completion
- Step indicators along the bar
- Current step highlighted
- Completed steps checked
- Estimated time remaining

**Use Case**: Simple, visual progress tracking

---

### 8. Tree View Hierarchy
**File**: `proposal-08-tree-view.html`

**Key Features**:
- Hierarchical tree structure
- Parent actions with nested sub-actions
- Expand/collapse branches
- Indentation shows depth
- Icons for different action types

**Use Case**: Complex workflows with dependencies

---

### 9. Kanban-style Columns
**File**: `proposal-09-kanban-columns.html`

**Key Features**:
- Three columns: "Pending", "Processing", "Complete"
- Cards move across columns in real-time
- Visual representation of workflow state
- Drag-and-drop (conceptual)
- Count badges on column headers

**Use Case**: Clear visualization of action states

---

### 10. Animated Sequence
**File**: `proposal-10-animated-sequence.html`

**Key Features**:
- Smooth animations as actions occur
- Fade-in for new actions
- Pulse effect for active operations
- Slide-out for completed actions
- Engaging visual feedback

**Use Case**: Dynamic, modern feel with high engagement

---

### 11. Inspector Panel
**File**: `proposal-11-inspector-panel.html`

**Key Features**:
- Developer-tool style interface
- JSON view of raw data
- Collapsible sections
- Syntax highlighting
- Copy-to-clipboard buttons

**Use Case**: Technical users wanting full transparency

---

### 12. Floating Action Cards
**File**: `proposal-12-floating-cards.html`

**Key Features**:
- Cards appear as overlay badges
- Float above main content
- Minimize/maximize individually
- Drag to reposition
- Auto-dismiss after completion

**Use Case**: Non-intrusive real-time notifications

---

### 13. Compact List View
**File**: `proposal-13-compact-list.html`

**Key Features**:
- Dense information display
- Single line per action
- Icon + description + timestamp
- Quick scan capability
- Minimal visual clutter

**Use Case**: Users preferring information density

---

### 14. Grid Layout
**File**: `proposal-14-grid-layout.html`

**Key Features**:
- Masonry-style grid of action cards
- Automatic responsive layout
- Visual grouping by type
- Hover for details
- Click to expand

**Use Case**: Visual learners, dashboard feel

---

### 15. Timeline with Branches
**File**: `proposal-15-branched-timeline.html`

**Key Features**:
- Central timeline with branching paths
- Parallel operations shown as branches
- Merge points where data combines
- Git-style visualization
- Complex workflow clarity

**Use Case**: Parallel processing transparency

---

### 16. Nested Accordion
**File**: `proposal-16-nested-accordion.html`

**Key Features**:
- Multi-level collapsible sections
- Category headers (Search, Retrieve, Process)
- Individual action items nested within
- Expand all/collapse all controls
- Maintains scroll position

**Use Case**: Organized, hierarchical information

---

### 17. Horizontal Scrollable Steps
**File**: `proposal-17-horizontal-scroll.html`

**Key Features**:
- Horizontal carousel of steps
- Left/right navigation arrows
- Current step centered and highlighted
- Breadcrumb trail at top
- Snap-to-step scrolling

**Use Case**: Step-by-step guided view

---

### 18. Radial/Circular Progress
**File**: `proposal-18-radial-progress.html`

**Key Features**:
- Circular progress indicator
- Actions arranged in a circle
- Center shows overall status
- Segments for each action type
- Animated arc progression

**Use Case**: Unique, visually striking design

---

### 19. Split View
**File**: `proposal-19-split-view.html`

**Key Features**:
- Screen divided into chat and transparency sections
- Adjustable divider (resize)
- Synchronized scrolling option
- Independent view controls
- Side-by-side comparison

**Use Case**: Power users wanting simultaneous views

---

### 20. Minimal Indicator Bar
**File**: `proposal-20-minimal-indicator.html`

**Key Features**:
- Thin bar at top/bottom of screen
- Color changes with activity
- Click to expand to full view
- Unobtrusive by default
- Quick status at a glance

**Use Case**: Users wanting minimal UI with optional depth

---

## Design Principles Applied

All designs follow these core principles:

1. **Transparency**: Every action is visible and explainable
2. **Consistency**: Uses OneSeek's design tokens and components
3. **Progressive Disclosure**: Basic info by default, details on demand
4. **Real-time Updates**: Designs support streaming/live data
5. **Accessibility**: Keyboard navigation, screen reader support
6. **Responsiveness**: Works on mobile and desktop
7. **Performance**: Lightweight, doesn't impact chat performance

## Color Palette

Based on OneSeek's design system:

### Light Mode
- Background: `hsl(0, 0%, 100%)`
- Foreground: `hsl(240, 10%, 3.9%)`
- Primary: `hsl(240, 5.9%, 10%)`
- Muted: `hsl(240, 4.8%, 95.9%)`
- Border: `hsl(240, 5.9%, 90%)`

### Dark Mode
- Background: `hsl(0, 0%, 9%)`
- Foreground: `hsl(0, 0%, 98%)`
- Primary: `hsl(0, 0%, 98%)`
- Muted: `hsl(240, 3.7%, 15.9%)`
- Border: `hsl(240, 3.7%, 15.9%)`

## Action Types & Icons

- 🔍 **Search**: Web searches, knowledge base queries
- 🔌 **API Call**: External service calls
- 📚 **Retrieval**: Document/data fetching (RAG)
- ⚙️ **Processing**: Data transformation, analysis
- ✅ **Complete**: Successfully finished action
- ❌ **Error**: Failed action
- ⏳ **Pending**: Queued action

## Implementation Notes

These are visual mockups created as HTML/CSS files. To implement in the actual OneSeek application:

1. Use existing shadcn/ui components as base
2. Extend `transparens-accordion.tsx` or create new components
3. Integrate with streaming API responses
4. Add state management for real-time updates
5. Implement animations using Framer Motion or CSS transitions
6. Ensure dark mode compatibility
7. Add keyboard shortcuts for power users
8. Test with actual API response data

## Viewing the Mockups

Each HTML file is self-contained and can be opened directly in a web browser:

```bash
cd design-proposals/mockups
open proposal-01-linear-timeline.html  # macOS
xdg-open proposal-01-linear-timeline.html  # Linux
start proposal-01-linear-timeline.html  # Windows
```

Or use a local server:

```bash
cd design-proposals/mockups
python3 -m http.server 8080
# Open http://localhost:8080 in browser
```

## Exporting as Images

To create PNG screenshots of each design:

1. Open each HTML file in a browser
2. Use browser DevTools device emulation (1200x800 recommended)
3. Take screenshots using browser tools or:
   - Chrome: Cmd/Ctrl + Shift + P → "Capture screenshot"
   - Firefox: Shift + F2 → "screenshot --fullpage"
4. Save to `design-proposals/screenshots/` directory

Or use automated tools:
```bash
# Using Playwright (if available)
npx playwright screenshot proposal-01-linear-timeline.html screenshot-01.png

# Using Puppeteer
node screenshot-script.js
```

## Feedback & Iteration

These proposals are starting points for discussion. Key questions to consider:

1. Which design best balances transparency with usability?
2. Should we combine elements from multiple designs?
3. What's the priority: simplicity or information density?
4. Mobile vs desktop: should they differ significantly?
5. How much control should users have (customize view)?

## Next Steps

1. Review all 20 proposals with stakeholders
2. Select top 3-5 for prototyping
3. Create interactive React components
4. User testing with real data
5. Iterate based on feedback
6. Implement final design in production

---

**Created**: 2026-01-23
**Version**: 1.0
**Author**: GitHub Copilot Design Team
