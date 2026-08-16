---
name: Review AI Design System
colors:
  surface: '#FFFFFF'
  surface-dim: '#dadad8'
  surface-bright: '#f9f9f7'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f4f4f2'
  surface-container: '#eeeeec'
  surface-container-high: '#e8e8e6'
  surface-container-highest: '#e2e3e1'
  on-surface: '#1a1c1b'
  on-surface-variant: '#444748'
  inverse-surface: '#2f3130'
  inverse-on-surface: '#f1f1ef'
  outline: '#747878'
  outline-variant: '#c4c7c7'
  surface-tint: '#5f5e5e'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#1c1b1b'
  on-primary-container: '#858383'
  inverse-primary: '#c9c6c5'
  secondary: '#006e07'
  on-secondary: '#ffffff'
  secondary-container: '#7bfe6a'
  on-secondary-container: '#007508'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#410005'
  on-tertiary-container: '#e94c4d'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#e5e2e1'
  primary-fixed-dim: '#c9c6c5'
  on-primary-fixed: '#1c1b1b'
  on-primary-fixed-variant: '#474646'
  secondary-fixed: '#7bfe6a'
  secondary-fixed-dim: '#5ee151'
  on-secondary-fixed: '#002201'
  on-secondary-fixed-variant: '#005304'
  tertiary-fixed: '#ffdad7'
  tertiary-fixed-dim: '#ffb3af'
  on-tertiary-fixed: '#410005'
  on-tertiary-fixed-variant: '#920418'
  background: '#f9f9f7'
  on-background: '#1a1c1b'
  surface-variant: '#e2e3e1'
  text-primary: '#111111'
  text-secondary: '#6B6B6B'
  border-subtle: '#E8E8E5'
  accent-soft: '#F1FFE8'
  negative-soft: '#FFF3F3'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.03em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: '1.4'
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
  label-caps:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: 0.1em
  mono-data:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: '1.4'
    letterSpacing: -0.01em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  margin-desktop: 40px
  margin-mobile: 20px
  gutter: 24px
  stack-xs: 4px
  stack-sm: 12px
  stack-md: 24px
  stack-lg: 48px
  stack-xl: 80px
---

## Brand & Style

This design system is a premium, light-themed evolution designed for high-end fashion technology and AI analysis. The aesthetic follows **Editorial Minimalism**, blending the sophistication of a luxury fashion lookbook with the precision of a modern SaaS platform. 

The brand personality is **Cultivated, Lucid, and Forward-leaning**. It targets fashion-industry decision-makers who require clarity amidst high-density data. The UI evokes a "Fashion Tech" emotional response—feeling like a high-end physical magazine but powered by invisible, intelligent algorithms.

Key style pillars:
- **Architectural Clarity:** Heavy use of whitespace and thin dividers instead of heavy shadows or containment boxes.
- **Modern Grotesk Foundation:** Utilizing Inter for its systematic, utilitarian, yet contemporary feel.
- **High-Contrast Accents:** Using a stark black header and a vibrant "Electric Lime" AI accent to create clear visual anchors against a warm, gallery-inspired background.

## Colors

The palette is optimized for a premium, high-readability light theme.

- **Foundational Neutrals:** The base background uses a "Warm Gray" (#F7F7F5) to reduce eye strain and provide a gallery-like backdrop. Cards and surfaces use pure White (#FFFFFF) to pop against the base.
- **Brand Primary:** Absolute Black (#0A0A0A) is reserved for the top header and high-impact structural elements, providing a strong anchor for the layout.
- **Typography:** Primary text is a deep, near-black (#111111) for maximum legibility, while secondary text (#6B6B6B) provides clear hierarchy.
- **AI & Sentiment Accents:** "Accent Green" (#7CFF6B) represents AI intelligence and positive insights, paired with a soft background (#F1FFE8) for non-intrusive highlighting. "Negative Red" (#FF5C5C) and its soft counterpart (#FFF3F3) are used strictly for critical alerts or negative sentiment analysis.
- **Borders:** A consistent, low-contrast border (#E8E8E5) is used for section separation, maintaining the minimalist editorial aesthetic without "boxing in" the content.

## Typography

This system uses a **Bold Grotesk** hierarchy to achieve an editorial feel. 

- **Weight as Hierarchy:** Use heavy weights (700+) for headlines and displays. The contrast between bold titles and airy body copy is central to the "Fashion Tech" look.
- **Tight Kerning:** High-level displays and headlines use negative letter spacing to feel "dense" and authoritative.
- **Labeling:** All metadata and category labels should be set in `label-caps` (Uppercase with 10% letter spacing) to provide a structural, functional contrast to editorial headlines.
- **Mono-feel Data:** While using Inter, numerical data should utilize tabular lining figures to ensure alignment in AI performance reports and comparison tables.

## Layout & Spacing

The layout philosophy follows a **Fixed-Fluid Hybrid** model. The content is contained within a 1440px max-width, while the background and header stretch to fill the screen.

- **12-Column Grid:** On desktop, use a 12-column grid with a 24px gutter. Cards typically span 4, 6, or 12 columns.
- **Editorial Whitespace:** Avoid cluttering the screen. Use `stack-lg` (48px) and `stack-xl` (80px) to separate major content groups.
- **Dividers over Boxes:** Use 1px borders (#E8E8E5) to separate vertical sections rather than using distinct background colors for every area. This maintains the "open-air" feeling of a digital magazine.
- **Mobile Reflow:** On mobile, margins reduce to 20px and the grid collapses to a single column. Horizontal scrolling "shelves" should be used for data cards to keep vertical scrolls concise.

## Elevation & Depth

To maintain the Minimalist aesthetic, depth is created through **Tonal Layering** and high-transparency shadows rather than heavy blurs.

- **Base Layer:** The Warm Gray (#F7F7F5) background acts as the lowest point.
- **Surface Layer:** White (#FFFFFF) cards sit on top of the base.
- **Subtle Elevation:** Only use shadows for floating elements like dropdowns, modals, or hovered cards. The shadow should be barely perceptible: `0px 4px 20px rgba(0, 0, 0, 0.04)`.
- **Interactions:** On hover, cards should not lift. Instead, they should transition their border color from #E8E8E5 to #111111 or exhibit a very subtle darkening of the background to indicate interactivity.
- **AI Highlight:** The "Accent Green" can be used as a 2px glow or a solid side-border to indicate "active" AI processing.

## Shapes

The shape language is refined and consistent, balancing the rigidity of the grid with "Soft" corners.

- **Corner Radius:** A standard radius of 10-12px is used for all primary cards, buttons, and input fields.
- **Pill Elements:** Use `rounded-full` exclusively for chips, tags, and toggle switches to provide a visual break from the rectangular layout.
- **Interactive States:** Clickable areas should have clearly defined rounded boundaries. Avoid sharp 0px corners to ensure the UI feels modern and approachable rather than aggressive.

## Components

### Buttons
- **Primary:** Black (#0A0A0A) background with White text. Bold weight. 10px radius.
- **AI Action:** Accent Green (#7CFF6B) background with Black (#0A0A0A) text.
- **Secondary/Ghost:** Transparent background with a 1px Black border.

### Cards
- **Editorial Card:** Pure White background, 1px #E8E8E5 border. No shadow unless hovered. 12px radius.
- **Highlight Card:** Soft Green (#F1FFE8) background for positive AI analysis results.

### Inputs & Forms
- **Field Style:** White background, 1px #E8E8E5 border. On focus, the border becomes Black (#0A0A0A).
- **Labels:** Use `label-caps` positioned above the input field with 8px spacing.

### Navigation (Header)
- **Top Bar:** Solid Black (#0A0A0A) background. All text and icons in White. Height: 64px.
- **Active State:** A thin 2px Accent Green (#7CFF6B) underline for the active navigation item.

### AI Sentiment Chips
- **Positive:** Soft Green background (#F1FFE8) with Green text (#008A00). Rounded-full.
- **Negative:** Soft Red background (#FFF3F3) with Red text (#FF5C5C). Rounded-full.

### Section Dividers
- Vertical or horizontal 1px lines using #E8E8E5. In high-density areas, use these instead of cards to keep the UI lightweight.