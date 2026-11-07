/**
 * Typed wrappers around the plugin API bridge.
 *
 * Every helper resolves with the endpoint's ``{ ok, ... }`` payload and
 * rejects with an ``Error`` carrying a human-readable message on failure.
 * Image uploads use a hand-rolled FormData call because the bridge's
 * ``api.upload`` helper cannot carry extra form fields.
 */

const bridge = window.PluginPageContext;

function pluginBase() {
  const ctx = bridge.getContext();
  return `/api/plugin/${encodeURIComponent(ctx.pluginId)}`;
}

async function unwrap(promise) {
  let data;
  try {
    data = await promise;
  } catch (_) {
    throw new Error('Network request failed');
  }
  if (data && data.ok) return data;
  throw new Error((data && (data.error || data.detail)) || 'Request failed');
}

export const api = {
  items() {
    return unwrap(bridge.api.get('items'));
  },

  catalog() {
    return unwrap(bridge.api.get('catalog'));
  },

  update(payload) {
    return unwrap(bridge.api.post('items/update', payload));
  },

  remove(id) {
    return unwrap(bridge.api.post('items/delete', { id }));
  },

  testshot(payload) {
    return unwrap(bridge.api.post('testshot', payload));
  },

  async upload(file, fields) {
    const form = new FormData();
    form.append('file', file);
    for (const [key, value] of Object.entries(fields)) {
      form.append(key, value ?? '');
    }
    return unwrap(fetch(`${pluginBase()}/items/upload`, {
      method: 'POST',
      credentials: 'same-origin',
      body: form,
    }).then((res) => res.json()));
  },

  imageURL(item) {
    return `${pluginBase()}/image/${encodeURIComponent(item.id)}?v=${item.updated_at}`;
  },
};
