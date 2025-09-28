---
applyTo: '**/{*.vue,*.tsx,*.ts}'
---
- The web pages are displayed within a iFrame in Home Assistant.
- Be careful when working with styles and CSS in Home Assistant (HA) projects. HA has its own theming system that can and we have code in the useHATheme.ts file that determines the current theme and extract the styles.
