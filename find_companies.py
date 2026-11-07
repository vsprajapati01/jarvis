#!/usr/bin/env python3
"""
Jarvis - find companies and make a list.
No API key needed. Uses Bing's public web search, which works
without a key, and saves the results to a CSV file.

Command in Jarvis (text, voice, or GUI):
    find companies hiring data analysts in USA
    find companies data scientist new grad remote
    find jobs machine learning engineer new grad

What it does:
- Searches the web for the query you gave.
- Pulls out the company / job titles and links from the results.
- Saves a list to companies-YYYY-MM-DD-HHMM.csv in the jarvis folder.
- Prints the list back to you, so you can review it.

It does NOT apply, submit, or message anyone. That click stays yours.
It also does NOT invent companies - every row comes from a real
search result, with its link. If the search returns nothing, it says so.
"""
import csv
import datetime
import html
import os
import re
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))


def _decode_bing_link(link):
    """Bing wraps results in bing.com/ck/a?u=a1<base64 real url>.
    Decode it back to the real link, so the saved list is usable."""
    if "/ck/a" in link and "u=" in link:
        try:
            import base64
            encoded = urllib.parse.unquote(link.split("u=", 1)[1].split("&")[0])
            if encoded.startswith("a1"):
                encoded = encoded[2:]
            encoded += "=" * (-len(encoded) % 4)
            return base64.urlsafe_b64decode(encoded).decode("utf-8", errors="ignore")
        except Exception:
            return link
    return link


def search_web(query, count=20):
    """Search Yahoo (no key needed), return [(title, link, snippet), ...].
    Falls back to Bing if Yahoo returns nothing."""
    for engine in ("yahoo", "bing"):
        results = _search_one(query, engine, count)
        if results:
            return results, ""
    return [], "No results found. Try different words."


def _search_one(query, engine, count):
    if engine == "yahoo":
        url = "https://search.yahoo.com/search?p=" + urllib.parse.quote(query)
        pattern = (r'<a[^>]*href="(https://r\.search\.yahoo\.com/[^"]*?/RU=([^/"]+?)/RK=[^"]*)"[^>]*>(.*?)</a>')
    else:
        url = "https://www.bing.com/search?q=" + urllib.parse.quote(query)
        pattern = (r'<li class="b_algo".*?<h2><a[^>]*href="([^"]+)"[^>]*>(.*?)</a></h2>.*?(?:<p[^>]*>(.*?)</p>)?')
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            page = r.read().decode("utf-8", errors="ignore")
    except Exception:
        return []
    results = []
    for m in re.finditer(pattern, page, re.S):
        if engine == "yahoo":
            link = urllib.parse.unquote(m.group(2))
            title = re.sub(r"<[^>]+>", "", html.unescape(m.group(3))).strip()
            snippet = ""
        else:
            link = _decode_bing_link(html.unescape(m.group(1)))
            title = re.sub(r"<[^>]+>", "", html.unescape(m.group(2))).strip()
            snippet = re.sub(r"<[^>]+>", "", html.unescape(m.group(3) or "")).strip()
        # Yahoo titles start with a URL slug + breadcrumb - drop a leading
        # slug token (hyphens, no spaces) and anything before the last "›".
        if "›" in title:
            title = title.rsplit("›", 1)[-1].strip()
        first = title.split(" ", 1)[0] if " " in title else ""
        if first and "-" in first and len(first) > 8 and first.lower() not in title[1:].lower():
            title = title[len(first):].strip()
        if (title and link.startswith("http") and "yahoo.com" not in link
                and "uservoice" not in link and "bing.com" not in link
                and title.lower() != "suggestions"
                and link not in [r[1] for r in results] and len(title) > 10):
            results.append((title, link, snippet))
        if len(results) >= count:
            break
    return results


def find_companies(query, count=20):
    """Search, save a CSV list, return (rows, filename, error)."""
    query = query.strip()
    if not query:
        return [], "", "Tell me what to find, like: find companies hiring data analysts in USA"
    results, err = search_web(query, count=count)
    if err:
        return [], "", err
    if not results:
        return [], "", f"No results found for '{query}'. Try different words."
    stamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M")
    filename = os.path.join(HERE, f"companies-{stamp}.csv")
    with open(filename, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["#", "Title / Company", "Link", "Notes"])
        for i, (title, link, snippet) in enumerate(results, 1):
            w.writerow([i, title, link, snippet])
    return results, filename, ""


def format_list(results):
    lines = [f"Found {len(results)} results:"]
    for i, (title, link, _snippet) in enumerate(results, 1):
        lines.append(f"{i}. {title} - {link}")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "data analyst companies hiring new graduates USA"
    rows, filename, err = find_companies(q)
    if err:
        print(err)
    else:
        print(format_list(rows))
        print(f"\nSaved to: {filename}")
