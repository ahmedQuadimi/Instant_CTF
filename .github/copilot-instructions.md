## Frontend Design Guidelines

When generating HTML/CSS for this project, prioritize usability and user experience while maintaining the aesthetic:

**Aesthetic & UX**: Layered dark-mode with high contrast. Use sweeping, organic curve shapes and masking. Prioritize clear visual hierarchy, accessible tap targets (minimum 44x44px), and obvious interactive states (hover, focus, active).

**Typography**: Monospace fonts only (e.g., JetBrains Mono, IBM Plex Mono). Maintain legible font sizes and clear line spacing for readability across devices.

**Color palette**: Use CSS variables. Base background is deep blue. Accents are vibrant cyan, deep magenta, and intense gold. Ensure WCAG-compliant contrast ratios for all text against backgrounds. Focus outlines must use high-visibility cyan.

**Layout**: Responsive landing page. Header, Hero section divided by an overlapping arc, and a responsive feature grid (columns stack on mobile). Use logical padding and whitespace to prevent cognitive overload.

**Interactivity**: CSS only. Use smooth transitions for interactive elements. Solved states must be visually distinct but not disabled. Use Django template tags for dynamic state.

**Never**: Poor contrast text, generic SaaS aesthetics, unstyled focus states, or non-responsive fixed widths.