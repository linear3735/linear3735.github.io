(() => {
  const article = document.querySelector('.post-content');
  if (article) {
    // Keep the Markdown's original contents list as a no-JavaScript fallback.
    const headings = [...article.querySelectorAll('h2, h3')].filter(h => h.id && h.textContent.trim() !== '目录');
    const navs = [...document.querySelectorAll('[data-toc]')];
    navs.forEach(nav => {
      const list = document.createElement('ol');
      let section;
      headings.forEach(heading => {
        const item = document.createElement('li');
        const link = document.createElement('a');
        link.href = `#${encodeURIComponent(heading.id)}`;
        link.textContent = heading.textContent;
        link.dataset.heading = heading.id;
        item.append(link);
        if (heading.tagName === 'H2' || !section) {
          list.append(item);
          section = item;
        } else {
          let children = section.querySelector('ol');
          if (!children) {
            children = document.createElement('ol');
            section.append(children);
          }
          children.append(item);
        }
      });
      nav.append(list);
    });
    if (headings.length && navs.length) {
      const oldTitle = [...article.querySelectorAll('h2')].find(h => h.textContent.trim() === '目录');
      if (oldTitle?.nextElementSibling?.tagName === 'UL') {
        oldTitle.nextElementSibling.hidden = true;
        oldTitle.hidden = true;
      }
      document.querySelector('.mobile-toc').hidden = false;
    }
    article.querySelectorAll('table').forEach((table, index) => {
      const wrapper = document.createElement('div');
      wrapper.className = 'table-scroll';
      wrapper.tabIndex = 0;
      wrapper.setAttribute('role', 'region');
      wrapper.setAttribute('aria-label', `表格 ${index + 1}，可横向滚动`);
      table.before(wrapper);
      wrapper.append(table);
    });
    const links = [...document.querySelectorAll('[data-heading]')];
    const progress = document.getElementById('reading-progress');
    const percent = document.getElementById('reading-percent');
    let queued = false;
    function updateReading() {
      queued = false;
      const offset = document.querySelector('.site-header').offsetHeight + 28;
      let active = headings[0];
      for (const heading of headings) {
        if (heading.getBoundingClientRect().top > offset) break;
        active = heading;
      }
      links.forEach(link => {
        const current = link.dataset.heading === active?.id;
        if (current) link.setAttribute('aria-current', 'location');
        else link.removeAttribute('aria-current');
        link.closest('li').classList.remove('active');
      });
      links.filter(link => link.hasAttribute('aria-current')).forEach(link => {
        let item = link.closest('li');
        item.classList.add('active');
        const parent = item.parentElement.closest('li');
        if (parent) parent.classList.add('active');
      });
      const bounds = article.getBoundingClientRect();
      const distance = Math.max(1, bounds.height - (window.innerHeight - offset));
      const value = Math.round(Math.min(1, Math.max(0, (offset - bounds.top) / distance)) * 100);
      progress.style.width = `${value}%`;
      percent.textContent = `${value}%`;
    }
    function scheduleReading() {
      if (!queued) {
        queued = true;
        requestAnimationFrame(updateReading);
      }
    }
    window.addEventListener('scroll', scheduleReading, { passive: true });
    window.addEventListener('resize', scheduleReading);
    document.querySelector('.mobile-toc')?.addEventListener('toggle', scheduleReading);
    document.querySelector('.mobile-toc nav')?.addEventListener('click', event => {
      if (event.target.closest('a')) event.currentTarget.closest('details').open = false;
    });
    updateReading();
  }

  const form = document.querySelector('.search-form');
  if (!form) return;
  const input = document.getElementById('search-input');
  const status = document.getElementById('search-status');
  const results = document.getElementById('search-results');
  let index;
  let request = 0;
  async function search() {
    const current = ++request;
    const query = input.value.trim();
    results.replaceChildren();
    if (!query) {
      status.textContent = '输入关键词，搜索全部笔记。';
      return;
    }
    status.textContent = '正在搜索…';
    try {
      if (!index) {
        const response = await fetch(form.dataset.index);
        if (!response.ok) throw new Error('Search index unavailable');
        index = await response.json();
      }
      if (current !== request) return;
      const terms = query.toLocaleLowerCase().split(/\s+/);
      const matches = index.filter(post => {
        const text = `${post.title} ${post.tags} ${post.content}`.toLocaleLowerCase();
        return terms.every(term => text.includes(term));
      });
      status.textContent = matches.length ? `找到 ${matches.length} 篇相关笔记` : '没有找到相关笔记，试试其他关键词。';
      matches.forEach(post => {
        const item = document.createElement('article');
        item.className = 'search-result';
        const title = document.createElement('h2');
        const link = document.createElement('a');
        link.href = post.url;
        link.textContent = post.title;
        title.append(link);
        const text = document.createElement('p');
        const start = Math.max(0, post.content.toLocaleLowerCase().indexOf(terms[0]) - 50);
        text.textContent = `${start ? '…' : ''}${post.content.slice(start, start + 190)}${post.content.length > start + 190 ? '…' : ''}`;
        const date = document.createElement('time');
        date.textContent = post.date;
        item.append(title, text, date);
        results.append(item);
      });
    } catch {
      if (current === request) status.textContent = '暂时无法加载搜索，请稍后重试，或从归档浏览。';
    }
  }
  form.addEventListener('submit', event => {
    event.preventDefault();
    const url = new URL(location.href);
    if (input.value.trim()) url.searchParams.set('q', input.value.trim());
    else url.searchParams.delete('q');
    history.replaceState(null, '', url);
    search();
  });
  let timer;
  input.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(search, 180); });
  input.value = new URLSearchParams(location.search).get('q') || '';
  if (input.value) search();
})();
