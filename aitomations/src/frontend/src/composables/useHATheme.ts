import { ref, onMounted } from 'vue'

export function useHATheme() {
  const haTheme = ref({
    primaryColor: '#03a9f4',
    primaryTextColor: '#212121',
    primaryBackgroundColor: '#fafafa',
    cardBackgroundColor: '#ffffff',
    secondaryTextColor: '#757575',
    dividerColor: '#e0e0e0',
    accentColor: '#ff9800',
    errorColor: '#f44336',
    warningColor: '#ff9800',
    successColor: '#4caf50',
    isDark: false,
  })

  const loadHATheme = () => {
    try {
      // Method 1: Test actual rendered colors (most reliable)
      const testDiv = window.parent.document.createElement('div')
      testDiv.style.cssText = `
        position: fixed;
        top: -200px;
        left: -200px;
        width: 10px;
        height: 10px;
        background-color: var(--primary-background-color);
        color: var(--primary-text-color);
        border: 1px solid var(--divider-color);
      `
      
      window.parent.document.body.appendChild(testDiv)
      
      const computedStyles = getComputedStyle(testDiv)
      
      // Extract actual colors
      const actualBg = computedStyles.backgroundColor
      const actualText = computedStyles.color
      const actualBorder = computedStyles.borderColor
      
      console.log('=== ACTUAL HA THEME COLORS ===')
      console.log('Background:', actualBg)
      console.log('Text:', actualText)
      console.log('Border:', actualBorder)
      
      // Determine if dark theme
      let isDark = false
      if (actualBg.includes('rgb')) {
        const values = actualBg.match(/\d+/g)?.map(Number)
        if (values && values.length >= 3) {
          const [r, g, b] = values
          const brightness = (r * 299 + g * 587 + b * 114) / 1000
          isDark = brightness < 128
          console.log('Background brightness:', brightness, 'isDark:', isDark)
        }
      }
      
      // Clean up test element
      window.parent.document.body.removeChild(testDiv)
      
      // Get CSS variables from parent (these should be correct now)
      const parentStyles = getComputedStyle(window.parent.document.documentElement)
      
      // Extract theme values
      const extractedTheme = {
        primaryColor: parentStyles.getPropertyValue('--primary-color').trim() || '#009ac7',
        primaryTextColor: actualText || '#e1e1e1',
        primaryBackgroundColor: actualBg || '#111111',
        cardBackgroundColor: isDark 
          ? (parentStyles.getPropertyValue('--card-background-color').trim() === '#ffffff' 
            ? '#1c1c1c'  // Override white with dark
            : parentStyles.getPropertyValue('--card-background-color').trim() || '#1c1c1c')
          : (parentStyles.getPropertyValue('--card-background-color').trim() || '#ffffff'),
        secondaryTextColor: isDark 
          ? (parentStyles.getPropertyValue('--secondary-text-color').trim().includes('#5e5e5e') 
            ? '#a0a0a0'  // Override light gray with dark theme gray
            : parentStyles.getPropertyValue('--secondary-text-color').trim() || '#a0a0a0')
          : (parentStyles.getPropertyValue('--secondary-text-color').trim() || '#757575'),
        dividerColor: actualBorder || (isDark ? 'rgba(225, 225, 225, 0.12)' : 'rgba(0, 0, 0, 0.12)'),
        accentColor: parentStyles.getPropertyValue('--accent-color').trim() || '#ff9800',
        errorColor: parentStyles.getPropertyValue('--error-color').trim() || '#f44336',
        warningColor: parentStyles.getPropertyValue('--warning-color').trim() || '#ff9800',
        successColor: parentStyles.getPropertyValue('--success-color').trim() || '#4caf50',
        isDark: isDark,
      }
      
      // Apply the theme
      haTheme.value = extractedTheme
      
      console.log('Applied HA Theme:', haTheme.value)
      
      // Inject CSS variables into our iframe
      injectThemeCSS(extractedTheme)
      
    } catch (error) {
      console.warn('Could not load HA theme:', error)
    }
  }

  const injectThemeCSS = (theme: typeof haTheme.value) => {
    // Remove existing theme style if it exists
    const existingStyle = document.getElementById('ha-theme-injection')
    if (existingStyle) {
      existingStyle.remove()
    }
    
    // Create new style element
    const style = document.createElement('style')
    style.id = 'ha-theme-injection'
    
    style.textContent = `
      :root {
        --ha-primary-color: ${theme.primaryColor};
        --ha-primary-text-color: ${theme.primaryTextColor};
        --ha-primary-background-color: ${theme.primaryBackgroundColor};
        --ha-card-background-color: ${theme.cardBackgroundColor};
        --ha-secondary-text-color: ${theme.secondaryTextColor};
        --ha-divider-color: ${theme.dividerColor};
        --ha-accent-color: ${theme.accentColor};
        --ha-error-color: ${theme.errorColor};
        --ha-warning-color: ${theme.warningColor};
        --ha-success-color: ${theme.successColor};
        --ha-is-dark: ${theme.isDark ? '1' : '0'};
      }
    `
    
    document.head.appendChild(style)
    console.log('✓ Injected HA theme CSS variables into iframe')
  }

  const watchThemeChanges = () => {
    try {
      const observer = new MutationObserver(() => {
        console.log('HA theme change detected, reloading...')
        setTimeout(loadHATheme, 300)
      })
      
      // Watch parent document for changes
      observer.observe(window.parent.document.documentElement, {
        attributes: true,
        attributeFilter: ['style'],
        subtree: false
      })
      
      // Also watch for class changes on body or HA elements
      const haElement = window.parent.document.querySelector('home-assistant')
      if (haElement) {
        observer.observe(haElement, {
          attributes: true,
          subtree: true
        })
      }
    } catch (error) {
      console.warn('Could not observe theme changes:', error)
    }
  }

  onMounted(() => {
    // Load theme immediately
    loadHATheme()
    
    // Set up change watching
    watchThemeChanges()
    
    // Also reload theme after a short delay to catch any initial loading
    setTimeout(loadHATheme, 1000)
  })

  return { haTheme, loadHATheme }
}