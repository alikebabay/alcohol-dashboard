// renderDeleteButtons.js

export const renderDeleteBrandButton = (brand, esc) => `
  <button data-del-brand="${esc(brand)}"
          style="font-size:11px; padding:2px 6px;"
          title="Delete brand">🗑</button>
`;

export const renderDeleteSeriesButton = (brand, series, esc) => `
  <button data-del-series
          data-brand="${esc(brand)}"
          data-series="${esc(series)}"
          style="font-size:11px; padding:1px 6px; margin-left:6px;"
          title="Delete series">🗑</button>
`;

export const renderDeleteCanonicalButton = (name, esc) => `
  <button data-del-canonical="${esc(name)}"
          style="font-size:11px; padding:1px 6px; margin-left:6px;"
          title="Delete canonical">🗑</button>
`;

export const renderDeleteBrandAliasButton = (brand, alias, esc) => `
  <button data-del-brand_alias="${esc(alias)}"
          data-brand="${esc(brand)}"
          style="font-size:11px; padding:1px 6px; margin-left:4px;"
          title="Delete brand alias">🗑</button>
`;
