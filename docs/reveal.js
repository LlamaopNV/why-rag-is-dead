// Progressive enhancement: scroll-reveal for [data-reveal] elements and
// fill the token bars when the receipt scrolls into view. Both paths degrade
// to the final state instantly under prefers-reduced-motion. No scroll listeners.

const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const reveals = document.querySelectorAll("[data-reveal]");
const bars = document.querySelectorAll(".bar[data-target]");
const fill = (el) => { el.style.width = el.getAttribute("data-target"); };

if (reduce) {
  reveals.forEach((el) => el.setAttribute("data-shown", ""));
  bars.forEach(fill);
} else {
  const revealObserver = new IntersectionObserver((entries, obs) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      entry.target.setAttribute("data-shown", "");
      obs.unobserve(entry.target);
    }
  }, { threshold: 0.18, rootMargin: "0px 0px -8% 0px" });
  reveals.forEach((el) => revealObserver.observe(el));

  const barObserver = new IntersectionObserver((entries, obs) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      fill(entry.target);
      obs.unobserve(entry.target);
    }
  }, { threshold: 0.4 });
  bars.forEach((el) => barObserver.observe(el));
}
