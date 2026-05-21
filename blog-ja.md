---
title: ブログ
lang: ja
lang_pair_url: /blog/
permalink: /blog-ja/
---

<h1 style="text-align:center; font-weight:800; font-size:3em; margin-top:1em;">ブログ</h1>
<p style="text-align:center; color:#888; margin-top:-0.5em;">Scattered Thoughts</p>

{% assign lang_posts = site.posts | where: "lang", "ja" %}
{% for post in lang_posts %}
  <article style="margin: 3em 0;">
    <h2 style="font-weight:800; margin-bottom:0.2em;">
      <a href="{{ post.url | relative_url }}" style="color:inherit; text-decoration:none;">{{ post.title | escape }}</a>
    </h2>
    <p style="color:#999; font-style:italic; margin-top:0;">{{ post.date | date: "%Y年%-m月%-d日" }} 投稿</p>
    <div style="color:#333;">
      {{ post.excerpt | strip_html | strip | truncate: 200 }}
      <strong><a href="{{ post.url | relative_url }}">[続きを読む]</a></strong>
    </div>
  </article>
  {% unless forloop.last %}<hr style="border:none; border-top:1px solid #eee;"/>{% endunless %}
{% endfor %}

{% if lang_posts.size == 0 %}
<p style="text-align:center; color:#999; margin: 4em 0;">まだ記事がありません。</p>
{% endif %}
