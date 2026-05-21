---
title: Blog
lang: en
lang_pair_url: /blog-ja/
permalink: /blog/
---

<h1 style="text-align:center; font-weight:800; font-size:3em; margin-top:1em;">Blog</h1>
<p style="text-align:center; color:#888; margin-top:-0.5em;">Scattered Thoughts</p>

{% assign lang_posts = site.posts | where: "lang", "en" %}
{% for post in lang_posts %}
  <article style="margin: 3em 0;">
    <h2 style="font-weight:800; margin-bottom:0.2em;">
      <a href="{{ post.url | relative_url }}" style="color:inherit; text-decoration:none;">{{ post.title | escape }}</a>
    </h2>
    <p style="color:#999; font-style:italic; margin-top:0;">Posted on {{ post.date | date: "%B %-d, %Y" }}</p>
    <div style="color:#333;">
      {{ post.excerpt | strip_html | strip | truncate: 280 }}
      <strong><a href="{{ post.url | relative_url }}">[Read More]</a></strong>
    </div>
  </article>
  {% unless forloop.last %}<hr style="border:none; border-top:1px solid #eee;"/>{% endunless %}
{% endfor %}

{% if lang_posts.size == 0 %}
<p style="text-align:center; color:#999; margin: 4em 0;">No posts yet.</p>
{% endif %}
