# Thomas Dullien / Halvar Flake website

This is a Quarto source repository for `https://thomasdullien.github.io/`.

## Local development

Install Quarto, then run:

```sh
quarto preview
```

Render the static site into `docs/` with:

```sh
quarto render
```

## GitHub Pages publishing

The workflow in `.github/workflows/render-site.yml` renders the site on pushes
to `main`, commits the generated HTML under `docs/`, and deploys that rendered
directory through GitHub Pages Actions.

In the GitHub repository settings, configure Pages with:

- Source: `GitHub Actions`

This keeps the source and rendered site in one repository while avoiding the
GitHub Pages limitation that commits made by the default `GITHUB_TOKEN` do not
trigger branch-based Pages builds.

Posts should be added as one directory per post, for example
`posts/2026-06-23-example/index.qmd`. The Writing page lists posts with this
front matter in `posts/index.qmd`:

```yaml
listing:
  contents: "*/index.qmd"
  type: default
  sort: "date desc"
  categories: true
  feed: true
```

The homepage shows recent posts with:

```yaml
listing:
  contents: "posts/*/index.qmd"
  type: default
  sort: "date desc"
  max-items: 6
  feed: true
```

## Interactive and mathematical posts

Use `_templates/interactive-post.qmd` as a starting point for posts that need
MathJax and Observable JS interactivity.
