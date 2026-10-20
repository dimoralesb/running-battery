// check-contrast.mjs — parse DESIGN.md's token block, resolve both themes, check every pair.
// WCAG formula copied verbatim from design-for-ai palette.mjs (luminance + contrast).
// Exit 2 if any pair misses its target; exit 3 if a required token is missing.
import { readFileSync } from "node:fs";

const md = readFileSync(process.argv[2], "utf8");
const css = md.match(/```css\n([\s\S]*?)```/)[1];
const block = (sel) => {
  const i = css.indexOf(sel + " {");
  const body = css.slice(i + sel.length + 2, css.indexOf("\n}", i));
  const out = {};
  for (const m of body.replace(/\/\*[\s\S]*?\*\//g, "").matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)) out[m[1]] = m[2].trim();
  return out;
};
const dark = block(":root");
const light = { ...dark, ...block(':root[data-theme="light"]') };

const resolve = (t, name, seen = 0) => {
  const v = t[name];
  if (v === undefined) throw new Error(`missing ${name}`);
  const m = v.match(/^var\((--[\w-]+)\)$/);
  return m ? resolve(t, m[1], seen + 1) : v;
};
const parseHex = (s) => { const v = s.replace("#", ""); return [0, 2, 4].map((i) => parseInt(v.slice(i, i + 2), 16) / 255); };
function luminance(rgb) {
  const [r, g, b] = rgb.map((x) => { const c = Math.min(1, Math.max(0, x)); return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
function contrast(a, b) { const [x, y] = [luminance(a), luminance(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); }

const required = ["--background", "--surface", "--text", "--accent-solid", "--text-xs", "--text-sm", "--text-base",
  "--text-lg", "--text-xl", "--text-2xl", "--text-3xl", "--text-4xl"];

// [fg, bg, target, what]
const TEXT = 4.5, LARGE = 3, UI = 3;
const pairs = [
  // page text
  ["--text", "--background", TEXT, "body text on page"],
  ["--text", "--surface", TEXT, "text on surface"],
  ["--text", "--surface-hover", TEXT, "text on hover fill (buttons only)"],
  ["--text-secondary", "--background", TEXT, "secondary text, tabs, play bar"],
  ["--text-secondary", "--surface", TEXT, "secondary on surface"],
  ["--text-secondary", "--surface-hover", TEXT, "secondary on hover fill"],
  ["--accent-on-solid", "--accent-solid", TEXT, "accent-on-solid on accent-solid"],
  // plates (both themes)
  ["--plate-text", "--plate", TEXT, "score bug names, player name"],
  ["--plate-text-2", "--plate", TEXT, "moment · clock, caption, position, flag"],
  ["--plate-text", "--plate-raised", TEXT, "score on score cell"],
  ["--charge", "--plate", TEXT, "battery % on plate"],
  // team text
  ["--on-team", "--home-on-dark", TEXT, "shirt number on home marker"],
  ["--on-team", "--away-on-dark", TEXT, "shirt number on away marker"],
  ["--on-pitch", "--grass", TEXT, "labels on grass"],
  ["--on-pitch", "--grass-alt", TEXT, "labels on grass stripe"],
  // non-text (WCAG 1.4.11)
  ["--charge", "--plate", UI, "battery fill vs empty part (plate) / shell vs plate"],
  ["--charge-band", "--plate", UI, "analyst band brackets on plate"],
  ["--accent-solid", "--background", UI, "page gauge fill/shell vs page"],
  ["--accent-solid", "--surface", UI, "page gauge fill/shell vs surface"],
    ["--gauge-band", "--surface", UI, "analyst band on page"],
  ["--control-edge", "--background", UI, "outlined button edge (Replay, Next)"],
  ["--focus", "--background", UI, "focus ring"],
  ["--text", "--background", UI, "selected-tab underline"],
  ["--home-on-dark", "--plate", UI, "home chip on score bug"],
  ["--away-on-dark", "--plate", UI, "away chip on score bug"],
  ["--home", "--background", UI, "home dot / chart line on page"],
  ["--away", "--background", UI, "away dot / chart line on page"],
  ["--home", "--surface", UI, "home dot on surface"],
  ["--away", "--surface", UI, "away dot on surface"],
  ["--home-on-dark", "--grass", UI, "home marker on grass"],
  ["--home-on-dark", "--grass-alt", UI, "home marker on stripe"],
  ["--away-on-dark", "--grass", UI, "away marker on grass"],
  ["--away-on-dark", "--grass-alt", UI, "away marker on stripe"],
  ["--trail", "--grass", UI, "run trail / star ring on grass"],
  ["--warning", "--grass", UI, "hardest-minutes ring on grass"],
  ["--warning", "--grass-alt", UI, "hardest-minutes ring on stripe"],
  ["--charge", "--grass", UI, "pitch battery icon outline on grass"],
];

let fails = 0;
const lines = [];
for (const [mode, t] of [["dark", dark], ["light", light]]) {
  for (const r of required) { try { resolve(t, r); } catch (e) { console.error(`[${mode}] ${e.message}`); process.exit(3); } }
  for (const [fg, bg, target, what] of pairs) {
    const c = contrast(parseHex(resolve(t, fg)), parseHex(resolve(t, bg)));
    const ok = c >= target;
    if (!ok) fails++;
    lines.push(`${ok ? "PASS" : "FAIL"}  [${mode}] ${fg} on ${bg}: ${c.toFixed(2)}:1 (target ${target}) — ${what}`);
  }
}
console.log(lines.join("\n"));
console.log(`\nrequired tokens resolved in both themes: ${required.join(" ")}`);
console.log(`${lines.length - fails}/${lines.length} pairs pass`);
if (fails) process.exit(2);
