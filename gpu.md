---
layout: page
title: GPU 与性能剖析
display_title: GPU 与性能剖析
description: 一个系列的入口。每条都记着我实测的数字、测试环境和结论的适用条件；没测过的就写「没测过」，不留着好看。
permalink: /gpu/
---

{% assign gpu = site.data.gpu %}
{% assign total = 0 %}
{% assign done = 0 %}
{% for sec in gpu %}
  {% for it in sec.items %}
    {% assign total = total | plus: 1 %}
    {% if it.status == 'done' or it.status == 'ready' %}{% assign done = done | plus: 1 %}{% endif %}
  {% endfor %}
{% endfor %}
{% assign todo = total | minus: done %}
{% assign pct = done | times: 100 | divided_by: total %}

<div class="rm-summary">
  <div class="rm-stat is-done"><b>{{ done }}</b><span>已放出</span></div>
  <div class="rm-stat"><b>{{ todo }}</b><span>待写</span></div>
  <div class="rm-stat"><b>{{ total }}</b><span>计划总数</span></div>
  <div class="rm-stat"><b>{{ pct }}%</b><span>完成度</span></div>
</div>
<div class="rm-progress" role="img" aria-label="完成度 {{ pct }}%"><i style="width: {{ pct }}%"></i></div>

{% for sec in gpu %}
{% assign sdone = 0 %}
{% for it in sec.items %}{% if it.status == 'done' or it.status == 'ready' %}{% assign sdone = sdone | plus: 1 %}{% endif %}{% endfor %}
<details class="rm-sec" id="{{ sec.section | slugify }}"{% if sdone > 0 %} open{% endif %}>
  <summary>
    <span class="rm-title">{{ sec.section }}</span>
    <span class="rm-note">{{ sec.note }}</span>
    <span class="rm-count">{{ sdone }}/{{ sec.items.size }}</span>
  </summary>
  <ul class="rm-list">
    {% for it in sec.items %}
    <li class="rm-item">
      {% if it.status == 'done' %}
      <a class="rm-row rm-done" href="{{ '/' | append: it.post_slug | append: '/' | relative_url }}">
        <span class="rm-a">{{ it.title }}</span>
        <span class="rm-d">{{ it.desc }}</span>
        <span class="rm-tag">已发布</span>
      </a>
      {% elsif it.status == 'ready' %}
      <a class="rm-row rm-doc" href="{{ '/' | append: it.path | relative_url }}">
        <span class="rm-a">{{ it.title }}</span>
        <span class="rm-d">{{ it.desc }}</span>
        <span class="rm-tag">仓库内</span>
      </a>
      {% else %}
      <div class="rm-row rm-planned">
        <span class="rm-a">{{ it.title }}</span>
        <span class="rm-d">{{ it.desc }}</span>
        <span class="rm-tag">待写</span>
      </div>
      {% endif %}
    </li>
    {% comment %}
      这一行必须带括号。Liquid 里 and/or 是从右往左求值的,写成
      `it.key and it.status == 'done' or it.key and it.status == 'ready'`
      会被解析成 `it.key and (it.status == 'done' or (it.key and it.status == 'ready'))`
      —— 对 planned 条目只要 key 非空就会漏进来说明行。先赋值再判,最稳。
    {% endcomment %}
    {% assign show_key = false %}
    {% if it.key %}{% if it.status == 'done' or it.status == 'ready' %}{% assign show_key = true %}{% endif %}{% endif %}
    {% if show_key %}
    <li class="rm-item rm-item-key"><p class="rm-key">{{ it.key }}</p></li>
    {% endif %}
    {% endfor %}
  </ul>
</details>
{% endfor %}

<div class="rm-foot">
  <p>这个系列只做一件事：<strong>把别人报的性能数字当成待验证的断言，而不是事实。</strong>一份性能演讲里的每个倍数都隐含着一组硬件、一个规模和一种测法；这三样没对齐，数字就不能搬。所以这里每条都写着测试环境，并且标出哪些是我实测的、哪些是实测之上的推断、哪些没验证。</p>
  <p>标「待写」的条目是我想验证但还没跑出数字的，所以不给链接 —— 我不想让你点进一个空页面或者一篇只有结论没有数据的文章。</p>
  <p>写这个系列的规矩单独立了一份体例：<a href="{{ '/assets/blog/_tools/CONVENTIONS-GPU.md' | relative_url }}">CONVENTIONS-GPU.md</a>。里面最贵的一条是<strong>每个性能实验至少跑两遍</strong> —— 这条规矩是复跑救回来的：我原本写好的一条「自旋锁快 34.8%」，第二遍只剩 5.2%。</p>
</div>
