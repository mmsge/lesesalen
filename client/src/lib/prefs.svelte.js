/**
 * The two reading preferences from Settings (4h), and where they are kept.
 *
 * Both are the reader's, both survive a reload, and neither is ever sent
 * anywhere — they are `localStorage` keys next to the language, and log out
 * clears them with everything else.
 */
const CW_KEY = 'lesesalen.aatvaringar';
const PERCENT_KEY = 'lesesalen.prosent';

function initial(key) {
  try {
    return window.localStorage.getItem(key) === '1';
  } catch {
    return false;
  }
}

export const prefs = $state({
  /** Content warnings start unwrapped rather than hatched. */
  cwOpen: initial(CW_KEY),
  /** Page positions are shown as a percentage of the edition's page count. */
  percent: initial(PERCENT_KEY),
});

function persist(key, value) {
  try {
    if (value) window.localStorage.setItem(key, '1');
    else window.localStorage.removeItem(key);
  } catch {
    /* private mode or a full quota: the preference just will not be remembered */
  }
}

export function setCwOpen(value) {
  prefs.cwOpen = Boolean(value);
  persist(CW_KEY, prefs.cwOpen);
}

export function setPercent(value) {
  prefs.percent = Boolean(value);
  persist(PERCENT_KEY, prefs.percent);
}

export function forgetPrefs() {
  prefs.cwOpen = false;
  prefs.percent = false;
  persist(CW_KEY, false);
  persist(PERCENT_KEY, false);
}
