// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT

(() => {
  "use strict";

  function openExternal(url) {
    const opened = window.open(url, "_blank", "noopener,noreferrer");
    if (!opened) {
      window.location.href = url;
    }
  }

  function encodedQuery(inputId) {
    const input = document.getElementById(inputId);
    return encodeURIComponent((input && input.value || "").trim());
  }

  const youtubeForm = document.getElementById("youtube-search-form");
  if (youtubeForm) {
    youtubeForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const query = encodedQuery("youtube-search");
      if (!query) return;
      openExternal(`https://www.youtube.com/results?search_query=${query}`);
    });
  }

  const youtubeOpen = document.getElementById("youtube-open");
  if (youtubeOpen) {
    youtubeOpen.addEventListener("click", () => {
      openExternal("https://www.youtube.com/");
    });
  }

  const netflixOpen = document.getElementById("netflix-open");
  if (netflixOpen) {
    netflixOpen.addEventListener("click", () => {
      openExternal("https://www.netflix.com/browse");
    });
  }

  const netflixForm = document.getElementById("netflix-search-form");
  if (netflixForm) {
    netflixForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const query = encodedQuery("netflix-search");
      if (!query) return;
      openExternal(`https://www.netflix.com/search?q=${query}`);
    });
  }
})();
