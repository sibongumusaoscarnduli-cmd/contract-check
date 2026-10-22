# Deployment

The `docs/` folder is a static project overview and sample report. It is suitable for GitHub Pages and does not need a server. The Python CLI and fixture API run locally and are not deployed; this keeps the demo safe and avoids exposing a writable sample API.

To preview the page from the project root:

```sh
python3 -m http.server 8080 --directory docs
```

Open `http://127.0.0.1:8080`. To publish with GitHub Pages, open the repository's **Settings → Pages**, choose **Deploy from a branch**, select `main` and `/docs`, then save. GitHub will serve the static project page from that folder. Run the Python test suite locally with `python3 -m unittest discover -v` before publishing code changes.
