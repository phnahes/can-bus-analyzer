# Internationalization (i18n)

### How It Works

The application uses a **lookup table system** for translations located in `src/i18n.py`.

### Supported Languages

| Language | Code | Status |
|----------|------|--------|
| English | `en` | Complete |
| Português | `pt` | Complete |
| Español | `es` | Complete |
| Deutsch | `de` | Complete |
| Français | `fr` | Complete |

### Changing Language

1. Open application
2. Go to **Settings** (Ctrl+,)
3. Select **Language** dropdown
4. Choose your preferred language
5. Click **OK**
6. **Interface updates immediately!**

**Note:** Most UI elements update instantly. Some dialogs may require reopening to see changes.

### Adding New Languages

Want to contribute a new language?

1. Edit `src/i18n.py`
2. Add your language code to `LANGUAGES` dict
3. Add translations for all keys in `TRANSLATIONS` dict
4. Test the application
5. Submit a pull request

**Example:**
```python
# In src/i18n.py
LANGUAGES = {
    'en': 'English',
    'pt': 'Português',
    'it': 'Italiano',  # New language
}

'app_title': {
    'en': 'CAN Analyzer - macOS',
    'pt': 'CAN Analyzer - macOS',
    'it': 'Analizzatore CAN - macOS',  # New translation
},
```
