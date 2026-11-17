---
layout: page
title: CUDA 与 GPU 优化课程序列
display_title: CUDA 与 GPU 优化课程序列
description: 一份按依赖关系排的学习序列。每个入口我都联网核过，标清楚「确认」和「没确认」；讲者身份对着贡献者名单和课程官网核，不按频道更新时间排。
permalink: /courses/
---

{% assign cs = site.data.courses %}
{% assign total = 0 %}
{% assign done = 0 %}
{% for sec in cs %}
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

<div class="rm-foot" style="margin-bottom: 18px;">
  <p>这条序列解决的是<strong>顺序问题</strong>：先建立执行模型，再补系统机制，然后才谈得上测量和优化。跳过前面的站直接看算子优化，看到的是结论，不是能迁移的判断力。</p>
  <p>选择标准是<strong>讲者的一手经验、机制解释、图示与源码、现代架构适用性</strong>，官方原版优先。内容同样合适时优先新版；旧经典保留它解释稳定原理、展示完整优化过程的价值 —— 但会写明它的年代和不再适用的部分。</p>
</div>

{% for sec in cs %}
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
      {% comment %}
        ready 条目分两种：仓库内相对路径（下划线目录链过去会 404，只给路径
        不给链接），以及外部 URL（必须给链接）。它们用**两个字段**区分：
        path / url。不要合成一个字段再用前缀猜 —— 门那边会把 path 当文件名
        去 exists()，混用就会报假问题。
      {% endcomment %}
      <div class="rm-row rm-doc">
        <span class="rm-a">{{ it.title }}</span>
        <span class="rm-d">{{ it.desc }}</span>
        {% if it.url %}
        <span class="rm-tag">外部</span>
        <a class="rm-path" href="{{ it.url }}" rel="noopener">{{ it.url }}</a>
        {% else %}
        <span class="rm-tag">仓库内</span>
        <span class="rm-path">{{ it.path }}</span>
        {% endif %}
      </div>
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
  <p><strong>计数口径：</strong>上面的「已放出」含 <strong>5 篇正文</strong>（五个站各一篇）和 <strong>2 项配套材料</strong>（核验记录、CuTe 布局代数论文入口）。所以 100% 指的是<strong>这条我列出来的序列已经写完并核过</strong>，不是「这些课我都上完了」。待写为 0 表示我不再给自己留没写完的条目 —— 以后要加新站，会先让它作为条目出现，这个数字自然掉下来。</p>
  <p>这份序列最初是为我自己排的：手上是 H800，要做的是把真实 kernel 的瓶颈找出来，所以重点落在<strong>能解释机制、能指出源码位置</strong>的材料上，而不是覆盖面最广的材料上。</p>
  <p>每个外部入口我都<strong>联网抓过一遍</strong>：链接是否可达、标题和讲者是否与标注一致、课表讲次是否对得上。核验记录在仓库里 <code>assets/blog/gpu-course-20261117/LINKS.md</code>（只给路径不给链接，理由见下），正文里也逐条标注。有几处流传较广的说法对不上官方页面，我在对应那一站里写明了<strong>哪一句是错的、官方原文是什么</strong>。</p>
  <p>需要说清楚的边界：我核对的是<strong>官方目录、标题、讲者、材料入口</strong>，没有逐段播放全部课程，也没有逐一操作网站上的交互图。所以「这个链接是那一场」我能负责，「这套课讲得好不好」只能由你自己判断。B 站入口是民间搬运、字幕或讲解，标题里的「官方」「全集」不等于官方发布或完整收录；本书面核验时 B 站对直接抓取返回 412，所以那几条我只标注了它是什么，没有当作已确认的完整收录。</p>
  <p>还有一条：<strong>这条序列不含实验</strong>。它是资源序列，不是实验结果；我实测过的数字都在 <a href="{{ '/gpu/' | relative_url }}">GPU 与性能剖析</a> 那个系列里，两边不要混着看。</p>
  <p><strong>关于「只给路径不给链接」：</strong>仓库内文件在发布前我没法在本地验证它线上可开，链过去等于赌一把；而这个站已经有链接指进 <code>_tools/</code> 结果线上 404 的先例（Jekyll 不发布下划线开头的目录）。所以凡是仓库内的路径，我只写路径，等它真上线了再决定要不要给链接。</p>
</div>
