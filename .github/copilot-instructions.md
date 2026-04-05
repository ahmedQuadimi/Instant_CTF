## Frontend Design Guidelines

When generating HTML/CSS for this project, prioritize usability and user experience while maintaining the aesthetic:

**Aesthetic & UX**: Layered dark-mode with high contrast. Use sweeping, organic curve shapes and masking. Prioritize clear visual hierarchy, accessible tap targets (minimum 44x44px), and obvious interactive states (hover, focus, active).

**Typography**: Monospace fonts only (e.g., JetBrains Mono, IBM Plex Mono). Maintain legible font sizes and clear line spacing for readability across devices.

**Color palette**: Use CSS variables. Base background is deep blue. Accents are vibrant cyan, deep magenta, and intense gold. Ensure WCAG-compliant contrast ratios for all text against backgrounds. Focus outlines must use high-visibility cyan.

**Layout**: Responsive landing page. Header, Hero section divided by an overlapping arc, and a responsive feature grid (columns stack on mobile). Use logical padding and whitespace to prevent cognitive overload.

**Cards & Modals**: Standalone cards (logout prompts, alerts, etc.) must be centered with generous padding (minimum 2rem). Apply consistent margin spacing.

**Checkboxes**: Use custom checkbox component with organic border-radius. Implement smooth scale/rotation transitions on hover and checked states. Ensure 44x44px minimum tap target. Must coordinate with adjacent elements using flexbox alignment.

**Tables & Cards**: Apply consistent padding (minimum 1.5rem) and margins. Ensure clear cell separation and readable row heights.

**Titles & Borders**: Add generous padding/margin around titles (minimum 1rem). Borders should have visible margin spacing to prevent visual crowding.

**Icons & Badges**: Ensure high contrast with background. Apply minimum 0.5rem padding inside containers. Use adequate margins (0.5rem–1rem) to separate from adjacent content. Verify visibility against all background colors.

**Interactivity**: CSS only. Use smooth transitions for interactive elements. Solved states must be visually distinct but not disabled. Use Django template tags for dynamic state.

**Never**: Poor contrast text, generic SaaS aesthetics, unstyled focus states, non-responsive fixed widths, crowded spacing, or low-contrast icons/badges.