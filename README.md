# Selfie Studio

English | [简体中文](README.zh.md)

A wardrobe & scene library that serves the character selfie flow. Upload outfit
pieces (tops, bottoms, dresses, footwear, accessories) and scenes from a WebUI
page; the character picks them up as extra reference images whenever a selfie
calls for them.

![Version](https://img.shields.io/badge/version-1.0.0-blue)

## Features

- **Wardrobe** — upload and curate outfit pieces grouped by category
  (tops / bottoms / dresses / footwear / accessories), with notes, an
  in-use switch, search, and filters.
- **Scenes** — upload places and environments (indoor, urban, nature, …).
- **Test shot** — pick outfits and a scene, write a pose, and render a
  preview selfie immediately with the default image model. Also produces
  the ready-to-send `<dressup>` tag.
- **Catalog feed** — shows exactly what gets injected into the character's
  system prompt each turn.

The page follows the parent WebUI theme (light / dark) and language
(zh / en) automatically; there is no in-page toggle for either.

## How it works

- **LLM integration** — an `on.llm_request` hook appends the enabled catalog
  (names, categories, notes) to the system prompt, and the plugin registers a
  `<dressup>` message tag:

  ```xml
  <dressup outfit="白色帆布鞋,牛仔外套" scene="咖啡厅">坐在落地窗边回眸</dressup>
  ```

  The tag resolves the names against the library, loads the persona reference
  image first (outfits and scenes follow), and renders via the default image
  model's img2img — the same contract as the builtin `<selfie>` tag. When the
  catalog is empty or disabled, the character falls back to plain `<selfie>`.

- **Reference merging (optional)** — with *Merge outfit references* enabled,
  multiple outfits are composed into a single labelled contact sheet with
  Pillow before sending (scenes stay separate), so image models with a
  limited reference count still see every piece.

- **Requirement** — the active persona must have a reference image set, and a
  default image model must be configured.

## Storage

Runtime data lives under the plugin data directory (`ctx.get_plugin_data_dir()`)
— never next to the plugin source:

```
data/plugin_data/kira-ai-plugin-selfie-studio/uploads/
├── wardrobe/<id>.<ext>   # outfit images
├── scenes/<id>.<ext>     # scene images
└── library.json          # manifest (atomic writes)
```

The library therefore survives plugin reinstall or deletion.
Accepted formats: PNG / JPEG / WebP, up to 10 MB each, 200 items max.

## Plugin settings

- **Announce wardrobe to the character** — append the catalog to the system
  prompt each turn (default on).
- **Merge outfit references** — compose multiple selected outfits into one
  labelled sheet before sending (default off).

## Endpoints

| Method | Path | Purpose |
| ------ | ---- | ------- |
| GET | `/api/plugin/kira-ai-plugin-selfie-studio/items` | list library |
| POST | `…/items/upload` | multipart upload (file, kind, name, category, note) |
| POST | `…/items/update` | rename / recategorize / note / enable |
| POST | `…/items/delete` | remove item and file |
| GET | `…/image/{id}` | serve an item image |
| GET | `…/catalog` | preview the injected catalog text |
| POST | `…/testshot` | render a preview selfie |
