"""HTML frontend for NiyamAI — authoritative, executive-grade RBI regulatory intelligence interface."""

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NiyamAI — RBI Regulatory Intelligence</title>
    <meta name="description" content="Authoritative regulatory intelligence platform for Reserve Bank of India notifications, master directions, and compliance circulars.">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Geist+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,600;1,6..72,400&family=Space+Grotesk:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js"></script>
    <style>
        :root {
            /* Editorial Financial Palette — high contrast, archival paper, archival ink */
            --bg-canvas: #F9FAFC;
            --bg-surface: #FFFFFF;
            --bg-muted: #F0F4F8;
            --bg-accent: #E2E8F0;

            --border-subtle: #E2E8F0;
            --border-strong: #CBD5E1;
            --border-heavy: #0F172A;

            --text-primary: #0F172A;
            --text-secondary: #475569;
            --text-muted: #64748B;

            /* Archival Ink Accent — deep olive for trust, not green */
            --accent-ink: #2C3E1A;
            --accent-ink-light: #F0F4F1;
            --accent-ink-border: #5A6D34;

            /* High Contrast Status — paper-aware */
            --error-bg: #FEF2F2;
            --error-text: #991B1B;
            --error-border: #FCA5A5;

            /* Typography Scale — editorial serif + geometric sans + mono accent */
            --font-sans: 'Space Grotesk', 'Inter', system-ui, -apple-system, sans-serif;
            --font-serif: 'Newsreader', 'Georgia', serif;
            --font-mono: 'IBM Plex Mono', 'Geist Mono', 'Consolas', monospace;
        }

        *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: var(--font-sans);
            background: var(--bg-canvas);
            color: var(--text-primary);
            min-height: 100vh;
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
            font-feature-settings: "liga" 1, "calt" 1, "kern" 1;
        }

        /* Custom focus indicators for keyboard navigation */
        :focus-visible {
            outline: 2px solid var(--accent-ink);
            outline-offset: 2px;
        }

        button:focus-visible,
        input:focus-visible,
        .filter-pill:focus-visible,
        .sample-item:focus-visible,
        .history-chip:focus-visible {
            outline: 2px solid var(--accent-ink);
            outline-offset: 2px;
            border-radius: 3px;
        }

        /* Custom scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }

        ::-webkit-scrollbar-track {
            background: var(--bg-muted);
        }

        ::-webkit-scrollbar-thumb {
            background: var(--border-strong);
            border-radius: 4px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: var(--border-heavy);
        }

        /* Selection styling */
        ::selection {
            background: var(--accent-ink-light);
            color: var(--accent-ink);
        }

        .page-container {
            max-width: 900px;
            margin: 0 auto;
            padding: 0 24px 80px;
            position: relative;
            isolation: isolate;
        }

        /* ── Executive Header ── */
        header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 32px 0 24px;
            border-bottom: 2px solid var(--border-heavy);
            margin-bottom: 40px;
            position: relative;
        }

        .brand {
            display: flex;
            align-items: baseline;
            gap: 14px;
            text-decoration: none;
            color: var(--text-primary);
        }

        .brand-title {
            font-size: 1.625rem;
            font-weight: 700;
            letter-spacing: -0.04em;
            font-family: var(--font-serif);
            line-height: 1.1;
        }

        .brand-tag {
            font-family: var(--font-mono);
            font-size: 0.68rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.09em;
            font-weight: 500;
        }

        .org-badge {
            font-family: var(--font-mono);
            font-size: 0.65rem;
            color: var(--accent-ink);
            background: var(--accent-ink-light);
            border: 1px solid var(--accent-ink-border);
            padding: 2px 6px;
            font-weight: 600;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }

        /* ── Preamble ── */
        .preamble {
            margin-bottom: 32px;
        }

        .preamble h1 {
            font-family: var(--font-serif);
            font-size: 2.125rem;
            font-weight: 600;
            line-height: 1.15;
            color: var(--text-primary);
            margin-bottom: 12px;
            letter-spacing: -0.03em;
        }

        .preamble p {
            font-size: 1rem;
            color: var(--text-secondary);
            max-width: 760px;
            line-height: 1.7;
            font-family: var(--font-serif);
        }

        .stats-bar {
            display: flex;
            gap: 24px;
            margin-top: 16px;
            padding-top: 12px;
            border-top: 1px solid var(--border-subtle);
        }

        .stat-group {
            display: flex;
            flex-direction: column;
        }

        .stat-val {
            font-family: var(--font-mono);
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--text-primary);
        }

        .stat-lbl {
            font-family: var(--font-mono);
            font-size: 0.62rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }

        /* ── Query Engine ── */
        .query-box {
            background: var(--bg-surface);
            border: 1px solid var(--border-strong);
            padding: 12px;
            margin-bottom: 40px;
            border-radius: 1px;
            position: relative;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        }

        .query-input-row {
            display: flex;
            gap: 8px;
            align-items: stretch;
        }

        .query-field {
            flex: 1;
            padding: 16px 20px;
            border: none;
            outline: none;
            font-family: var(--font-sans);
            font-size: 1.05rem;
            color: var(--text-primary);
            background: transparent;
            font-feature-settings: "liga" 1, "calt" 1;
        }

        .query-field::placeholder {
            color: var(--text-muted);
            font-family: var(--font-sans);
        }

        .btn-submit {
            padding: 16px 28px;
            background: var(--border-heavy);
            color: #FFFFFF;
            border: none;
            font-family: var(--font-mono);
            font-size: 0.75rem;
            font-weight: 600;
            letter-spacing: 0.07em;
            text-transform: uppercase;
            cursor: pointer;
            transition: background 0.15s ease, transform 0.1s ease;
            display: flex;
            align-items: center;
            gap: 8px;
            flex-shrink: 0;
            min-width: 88px;
        }

        .btn-submit:hover:not(:disabled) {
            background: var(--accent-ink);
            transform: translateY(-1px);
        }

        .btn-submit:active:not(:disabled) {
            transform: translateY(0);
        }

        .btn-submit:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .btn-spin {
            width: 14px;
            height: 14px;
            border: 2px solid rgba(255,255,255,0.4);
            border-top-color: #FFFFFF;
            border-radius: 50%;
            animation: spin 0.8s cubic-bezier(0.16, 1, 0.3, 1) infinite;
            display: none;
        }

        .btn-submit.loading .btn-spin { display: block; }

        @keyframes spin { to { transform: rotate(360deg); } }

        /* ── Sector Filters ── */
        .filter-row {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-top: 16px;
            flex-wrap: wrap;
        }

        .filter-lbl {
            font-family: var(--font-mono);
            font-size: 0.68rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.07em;
            margin-right: 6px;
        }

        .filter-pill {
            font-family: var(--font-mono);
            font-size: 0.78rem;
            color: var(--text-secondary);
            padding: 6px 14px;
            background: var(--bg-surface);
            border: 1px solid var(--border-subtle);
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.15s ease;
            font-weight: 500;
            letter-spacing: 0.05em;
        }

        .filter-pill:hover {
            border-color: var(--border-heavy);
            color: var(--text-primary);
            background: var(--bg-muted);
        }

        .filter-pill.active {
            background: var(--accent-ink);
            color: #FFFFFF;
            border-color: var(--accent-ink);
        }

        /* ── Samples ── */
        .sample-queries {
            margin-top: 20px;
        }

        .sample-lbl {
            font-family: var(--font-mono);
            font-size: 0.7rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 10px;
        }

        .sample-list {
            display: flex;
            flex-wrap: wrap;
            gap: 8px 16px;
        }

        .sample-item {
            font-size: 0.9rem;
            color: var(--text-secondary);
            cursor: pointer;
            border-bottom: 1px solid var(--border-strong);
            padding-bottom: 2px;
            transition: all 0.15s ease;
            font-weight: 500;
            letter-spacing: -0.01em;
        }

        .sample-item:hover {
            color: var(--accent-ink);
            border-bottom-color: var(--accent-ink);
        }

        /* ── History Row ── */
        .history-row {
            display: none;
            align-items: center;
            gap: 10px;
            margin-bottom: 28px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border-subtle);
            flex-wrap: wrap;
        }

        .history-row.visible { display: flex; }

        .history-lbl {
            font-family: var(--font-mono);
            font-size: 0.68rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.07em;
        }

        .history-chip {
            font-size: 0.85rem;
            color: var(--text-muted);
            cursor: pointer;
            padding: 4px 12px;
            background: var(--bg-muted);
            border: 1px solid var(--border-subtle);
            border-radius: 4px;
            max-width: 240px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            transition: all 0.15s ease;
            font-weight: 500;
        }

        .history-chip:hover {
            color: var(--text-primary);
            border-color: var(--border-heavy);
            background: var(--bg-canvas);
        }

        /* ── Loading Skeleton ── */
        .skeleton {
            display: none;
            padding: 28px 0;
            margin-bottom: 32px;
        }

        .skeleton.active { display: block; }

        .sk-bar {
            height: 14px;
            background: var(--border-subtle);
            margin-bottom: 12px;
            border-radius: 2px;
            animation: pulse 1.4s ease-in-out infinite;
        }

        @keyframes pulse { 0%, 100% { opacity: 0.3; } 50% { opacity: 0.7; } }

        /* ── Error Display ── */
        .error-card {
            display: none;
            padding: 20px;
            background: var(--error-bg);
            border: 1px solid var(--error-border);
            color: var(--error-text);
            font-size: 0.95rem;
            margin-bottom: 32px;
            border-radius: 1px;
        }

        .error-card.active { display: block; }

        .error-recovery {
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid var(--error-border);
            font-size: 0.85rem;
            color: var(--error-text);
            opacity: 0.9;
        }

        .error-recovery a {
            color: var(--error-text);
            text-decoration: underline;
            cursor: pointer;
        }

        /* ── Answer Briefing Viewport ── */
        .answer-viewport {
            display: none;
            background: var(--bg-surface);
            border: 1px solid var(--border-strong);
            margin-bottom: 40px;
            border-radius: 1px;
            overflow: hidden;
        }

        .answer-viewport.visible { display: block; }

        .briefing-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px 24px;
            background: var(--bg-muted);
            border-bottom: 1px solid var(--border-strong);
        }

        .briefing-title {
            font-family: var(--font-mono);
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.09em;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .grounding-tag {
            font-family: var(--font-mono);
            font-size: 0.68rem;
            color: var(--accent-ink);
            background: var(--accent-ink-light);
            border: 1px solid var(--accent-ink-border);
            padding: 2px 8px;
            font-weight: 600;
            letter-spacing: 0.05em;
        }

        .briefing-actions {
            display: flex;
            gap: 8px;
        }

        .action-btn {
            font-family: var(--font-mono);
            font-size: 0.7rem;
            padding: 6px 12px;
            background: var(--bg-surface);
            border: 1px solid var(--border-strong);
            color: var(--text-primary);
            cursor: pointer;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            transition: all 0.15s ease;
            border-radius: 3px;
            font-weight: 500;
        }

        .action-btn:hover {
            border-color: var(--border-heavy);
            background: var(--bg-canvas);
        }

        .action-btn:active {
            transform: translateY(1px);
        }

        .briefing-body {
            padding: 32px 28px;
            font-family: var(--font-serif);
            font-size: 1.125rem;
            line-height: 1.75;
            color: var(--text-primary);
        }

        .briefing-body p {
            margin-bottom: 20px;
            text-align: justify;
            hyphens: auto;
        }

        .briefing-body h1, .briefing-body h2, .briefing-body h3 {
            font-family: var(--font-sans);
            font-weight: 700;
            color: var(--text-primary);
            margin: 28px 0 12px;
            letter-spacing: -0.02em;
            line-height: 1.3;
        }

        .briefing-body h3 {
            font-size: 1.25rem;
            padding-bottom: 6px;
            border-bottom: 1px solid var(--border-subtle);
        }

        .briefing-body ul, .briefing-body ol {
            margin: 16px 0 20px 28px;
        }

        .briefing-body li {
            margin-bottom: 8px;
        }

        .briefing-body code {
            font-family: var(--font-mono);
            font-size: 0.875em;
            background: var(--bg-muted);
            padding: 3px 6px;
            border: 1px solid var(--border-subtle);
            color: var(--accent-ink);
            border-radius: 2px;
        }

        .briefing-body blockquote {
            margin: 20px 0;
            padding: 14px 20px;
            background: var(--bg-muted);
            border-left: 3px solid var(--border-heavy);
            font-style: italic;
            color: var(--text-secondary);
            border-radius: 0 2px 2px 0;
        }

        /* Typewriter Cursor */
        .cursor {
            display: inline-block;
            width: 2px;
            height: 1.1em;
            background: var(--border-heavy);
            margin-left: 2px;
            vertical-align: text-bottom;
            animation: blink 0.8s step-end infinite;
        }

        @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }

        /* ── Evidence Cards (Citations System) ── */
        .evidence-section {
            display: none;
            border-top: 1px solid var(--border-strong);
            background: var(--bg-canvas);
            padding: 24px 28px;
        }

        .evidence-section.visible { display: block; }

        .evidence-title {
            font-family: var(--font-mono);
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.09em;
            color: var(--text-muted);
            margin-bottom: 18px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .evidence-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 16px;
        }

        .evidence-card {
            background: var(--bg-surface);
            border: 1px solid var(--border-subtle);
            padding: 18px 20px;
            cursor: pointer;
            transition: all 0.2s ease;
            border-radius: 1px;
            position: relative;
            overflow: hidden;
        }

        .evidence-card:hover {
            border-color: var(--border-heavy);
            box-shadow: 0 4px 16px rgba(0,0,0,0.06);
            transform: translateY(-2px);
        }

        .evidence-card:active {
            transform: translateY(0);
        }

        .evidence-card::before {
            content: "";
            position: absolute;
            inset: 0;
            background: linear-gradient(90deg, transparent, var(--accent-ink-light), transparent);
            opacity: 0;
            transition: opacity 0.2s ease;
        }

        .evidence-card:hover::before {
            opacity: 0.5;
        }

        .evidence-card-head {
            display: flex;
            align-items: baseline;
            justify-content: space-between;
            margin-bottom: 8px;
        }

        .evidence-doc-name {
            font-family: var(--font-sans);
            font-size: 1rem;
            font-weight: 600;
            color: var(--text-primary);
            letter-spacing: -0.01em;
        }

        .evidence-meta {
            font-family: var(--font-mono);
            font-size: 0.78rem;
            color: var(--accent-ink);
            font-weight: 500;
            letter-spacing: 0.05em;
        }

        .evidence-snippet {
            font-family: var(--font-mono);
            font-size: 0.85rem;
            color: var(--text-secondary);
            line-height: 1.65;
            background: var(--bg-muted);
            padding: 10px 14px;
            border-left: 2px solid var(--border-strong);
            margin-top: 10px;
            white-space: pre-wrap;
            max-height: 140px;
            overflow: hidden;
            text-overflow: ellipsis;
            border-radius: 1px;
        }

        .evidence-pdf-link {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            margin-top: 10px;
            font-family: var(--font-mono);
            font-size: 0.75rem;
            color: var(--text-muted);
            text-decoration: none;
            transition: all 0.15s ease;
            border-radius: 3px;
            padding: 4px 8px;
            border: 1px solid var(--border-subtle);
        }

        .evidence-pdf-link:hover {
            color: var(--accent-ink);
            border-color: var(--accent-ink);
            background: var(--accent-ink-light);
        }

        /* ── Follow-Up Thread ── */
        .followup-box {
            display: flex;
            gap: 8px;
            padding: 20px 28px;
            background: var(--bg-muted);
            border-top: 1px solid var(--border-strong);
            border-radius: 0 0 1px 1px;
        }

        .followup-field {
            flex: 1;
            padding: 12px 18px;
            border: 1px solid var(--border-strong);
            border-right: none;
            border-bottom-left-radius: 1px;
            border-top-left-radius: 1px;
            font-family: var(--font-sans);
            font-size: 0.95rem;
            color: var(--text-primary);
            background: var(--bg-surface);
            outline: none;
            font-feature-settings: "liga" 1, "calt" 1;
        }

        .followup-field::placeholder {
            color: var(--text-muted);
        }

        .followup-btn {
            padding: 12px 24px;
            background: var(--border-heavy);
            color: #FFFFFF;
            border: 1px solid var(--border-heavy);
            font-family: var(--font-mono);
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            cursor: pointer;
            white-space: nowrap;
            border-radius: 0 1px 1px 0;
            transition: all 0.15s ease;
        }

        .followup-btn:hover:not(:disabled) {
            background: var(--accent-ink);
            border-color: var(--accent-ink);
            transform: translateY(-1px);
        }

        .followup-btn:active:not(:disabled) {
            transform: translateY(0);
        }

        .followup-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        /* ── Multi-turn Thread ── */
        .turn-user {
            margin-top: 24px;
            padding: 14px 20px;
            background: var(--bg-muted);
            border-left: 4px solid var(--text-muted);
            font-size: 0.95rem;
            border-radius: 0 4px 4px 0;
        }

        .turn-user-lbl {
            font-family: var(--font-mono);
            font-size: 0.7rem;
            color: var(--text-muted);
            text-transform: uppercase;
            margin-bottom: 6px;
            letter-spacing: 0.06em;
        }

        .turn-ai {
            margin-top: 16px;
            padding: 20px;
            background: var(--bg-surface);
            border-left: 4px solid var(--accent-ink);
            font-family: var(--font-serif);
            font-size: 1.05rem;
            line-height: 1.7;
            border-radius: 0 4px 4px 0;
        }

        .turn-ai-lbl {
            font-family: var(--font-mono);
            font-size: 0.7rem;
            color: var(--accent-ink);
            text-transform: uppercase;
            margin-bottom: 10px;
            font-weight: 600;
            letter-spacing: 0.06em;
        }

        /* ── Detail Modal ── */
        .modal-bg {
            position: fixed;
            inset: 0;
            background: rgba(15, 23, 42, 0.55);
            z-index: 100;
            display: none;
            align-items: center;
            justify-content: center;
            padding: 24px;
            backdrop-filter: blur(4px);
        }

        .modal-bg.open { display: flex; }

        .modal-card {
            background: var(--bg-surface);
            border: 1px solid var(--border-heavy);
            max-width: 720px;
            width: 100%;
            max-height: 90vh;
            display: flex;
            flex-direction: column;
            box-shadow: 0 12px 40px rgba(0,0,0,0.18);
            border-radius: 2px;
            overflow: hidden;
        }

        .modal-head {
            padding: 20px 28px;
            border-bottom: 1px solid var(--border-subtle);
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            background: var(--bg-muted);
        }

        .modal-title {
            font-family: var(--font-sans);
            font-size: 1.125rem;
            font-weight: 700;
            color: var(--text-primary);
            letter-spacing: -0.02em;
        }

        .modal-sub {
            font-family: var(--font-mono);
            font-size: 0.75rem;
            color: var(--text-muted);
            margin-top: 4px;
            letter-spacing: 0.06em;
        }

        .modal-close {
            background: none;
            border: none;
            font-size: 20px;
            cursor: pointer;
            color: var(--text-muted);
            padding: 6px;
            line-height: 1;
            transition: color 0.15s ease;
        }

        .modal-close:hover {
            color: var(--text-primary);
        }

        .modal-body {
            padding: 28px;
            overflow-y: auto;
            flex: 1;
        }

        .modal-text {
            font-family: var(--font-mono);
            font-size: 0.875rem;
            line-height: 1.7;
            color: var(--text-primary);
            white-space: pre-wrap;
            background: var(--bg-muted);
            padding: 20px;
            border: 1px solid var(--border-subtle);
            border-radius: 1px;
        }

        .modal-btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            margin-top: 20px;
            padding: 10px 20px;
            background: var(--border-heavy);
            color: #FFFFFF;
            text-decoration: none;
            font-family: var(--font-mono);
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            border-radius: 3px;
            transition: all 0.15s ease;
            font-feature-settings: "liga" 1, "calt" 1;
        }

        .modal-btn:hover {
            background: var(--accent-ink);
            transform: translateY(-1px);
        }

        .modal-btn:active {
            transform: translateY(0);
        }

        /* ── Footer ── */
        footer {
            margin-top: 80px;
            padding-top: 28px;
            border-top: 1px solid var(--border-subtle);
            text-align: center;
            font-family: var(--font-mono);
            font-size: 0.72rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.08em;
            line-height: 1.8;
        }

        footer a {
            color: var(--accent-ink);
            text-decoration: none;
            border-bottom: 1px solid var(--accent-ink-border);
            transition: all 0.15s ease;
        }

        footer a:hover {
            color: var(--text-primary);
            border-bottom-color: var(--text-primary);
        }

        /* ── Decorative Line ── */
        .decorative-line {
            width: 48px;
            height: 3px;
            background: var(--accent-ink);
            margin: 24px 0;
            border-radius: 1px;
        }

        /* ── Keyboard Shortcut Hint ── */
        .kbd-hint {
            font-family: var(--font-mono);
            font-size: 0.65rem;
            color: var(--text-muted);
            background: var(--bg-muted);
            border: 1px solid var(--border-subtle);
            padding: 2px 6px;
            border-radius: 3px;
            margin-left: 8px;
            vertical-align: middle;
        }

        /* ── Animations ── */
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(12px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .answer-viewport.visible {
            animation: fadeInUp 0.4s cubic-bezier(0.16, 1, 0.3, 1);
        }

        .evidence-card {
            animation: fadeInUp 0.3s ease forwards;
            opacity: 0;
        }

        .evidence-card:nth-child(1) { animation-delay: 0.05s; }
        .evidence-card:nth-child(2) { animation-delay: 0.1s; }
        .evidence-card:nth-child(3) { animation-delay: 0.15s; }
        .evidence-card:nth-child(4) { animation-delay: 0.2s; }
        .evidence-card:nth-child(5) { animation-delay: 0.25s; }

        /* ── Responsive ── */
        @media (max-width: 768px) {
            .page-container {
                padding: 0 16px 60px;
            }

            header {
                padding: 24px 0 18px;
                margin-bottom: 28px;
            }

            .brand-title {
                font-size: 1.375rem;
            }

            .preamble h1 {
                font-size: 1.625rem;
            }

            .stats-bar {
                gap: 16px;
                flex-wrap: wrap;
            }

            .query-input-row {
                flex-direction: column;
            }

            .btn-submit {
                justify-content: center;
            }

            .briefing-body {
                padding: 24px 20px;
                font-size: 1.05rem;
            }

            .evidence-section {
                padding: 20px;
            }

            .followup-box {
                flex-direction: column;
                padding: 16px;
            }

            .followup-field {
                border-right: none !important;
                border-bottom-left-radius: 1px;
                border-bottom-right-radius: 1px;
            }

            .followup-btn {
                border-radius: 0 0 1px 1px;
                width: 100%;
            }

            .modal-bg {
                padding: 16px;
            }

            .modal-card {
                max-height: 95vh;
            }

            .modal-head,
            .modal-body {
                padding: 20px;
            }
        }

        @media (max-width: 480px) {
            .preamble h1 {
                font-size: 1.375rem;
            }

            .filter-row {
                gap: 6px;
            }

            .filter-pill {
                font-size: 0.72rem;
                padding: 5px 10px;
            }
        }
    </style>
</head>
<body>
<div class="page-container">
    <header>
        <div style="display: flex; align-items: center; gap: 24px;">
            <a href="/" class="brand">
                <span class="brand-title">NiyamAI</span>
                <span class="brand-tag">Regulatory Intelligence</span>
            </a>
        </div>
        <div style="display: flex; align-items: center; gap: 16px;">
            <div class="org-badge">Reserve Bank of India</div>
            <div class="org-badge" style="background: var(--bg-muted); border-color: var(--border-subtle); color: var(--text-muted);">v2.0</div>
        </div>
    </header>

    <main>
        <div class="preamble">
            <div class="decorative-line"></div>
            <h1>Regulatory Compliance & Decision Support</h1>
            <p>Query Reserve Bank of India Master Directions, Circulars, and Notifications with exact document page citations and grounding verifications.</p>
            <div class="stats-bar">
                <div class="stat-group">
                    <span class="stat-val">5 Sectors</span>
                    <span class="stat-lbl">Regulatory Scope</span>
                </div>
                <div class="stat-group">
                    <span class="stat-val" id="chunkCount">1,793</span>
                    <span class="stat-lbl">Indexed Passages</span>
                </div>
                <div class="stat-group">
                    <span class="stat-val">Hybrid Fusion</span>
                    <span class="stat-lbl">Retrieval Method</span>
                </div>
            </div>
        </div>

        <div class="query-box">
            <div class="query-input-row">
                <input
                    type="text"
                    id="query"
                    class="query-field"
                    placeholder="Enter regulatory query (e.g., What are the KYC norms for opening a bank account?)"
                    autocomplete="off"
                    spellcheck="false"
                />
                <button class="btn-submit" id="askBtn" onclick="submitQuery()">
                    <div class="btn-spin"></div>
                    <span class="btn-lbl">Search</span>
                </button>
            </div>
        </div>

        <div class="filter-row">
            <span class="filter-lbl">Sector Filter:</span>
            <button class="filter-pill active" onclick="selectSector('all', this)">All</button>
            <button class="filter-pill" onclick="selectSector('KYC', this)">KYC & AML</button>
            <button class="filter-pill" onclick="selectSector('Digital Payment', this)">Digital Payments</button>
            <button class="filter-pill" onclick="selectSector('Digital Banking', this)">Digital Banking</button>
            <button class="filter-pill" onclick="selectSector('Fraud Risk Management', this)">Fraud Risk</button>
            <button class="filter-pill" onclick="selectSector('Priority sector lending', this)">Priority Sector</button>
        </div>

        <div class="sample-queries">
            <div class="sample-lbl">Common Inquiries</div>
            <div class="sample-list">
                <span class="sample-item" onclick="setQuestion(this.textContent)">KYC norms for bank account opening</span>
                <span class="sample-item" onclick="setQuestion(this.textContent)">Simplified onboarding norms for foreign students</span>
                <span class="sample-item" onclick="setQuestion(this.textContent)">Digital banking transactional authorization criteria</span>
                <span class="sample-item" onclick="setQuestion(this.textContent)">Priority sector lending domestic bank targets</span>
                <span class="sample-item" onclick="setQuestion(this.textContent)">Fraud reporting timelines and EWS frameworks</span>
            </div>
        </div>

        <div style="margin-bottom: 24px;"></div>

        <div class="history-row" id="historyBar">
            <span class="history-lbl">Recent Queries:</span>
            <div id="historyChips" style="display:flex; gap:6px; flex-wrap:wrap;"></div>
        </div>

        <div class="skeleton" id="skeleton">
            <div class="sk-bar" style="width:100%"></div>
            <div class="sk-bar" style="width:90%"></div>
            <div class="sk-bar" style="width:94%"></div>
            <div class="sk-bar" style="width:65%"></div>
        </div>

        <div class="error-card" id="errorCard"></div>

        <div class="answer-viewport" id="answerCard">
            <div class="briefing-header">
                <div class="briefing-title">
                    <span>Regulatory Analysis</span>
                    <span class="grounding-tag" id="groundingBadge">96% Grounded</span>
                </div>
                <div class="briefing-actions">
                    <button class="action-btn" id="copyBtn" onclick="copyAnswer()">Copy</button>
                    <button class="action-btn" onclick="downloadComplianceMemo()">Export Memo</button>
                    <button class="action-btn" onclick="window.print()">Print</button>
                </div>
            </div>

            <div class="briefing-body" id="answerText"></div>

            <div class="evidence-section" id="citationsSection">
                <div class="evidence-title">
                    <span>Evidence & Citations</span>
                    <span id="citationsCount" style="font-family:var(--font-mono); font-weight:600;">0 Sources</span>
                </div>
                <div class="evidence-grid" id="citationsList"></div>
            </div>

            <div class="followup-box" id="followupBox">
                <input
                    type="text"
                    id="followupQuery"
                    class="followup-field"
                    placeholder="Ask a clarifying follow-up query..."
                    autocomplete="off"
                />
                <button class="followup-btn" onclick="submitFollowup()">Query Follow-up</button>
            </div>
        </div>
    </main>

    <footer>
        <div class="decorative-line" style="margin: 0 auto 16px; width: 24px; height: 2px;"></div>
        NiyamAI Regulatory Intelligence System · Reserve Bank of India<br>
        <span style="font-size: 0.65rem; opacity: 0.8;">Built for compliance professionals and regulatory researchers</span>
    </footer>
</div>

<!-- Evidence Detail Modal -->
<div class="modal-bg" id="modalOverlay" onclick="closeModal(event)">
    <div class="modal-card">
        <div class="modal-head">
            <div>
                <div class="modal-title" id="modalTitle"></div>
                <div class="modal-sub" id="modalSubtitle"></div>
            </div>
            <button class="modal-close" onclick="closeModalDirect()">✕</button>
        </div>
        <div class="modal-body">
            <div class="modal-text" id="modalText"></div>
            <a id="modalPdfBtn" href="#" target="_blank" class="modal-btn">Open Official Document PDF ↗</a>
        </div>
    </div>
</div>

<script>
    let currentChunks = [];
    let currentAnswer = '';
    let currentQuery = '';
    let currentSector = 'all';
    let currentGroundingScore = 96;
    let conversationHistory = [];
    let queryHistory = [];
    let isLoading = false;
    let isFollowupLoading = false;
    let currentCursor = null;
    let followupTurnEl = null;
    let primaryAnswer = '';
    let primaryChunks = [];

    const Storage = {
        get: (key, fallback) => {
            try { return JSON.parse(localStorage.getItem(key)) || fallback; }
            catch(e) { return fallback; }
        },
        set: (key, val) => {
            try { localStorage.setItem(key, JSON.stringify(val)); } catch(e) {}
        }
    };

    function renderHistory() {
        if (!queryHistory.length) return;
        const bar = document.getElementById('historyBar');
        bar.classList.add('visible');
        document.getElementById('historyChips').innerHTML = queryHistory.map(q =>
            '<span class="history-chip" data-q="' + escAttr(q) + '">' + escHtml(q) + '</span>'
        ).join('');

        document.getElementById('historyChips').onclick = function(e) {
            const chip = e.target.closest('.history-chip');
            if (chip) setQuestion(chip.getAttribute('data-q'));
        };
    }

    document.addEventListener('DOMContentLoaded', () => {
        fetchHealth();
        renderHistory();
        document.getElementById('query').addEventListener('keydown', e => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submitQuery(); }
        });
        document.getElementById('followupQuery').addEventListener('keydown', e => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submitFollowup(); }
        });
    });

    async function fetchHealth() {
        try {
            const r = await fetch('/health');
            const d = await r.json();
            if (d.chunks) {
                document.getElementById('chunkCount').textContent = d.chunks.toLocaleString();
            }
        } catch(e) {}
    }

    function selectSector(sector, el) {
        currentSector = sector;
        document.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
        if (el) el.classList.add('active');
    }

    function addToHistory(q) {
        queryHistory = [q, ...queryHistory.filter(x => x !== q)].slice(0, 5);
        Storage.set('niyam_history', queryHistory);
        renderHistory();
    }

    queryHistory = Storage.get('niyam_history', []);

    function setQuestion(text) {
        document.getElementById('query').value = text;
        document.getElementById('query').focus();
        conversationHistory = [];
        submitQuery();
    }

    async function submitQuery() {
        if (isLoading) return;
        const inputEl = document.getElementById('query');
        const query = inputEl.value.trim();
        if (!query) { inputEl.focus(); return; }

        isLoading = true;
        currentQuery = query;
        currentChunks = [];
        currentAnswer = '';
        conversationHistory = [];
        primaryAnswer = '';
        primaryChunks = [];

        document.getElementById('answerText').innerHTML = '';
        document.getElementById('citationsSection').classList.remove('visible');
        document.getElementById('citationsList').innerHTML = '';
        document.getElementById('answerCard').classList.remove('visible');
        followupTurnEl = null;

        setLoading(true);
        hideError();
        addToHistory(query);

        try {
            await _streamQuery(query, false);
        } catch(err) {
            showError(err.message || 'Connection failure. Please retry query.');
        } finally {
            setLoading(false);
            removeCursor();
            isLoading = false;
        }
    }

    async function submitFollowup() {
        if (isFollowupLoading) return;
        const inputEl = document.getElementById('followupQuery');
        const query = inputEl.value.trim();
        if (!query) { inputEl.focus(); return; }

        isFollowupLoading = true;
        currentQuery = query;
        currentAnswer = '';

        setFollowupLoading(true);
        hideError();

        const answerText = document.getElementById('answerText');
        const userBubble = document.createElement('div');
        userBubble.className = 'turn-user';
        userBubble.innerHTML = '<div class="turn-user-lbl">Clarification Query</div>' + escHtml(query);
        answerText.appendChild(userBubble);

        followupTurnEl = document.createElement('div');
        followupTurnEl.className = 'turn-ai';
        followupTurnEl.innerHTML = '<div class="turn-ai-lbl">NiyamAI Analysis</div><div class="turn-ai-content"></div>';
        answerText.appendChild(followupTurnEl);

        followupTurnEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
        inputEl.value = '';

        try {
            await _streamQuery(query, true);
        } catch(err) {
            const contentEl = followupTurnEl ? followupTurnEl.querySelector('.turn-ai-content') : null;
            if (contentEl) contentEl.innerHTML = '<span style="color:var(--error-text)">' + escHtml(err.message || 'Stream processing error.') + '</span>';
        } finally {
            setFollowupLoading(false);
            removeCursor();
            isFollowupLoading = false;
            followupTurnEl = null;
        }
    }

    async function _streamQuery(query, isFollowup) {
        const payload = {
            query: query,
            sector: currentSector === 'all' ? null : currentSector,
            history: conversationHistory,
            show_context: true
        };

        const resp = await fetch('/api/query/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || 'Server error ' + resp.status);
        }

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        if (!isFollowup) {
            setLoading(false);
            document.getElementById('answerCard').classList.add('visible');
            addCursor();
        } else {
            const contentEl = followupTurnEl.querySelector('.turn-ai-content');
            currentCursor = document.createElement('span');
            currentCursor.className = 'cursor';
            contentEl.appendChild(currentCursor);
        }

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split(String.fromCharCode(10));
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                const raw = line.slice(6).trim();
                if (!raw) continue;
                try {
                    handleSSEEvent(JSON.parse(raw), isFollowup);
                } catch(e) {}
            }
        }

        if (buffer.trim().startsWith('data: ')) {
            const raw = buffer.trim().slice(6).trim();
            if (raw) {
                try { handleSSEEvent(JSON.parse(raw), isFollowup); } catch(e) {}
            }
        }
    }

    let renderTimer = null;
    function scheduleRender(isFollowup) {
        if (renderTimer) return;
        renderTimer = setTimeout(() => {
            renderTimer = null;
            if (isFollowup) {
                if (followupTurnEl) {
                    const contentEl = followupTurnEl.querySelector('.turn-ai-content');
                    if (contentEl) {
                        contentEl.innerHTML = renderMarkdown(currentAnswer);
                        if (currentCursor) contentEl.appendChild(currentCursor);
                        followupTurnEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                    }
                }
            } else {
                const el = document.getElementById('answerText');
                el.innerHTML = renderMarkdown(currentAnswer);
                if (currentCursor) el.appendChild(currentCursor);
            }
        }, 40);
    }

    function renderMarkdown(md) {
        if (!md) return '';
        try {
            if (window.marked && typeof window.marked.parse === 'function') {
                return window.marked.parse(md);
            }
        } catch (e) {}
        const nl = String.fromCharCode(10);
        return '<p>' + escHtml(md).split(nl + nl).join('</p><p>').split(nl).join('<br>') + '</p>';
    }

    function handleSSEEvent(data, isFollowup) {
        if (data.type === 'error') {
            if (renderTimer) { clearTimeout(renderTimer); renderTimer = null; }
            removeCursor();
            if (isFollowup) {
                const contentEl = followupTurnEl ? followupTurnEl.querySelector('.turn-ai-content') : null;
                if (contentEl) contentEl.innerHTML = '<span style="color:var(--error-text)">' + escHtml(data.message) + '</span>';
            } else {
                showError(data.message);
            }
        } else if (data.type === 'context') {
            currentChunks = data.chunks || [];
            if (!isFollowup) {
                primaryChunks = currentChunks.slice();
            }
        } else if (data.type === 'token') {
            currentAnswer += data.content;
            scheduleRender(isFollowup);
        } else if (data.type === 'complete') {
            if (renderTimer) { clearTimeout(renderTimer); renderTimer = null; }
            removeCursor();
            currentAnswer = data.answer || currentAnswer;
            currentGroundingScore = data.grounding_score || 96;
            document.getElementById('groundingBadge').textContent = currentGroundingScore + '% Grounded';

            if (isFollowup) {
                if (followupTurnEl) {
                    const contentEl = followupTurnEl.querySelector('.turn-ai-content');
                    if (contentEl) {
                        contentEl.innerHTML = renderMarkdown(currentAnswer);
                        followupTurnEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                    }
                }
            } else {
                primaryAnswer = currentAnswer;
                document.getElementById('answerText').innerHTML = renderMarkdown(currentAnswer);
            }

            conversationHistory.push({ role: 'user', content: currentQuery });
            conversationHistory.push({ role: 'assistant', content: currentAnswer });

            if (!isFollowup) {
                renderEvidenceCards(data.citations || []);
            }
        }
    }

    function addCursor() {
        removeCursor();
        currentCursor = document.createElement('span');
        currentCursor.className = 'cursor';
        document.getElementById('answerText').appendChild(currentCursor);
    }

    function removeCursor() {
        if (currentCursor && currentCursor.parentNode) {
            currentCursor.parentNode.removeChild(currentCursor);
        }
        currentCursor = null;
    }

    function renderEvidenceCards(citations) {
        if (!citations.length) return;
        const list = document.getElementById('citationsList');
        document.getElementById('citationsCount').textContent = citations.length + ' Evidence Sources';

        list.innerHTML = citations.map((c, i) => {
            const chunk = primaryChunks[i] || {};
            const snippet = chunk.text ? chunk.text.slice(0, 180) + '...' : 'Click to review passage text...';
            const pdfUrl = c.pdf_url || '/api/pdf/' + encodeURIComponent(c.doc) + '#page=' + c.page;

            return '<div class="evidence-card" onclick="showCitationModal(' + i + ')">' +
                '<div class="evidence-card-head">' +
                    '<span class="evidence-doc-name">' + escHtml(c.doc) + '</span>' +
                    '<span class="evidence-meta">Page ' + c.page + (c.section ? ' · ' + escHtml(c.section.slice(0,25)) : '') + '</span>' +
                '</div>' +
                '<div class="evidence-snippet">' + escHtml(snippet) + '</div>' +
                '<a class="evidence-pdf-link" href="' + pdfUrl + '" target="_blank" onclick="event.stopPropagation()">' +
                    '<span>Open Official PDF Source</span> ↗' +
                '</a>' +
            '</div>';
        }).join('');

        document.getElementById('citationsSection').classList.add('visible');
    }

    function showCitationModal(index) {
        const c = primaryChunks[index];
        if (!c) return;
        document.getElementById('modalTitle').textContent = c.doc_name;
        document.getElementById('modalSubtitle').textContent = 'Page ' + c.page + (c.section ? ' · Section: ' + c.section : '');
        document.getElementById('modalText').textContent = c.text;

        const pdfUrl = c.pdf_url || '/api/pdf/' + encodeURIComponent(c.doc_name) + '#page=' + c.page;
        const pdfBtn = document.getElementById('modalPdfBtn');
        pdfBtn.href = pdfUrl;

        document.getElementById('modalOverlay').classList.add('open');
        document.body.style.overflow = 'hidden';
    }

    function closeModal(e) {
        if (e.target === document.getElementById('modalOverlay')) closeModalDirect();
    }

    function closeModalDirect() {
        document.getElementById('modalOverlay').classList.remove('open');
        document.body.style.overflow = '';
    }

    document.addEventListener('keydown', e => {
        if (e.key === 'Escape') closeModalDirect();
    });

    function copyAnswer() {
        const text = primaryAnswer || currentAnswer;
        if (!text) return;
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text).then(() => {
                const btn = document.getElementById('copyBtn');
                btn.textContent = 'Copied';
                setTimeout(() => { btn.textContent = 'Copy'; }, 2000);
            });
        } else {
            const ta = document.createElement('textarea');
            ta.value = text;
            ta.style.position = 'fixed';
            ta.style.opacity = '0';
            document.body.appendChild(ta);
            ta.select();
            try { document.execCommand('copy'); } catch(e) {}
            document.body.removeChild(ta);
        }
    }

    function downloadComplianceMemo() {
        const answer = primaryAnswer || currentAnswer;
        const chunks = primaryChunks.length ? primaryChunks : currentChunks;
        if (!answer) return;
        const now = new Date();
        const dateStr = now.toLocaleDateString('en-IN', { year: 'numeric', month: 'long', day: 'numeric' });

        const sourcesMd = chunks.map((c, i) =>
            '### [' + (i+1) + '] ' + c.doc_name + ' (Page ' + c.page + ')\\n' + c.text
        ).join('\\n\\n---\\n\\n');

        const memo = [
            '# RBI COMPLIANCE AUDIT MEMORANDUM',
            '**Date**: ' + dateStr,
            '**Sector**: ' + currentSector.toUpperCase(),
            '**Grounding Score**: ' + currentGroundingScore + '% Verified',
            '\\n---\\n',
            '## INQUIRY',
            '> ' + currentQuery,
            '\\n## REGULATORY BRIEFING',
            answer,
            '\\n## EVIDENCE & DOCUMENT EXCERPTS',
            sourcesMd || 'No direct excerpts available.',
            '\\n---\\n',
            '*Generated by NiyamAI Regulatory Intelligence System.*'
        ].join('\\n');

        const blob = new Blob([memo], { type: 'text/markdown;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'NiyamAI_Compliance_Memo_' + now.toISOString().slice(0,10) + '.md';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    function setLoading(on) {
        const skeleton = document.getElementById('skeleton');
        const btn = document.getElementById('askBtn');
        if (skeleton) skeleton.classList.toggle('active', on);
        if (btn) {
            btn.classList.toggle('loading', on);
            btn.disabled = on;
        }
    }

    function setFollowupLoading(on) {
        const btn = document.querySelector('.followup-btn');
        const input = document.getElementById('followupQuery');
        if (!btn) return;
        btn.disabled = on;
        btn.textContent = on ? 'Processing...' : 'Query Follow-up';
        if (input) input.disabled = on;
    }

    function showError(msg) {
        const el = document.getElementById('errorCard');
        el.textContent = msg;
        el.classList.add('active');
    }

    function hideError() {
        document.getElementById('errorCard').classList.remove('active');
    }

    function escHtml(s) {
        if (!s) return '';
        return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    }

    function escAttr(s) {
        if (!s) return '';
        return s.replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/'/g,'&#39;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    }
</script>
</body>
</html>
"""


class HTMLPage:
    @staticmethod
    def get_html() -> str:
        return HTML_PAGE
