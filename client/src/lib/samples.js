/**
 * Invented sample cards for the logged-out landing page.
 *
 * These are made up, deliberately. A stranger arriving at the site sees an
 * explainer and some samples — never other people's reading. If you are ever
 * tempted to make this "more realistic" by pulling live posts, that is exactly
 * the discovery surface the project does not have (see the About page and
 * docs/decision-records/0002).
 */
const BOOK_A = {
  id: 'demo-a',
  tittel: 'Kransen',
  forfattarar: ['Sigrid Undset'],
  sider: 320,
  omslag: null,
  blurhash: null,
};

const BOOK_B = {
  id: 'demo-b',
  tittel: 'Is-slottet',
  forfattarar: ['Tarjei Vesaas'],
  sider: 216,
  omslag: null,
  blurhash: null,
};

function account(name, handle, domain) {
  return {
    id: `demo-${handle}`,
    acct: `${handle}@${domain}`,
    username: handle,
    display_name: name,
    url: `https://${domain}/user/${handle}`,
    avatar: null,
    emojis: [],
  };
}

const READER = account('Åsta', 'aasta', 'bookwyrm.social');
const OTHER = account('Jon', 'jon', 'bokwyrm.example');

function status(id, created, extra = {}) {
  return {
    id,
    uri: `https://bookwyrm.social/user/aasta/review/${id}`,
    url: `https://bookwyrm.social/user/aasta/review/${id}`,
    created_at: created,
    account: READER,
    content: '',
    sensitive: false,
    spoiler_text: '',
    favourited: false,
    reblogged: false,
    favourites_count: 3,
    reblogs_count: 1,
    media_attachments: [],
    emojis: [],
    ...extra,
  };
}

const now = Date.now();
const hoursAgo = (hours) => new Date(now - hours * 3600_000).toISOString();

export const SAMPLES = [
  {
    id: 'sample-review',
    demo: true,
    status: status('1', hoursAgo(3)),
    core: status('1', hoursAgo(3)),
    boostedBy: null,
    book: BOOK_A,
    enrichment: {
      slag: 'omtale',
      tittel: 'Eit år i eit menneskeliv',
      vurdering: 4.5,
      innhald:
        '<p>Undset skriv middelalderen som om ho hadde vore der sjølv, og likevel er det aldri kulissane som ber boka. Det er Kristin.</p>',
      sitat: null,
      posisjon: null,
      sluttposisjon: null,
      posisjonsmodus: 'side',
      status: null,
      sensitiv: false,
      aatvaring: null,
      bok: 'demo-a',
      kjelde: 'https://bookwyrm.social/user/aasta/review/1',
    },
  },
  {
    id: 'sample-rating',
    demo: true,
    status: status('2', hoursAgo(9)),
    core: status('2', hoursAgo(9)),
    boostedBy: null,
    book: BOOK_B,
    enrichment: {
      slag: 'vurdering',
      tittel: null,
      vurdering: 5,
      innhald: null,
      sitat: null,
      posisjon: null,
      sluttposisjon: null,
      posisjonsmodus: 'side',
      status: null,
      sensitiv: false,
      aatvaring: null,
      bok: 'demo-b',
      kjelde: 'https://bookwyrm.social/user/aasta/rating/2',
    },
  },
  {
    id: 'sample-quotation',
    demo: true,
    status: status('3', hoursAgo(14)),
    core: status('3', hoursAgo(14)),
    boostedBy: null,
    book: BOOK_B,
    enrichment: {
      slag: 'sitat',
      tittel: null,
      vurdering: null,
      innhald: null,
      sitat: '<p>Ho stod og såg inn i den store, blanke veggen av is, og ho visste at ho kom til å gå inn.</p>',
      posisjon: 41,
      sluttposisjon: null,
      posisjonsmodus: 'side',
      status: null,
      sensitiv: false,
      aatvaring: null,
      bok: 'demo-b',
      kjelde: 'https://bookwyrm.social/user/aasta/quotation/3',
    },
  },
  {
    id: 'sample-comment',
    demo: true,
    status: status('4', hoursAgo(20)),
    core: status('4', hoursAgo(20)),
    boostedBy: OTHER,
    book: BOOK_A,
    enrichment: {
      slag: 'kommentar',
      tittel: null,
      vurdering: null,
      innhald: '<p>Midtpartiet drar seg, men eg mistenkjer at det er meininga.</p>',
      sitat: null,
      posisjon: 143,
      sluttposisjon: null,
      posisjonsmodus: 'side',
      status: null,
      sensitiv: false,
      aatvaring: null,
      bok: 'demo-a',
      kjelde: 'https://bookwyrm.social/user/aasta/comment/4',
    },
  },
  {
    id: 'sample-status',
    demo: true,
    status: status('5', hoursAgo(26)),
    core: status('5', hoursAgo(26)),
    boostedBy: null,
    book: BOOK_B,
    enrichment: {
      slag: 'lesestatus',
      tittel: null,
      vurdering: null,
      innhald: null,
      sitat: null,
      posisjon: null,
      sluttposisjon: null,
      posisjonsmodus: 'side',
      status: 'ferdig',
      sensitiv: false,
      aatvaring: null,
      bok: 'demo-b',
      kjelde: 'https://bookwyrm.social/user/aasta/generatednote/5',
    },
  },
];
