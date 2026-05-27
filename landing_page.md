# ESP32-S3 Neural Vision — Landing Page Specification

> **Single Source of Truth for Svelte + Tailwind + GitHub Pages**
> 
> Edge AI Camera with Wake Word Detection & Face Recognition. Entirely on-device. No cloud. No Linux. Just a $15 microcontroller.

---

## 0. Philosophy & Vibe

**Vibe:** Cyberpunk lab equipment meets consumer electronics. Dark mode. Neon accents (purple/cyan on dark backgrounds). Think: a product that belongs in a Blade Runner lab but costs less than lunch.

**Core feeling:** "This shouldn't be possible on a $15 microcontroller."

**Tone:** Confident, technical-but-accessible, slightly rebellious. No corporate speak. No buzzword salad. Engineers should read this and nod. Makers should read this and want to build it.

**Anti-patterns (NO AI SLOP):**
- NO generic gradient blobs
- NO floating 3D spheres
- NO "Trusted by 10,000+ companies" fake social proof
- NO stock photo of people in a meeting
- NO generic SaaS template layout
- NO "revolutionize your workflow"
- NO particle effects that serve no purpose
- NO generic "AI-powered" hero image

---

## 1. Color System

### Primary Palette

| Token | Hex | Usage |
|-------|-----|-------|
| `--bg-primary` | `#0a0a0f` | Main page background |
| `--bg-secondary` | `#12121a` | Cards, sections, elevated surfaces |
| `--bg-tertiary` | `#1a1a24` | Hover states, subtle elevation |
| `--bg-code` | `#0d0d14` | Code blocks, terminal windows |
| `--accent-primary` | `#7c8aff` | Primary accent — links, buttons, highlights, glow effects |
| `--accent-secondary` | `#00e5ff` | Secondary accent — data flow animations, status indicators, secondary CTAs |
| `--accent-tertiary` | `#ff6b6b` | Error states, attention grabbers, "No Cloud" badge |
| `--text-primary` | `#e8e8f0` | Headlines, primary text |
| `--text-secondary` | `#9ca3af` | Body text, descriptions |
| `--text-muted` | `#6b7280` | Captions, labels, timestamps |
| `--text-code` | `#a5b4fc` | Inline code, technical specs |
| `--border-subtle` | `rgba(124, 138, 255, 0.1)` | Card borders, dividers |
| `--border-glow` | `rgba(124, 138, 255, 0.3)` | Hover borders, active states |
| `--success` | `#4ade80` | Online status, checkmarks |
| `--warning` | `#fbbf24` | Warnings, attention |

### Gradient Definitions

```css
/* Hero text gradient */
.hero-gradient {
  background: linear-gradient(135deg, #7c8aff 0%, #00e5ff 50%, #7c8aff 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* Card hover glow */
.card-glow {
  box-shadow: 0 0 0 1px rgba(124, 138, 255, 0.1),
              0 4px 24px -4px rgba(124, 138, 255, 0.15);
}

/* Accent button gradient */
.btn-primary {
  background: linear-gradient(135deg, #7c8aff 0%, #6366f1 100%);
}

/* Data flow line gradient */
.flow-line {
  background: linear-gradient(90deg, transparent 0%, #00e5ff 50%, transparent 100%);
}
```

### Dark Mode Only

This is a dark-mode-only page. No light mode toggle. The dark background is part of the brand identity.

---

## 2. Typography

### Font Stack

```css
:root {
  --font-sans: 'Inter', system-ui, -apple-system, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', 'SF Mono', monospace;
  --font-display: 'Inter', system-ui, sans-serif; /* Could swap for Space Grotesk or similar */
}
```

**Font loading:** Use Google Fonts CDN or self-host. Preload `Inter` and `JetBrains Mono`.

### Type Scale

| Token | Size | Weight | Line-height | Letter-spacing | Usage |
|-------|------|--------|-------------|----------------|-------|
| `display-1` | clamp(3rem, 8vw, 6rem) | 800 | 1.0 | -0.03em | Hero headline |
| `display-2` | clamp(2rem, 5vw, 3.5rem) | 700 | 1.1 | -0.02em | Section headlines |
| `heading-1` | 2rem | 600 | 1.2 | -0.01em | Card titles, sub-sections |
| `heading-2` | 1.5rem | 600 | 1.3 | 0 | Feature titles |
| `body-large` | 1.125rem | 400 | 1.7 | 0 | Lead paragraphs |
| `body` | 1rem | 400 | 1.6 | 0 | Body text |
| `body-small` | 0.875rem | 400 | 1.5 | 0 | Secondary text |
| `caption` | 0.75rem | 500 | 1.4 | 0.05em | Labels, uppercase captions |
| `mono` | 0.875rem | 400 | 1.5 | 0 | Code, specs, technical data |

### Typography Rules

- **Headlines:** Use `font-weight: 800` for hero, `700` for sections. Tight letter-spacing.
- **Body:** `font-weight: 400`, comfortable line-height (1.6–1.7).
- **Code/Specs:** Always `JetBrains Mono`. Color: `--text-code`.
- **Numbers in specs:** Tabular figures (`font-variant-numeric: tabular-nums`).
- **Uppercase captions:** `letter-spacing: 0.05em`, `font-weight: 500`, `font-size: 0.75rem`, color `--text-muted`.

---

## 3. Spacing System

### Base Unit: 4px

| Token | Value | Usage |
|-------|-------|-------|
| `space-1` | 4px | Tight gaps |
| `space-2` | 8px | Icon gaps, small padding |
| `space-3` | 12px | Component internal spacing |
| `space-4` | 16px | Standard gap |
| `space-6` | 24px | Card padding |
| `space-8` | 32px | Section internal spacing |
| `space-12` | 48px | Between related elements |
| `space-16` | 64px | Between sections |
| `space-24` | 96px | Major section breaks |
| `space-32` | 128px | Hero spacing |

### Container

```css
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}

/* On large screens */
@media (min-width: 1280px) {
  .container {
    padding: 0 48px;
  }
}
```

---

## 4. Component Design System

### 4.1 Buttons

**Primary Button (CTA)**
```css
.btn-primary {
  background: linear-gradient(135deg, #7c8aff 0%, #6366f1 100%);
  color: #0a0a0f;
  font-weight: 600;
  padding: 14px 32px;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  overflow: hidden;
}
.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 32px -8px rgba(124, 138, 255, 0.4);
}
.btn-primary:active {
  transform: translateY(0);
}
```

**Secondary Button (Ghost)**
```css
.btn-secondary {
  background: transparent;
  color: #7c8aff;
  font-weight: 500;
  padding: 14px 32px;
  border-radius: 8px;
  border: 1px solid rgba(124, 138, 255, 0.3);
  cursor: pointer;
  transition: all 0.2s ease;
}
.btn-secondary:hover {
  background: rgba(124, 138, 255, 0.1);
  border-color: rgba(124, 138, 255, 0.5);
}
```

**Icon Button**
```css
.btn-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: rgba(124, 138, 255, 0.1);
  border: 1px solid rgba(124, 138, 255, 0.2);
  color: #7c8aff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
}
.btn-icon:hover {
  background: rgba(124, 138, 255, 0.2);
}
```

### 4.2 Cards

**Feature Card**
```css
.card {
  background: #12121a;
  border: 1px solid rgba(124, 138, 255, 0.1);
  border-radius: 12px;
  padding: 32px;
  transition: all 0.3s ease;
}
.card:hover {
  border-color: rgba(124, 138, 255, 0.3);
  box-shadow: 0 4px 24px -4px rgba(124, 138, 255, 0.1);
  transform: translateY(-2px);
}
```

**Spec Card (Technical)**
```css
.spec-card {
  background: #0d0d14;
  border: 1px solid rgba(124, 138, 255, 0.08);
  border-radius: 8px;
  padding: 20px 24px;
  font-family: 'JetBrains Mono', monospace;
}
.spec-card .label {
  color: #6b7280;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.spec-card .value {
  color: #e8e8f0;
  font-size: 1.25rem;
  font-weight: 600;
  margin-top: 4px;
}
```

**Comparison Card**
```css
.comparison-card {
  background: #12121a;
  border: 1px solid rgba(124, 138, 255, 0.1);
  border-radius: 12px;
  padding: 24px;
}
.comparison-card.highlight {
  border-color: rgba(124, 138, 255, 0.4);
  background: linear-gradient(180deg, #12121a 0%, rgba(124, 138, 255, 0.05) 100%);
}
```

### 4.3 Badges

```css
.badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 500;
}
.badge-accent {
  background: rgba(124, 138, 255, 0.15);
  color: #7c8aff;
  border: 1px solid rgba(124, 138, 255, 0.2);
}
.badge-success {
  background: rgba(74, 222, 128, 0.15);
  color: #4ade80;
  border: 1px solid rgba(74, 222, 128, 0.2);
}
.badge-error {
  background: rgba(255, 107, 107, 0.15);
  color: #ff6b6b;
  border: 1px solid rgba(255, 107, 107, 0.2);
}
```

### 4.4 Code Blocks / Terminal Windows

```css
.terminal {
  background: #0d0d14;
  border: 1px solid rgba(124, 138, 255, 0.15);
  border-radius: 12px;
  overflow: hidden;
}
.terminal-header {
  background: rgba(124, 138, 255, 0.05);
  padding: 12px 16px;
  border-bottom: 1px solid rgba(124, 138, 255, 0.1);
  display: flex;
  align-items: center;
  gap: 8px;
}
.terminal-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}
.terminal-dot.red { background: #ff6b6b; }
.terminal-dot.yellow { background: #fbbf24; }
.terminal-dot.green { background: #4ade80; }
.terminal-body {
  padding: 20px 24px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.875rem;
  line-height: 1.6;
  color: #a5b4fc;
}
.terminal-body .prompt { color: #4ade80; }
.terminal-body .command { color: #e8e8f0; }
.terminal-body .output { color: #9ca3af; }
```

### 4.5 Status Indicators

```css
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}
.status-online { background: #4ade80; box-shadow: 0 0 8px rgba(74, 222, 128, 0.5); }
.status-offline { background: #ff6b6b; }
.status-idle { background: #fbbf24; }
```

---

## 5. Animation & Motion System

### Philosophy

Animations should feel **functional and precise** — like firmware executing, not like a marketing page. Every animation serves a purpose: guiding attention, showing state change, or revealing information.

**Timing:** Snappy. 200–400ms for micro-interactions. 600–800ms for reveals.
**Easing:** `cubic-bezier(0.4, 0, 0.2, 1)` for most things. `cubic-bezier(0.16, 1, 0.3, 1)` for dramatic entrances.

### 5.1 Scroll-Triggered Reveals

```css
.reveal {
  opacity: 0;
  transform: translateY(30px);
  transition: opacity 0.6s cubic-bezier(0.16, 1, 0.3, 1),
              transform 0.6s cubic-bezier(0.16, 1, 0.3, 1);
}
.reveal.visible {
  opacity: 1;
  transform: translateY(0);
}
.reveal-delay-1 { transition-delay: 0.1s; }
.reveal-delay-2 { transition-delay: 0.2s; }
.reveal-delay-3 { transition-delay: 0.3s; }
```

Use Intersection Observer with `threshold: 0.1` to trigger. Stagger children with 0.1s delay increments.

### 5.2 Hero Entrance Sequence

Order of appearance (staggered, 150ms apart):
1. Background grid fades in (opacity 0 → 0.3)
2. Badge "Edge AI Camera" fades in + slides up
3. Headline words appear (clip-path reveal or opacity)
4. Subheadline fades in
5. CTA buttons fade in + slide up
6. Hero visual (board image / diagram) fades in

```css
@keyframes hero-entrance {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
```

### 5.3 Data Flow Animation (The Signature Animation)

This is the **hero animation** — a visual representation of data flowing through the system.

**Concept:** Animated SVG lines showing:
- Sound wave → Microphone → Ring Buffer → ML Model
- Camera → JPEG Buffer → MJPEG Stream → Browser
- Face Detection pipeline as a branching path

**Implementation:**
```css
.flow-path {
  stroke: #00e5ff;
  stroke-width: 2;
  fill: none;
  stroke-dasharray: 1000;
  stroke-dashoffset: 1000;
  animation: flow-draw 3s ease-in-out infinite;
}
@keyframes flow-draw {
  to { stroke-dashoffset: 0; }
}

.flow-particle {
  fill: #00e5ff;
  filter: drop-shadow(0 0 4px #00e5ff);
  animation: flow-move 3s ease-in-out infinite;
}
```

**Layout:** Positioned behind or beside the hero text. Semi-transparent. Should feel like a circuit diagram come to life.

### 5.4 LED Pattern Animation

Show the 5 LED states as a small animated sequence:
1. Breathing pulse (opacity oscillates)
2. Slow blink (1s interval)
3. Fast blink (300ms interval)
4. Solid on
5. Error blink (rapid red)

```css
@keyframes led-breathe {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 1; }
}
@keyframes led-blink-slow {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.2; }
}
@keyframes led-blink-fast {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.2; }
}
```

Use this in the "How It Works" section to visualize device states.

### 5.5 Memory Budget Visualization

Animated bar chart showing PSRAM allocation:
- Total: 8MB
- Used: ~1.3MB (animated fill)
- Free: ~6.7MB

```css
.memory-bar {
  height: 32px;
  background: #1a1a24;
  border-radius: 6px;
  overflow: hidden;
}
.memory-fill {
  height: 100%;
  background: linear-gradient(90deg, #7c8aff 0%, #00e5ff 100%);
  border-radius: 6px;
  transition: width 1.5s cubic-bezier(0.16, 1, 0.3, 1);
}
```

Trigger width animation on scroll into view. Show tooltip on hover with exact bytes.

### 5.6 State Machine Animation

Interactive or auto-playing diagram showing the 6 states:
- INIT → AP_MODE → CONNECTING → IDLE → ACTIVE → ERROR
- Each state is a node
- Active state glows
- Transitions show as animated arrows
- LED pattern shown inside each node

Use SVG or CSS. Auto-advance every 3 seconds with smooth transitions.

### 5.7 Hover Effects

```css
/* Card lift */
.card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 40px -8px rgba(124, 138, 255, 0.15);
}

/* Link underline animation */
.link-animated {
  position: relative;
}
.link-animated::after {
  content: '';
  position: absolute;
  bottom: -2px;
  left: 0;
  width: 0;
  height: 1px;
  background: #7c8aff;
  transition: width 0.3s ease;
}
.link-animated:hover::after {
  width: 100%;
}

/* Button shine effect */
.btn-primary::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
  transition: left 0.5s ease;
}
.btn-primary:hover::before {
  left: 100%;
}
```

### 5.8 Background Effects

**Subtle Grid Pattern**
```css
.bg-grid {
  background-image: 
    linear-gradient(rgba(124, 138, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(124, 138, 255, 0.03) 1px, transparent 1px);
  background-size: 60px 60px;
}
```

**Noise Texture (Optional)**
```css
.bg-noise {
  position: relative;
}
.bg-noise::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image: url("data:image/svg+xml,..."); /* tiny noise SVG */
  opacity: 0.02;
  pointer-events: none;
}
```

**Gradient Orbs (Very Subtle)**
```css
.orb {
  position: absolute;
  width: 600px;
  height: 600px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(124, 138, 255, 0.08) 0%, transparent 70%);
  filter: blur(80px);
  pointer-events: none;
}
```

Use sparingly — max 2 orbs, positioned behind content, very low opacity.

---

## 6. Page Structure & Sections

### Section Order (Top to Bottom)

1. **Navigation**
2. **Hero**
3. **Social Proof / Stats Bar**
4. **The Problem (Why Existing Solutions Suck)**
5. **The Solution (Product Overview)**
6. **Live Demo / Dashboard Preview**
7. **Technical Architecture**
8. **Memory Budget Visualization**
9. **Performance Targets**
10. **Comparison Table**
11. **Use Cases / Target Audience**
12. **Technical Specs (Detailed)**
13. **Build & Development**
14. **FAQ**
15. **CTA / Get Started**
16. **Footer**

---

## 7. Section-by-Section Specification

### 7.1 Navigation

**Layout:** Fixed top, full-width, `backdrop-filter: blur(12px)`, background `rgba(10, 10, 15, 0.8)`.

**Height:** 64px

**Content:**
- **Left:** Logo + "Neural Vision" text
  - Logo: Stylized eye icon (SVG) with circuit traces
  - Text: "Neural Vision" in `--font-mono`, `font-weight: 600`, `font-size: 1rem`
- **Center:** Nav links (hidden on mobile)
  - Overview | Architecture | Specs | Compare | Docs
  - Smooth scroll to sections
- **Right:** 
  - GitHub icon button (links to repo)
  - "Get Started" button (primary, small)

**Mobile:** Hamburger menu, slide-in drawer from right.

**Scroll behavior:** Add subtle border-bottom `rgba(124, 138, 255, 0.1)` when scrolled > 50px.

---

### 7.2 Hero Section

**Layout:** Full viewport height (100vh), centered content, two-column on desktop (text left, visual right), stacked on mobile.

**Background:** `--bg-primary` + subtle grid pattern + 1–2 gradient orbs (very subtle).

**Left Column (Text):**
- **Badge:** "Edge AI Camera" with pulse dot
  ```
  [●] Edge AI Camera — $15 Microcontroller
  ```
  - Dot: 8px, `--accent-secondary`, pulsing glow animation
  - Text: `--caption` style, `--accent-primary`

- **Headline:** 
  ```
  See. Hear. Recognize.
  All on a $15 chip.
  ```
  - Line 1: `--display-1`, `--text-primary`
  - Line 2: `--display-1`, `hero-gradient` (gradient text)
  - Max-width: 600px

- **Subheadline:**
  ```
  Face detection. Wake word recognition. Live MJPEG streaming. 
  Zero cloud. Zero Linux. Zero subscription.
  Entirely on the ESP32-S3 — a microcontroller smaller than a stick of gum.
  ```
  - `--body-large`, `--text-secondary`
  - Max-width: 520px
  - Margin-top: 24px

- **CTA Row:**
  - Primary: "View the Demo" → scrolls to Live Demo section
  - Secondary: "Read the Docs" → links to GitHub/README
  - Tertiary (text link): "See how it works ↓" → smooth scroll to Architecture
  - Gap: 16px between buttons

- **Trust Micro-bar:**
  ```
  ⚡ <1s boot  ·  🔒 No cloud  ·  🧠 8MB RAM  ·  📡 WiFi + BLE
  ```
  - `--caption` style, `--text-muted`
  - Icons: 16px, inline
  - Margin-top: 40px

**Right Column (Visual):**
- **Primary visual:** The ESP32-S3 Sense board
  - High-quality product photo (see Assets section)
  - Slight float animation (`translateY` oscillation, 4s, ease-in-out)
  - Subtle drop shadow / glow
  - Size: ~400px on desktop

- **Secondary visual (overlay):** Data flow diagram
  - SVG lines showing mic → buffer → ML and camera → stream
  - Animated with `stroke-dashoffset` (see Animation section)
  - Positioned behind/around the board image
  - Opacity: 0.6

- **Tertiary visual:** Small floating cards
  - "15–25 FPS" badge
  - "<50ms Wake Word" badge
  - "128-dim Embedding" badge
  - These float around the board with subtle parallax on mouse move

**Mobile:** Stack vertically. Board image above text. Reduce to 60vh height.

---

### 7.3 Stats Bar (Social Proof)

**Layout:** Full-width, `--bg-secondary`, padding 48px 0.

**Content:** 4-column grid (2x2 on mobile)

| Stat | Value | Label |
|------|-------|-------|
| Price | $15 | BOM Cost |
| Power | ~1W | Peak Draw |
| Boot | <1s | Cold Boot |
| Size | 21×17.5mm | Footprint |

**Design:**
- Value: `--heading-1`, `--text-primary`, `font-variant-numeric: tabular-nums`
- Label: `--caption`, `--text-muted`
- Subtle vertical dividers between columns (1px, `--border-subtle`)
- Each stat fades in with stagger on scroll

---

### 7.4 The Problem Section

**Layout:** `--bg-primary`, padding 96px 0.

**Headline:**
```
Why does AI vision cost $100+ and need a fan?
```
- `--display-2`, centered

**Subheadline:**
```
Existing solutions force you to choose between capability and sanity.
```
- `--body-large`, `--text-secondary`, centered, max-width 600px

**Content:** 3-column grid of "pain point" cards

**Card 1: Raspberry Pi + Camera**
- Icon: Fan icon (or thermometer)
- Title: "The Overkill Stack"
- Body: "$75–$100. 3–6W power draw. Needs active cooling. 20–40 second boot. Full Linux kernel just to detect a face."
- Tag: "Too Much"

**Card 2: ESP32-CAM (Bare)**
- Icon: Camera with X
- Title: "The Dumb Camera"
- Body: "$7–10. No streaming. No audio. No ML. Hardcoded WiFi credentials. Recompile firmware to change networks."
- Tag: "Too Little"

**Card 3: Cloud APIs**
- Icon: Cloud with lock
- Title: "The Privacy Nightmare"
- Body: "Send every frame to the cloud. Latency. Bandwidth costs. Privacy violations. Requires internet. Subscription fees."
- Tag: "Too Risky"

**Card Design:**
- `--bg-secondary` background
- Icon: 40px, `--accent-tertiary` (red-tinted for pain points)
- Title: `--heading-2`
- Body: `--body`, `--text-secondary`
- Tag: `badge-error`
- Border-left: 3px solid `--accent-tertiary`

**Transition:** After cards, a centered statement:
```
There had to be a middle ground.
```
- `--heading-1`, `--accent-primary`, italic
- Fade in after cards

---

### 7.5 The Solution / Product Overview

**Layout:** `--bg-primary`, padding 96px 0.

**Headline:**
```
Meet Neural Vision
```
- `--display-2`

**Subheadline:**
```
A complete vision + voice AI pipeline that fits in 8MB of RAM.
```
- `--body-large`, `--text-secondary`

**Content:** Large feature cards, 2-column grid

**Card 1: On-Device Intelligence**
- Icon: Brain / chip icon
- Title: "Face Detection + Recognition"
- Body: "MTCNN detects faces in 100–150ms. MobileFaceNet generates 128-dimensional embeddings. All inference happens on the ESP32-S3 — no data leaves the device."
- Visual: Small diagram showing face → bounding box → embedding → match

**Card 2: Wake Word Detection**
- Icon: Microphone with sound waves
- Title: "Voice-Activated"
- Body: "22KB TFLite Micro model listens for your wake word. <50ms latency. 3-second audio ring buffer in PSRAM. The device wakes up when you speak."
- Visual: Audio waveform animation

**Card 3: Live Streaming**
- Icon: Video camera
- Title: "MJPEG Dashboard"
- Body: "Stream live video to any browser at 15–25 FPS. Zero-copy JPEG pipeline. Single-page dashboard served directly from firmware — no external dependencies."
- Visual: Browser mockup showing dashboard

**Card 4: Zero-Config Setup**
- Icon: WiFi with sparkles
- Title: "Captive Portal Setup"
- Body: "First boot → connect to 'ESP32-S3-Setup' → pick your WiFi → done. The entire UI is 4KB gzipped, compiled into firmware. No SPIFFS. No SD card corruption."
- Visual: 3-step mini-flow diagram

**Card Design:**
- `--bg-secondary`
- Icon: 48px, `--accent-primary`
- Hover: card lifts, border glows
- Each card has a subtle gradient border on hover

---

### 7.6 Live Demo / Dashboard Preview

**Layout:** `--bg-secondary`, padding 96px 0. Full-width feel.

**Headline:**
```
See it in action
```
- `--display-2`, centered

**Subheadline:**
```
The dashboard runs entirely on the device. No cloud backend. No subscription.
```
- `--body-large`, `--text-secondary`, centered

**Content:** Browser mockup showing the actual dashboard

**Browser Chrome:**
```
┌─────────────────────────────────────────┐
│ ● ● ●  192.168.1.100                    │
├─────────────────────────────────────────┤
│                                         │
│    [DASHBOARD CONTENT]                  │
│                                         │
└─────────────────────────────────────────┘
```
- Rounded corners (12px)
- `--bg-code` background
- Window controls: 3 dots (red, yellow, green)
- URL bar: `--bg-tertiary`, monospace font, showing device IP

**Dashboard Content (inside mockup):**
- **Top bar:** Status dot (green, pulsing), "ONLINE", uptime counter
- **Left sidebar:** 
  - System state: "IDLE" with green badge
  - PSRAM: "6.7MB free" with bar
  - WiFi: "-52 dBm" with signal icon
  - Audio energy: live bar (animated)
  - Detection log: timestamped entries
- **Main area:** 
  - Large MJPEG stream placeholder (show actual camera feed if possible, or a demo loop)
  - "Face detected: Unknown" overlay (simulated)
- **Bottom:** Factory reset button (styled as danger)

**Animation:**
- The mockup fades in and scales from 0.95 → 1.0
- Internal elements (bars, counters) animate after mockup appears
- Uptime counter increments (simulated)
- Audio energy bar oscillates randomly

**Below mockup:**
- "Try the live demo" button (if deployed) OR "Watch demo video" button
- Small text: "Dashboard is a single HTML file compiled into firmware. 4KB gzipped."

---

### 7.7 Technical Architecture

**Layout:** `--bg-primary`, padding 96px 0.

**Headline:**
```
Built like a firmware engineer's dream
```
- `--display-2`

**Subheadline:**
```
Every decision optimized for reliability, performance, and zero maintenance.
```
- `--body-large`, `--text-secondary`

**Content:** 3 sub-sections

**Sub-section 1: Dual-Core Architecture**
- Visual: Two vertical columns side by side
  - Left: "Core 0 — Network" with WiFi, lwIP, HTTP, DNS icons
  - Right: "Core 1 — Processing" with Mic, Camera, ML, State Machine icons
  - Divider: Vertical line with "FreeRTOS" label
- Text: "WiFi and ML inference are scheduling-incompatible. Core pinning solved instability that priority tuning couldn't."
- Style: Terminal/code aesthetic. Monospace labels.

**Sub-section 2: 6-State Finite State Machine**
- Visual: Interactive or auto-playing state diagram
  - 6 nodes: INIT → AP_MODE → CONNECTING → IDLE → ACTIVE → ERROR
  - Active node glows
  - LED pattern shown inside each node
  - Arrows animate between states
- Text: "The ACTIVE → IDLE 30s timeout cuts average power draw by ~70%."

**Sub-section 3: EventBus**
- Visual: Small publish/subscribe diagram
  - Topics: WAKE_WORD_DETECTED, FACE_DETECTED, ERROR_OCCURRED, etc.
  - Arrows showing event flow
- Text: "32-message queue. Zero heap allocation during dispatch. No memory fragmentation. Weeks of uptime proven."

**Design:**
- Each sub-section is a `--bg-secondary` card
- Icons/graphics are SVG, styled with `--accent-primary` and `--accent-secondary`
- Use `--font-mono` for all technical labels

---

### 7.8 Memory Budget Visualization

**Layout:** `--bg-secondary`, padding 96px 0.

**Headline:**
```
8MB. Fully accounted for.
```
- `--display-2`, centered

**Subheadline:**
```
Every byte has a job. 6.7MB headroom for your features.
```
- `--body-large`, `--text-secondary`, centered

**Content:** Animated bar chart + breakdown table

**Bar Chart:**
- Total width represents 8MB
- Segments (left to right):
  - Camera frame buffers: ~100KB (DRAM) — color: `#fbbf24`
  - FreeRTOS stacks: ~32KB (DRAM) — color: `#fbbf24`
  - Audio ring buffer: 96KB — color: `#7c8aff`
  - MFCC buffer: 8KB — color: `#7c8aff`
  - TFLite arena: 32KB — color: `#7c8aff`
  - RGB565 buffer: 307KB — color: `#7c8aff`
  - MTCNN weights: ~250KB — color: `#00e5ff`
  - MobileFaceNet: ~400KB — color: `#00e5ff`
  - Face alignment: 38KB — color: `#00e5ff`
  - HTTP buffers: ~32KB — color: `#7c8aff`
  - Free: ~6.7MB — color: `rgba(124, 138, 255, 0.1)` (subtle)

- Legend below chart
- Hover on segment: tooltip with exact size and purpose
- Animate width on scroll into view

**Breakdown Table:**
| Allocation | Size | Location | Purpose |
|------------|------|----------|---------|
| Audio ring buffer | 96KB | PSRAM | 3s @ 16kHz/16bit circular |
| ... | ... | ... | ... |

- Styled as `--bg-code` rows
- `--font-mono` for sizes
- Alternating row backgrounds for readability

**Callout Box:**
```
⚠️ Critical constraint: DRAM (512KB) is the real bottleneck — not PSRAM. 
Camera DMA + WiFi/lwIP + task stacks consume the vast majority.
```
- `--bg-primary`, left border 3px `--warning`, padding 16px 24px
- `--body-small`

---

### 7.9 Performance Targets

**Layout:** `--bg-primary`, padding 96px 0.

**Headline:**
```
Numbers that matter
```
- `--display-2`

**Content:** 2x3 grid of spec cards

| Operation | Target | Notes |
|-----------|--------|-------|
| MJPEG Stream | 15–25 FPS | Zero-copy path |
| Face Detection | 100–150ms | Every 3rd frame |
| Face Recognition | 50–80ms | int8 quantized |
| Wake Word | <50ms | 22KB model |
| Boot Time | <1s | Cold start |
| Power Draw | ~300mA | Peak @ 5V |

**Card Design:**
- `--spec-card` style
- Value: Large, `--text-primary`, tabular nums
- Unit: `--caption`, `--text-muted`
- Operation: `--heading-2`
- Notes: `--body-small`, `--text-muted`
- Hover: subtle glow

---

### 7.10 Comparison Table

**Layout:** `--bg-secondary`, padding 96px 0.

**Headline:**
```
How we stack up
```
- `--display-2`, centered

**Subheadline:**
```
The only sub-$20 system with face detection + wake word + streaming + dashboard.
```
- `--body-large`, `--text-secondary`, centered

**Content:** Full comparison table

| Product | Price | ML | Stream | Setup | Open Source |
|---------|-------|-----|--------|-------|-------------|
| **Neural Vision** | **$15** | **Face + Voice** | **MJPEG** | **Captive Portal** | **✅ MIT** |
| RPi + Camera | $75–100 | Python/cloud | MJPEG/RTSP | SSH/desktop | ❌ |
| Arducam Mini | $30–50 | None | SPI/I2C | Wired | ❌ |
| ESP32-CAM | $7–10 | None | None¹ | Hardcoded² | Varies |
| OAK-D Lite | $300 | Depth AI | USB3 | USB | ❌ |

¹ Needs extra firmware
² No captive portal

**Table Design:**
- First row (Neural Vision): `--comparison-card.highlight`
- Checkmarks: `--success` color
- X marks: `--accent-tertiary` color
- Header row: `--bg-tertiary`, uppercase, `--caption`
- Cell padding: 16px 20px
- Border: 1px `--border-subtle`
- Hover on row: subtle highlight

**Below table:**
```
Primary differentiator: No other sub-$20 embedded system offers face detection + 
wake word + MJPEG streaming + captive portal + live dashboard in a single firmware image.
```
- `--body-large`, `--accent-primary`, centered, max-width 700px

---

### 7.11 Use Cases / Target Audience

**Layout:** `--bg-primary`, padding 96px 0.

**Headline:**
```
Built for builders
```
- `--display-2`

**Content:** 5 audience cards in a row (horizontal scroll on mobile)

**Card 1: Embedded ML Engineers**
- Icon: Code brackets
- Title: "Reference Implementation"
- Body: "A production-ready blueprint for on-device vision + voice. Study the architecture. Adapt the pipeline. Ship your product."

**Card 2: IoT Product Developers**
- Icon: Circuit board
- Title: "Production Building Block"
- Body: "Drop this firmware into your camera-based product. Add your model. Customize the dashboard. Go to market in weeks, not months."

**Card 3: Makers & Hobbyists**
- Icon: Wrench
- Title: "Smart Everything"
- Body: "Smart doorbell. Pet camera. Plant monitor. Presence detection. If you can solder, you can build it."

**Card 4: Portfolio Builders**
- Icon: Star
- Title: "Prove Your Skills"
- Body: "FreeRTOS. C++17. Computer vision. Audio processing. WiFi networking. ML deployment. One project, six disciplines."

**Card 5: Hardware Startups**
- Icon: Rocket
- Title: "MVP Foundation"
- Body: "Skip the $100k NRE. Start with proven firmware. Iterate on hardware. Raise with a working demo."

**Card Design:**
- `--bg-secondary`
- Icon: 40px, `--accent-primary`
- Title: `--heading-2`
- Body: `--body`, `--text-secondary`
- Equal height cards
- Staggered reveal on scroll

---

### 7.12 Technical Specs (Detailed)

**Layout:** `--bg-secondary`, padding 96px 0.

**Headline:**
```
The full spec sheet
```
- `--display-2`

**Content:** Tabbed interface or accordion

**Tab 1: Hardware**
- Board: Seeed Studio XIAO ESP32S3 Sense
- MCU: ESP32-S3, Xtensa LX7 dual-core @ 240MHz
- PSRAM: 8MB OPI @ 80MHz
- Flash: 8MB QSPI NOR
- Camera: OV2640 UXGA (1600×1200), HW JPEG
- Mic: MSM261D3526H1CPM digital MEMS (PDM/I2S)
- Wireless: WiFi 2.4GHz b/g/n + BLE 5.0
- LED: Orange on GPIO21 (PWM)
- Dimensions: 21 × 17.5mm
- Cost: ~$15

**Tab 2: I/O & Pins**
- Camera DVP: GPIOs 10–18, 38–40, 47–48
- PDM Mic: GPIO 41 (DATA), 42 (CLK)
- MicroSD (SPI): GPIO 3 (CS), 7 (SCK), 8 (MISO), 9 (MOSI)
- User LED: GPIO 21
- UART: GPIO 43 (TX), 44 (RX)
- I2C: GPIO 5 (SDA), GPIO 6 (SCL)

**Tab 3: Memory Map**
- (Same as Memory Budget section, but in table form)

**Tab 4: API Endpoints**
| Method | Path | Description |
|--------|------|-------------|
| GET | / | Dashboard SPA |
| GET | /stream | MJPEG camera stream |
| GET | /capture | Single JPEG photo |
| GET | /api/status | System status JSON |
| GET | /api/config | Configuration |
| GET | /api/factory-reset | Clear & reboot |
| POST | /api/system/reboot | Reboot device |

**Tab 5: Build Environments**
- `full`: All modules integrated
- `test_cam`: Camera + WiFi + HTTP stream
- `test_mic`: I2S audio + serial dump
- `test_wifi`: WiFi manager + captive portal

**Design:**
- Tabs: Pill-style, `--bg-primary` inactive, `--accent-primary` active
- Content: `--bg-code` background, `--font-mono` for technical data
- Copy button on code blocks

---

### 7.13 Build & Development

**Layout:** `--bg-primary`, padding 96px 0.

**Headline:**
```
Start building in minutes
```
- `--display-2`

**Content:** Terminal window showing build commands

```bash
# Clone the repo
git clone https://github.com/yourname/esp32-neural-vision.git
cd esp32-neural-vision

# Build production firmware
pio run -e full

# Flash to device
pio run -e full -t upload

# Monitor serial output
pio device monitor -e full
```

**Terminal Design:**
- Use `--terminal` component style
- Syntax highlighting: comments in `--text-muted`, commands in `--text-primary`, prompts in `--success`

**Below terminal:**
- "Requirements: PlatformIO CLI, ESP32 Arduino Core, USB-C cable"
- "Compatible with: Windows, macOS, Linux"
- Links: "View on GitHub" | "Read the Docs"

---

### 7.14 FAQ

**Layout:** `--bg-secondary`, padding 96px 0.

**Headline:**
```
Questions? Answered.
```
- `--display-2`, centered

**Content:** Accordion-style FAQ

**Q1: Does this need internet?**
A: No. Everything runs on-device. The captive portal and dashboard are served directly from the ESP32's flash memory. No cloud APIs, no subscription, no data leaving your network.

**Q2: Can I use my own wake word?**
A: Yes. The TFLite Micro model can be retrained with your own audio samples. The pipeline supports custom keyword detection with the same 22KB footprint.

**Q3: How many faces can it recognize?**
A: The embedding database is stored in flash. With 8MB flash, you can store 50–100 face embeddings (128-dim float32 each) with room for firmware and OTA partitions.

**Q4: What's the range for face detection?**
A: The OV2640 + MTCNN pipeline works best at 1–3 meters with good lighting. Detection drops beyond 5 meters or in very low light.

**Q5: Can I modify the dashboard?**
A: Yes. The dashboard is a single HTML file (4KB gzipped) compiled as a `constexpr` string. Edit `src/dashboard.h`, rebuild, and flash.

**Q6: Is this production-ready?**
A: Phases 1–2 (system framework, WiFi, streaming, dashboard) are complete and stable. Phases 3–6 (wake word, face detection, recognition) are in active development. The architecture is designed for production.

**Q7: Power requirements?**
A: 5V USB-C, ~300mA peak during WiFi + camera active. A standard phone charger or USB battery bank is sufficient. Average draw in IDLE state is ~80mA.

**Accordion Design:**
- Question: `--heading-2`, clickable
- Answer: `--body`, `--text-secondary`, max-height animation
- Chevron icon rotates 180° on open
- Border-bottom: 1px `--border-subtle`

---

### 7.15 CTA / Get Started

**Layout:** `--bg-primary`, padding 128px 0. Centered.

**Background:** Subtle gradient orb centered behind content. `--accent-primary` at 5% opacity.

**Headline:**
```
AI vision doesn't need a data center.
```
- `--display-1`, centered, `hero-gradient`

**Subheadline:**
```
Get the firmware, flash it to a $15 board, and start building.
Open source. MIT licensed. No strings attached.
```
- `--body-large`, `--text-secondary`, centered, max-width 500px

**Buttons:**
- Primary: "Get Started →" (large)
- Secondary: "View on GitHub" (GitHub icon)
- Gap: 16px

**Below buttons:**
```
⭐ Star us on GitHub  ·  🐛 Report an issue  ·  💬 Join the discussion
```
- `--caption`, `--text-muted`
- Links to respective GitHub pages

---

### 7.16 Footer

**Layout:** Full-width, `--bg-secondary`, padding 48px 0.

**Content:**
- **Top row:**
  - Left: Logo + "Neural Vision" + "Edge AI for everyone"
  - Right: Links — GitHub | Docs | Issues | Discussions
- **Divider:** 1px `--border-subtle`
- **Bottom row:**
  - Left: "© 2026 Neural Vision. MIT Licensed."
  - Right: "Built with ESP32-S3 + FreeRTOS + TFLite Micro"

**Design:**
- Links: `--body-small`, `--text-muted`, hover `--accent-primary`
- Minimal, clean, no clutter

---

## 8. Responsive Breakpoints

| Breakpoint | Width | Changes |
|------------|-------|---------|
| Mobile | < 640px | Single column, stacked layout, hamburger nav, reduced padding |
| Tablet | 640–1024px | 2-column grids, medium padding |
| Desktop | 1024–1280px | Full layout, max-width container |
| Large | > 1280px | Wider container, larger spacing |

**Mobile-specific:**
- Hero: 60vh height, board image above text
- Stats: 2x2 grid
- Problem cards: single column
- Feature cards: single column
- Comparison table: horizontal scroll with sticky first column
- Architecture diagram: stacked vertically
- Use case cards: horizontal scroll

---

## 9. Assets & Images

### Required Images

1. **Hero Board Photo**
   - High-quality photo of XIAO ESP32S3 Sense
   - Transparent or dark background
   - Size: 800×800px minimum
   - Format: WebP with PNG fallback
   - Style: Product photography, slight angle, visible camera and mic

2. **Dashboard Screenshot**
   - Actual screenshot of the web dashboard
   - Show live stream, status panel, detection log
   - Size: 1200×800px
   - Format: WebP

3. **Architecture Diagram**
   - SVG preferred
   - Dual-core layout, state machine, data flow
   - Style: Clean, technical, dark theme

4. **Data Flow Illustration**
   - SVG animation
   - Mic → Buffer → ML and Camera → Stream
   - Style: Circuit diagram aesthetic

5. **Favicon**
   - Stylized eye icon
   - Sizes: 32×32, 180×180 (apple-touch)

### Image Treatment

- All photos: slight blue/purple tint to match brand
- Shadows: colored shadows (`rgba(124, 138, 255, 0.2)`) instead of black
- Borders: subtle `--border-subtle` on all images
- Rounded corners: 12px for photos, 8px for UI screenshots

---

## 10. SEO & Meta

```html
<title>Neural Vision — $15 Edge AI Camera with Face Recognition & Wake Word</title>
<meta name="description" content="A complete vision + voice AI pipeline on a $15 ESP32-S3 microcontroller. Face detection, wake word recognition, live MJPEG streaming, and web dashboard — entirely on-device, no cloud required.">
<meta name="keywords" content="ESP32, edge AI, face recognition, wake word, microcontroller, computer vision, IoT, embedded ML, TFLite Micro">
<meta property="og:title" content="Neural Vision — $15 Edge AI Camera">
<meta property="og:description" content="Face detection + wake word + live streaming on a $15 microcontroller. No cloud. No Linux. No subscription.">
<meta property="og:image" content="/og-image.png">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary_large_image">
```

---

## 11. Performance Requirements

- **Lighthouse Score:** > 90 on all metrics
- **First Contentful Paint:** < 1.5s
- **Largest Contentful Paint:** < 2.5s
- **Total Page Size:** < 500KB (excluding images)
- **JavaScript:** < 100KB gzipped
- **CSS:** < 20KB gzipped (Tailwind purged)
- **Images:** WebP format, lazy loaded, responsive srcset
- **Fonts:** Preload Inter and JetBrains Mono, `font-display: swap`
- **Animations:** Use `transform` and `opacity` only. Respect `prefers-reduced-motion`.

---

## 12. Accessibility

- All images have descriptive `alt` text
- Color contrast ratio > 4.5:1 for all text
- Focus states visible on all interactive elements
- Keyboard navigable accordion, tabs, and mobile menu
- `prefers-reduced-motion`: disable animations, instant transitions
- Semantic HTML: proper heading hierarchy, landmarks, aria-labels

---

## 13. File Structure (Svelte + Tailwind)

```
landing-page/
├── src/
│   ├── lib/
│   │   ├── components/
│   │   │   ├── Navigation.svelte
│   │   │   ├── Hero.svelte
│   │   │   ├── StatsBar.svelte
│   │   │   ├── ProblemSection.svelte
│   │   │   ├── SolutionSection.svelte
│   │   │   ├── DemoSection.svelte
│   │   │   ├── ArchitectureSection.svelte
│   │   │   ├── MemorySection.svelte
│   │   │   ├── PerformanceSection.svelte
│   │   │   ├── ComparisonSection.svelte
│   │   │   ├── UseCasesSection.svelte
│   │   │   ├── SpecsSection.svelte
│   │   │   ├── BuildSection.svelte
│   │   │   ├── FAQSection.svelte
│   │   │   ├── CTASection.svelte
│   │   │   ├── Footer.svelte
│   │   │   ├── Card.svelte
│   │   │   ├── Badge.svelte
│   │   │   ├── Terminal.svelte
│   │   │   ├── AnimatedCounter.svelte
│   │   │   ├── ScrollReveal.svelte
│   │   │   ├── DataFlowSVG.svelte
│   │   │   ├── StateMachine.svelte
│   │   │   └── MemoryBar.svelte
│   │   ├── stores/
│   │   │   └── scrollStore.js
│   │   └── utils/
│   │       └── intersectionObserver.js
│   ├── routes/
│   │   └── +page.svelte
│   ├── app.html
│   └── app.css
├── static/
│   ├── images/
│   │   ├── board.webp
│   │   ├── dashboard.webp
│   │   └── og-image.png
│   └── favicon.png
├── tailwind.config.js
├── svelte.config.js
├── vite.config.js
└── package.json
```

---

## 14. Tailwind Config Extensions

```javascript
// tailwind.config.js
module.exports = {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  theme: {
    extend: {
      colors: {
        'nv-bg': {
          primary: '#0a0a0f',
          secondary: '#12121a',
          tertiary: '#1a1a24',
          code: '#0d0d14',
        },
        'nv-accent': {
          primary: '#7c8aff',
          secondary: '#00e5ff',
          tertiary: '#ff6b6b',
        },
        'nv-text': {
          primary: '#e8e8f0',
          secondary: '#9ca3af',
          muted: '#6b7280',
          code: '#a5b4fc',
        },
        'nv-border': {
          subtle: 'rgba(124, 138, 255, 0.1)',
          glow: 'rgba(124, 138, 255, 0.3)',
        },
        'nv-status': {
          success: '#4ade80',
          warning: '#fbbf24',
          error: '#ff6b6b',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      animation: {
        'pulse-glow': 'pulse-glow 2s ease-in-out infinite',
        'float': 'float 4s ease-in-out infinite',
        'flow-draw': 'flow-draw 3s ease-in-out infinite',
        'led-breathe': 'led-breathe 2s ease-in-out infinite',
        'led-blink-slow': 'led-blink-slow 1s ease-in-out infinite',
        'led-blink-fast': 'led-blink-fast 300ms ease-in-out infinite',
      },
      keyframes: {
        'pulse-glow': {
          '0%, 100%': { boxShadow: '0 0 4px rgba(0, 229, 255, 0.4)' },
          '50%': { boxShadow: '0 0 12px rgba(0, 229, 255, 0.8)' },
        },
        'float': {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        'flow-draw': {
          to: { strokeDashoffset: '0' },
        },
        'led-breathe': {
          '0%, 100%': { opacity: '0.3' },
          '50%': { opacity: '1' },
        },
        'led-blink-slow': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.2' },
        },
        'led-blink-fast': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.2' },
        },
      },
    },
  },
  plugins: [],
};
```

---

## 15. Key Copy Snippets (Exact Text to Use)

### Hero
```
See. Hear. Recognize.
All on a $15 chip.

Face detection. Wake word recognition. Live MJPEG streaming. 
Zero cloud. Zero Linux. Zero subscription.
Entirely on the ESP32-S3 — a microcontroller smaller than a stick of gum.
```

### One-Liner (for meta, sharing)
```
A $15 AI camera that detects faces, listens for wake words, streams live MJPEG video, 
and lets you control everything from a web dashboard — no cloud, no Linux, no subscription.
```

### Value Props (short)
```
⚡ <1s boot  ·  🔒 No cloud  ·  🧠 8MB RAM  ·  📡 WiFi + BLE
```

### Problem Statement
```
Why does AI vision cost $100+ and need a fan?
```

### Solution Statement
```
Meet Neural Vision. A complete vision + voice AI pipeline that fits in 8MB of RAM.
```

### CTA
```
AI vision doesn't need a data center.
Get the firmware, flash it to a $15 board, and start building.
Open source. MIT licensed. No strings attached.
```

### Differentiator
```
No other sub-$20 embedded system offers face detection + wake word + 
MJPEG streaming + captive portal + live dashboard in a single firmware image.
```

---

## 16. Animation Choreography (Scroll Timeline)

| Scroll Position | Animation |
|-----------------|-----------|
| 0% (top) | Hero content fully visible, board floating |
| 0–10% | Nav gains border, slight background opacity increase |
| 10–20% | Stats bar fades in, numbers count up |
| 20–35% | Problem cards stagger in from bottom |
| 35–50% | Solution cards stagger in, icons animate |
| 50–60% | Dashboard mockup scales in, internal elements animate |
| 60–70% | Architecture diagram draws in (SVG stroke animation) |
| 70–80% | Memory bar fills, segments color in sequence |
| 80–90% | Performance cards flip in (3D transform) |
| 90–100% | Comparison table rows slide in |
| Footer | CTA text gradient shifts subtly |

---

## 17. GitHub Pages Deployment Notes

- **Build command:** `npm run build` (adapter-static)
- **Output:** `build/` directory
- **Deploy:** Push `build/` contents to `gh-pages` branch OR use GitHub Actions
- **Base path:** Set `paths.base` in `svelte.config.js` to repo name
- **Trailing slashes:** Enable for GitHub Pages compatibility
- **404 page:** Copy `index.html` to `404.html` for SPA routing

---

*This specification is the single source of truth. Any deviation from colors, fonts, spacing, or section structure must be discussed and documented. The goal is a landing page that makes engineers stop scrolling and makers reach for their wallets.*
