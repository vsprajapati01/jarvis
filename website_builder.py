#!/usr/bin/env python3
"""Jarvis v10 - clean website builder.

Builds one small, clean, static website for a business.
No framework, no JavaScript, no animations, no stock photos,
no extra sections. One HTML file, plain CSS, system font.

Style, on purpose:
  white background, dark text, one quiet accent colour,
  plenty of space, readable type. Clean and premium,
  nothing eye-catching for its own sake.

Input: business name, what it does, location, and up to
6 menu / service items. Output: index.html in
websites/<slug>/, plus a short summary.

Usage:
    from website_builder import build_website
    path, summary = build_website(
        name="Ember and Salt",
        description="A small restaurant in Brickell, Miami. Simple food, deep flavour.",
        location="Brickell Avenue, Miami",
        items=[("Margherita Pizza", "Tomato, mozzarella, basil.", "$14"),
               ("House Salad", "Greens, lemon, olive oil.", "$9")],
    )
"""
import os
import re

_BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "websites")


def _slug(name):
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "website"


def _escape(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def build_website(name, description, location="", items=None, contact=""):
    """Build the site. Returns (folder_path, summary)."""
    items = items or []
    slug = _slug(name)
    folder = os.path.join(_BASE, slug)
    os.makedirs(folder, exist_ok=True)

    rows = ""
    for item_name, item_desc, item_price in items[:6]:
        rows += (
            f"      <div class=\"item\">\n"
            f"        <div><h3>{_escape(item_name)}</h3>"
            f"<p>{_escape(item_desc)}</p></div>\n"
            f"        <div class=\"price\">{_escape(item_price)}</div>\n"
            f"      </div>\n"
        )
    menu = f"    <section>\n      <h2>Menu</h2>\n{rows}    </section>\n" if rows else ""
    location_html = f"<p class=\"meta\">{_escape(location)}</p>\n" if location else ""
    contact_html = f"<p class=\"meta\">Contact: {_escape(contact)}</p>\n" if contact else ""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_escape(name)}</title>
<style>
  body {{ margin: 0; font-family: system-ui, -apple-system, "Segoe UI", sans-serif; color: #1a1a1a; background: #ffffff; line-height: 1.6; }}
  main {{ max-width: 640px; margin: 0 auto; padding: 64px 24px; }}
  h1 {{ font-size: 40px; line-height: 1.2; margin: 0 0 16px; font-weight: 600; }}
  h2 {{ font-size: 20px; margin: 48px 0 16px; font-weight: 600; border-top: 1px solid #e5e5e5; padding-top: 32px; }}
  h3 {{ font-size: 17px; margin: 0; font-weight: 600; }}
  p {{ margin: 0 0 16px; color: #444444; }}
  .meta {{ font-size: 14px; color: #777777; }}
  .item {{ display: flex; justify-content: space-between; gap: 24px; padding: 16px 0; border-top: 1px solid #eeeeee; }}
  .item p {{ margin: 4px 0 0; font-size: 14px; }}
  .price {{ white-space: nowrap; font-weight: 600; }}
  footer {{ margin-top: 64px; font-size: 13px; color: #999999; }}
</style>
</head>
<body>
<main>
  <h1>{_escape(name)}</h1>
  <p>{_escape(description)}</p>
{location_html}{contact_html}{menu}  <footer>Built with Jarvis.</footer>
</main>
</body>
</html>
"""
    path = os.path.join(folder, "index.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    summary = (
        f"Website built for {name}: {path}. "
        f"{len(items)} menu item(s), clean single page, no JavaScript."
    )
    return folder, summary
