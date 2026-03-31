const menuToggle = document.querySelector(".menu-toggle");
const navPanel = document.querySelector(".nav-panel");
const contactForm = document.querySelector(".contact-form");
const siteHeader = document.querySelector(".site-header");
const animatedSections = document.querySelectorAll(".animate-on-scroll, .stagger-children");
const heroFrame = document.querySelector(".hero-image-frame");
const internalLinks = document.querySelectorAll("a[href$='.html']");
const counters = document.querySelectorAll(".counter");
const vehicleFinders = document.querySelectorAll("[data-vehicle-finder]");

document.body.insertAdjacentHTML(
  "afterbegin",
  `
    <div class="mobile-nav-backdrop" aria-hidden="true"></div>
    <div class="page-loader" aria-hidden="true">
      <div class="loader-mark">
        <span class="brand-mark">LM</span>
        <p>Lota Motors</p>
      </div>
    </div>
    <div class="page-transition-overlay" aria-hidden="true"></div>
  `
);

const pageLoader = document.querySelector(".page-loader");
const mobileNavBackdrop = document.querySelector(".mobile-nav-backdrop");

window.requestAnimationFrame(() => {
  document.body.classList.add("page-ready");
});

window.addEventListener("load", () => {
  if (pageLoader) {
    window.setTimeout(() => {
      pageLoader.classList.add("is-hidden");
    }, 260);
  }
});

if (menuToggle && navPanel) {
  const setMenuState = (isOpen) => {
    navPanel.classList.toggle("is-open", isOpen);
    menuToggle.classList.toggle("is-open", isOpen);
    menuToggle.setAttribute("aria-expanded", String(isOpen));
    if (mobileNavBackdrop) {
      mobileNavBackdrop.classList.toggle("is-visible", isOpen);
    }
  };

  menuToggle.addEventListener("click", () => {
    const isOpen = !navPanel.classList.contains("is-open");
    setMenuState(isOpen);
  });

  if (mobileNavBackdrop) {
    mobileNavBackdrop.addEventListener("click", () => setMenuState(false));
  }

  navPanel.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => setMenuState(false));
  });

  window.addEventListener("resize", () => {
    if (window.innerWidth > 820) {
      setMenuState(false);
    }
  });
}

if (siteHeader) {
  const syncHeaderState = () => {
    siteHeader.classList.toggle("is-scrolled", window.scrollY > 18);
  };

  syncHeaderState();
  window.addEventListener("scroll", syncHeaderState, { passive: true });
}

if (animatedSections.length > 0) {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.16 }
  );

  animatedSections.forEach((section) => observer.observe(section));
}

if (counters.length > 0) {
  const runCounter = (element) => {
    const target = Number(element.dataset.target || "0");
    const duration = 1300;
    const start = performance.now();

    const step = (timestamp) => {
      const progress = Math.min((timestamp - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      element.textContent = String(Math.round(target * eased));

      if (progress < 1) {
        window.requestAnimationFrame(step);
      } else {
        element.textContent = String(target);
      }
    };

    window.requestAnimationFrame(step);
  };

  const counterObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          runCounter(entry.target);
          counterObserver.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.4 }
  );

  counters.forEach((counter) => counterObserver.observe(counter));
}

if (heroFrame) {
  const resetTilt = () => {
    heroFrame.style.transform = "rotateY(-4deg) rotateX(1.5deg)";
  };

  heroFrame.addEventListener("mousemove", (event) => {
    const rect = heroFrame.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width;
    const y = (event.clientY - rect.top) / rect.height;
    const rotateY = -4 + (x - 0.5) * 6;
    const rotateX = 1.5 + (0.5 - y) * 5;
    heroFrame.style.transform = `rotateY(${rotateY.toFixed(2)}deg) rotateX(${rotateX.toFixed(2)}deg)`;
  });

  heroFrame.addEventListener("mouseleave", resetTilt);
  resetTilt();
}

internalLinks.forEach((link) => {
  link.addEventListener("click", (event) => {
    const href = link.getAttribute("href");
    const target = link.getAttribute("target");

    if (!href || target === "_blank" || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
      return;
    }

    event.preventDefault();
    document.body.classList.add("is-transitioning");

    window.setTimeout(() => {
      window.location.href = href;
    }, 320);
  });
});

if (contactForm) {
  contactForm.addEventListener("submit", (event) => {
    event.preventDefault();

    const submitButton = contactForm.querySelector("button[type='submit']");
    if (!submitButton) {
      return;
    }

    const originalLabel = submitButton.textContent;
    submitButton.textContent = "Enquiry Received";
    submitButton.disabled = true;

    window.setTimeout(() => {
      submitButton.textContent = originalLabel;
      submitButton.disabled = false;
      contactForm.reset();
    }, 2200);
  });
}

if (vehicleFinders.length > 0) {
  const brandModels = {
    all: [{ value: "all", label: "All models" }],
    subaru: [
      { value: "all", label: "All Subaru models" },
      { value: "outback", label: "Outback" },
      { value: "forester", label: "Forester" },
    ],
    toyota: [
      { value: "all", label: "All Toyota models" },
      { value: "land-cruiser", label: "Land Cruiser" },
      { value: "harrier", label: "Harrier" },
      { value: "prado", label: "Prado" },
    ],
    nissan: [
      { value: "all", label: "All Nissan models" },
      { value: "x-trail", label: "X-Trail" },
      { value: "note", label: "Note" },
      { value: "juke", label: "Juke" },
    ],
    mazda: [
      { value: "all", label: "All Mazda models" },
      { value: "cx-5", label: "CX-5" },
      { value: "atenza", label: "Atenza" },
      { value: "demio", label: "Demio" },
    ],
  };

  vehicleFinders.forEach((finder) => {
    const stockFilterForm = finder.querySelector("[data-stock-filter]");
    const stockGrid = finder.parentElement.querySelector("[data-stock-grid]");
    const stockResults = finder.parentElement.querySelector("[data-stock-results]");
    const stockReset = finder.querySelector("[data-stock-reset]");
    const stockCards = stockGrid ? Array.from(stockGrid.querySelectorAll(".car-card")) : [];
    const brandSelect = stockFilterForm ? stockFilterForm.querySelector("select[name='brand']") : null;
    const modelSelect = stockFilterForm ? stockFilterForm.querySelector("select[name='model']") : null;
    const priceSelect = stockFilterForm ? stockFilterForm.querySelector("select[name='price']") : null;
    const brandButtons = finder.querySelectorAll("[data-brand-option]");

    if (!stockFilterForm || !stockGrid || !brandSelect || !modelSelect || !priceSelect) {
      return;
    }

    const updateModelOptions = (brand) => {
      const nextOptions = brandModels[brand] || brandModels.all;
      const currentValue = modelSelect.value;

      modelSelect.innerHTML = nextOptions
        .map((option) => `<option value="${option.value}">${option.label}</option>`)
        .join("");

      const hasCurrentValue = nextOptions.some((option) => option.value === currentValue);
      modelSelect.value = hasCurrentValue ? currentValue : nextOptions[0].value;
    };

    const syncBrandButtons = (brand) => {
      brandButtons.forEach((button) => {
        button.classList.toggle("is-active", button.dataset.brandOption === brand);
      });
    };

    const syncStockResults = () => {
      const selectedBrand = brandSelect.value;
      const selectedModel = modelSelect.value;
      const selectedPrice = priceSelect.value;

      let visibleCount = 0;

      stockCards.forEach((card) => {
        const matchesBrand = selectedBrand === "all" || card.dataset.brand === selectedBrand;
        const matchesModel = selectedModel === "all" || card.dataset.model === selectedModel;
        const matchesPrice = selectedPrice === "all" || card.dataset.price === selectedPrice;
        const isVisible = matchesBrand && matchesModel && matchesPrice;

        card.classList.toggle("is-hidden", !isVisible);

        if (isVisible) {
          visibleCount += 1;
        }
      });

      if (stockResults) {
        stockResults.textContent =
          visibleCount === 1 ? "Showing 1 vehicle" : `Showing ${visibleCount} vehicles`;
      }
    };

    brandButtons.forEach((button) => {
      button.addEventListener("click", () => {
        const nextBrand = button.dataset.brandOption || "all";
        brandSelect.value = nextBrand;
        updateModelOptions(nextBrand);
        syncBrandButtons(nextBrand);
        syncStockResults();
      });
    });

    brandSelect.addEventListener("change", () => {
      updateModelOptions(brandSelect.value);
      syncBrandButtons(brandSelect.value);
      syncStockResults();
    });

    modelSelect.addEventListener("change", syncStockResults);
    priceSelect.addEventListener("change", syncStockResults);

    if (stockReset) {
      stockReset.addEventListener("click", () => {
        stockFilterForm.reset();
        updateModelOptions("all");
        syncBrandButtons("all");
        syncStockResults();
      });
    }

    updateModelOptions(brandSelect.value);
    syncBrandButtons(brandSelect.value);
    syncStockResults();
  });
}
