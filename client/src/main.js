import './app.css';
import { mount } from 'svelte';
import App from './App.svelte';
import { i18n } from './lib/i18n.svelte.js';

// Keep <html lang> honest from the first frame: the server negotiated a
// language from Accept-Language, but a stored preference wins.
document.documentElement.lang = i18n.lang;

export default mount(App, { target: document.getElementById('app') });
