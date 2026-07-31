(() => {
  const canonicalUrl = new URL(window.location.pathname, window.location.origin).href;
  const title = document.title.replace(/\s*-\s*Cartas dos Gestores.*$/i, '').trim() || 'Cartas dos Gestores';
  const description = `Análise educativa da carta e dos dados do fundo ${title}, com contexto, estratégia e riscos.`;

  if (!document.querySelector('link[rel="canonical"]')) {
    const canonical = document.createElement('link');
    canonical.rel = 'canonical';
    canonical.href = canonicalUrl;
    document.head.append(canonical);
  }
  if (!document.querySelector('meta[name="description"]')) {
    const meta = document.createElement('meta');
    meta.name = 'description';
    meta.content = description;
    document.head.append(meta);
  }
  if (!document.querySelector('script[data-cartas-schema]')) {
    const schema = document.createElement('script');
    schema.type = 'application/ld+json';
    schema.dataset.cartasSchema = 'true';
    schema.textContent = JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'WebPage',
      name: document.title,
      description,
      url: canonicalUrl,
      isPartOf: { '@type': 'WebSite', name: 'Bom Dia Investidor', url: 'https://bomdiainvestidor.com.br/' },
      about: { '@type': 'Thing', name: title },
    });
    document.head.append(schema);
  }
  if (!document.querySelector('script[data-adsense-cartas]')) {
    const ads = document.createElement('script');
    ads.async = true;
    ads.dataset.adsenseCartas = 'true';
    ads.crossOrigin = 'anonymous';
    ads.src = 'https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-3247427934205365';
    document.head.append(ads);
  }
})();
