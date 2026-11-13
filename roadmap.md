---
layout: page
title: 面试算法路线图
display_title: 面试算法路线图
description: 一张可以点着走的算法复习地图。每一条都标着「已发布」或「待写」，写完一条就点亮一条。
permalink: /roadmap/
---

{% assign roadmap = site.data.roadmap %}
{% assign total = 0 %}
{% assign done = 0 %}
{% for sec in roadmap %}
  {% for it in sec.items %}
    {% assign total = total | plus: 1 %}
    {% if it.status == 'done' %}{% assign done = done | plus: 1 %}{% endif %}
  {% endfor %}
{% endfor %}
{% assign todo = total | minus: done %}
{% assign pct = done | times: 100 | divided_by: total %}

<div class="rm-summary">
  <div class="rm-stat is-done"><b>{{ done }}</b><span>已发布</span></div>
  <div class="rm-stat"><b>{{ todo }}</b><span>待写</span></div>
  <div class="rm-stat"><b>{{ total }}</b><span>计划总数</span></div>
  <div class="rm-stat"><b>{{ pct }}%</b><span>完成度</span></div>
</div>
<div class="rm-progress" role="img" aria-label="完成度 {{ pct }}%"><i style="width: {{ pct }}%"></i></div>

{% for sec in roadmap %}
{% assign sdone = 0 %}
{% for it in sec.items %}{% if it.status == 'done' %}{% assign sdone = sdone | plus: 1 %}{% endif %}{% endfor %}
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
      {% elsif it.status == 'planned' %}
      <div class="rm-row rm-planned">
        <span class="rm-a">{{ it.title }}</span>
        <span class="rm-d">{{ it.desc }}</span>
        <span class="rm-tag">待写</span>
      </div>
      {% else %}
      <div class="rm-row rm-todo">
        <span class="rm-a">{{ it.title }}</span>
        <span class="rm-d">{{ it.desc }}</span>
        <span class="rm-tag">待定</span>
      </div>
      {% endif %}
    </li>
    {% endfor %}
  </ul>
</details>
{% endfor %}

<div class="rm-foot">
  <p>这份地图是我自己的复习顺序，不是任何课程的官方目录。选题参考了 labuladong 的算法教程体系（特别是《学习数据结构和算法的框架思维》与《双指针技巧秒杀七道链表题目》两篇），条目名称和分组是我按自己的理解重写的。</p>
  <p>标「待写」的条目已经排好了篇目、但文章还没写，所以这里不给链接——我不想让你点进一个空页面。写一篇点亮一篇，标成「已发布」的才会变成可以点的链接。</p>
  <p>每篇文章的体例是一致的：先讲清这个套路为什么成立，再给出 <strong>Python 3 和 C++ 双语言实现</strong>，配自绘的 SVG 示意图，并把最容易写错的那一行标出来。代码都真跑过，不是看着像对的。</p>
</div>
