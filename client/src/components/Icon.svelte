<script>
  /**
   * Every icon in the app, as one inline SVG component.
   *
   * Line icons at 20–22px, `stroke-width: 1.5`, round caps — no icon font and
   * no icon library. They are drawn in `currentColor`, so a button colours its
   * icon by colouring itself; nothing here needs to know about brass or dim.
   *
   * Icons are decorative by default (`aria-hidden`): the button around them
   * carries the label. Pass `label` only when an icon is the sole content of
   * something that is not a button.
   */
  let { name, size = 20, label = null, stroke = 1.5 } = $props();

  // Each entry is a viewBox plus the shapes that make up the glyph.
  const SHAPES = {
    back: { box: 20, paths: ['M12 4 6 10l6 6'] },
    forward: { box: 20, paths: ['M7 4l6 6-6 6'] },
    close: { box: 20, paths: ['M5 5l10 10', 'M15 5 5 15'] },
    reply: { box: 20, paths: ['M8 4 3.5 8.5 8 13', 'M3.5 8.5h7a5.5 5.5 0 0 1 5.5 5.5v2'] },
    boost: { box: 20, paths: ['M4 7h9l-2.5-2.5', 'M16 13H7l2.5 2.5'] },
    share: { box: 20, paths: ['M10 4v9', 'M6.5 9.5 10 13l3.5-3.5', 'M5 16h10'] },
    hidden: {
      box: 20,
      paths: ['M2.5 10s3-5 7.5-5 7.5 5 7.5 5-3 5-7.5 5-7.5-5-7.5-5z', 'M4 16 16 4'],
    },
    shown: {
      box: 20,
      paths: ['M2.5 10s3-5 7.5-5 7.5 5 7.5 5-3 5-7.5 5-7.5-5-7.5-5z'],
      circles: [{ cx: 10, cy: 10, r: 2 }],
    },
    bang: { box: 20, paths: ['M10 5v6', 'M10 14.5v.5'] },
    book: {
      box: 22,
      paths: ['M4 4.5v13c3-1.2 5-1.2 7 0 2-1.2 4-1.2 7 0v-13c-3-1.2-5-1.2-7 0-2-1.2-4-1.2-7 0z', 'M11 4.5v13'],
    },
    shelf: { box: 22, paths: ['M3 17h16', 'M6 17V7h3v10', 'M12 17V9h3v8'] },
    filter: { box: 22, paths: ['M4 5h14l-5.5 6.5V18l-3-1.6v-4.9z'] },
    sliders: {
      box: 22,
      paths: ['M4 7h14', 'M4 15h14'],
      circles: [
        { cx: 9, cy: 7, r: 2.2 },
        { cx: 14, cy: 15, r: 2.2 },
      ],
    },
    copy: {
      box: 20,
      paths: ['M12.5 4.5H5.5A1 1 0 0 0 4.5 5.5v7'],
      rects: [{ x: 7, y: 7, width: 9, height: 9, rx: 1.5 }],
    },
    check: { box: 20, paths: ['M3 10.5 7.5 15 17 5.5'] },
    cross: { box: 20, paths: ['M5 5l10 10', 'M15 5 5 15'] },
    globe: { box: 16, paths: ['M8 2.5v11', 'M2.5 8h11'], circles: [{ cx: 8, cy: 8, r: 5.5 }] },
    external: { box: 20, paths: ['M8 4h8v8', 'M16 4 8.5 11.5', 'M13 12v4H4V7h4'] },
  };

  const glyph = $derived(SHAPES[name] || SHAPES.book);
</script>

<svg
  width={size}
  height={size}
  viewBox="0 0 {glyph.box} {glyph.box}"
  fill="none"
  stroke="currentColor"
  stroke-width={stroke}
  stroke-linecap="round"
  stroke-linejoin="round"
  role={label ? 'img' : 'presentation'}
  aria-hidden={label ? undefined : 'true'}
  aria-label={label || undefined}
>
  {#each glyph.paths || [] as d, index (index)}
    <path {d} />
  {/each}
  {#each glyph.circles || [] as circle, index (index)}
    <circle cx={circle.cx} cy={circle.cy} r={circle.r} />
  {/each}
  {#each glyph.rects || [] as rect, index (index)}
    <rect x={rect.x} y={rect.y} width={rect.width} height={rect.height} rx={rect.rx} />
  {/each}
</svg>

<style>
  svg {
    display: block;
    flex: none;
  }
</style>
