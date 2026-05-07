<!DOCTYPE html>

<html class="dark" lang="en"><head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>Command Center - HUD Edition</title>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700;800&amp;family=Space+Grotesk:wght@600;700&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<style>
        body {
            background-color: #050505;
            color: #e5e2e1;
            font-family: 'JetBrains Mono', monospace;
        }
        .scanline-overlay {
            background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06));
            background-size: 100% 2px, 3px 100%;
            pointer-events: none;
        }
        .hud-border {
            border: 1px solid #1E1B4B;
        }
        .hud-border-active {
            border: 1px solid #8B5CF6;
            box-shadow: 0 0 8px rgba(139, 92, 246, 0.2);
        }
        .glow-indicator {
            box-shadow: 0 0 8px #8B5CF6;
        }
        .glow-indicator-cyan {
            box-shadow: 0 0 8px #4cd7f6;
        }
        .material-symbols-outlined {
            font-variation-settings: 'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 24;
        }
    </style>
<script id="tailwind-config">
        tailwind.config = {
          darkMode: "class",
          theme: {
            extend: {
              "colors": {
                      "surface-container-high": "#2a2a2a",
                      "surface-container-lowest": "#0e0e0e",
                      "inverse-on-surface": "#313030",
                      "on-primary-fixed": "#23005c",
                      "tertiary-fixed-dim": "#4cd7f6",
                      "on-tertiary-fixed-variant": "#004e5c",
                      "on-tertiary": "#003640",
                      "primary-container": "#a078ff",
                      "surface": "#131313",
                      "on-tertiary-container": "#002f38",
                      "tertiary-container": "#009eb9",
                      "secondary-fixed-dim": "#c3c0ff",
                      "secondary-fixed": "#e3dfff",
                      "on-error": "#690005",
                      "primary-fixed": "#e9ddff",
                      "on-surface-variant": "#cbc3d7",
                      "on-tertiary-fixed": "#001f26",
                      "on-primary-container": "#340080",
                      "on-error-container": "#ffdad6",
                      "surface-dim": "#131313",
                      "secondary-container": "#3a2dc2",
                      "surface-variant": "#353534",
                      "outline": "#958ea0",
                      "inverse-surface": "#e5e2e1",
                      "background": "#131313",
                      "inverse-primary": "#6d3bd7",
                      "secondary": "#c3c0ff",
                      "primary": "#d0bcff",
                      "surface-tint": "#d0bcff",
                      "outline-variant": "#494454",
                      "error-container": "#93000a",
                      "on-secondary-container": "#b4b0ff",
                      "on-background": "#e5e2e1",
                      "surface-container-low": "#1c1b1b",
                      "on-primary-fixed-variant": "#5516be",
                      "primary-fixed-dim": "#d0bcff",
                      "error": "#ffb4ab",
                      "on-secondary": "#1f00a4",
                      "on-secondary-fixed": "#100069",
                      "on-primary": "#3c0091",
                      "surface-container": "#201f1f",
                      "on-secondary-fixed-variant": "#372abf",
                      "surface-bright": "#3a3939",
                      "on-surface": "#e5e2e1",
                      "surface-container-highest": "#353534",
                      "tertiary": "#4cd7f6",
                      "tertiary-fixed": "#acedff"
              },
              "borderRadius": {
                      "DEFAULT": "0.25rem",
                      "lg": "0.5rem",
                      "xl": "0.75rem",
                      "full": "9999px"
              },
              "spacing": {
                      "density-high": "4px",
                      "gutter": "16px",
                      "margin": "24px",
                      "density-med": "12px",
                      "unit": "4px"
              },
              "fontFamily": {
                      "body-sm": ["JetBrains Mono"],
                      "label-caps": ["JetBrains Mono"],
                      "data-mono": ["JetBrains Mono"],
                      "body-lg": ["JetBrains Mono"],
                      "headline-lg": ["Space Grotesk"],
                      "headline-md": ["Space Grotesk"]
              },
              "fontSize": {
                      "body-sm": ["14px", {"lineHeight": "1.5", "letterSpacing": "0em", "fontWeight": "400"}],
                      "label-caps": ["12px", {"lineHeight": "1", "letterSpacing": "0.1em", "fontWeight": "700"}],
                      "data-mono": ["13px", {"lineHeight": "1", "letterSpacing": "-0.02em", "fontWeight": "500"}],
                      "body-lg": ["16px", {"lineHeight": "1.5", "letterSpacing": "0em", "fontWeight": "400"}],
                      "headline-lg": ["32px", {"lineHeight": "1.2", "letterSpacing": "-0.02em", "fontWeight": "700"}],
                      "headline-md": ["24px", {"lineHeight": "1.2", "letterSpacing": "-0.01em", "fontWeight": "600"}]
              }
            },
          },
        }
      </script>
</head>
<body class="flex min-h-screen">
<!-- REST OF THE CONTENT ... -->
</body>
</html>
