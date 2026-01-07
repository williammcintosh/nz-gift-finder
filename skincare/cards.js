(() => {
  const mount = document.getElementById("cards");
  if (!mount) {
    return;
  }

  const buildCard = (item) => {
    const link = document.createElement("a");
    link.className = "card";
    link.href = item.href || "#";

    const imgWrap = document.createElement("div");
    imgWrap.className = "card-img";

    const img = document.createElement("img");
    img.src = item.image || "";
    img.alt = item.alt || item.title || "";

    imgWrap.appendChild(img);

    const title = document.createElement("div");
    title.className = "card-title";
    title.textContent = item.title || "";

    const sub = document.createElement("div");
    sub.className = "card-sub";
    sub.textContent = item.sub || "";

    link.appendChild(imgWrap);
    link.appendChild(title);
    link.appendChild(sub);

    return link;
  };

  fetch("./products.json")
    .then((res) => (res.ok ? res.json() : []))
    .then((items) => {
      if (!Array.isArray(items) || items.length === 0) {
        return;
      }
      items.forEach((item) => {
        mount.appendChild(buildCard(item));
      });
    })
    .catch(() => {
      // Silent fail for static hosting or missing catalog.
    });
})();
