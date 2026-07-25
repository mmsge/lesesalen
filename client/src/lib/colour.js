/**
 * The average colour of a BlurHash, without a full decoder.
 *
 * A BlurHash's DC component — characters 2..6 — is the average colour of the
 * image in linear space. That is all a cover placeholder needs: a warm block in
 * roughly the right hue while the JPEG loads. Decoding the AC components would
 * mean shipping a whole decoder for a 40x60 blur nobody looks at.
 */
const CHARS =
  '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz#$%*+,-.:;=?@[]^_{|}~';

function decode83(value) {
  let result = 0;
  for (const character of value) {
    const index = CHARS.indexOf(character);
    if (index < 0) return null;
    result = result * 83 + index;
  }
  return result;
}

function linearToSrgb(value) {
  const clamped = Math.max(0, Math.min(1, value));
  const converted =
    clamped <= 0.0031308
      ? clamped * 12.92 * 255
      : (1.055 * clamped ** (1 / 2.4) - 0.055) * 255;
  return Math.round(converted);
}

function srgbToLinear(value) {
  const v = value / 255;
  return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
}

/** `#rrggbb` for the hash's average colour, or null if it is unusable. */
export function averageColour(hash) {
  if (typeof hash !== 'string' || hash.length < 6) return null;
  const dc = decode83(hash.slice(2, 6));
  if (dc === null) return null;
  const r = (dc >> 16) & 255;
  const g = (dc >> 8) & 255;
  const b = dc & 255;
  // The DC is stored already sRGB-encoded; round-tripping keeps this honest if
  // that ever changes.
  const hex = [r, g, b]
    .map((channel) => linearToSrgb(srgbToLinear(channel)).toString(16).padStart(2, '0'))
    .join('');
  return `#${hex}`;
}
