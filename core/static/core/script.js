function closeAd() {
  const popup = document.getElementById("adPopup");
  if (popup) {
    popup.style.display = "none";
  }
}

function closeDashboardImage() {
  const popup = document.getElementById("dashboardImagePopup");
  if (popup) {
    popup.style.display = "none";
  }
}

window.addEventListener("load", function () {
  const popup = document.getElementById("dashboardImagePopup");

  // safely check navigation type if available
  try {
    const navEntries = performance.getEntriesByType("navigation");
    const isReload = navEntries && navEntries.length > 0 && navEntries[0].type === "reload";

    if (popup && isReload) {
      popup.style.display = "flex";
    }
  } catch (err) {
    console.debug("Navigation timing not available:", err);
  }
});