## Frontend Design Guidelines

When generating HTML/CSS for this project, prioritize usability and user experience while maintaining the aesthetic:

**Aesthetic & UX**: Layered dark-mode with high contrast. Use sweeping, organic curve shapes and masking. Prioritize clear visual hierarchy, accessible tap targets (minimum 44x44px), and obvious interactive states (hover, focus, active).

**Typography**: Monospace fonts only (e.g., JetBrains Mono, IBM Plex Mono). Maintain legible font sizes and clear line spacing for readability across devices.

**Color palette**: Use CSS variables. Base background is deep blue. Accents are vibrant cyan, deep magenta, and intense gold. Ensure WCAG-compliant contrast ratios for all text against backgrounds. Focus outlines must use high-visibility cyan.

**Layout**: Responsive landing page. Header, Hero section divided by an overlapping arc, and a responsive feature grid (columns stack on mobile). Use logical padding and whitespace to prevent cognitive overload.

**Cards & Modals**: Standalone cards (logout prompts, alerts, etc.) must be centered with generous padding (minimum 2rem). Apply consistent margin spacing.

**Checkboxes**: Use custom checkbox component. Always use a small variant of the following code:

```html
<label class="container">
  <input type="checkbox" checked="checked" />
  <div class="checkmark"></div>
</label>
```

```css
/* From Uiverse.io by byllzz */ 
/*checkbox container */
.container {
  display: block;
  position: relative;
  cursor: pointer;
  font-size: 25px;
  user-select: none;
  width: 1.5em;
  height: 1.5em;
}

.container input {
  position: absolute;
  opacity: 0;
  cursor: pointer;
}

.container .checkmark {
  position: absolute;
  top: 0;
  left: 0;
  height: 1.5em;
  width: 1.5em;
  background-color: #fdfcf0;
  border: 4px solid #1a1a1a;
  border-radius: 8% 92% 12% 88% / 87% 11% 89% 13%;
  box-shadow: 5px 5px 0px #1a1a1a;
  transition:
    transform 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275),
    box-shadow 0.2s;
}

.container:hover .checkmark {
  transform: scale(1.05) rotate(2deg);
}

.container input:checked ~ .checkmark {
  background-color: #ff5722;
  border-radius: 92% 8% 88% 12% / 11% 87% 13% 89%;
  transform: scale(1.1) rotate(-2deg);
}

.container .checkmark:after {
  content: "";
  position: absolute;
  display: none;
  left: 0.36em;
  top: 0.09em;
  width: 0.3em;
  transform: translate(-50%, -50%) rotate(40deg);
  height: 0.7em;
  border: solid #1a1a1a;
  border-width: 0 0.25em 0.25em 0;
  border-radius: 2px;
}

/* cheked */
.container input:checked ~ .checkmark:after {
  display: block;
  animation: splash 0.3s forwards;
}

.container:active .checkmark {
  transform: scale(0.9) translateY(4px);
  box-shadow: 0px 0px 0px #1a1a1a;
}

@keyframes splash {
  0% {
    transform: scale(0) rotate(40deg);
    opacity: 0;
  }
  70% {
    transform: scale(1.2) rotate(40deg);
  }
  100% {
    transform: scale(1) rotate(40deg);
    opacity: 1;
  }
}
```

**Tables & Cards**: Apply consistent padding (minimum 1.5rem) and margins. Ensure clear cell separation and readable row heights.

**Titles & Borders**: Add generous padding/margin around titles (minimum 1rem). Borders should have visible margin spacing to prevent visual crowding.

**Icons & Badges**: Ensure high contrast with background. Apply minimum 0.5rem padding inside containers. Use adequate margins (0.5rem–1rem) to separate from adjacent content. Verify visibility against all background colors.

**Interactivity**: CSS only. Use smooth transitions for interactive elements. Solved states must be visually distinct but not disabled. Use Django template tags for dynamic state.

**Never**: Poor contrast text, generic SaaS aesthetics, unstyled focus states, non-responsive fixed widths, crowded spacing, or low-contrast icons/badges.